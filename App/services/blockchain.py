import asyncio
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from web3 import Web3

from App.schemas.blockchain import BalanceSchema, TxStatusSchema
from App.services.web3_client import get_web3_client
from App.utils.logger import MyLogger

logger = MyLogger.__call__().get_logger()


def _assert_connected():
    """
    Lanza 503 si el nodo Ethereum no está disponible o el RPC no responde.
    Hace una llamada real (eth_block_number) para verificar conectividad efectiva.
    """
    w3 = get_web3_client()

    try:
        w3.w3.eth.block_number  # llamada real al RPC
    except Exception as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nodo blockchain no disponible ({type(e).__name__}). Verifica RPC_URL en .env.",
        )

    return w3


async def get_balances(
    address: str,
    logger_message: str,
    vault_id: Optional[int] = None,
) -> BalanceSchema:
    """Retorna balances de ETH, USDC y opcionalmente bCROP (por vault_id) para una dirección."""
    w3 = _assert_connected()

    try:
        checksum_addr = Web3.to_checksum_address(address)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Dirección Ethereum inválida")

    def _query():
        eth_wei = w3.w3.eth.get_balance(checksum_addr)

        usdc_wei = 0
        if w3.usdc_contract:
            try:
                usdc_wei = w3.usdc_contract.functions.balanceOf(checksum_addr).call()
            except Exception as e:
                logger.warning("No se pudo obtener balance USDC para %s: %s", address, e)

        return eth_wei, usdc_wei, None

    eth_wei, usdc_wei, bcrop_wei = await asyncio.to_thread(_query)
    logger.info("%s [SUCCESS] Balances obtenidos para %s", logger_message, address)

    return BalanceSchema(
        address=address,
        eth_balance=Decimal(str(w3.w3.from_wei(eth_wei, "ether"))),
        usdc_balance=Decimal(usdc_wei) / 10 ** 6,
        bcrop_balance=Decimal(bcrop_wei) / 10 ** 6 if bcrop_wei is not None else None,
    )


async def get_tx_status(tx_hash: str, logger_message: str) -> TxStatusSchema:
    """Consulta el estado de una transacción por su hash."""
    w3 = _assert_connected()

    def _query():
        try:
            receipt = w3.w3.eth.get_transaction_receipt(tx_hash)
            if receipt is None:
                return "pending", None, None
            estado = "confirmed" if receipt["status"] == 1 else "failed"
            return estado, receipt["blockNumber"], receipt["gasUsed"]
        except Exception:
            return "pending", None, None

    estado, block_num, gas_used = await asyncio.to_thread(_query)
    logger.info("%s [SUCCESS] Estado de tx %s: %s", logger_message, tx_hash, estado)

    return TxStatusSchema(
        tx_hash=tx_hash,
        status=estado,
        block_number=block_num,
        gas_used=gas_used,
    )


async def get_api_wallet_info(logger_message: str) -> BalanceSchema:
    """Retorna información del API wallet (dirección y balances)."""
    w3 = _assert_connected()

    if not w3.api_account:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API wallet no configurado. Agrega API_PRIVATE_KEY en .env",
        )

    return await get_balances(w3.api_account.address, logger_message)
