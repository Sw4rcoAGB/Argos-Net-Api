"""
Singleton Web3 client con bindings al contrato unificado AgroNest.
Todas las interacciones con la blockchain van a través de este módulo.
Las llamadas bloqueantes de Web3.py se envuelven en asyncio.to_thread
para no bloquear el event loop de FastAPI.

Resolución de addresses en orden de prioridad:
  1. contracts/deployed_addresses.<network>.json  (generado por deploy — dev local o sepolia)
  2. Variables de entorno en .env                 (staging / producción)
"""

import asyncio
import json
from functools import lru_cache
from pathlib import Path

from web3 import Web3

import App.core.settings as config
from App.utils.logger import MyLogger

logger = MyLogger.__call__().get_logger()

def _load_deployed_addresses() -> dict:
    """
    Busca el archivo deployed_addresses adecuado según la red configurada en RPC_URL.

    Prioridad:
      1. deployed_addresses.<network>.json  (ej: sepolia, polygon)
      2. deployed_addresses.json            SOLO si RPC_URL apunta a localhost/127.0.0.1
      3. dict vacío → usa los valores de .env
    """
    s = config.settings
    is_local_rpc = "localhost" in s.rpc_url or "127.0.0.1" in s.rpc_url

    rpc = s.rpc_url.lower()
    if "sepolia" in rpc:
        network_hint = "sepolia"
    elif "polygon" in rpc or "matic" in rpc:
        network_hint = "polygon"
    elif "mainnet" in rpc:
        network_hint = "mainnet"
    else:
        network_hint = None

    candidates = []
    if network_hint:
        candidates += [
            Path(f"./contracts/deployed_addresses.{network_hint}.json"),
            Path(f"../contracts/deployed_addresses.{network_hint}.json"),
        ]
    if is_local_rpc:
        candidates += [
            Path("./contracts/deployed_addresses.json"),
            Path("../contracts/deployed_addresses.json"),
            Path("./deployed_addresses.json"),
        ]

    for candidate in candidates:
        if not candidate.exists():
            continue
        with open(candidate) as f:
            data = json.load(f)
        file_network = data.get("NETWORK", "?")
        logger.info(
            "Web3: usando addresses de %s (red: %s, desplegado: %s)",
            candidate.resolve(),
            file_network,
            data.get("DEPLOYED_AT", "?"),
        )
        return data

    logger.info(
        "Web3: ningún deployed_addresses*.json aplicable para RPC_URL=%s — usando valores de .env",
        s.rpc_url,
    )
    return {}


class Web3Client:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        s = config.settings

        deployed = _load_deployed_addresses()
        crop_address   = deployed.get("CROP_CONTRACT_ADDRESS")   or s.agronest_contract_address
        oracle_address = deployed.get("ORACLE_CONTRACT_ADDRESS") or ""
        usdc_address   = deployed.get("USDC_CONTRACT_ADDRESS")   or s.usdc_contract_address

        self.w3 = Web3(Web3.HTTPProvider(s.rpc_url, request_kwargs={"timeout": 30}))

        if not self.w3.is_connected():
            logger.warning("Web3: no se pudo conectar al nodo en %s — funciones blockchain no disponibles", s.rpc_url)

        if s.api_private_key:
            self.api_account = self.w3.eth.account.from_key(s.api_private_key)
            logger.info("Web3: API wallet cargado: %s", self.api_account.address)
        else:
            self.api_account = None
            logger.warning("Web3: API_PRIVATE_KEY no configurada — operaciones de escritura no disponibles")

        self._abi_dir = Path(s.contract_abi_dir)

        self.crop_contract   = self._load_contract(crop_address,   "AgroNestCrop.json")
        self.oracle_contract = self._load_contract(oracle_address, "MockOracle.json")
        self.usdc_contract   = self._load_contract(usdc_address,   "MockUSDC.json")

        self._initialized = True

    def get_vault_contract(self, vault_address: str):
        """Carga una instancia de CropVault desde su address desplegada."""
        abi = self._load_abi("CropVault.json")
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(vault_address), abi=abi
        )

    def assert_connected(self):
        """Lanza HTTPException 503 si el nodo Ethereum no está disponible."""
        from fastapi import HTTPException, status as http_status
        try:
            self.w3.eth.block_number
        except Exception as e:
            raise HTTPException(
                http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Nodo blockchain no disponible ({type(e).__name__}). Verifica RPC_URL en .env.",
            )

    def _load_abi(self, relative_path: str) -> list:
        full_path = self._abi_dir / relative_path
        if not full_path.exists():
            logger.warning("Web3: ABI no encontrado en %s", full_path)
            return []
        with open(full_path) as f:
            artifact = json.load(f)
        return artifact.get("abi", [])

    def _load_contract(self, address: str, abi_path: str):
        abi = self._load_abi(abi_path)
        if not address or not abi:
            return None
        try:
            return self.w3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=abi
            )
        except Exception as e:
            logger.warning("Web3: No se pudo cargar contrato %s: %s", abi_path, e)
            return None

    def load_artifact(self, filename: str) -> dict:
        """Carga el artifact completo (abi + bytecode) de contracts/abis/."""
        full_path = self._abi_dir / filename
        if not full_path.exists():
            raise FileNotFoundError(f"Artifact no encontrado: {full_path}")
        with open(full_path) as f:
            return json.load(f)

    async def send_transaction(self, build_tx_func) -> str:
        """
        Construye, firma y envía una transacción. Retorna el tx_hash como hex string.
        Envuelve las llamadas bloqueantes en asyncio.to_thread.
        """
        if not self.api_account:
            raise RuntimeError("API_PRIVATE_KEY no configurada — no se pueden firmar transacciones")

        def _send():
            nonce     = self.w3.eth.get_transaction_count(self.api_account.address, "pending")
            gas_price = max(self.w3.eth.gas_price, self.w3.to_wei("2", "gwei"))
            tx = build_tx_func().build_transaction({
                "from":     self.api_account.address,
                "nonce":    nonce,
                "gas":      500_000,
                "gasPrice": gas_price,
                "chainId":  config.settings.chain_id,
            })
            signed   = self.api_account.sign_transaction(tx)
            tx_hash  = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            return tx_hash.hex()

        return await asyncio.to_thread(_send)

    async def deploy_contract(self, abi: list, bytecode: str, *constructor_args) -> str:
        """Despliega un nuevo contrato y retorna su dirección."""
        if not self.api_account:
            raise RuntimeError("API_PRIVATE_KEY no configurada")

        def _deploy():
            factory   = self.w3.eth.contract(abi=abi, bytecode=bytecode)
            nonce     = self.w3.eth.get_transaction_count(self.api_account.address, "pending")
            gas_price = max(self.w3.eth.gas_price, self.w3.to_wei("2", "gwei"))
            tx        = factory.constructor(*constructor_args).build_transaction({
                "from":     self.api_account.address,
                "nonce":    nonce,
                "gas":      3_000_000,
                "gasPrice": gas_price,
                "chainId":  config.settings.chain_id,
            })
            signed  = self.api_account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            return receipt["contractAddress"]

        return await asyncio.to_thread(_deploy)

    async def wait_for_receipt(self, tx_hash: str) -> dict:
        """Espera la confirmación de una transacción y retorna el receipt."""
        def _wait():
            return dict(self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120))
        return await asyncio.to_thread(_wait)

    async def call_contract(self, call_func) -> any:
        """Llamada de solo lectura a un contrato (no consume gas)."""
        def _call():
            return call_func().call()
        return await asyncio.to_thread(_call)


@lru_cache(maxsize=1)
def get_web3_client() -> Web3Client:
    return Web3Client()


def reset_web3_client() -> None:
    """
    Limpia el singleton para que se reinicialice con la configuración actual.
    Útil después de un nuevo deploy (las addresses cambian).
    """
    get_web3_client.cache_clear()
    Web3Client._instance = None
