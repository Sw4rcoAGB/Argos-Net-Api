from fastapi import HTTPException, status

from App.models.boveda import Boveda
from App.models.cosecha import Cosecha
from App.services.web3_client import get_web3_client
from App.utils.logger import MyLogger

logger = MyLogger.__call__().get_logger()

ORACLE_STATE_NAMES = {
    0: "PLANTED",
    1: "ACTIVE",
    2: "MATURE",
    3: "LIQUIDATED",
    4: "DEFAULTED",
}


async def avanzar_estado(
    cosecha_id: int,
    exito: bool,
    logger_message: str,
) -> dict:
    """
    Avanza el estado del ciclo de vida del cultivo en el oráculo MockOracle.
    - exito=True  cuando el estado es MATURE → dispara LIQUIDATED
    - exito=False cuando el estado es MATURE → dispara DEFAULTED
    - En estados anteriores a MATURE simplemente avanza al siguiente estado.
    """
    w3 = get_web3_client()

    boveda = await Boveda.get_or_none(cosecha_id=cosecha_id)
    if not boveda or not boveda.vault_address:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Bóveda no encontrada o sin vault_address")

    cosecha = await Cosecha.get_or_none(id=cosecha_id)
    if not cosecha:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cosecha no encontrada")

    if boveda.estado in ("LIQUIDATED", "DEFAULTED"):
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"La bóveda ya está en estado terminal: {boveda.estado}")

    if not w3.oracle_contract:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contrato MockOracle no disponible — verifica ORACLE_CONTRACT_ADDRESS en .env"
        )

    tx_hash = await w3.send_transaction(
        lambda: w3.oracle_contract.functions.advanceState(boveda.vault_address, exito)
    )
    receipt = await w3.wait_for_receipt(tx_hash)
    if receipt.get("status") != 1:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="La transacción del oráculo falló en la blockchain")

    new_estado = _determinar_nuevo_estado(receipt, w3, boveda.vault_address, boveda.estado, exito)

    boveda.estado  = new_estado
    cosecha.estado = new_estado
    await boveda.save()
    await cosecha.save()

    logger.info(f"{logger_message} [SUCCESS] Estado avanzado a {new_estado} para cosecha {cosecha_id}")
    return {
        "cosecha_id":   cosecha_id,
        "vault_address": boveda.vault_address,
        "nuevo_estado":  new_estado,
        "tx_hash":       tx_hash,
    }


def _determinar_nuevo_estado(receipt, w3, vault_address: str, estado_actual: str, exito: bool) -> str:
    """Determina el nuevo estado leyendo los eventos del CropVault."""
    vault = w3.get_vault_contract(vault_address)
    try:
        liq_logs = vault.events.CropLiquidated().process_receipt(receipt)
        if liq_logs:
            return "LIQUIDATED"
    except Exception:
        pass
    try:
        def_logs = vault.events.CropDefaulted().process_receipt(receipt)
        if def_logs:
            return "DEFAULTED"
    except Exception:
        pass

    state_progression = {
        "PENDIENTE": "MINTED",
        "MINTED":    "ACTIVE",
        "OPEN":      "ACTIVE",   # boveda recién abierta, primer avance del oracle
        "FUNDED":    "ACTIVE",   # vault financiado, oracle sigue avanzando
        "ACTIVE":    "MATURE",
        "MATURE":    "LIQUIDATED" if exito else "DEFAULTED",
    }
    return state_progression.get(estado_actual, estado_actual)


async def solicitar_resolucion_chainlink(
    cosecha_id: int,
    lat: str,
    lon: str,
    logger_message: str,
) -> dict:
    """
    Llama ChainlinkOracle.requestWeatherData() para resolver una bóveda en estado MATURE
    consultando datos reales de precipitación vía Chainlink Functions (Open-Meteo).

    Requiere:
      - Oracle desplegado como ChainlinkOracle.sol (no MockOracle)
      - ABI en contracts/abis/ChainlinkOracle.json
      - Suscripción Chainlink Functions activa con LINK suficiente
      - ORACLE_CONTRACT_ADDRESS en .env apuntando al ChainlinkOracle desplegado

    El callback fulfillRequest() llega en ~30s y resuelve LIQUIDATED o DEFAULTED.
    El event listener existente (poll 15s) detecta el cambio y actualiza PostgreSQL.
    """
    w3 = get_web3_client()

    boveda = await Boveda.get_or_none(cosecha_id=cosecha_id)
    if not boveda or not boveda.vault_address:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Bóveda no encontrada o sin vault_address")

    if boveda.estado != "MATURE":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"La bóveda debe estar en estado MATURE para usar Chainlink. Estado actual: {boveda.estado}",
        )

    if not w3.oracle_contract:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contrato Oracle no disponible — verifica ORACLE_CONTRACT_ADDRESS en .env",
        )

    # Verificar que el contrato expone requestWeatherData (ChainlinkOracle, no MockOracle)
    chainlink_fn = getattr(w3.oracle_contract.functions, "requestWeatherData", None)
    if chainlink_fn is None:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "El contrato Oracle actual es MockOracle y no soporta Chainlink Functions. "
                "Despliega ChainlinkOracle.sol en Remix y actualiza ORACLE_CONTRACT_ADDRESS en .env."
            ),
        )

    tx_hash = await w3.send_transaction(
        lambda: w3.oracle_contract.functions.requestWeatherData(boveda.vault_address, lat, lon)
    )
    receipt = await w3.wait_for_receipt(tx_hash)
    if receipt.get("status") != 1:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="La transacción Chainlink falló en la blockchain")

    logger.info(
        "%s [CHAINLINK] requestWeatherData enviado para cosecha %d vault=%s lat=%s lon=%s tx=%s",
        logger_message, cosecha_id, boveda.vault_address, lat, lon, tx_hash,
    )
    return {
        "cosecha_id":    cosecha_id,
        "vault_address": boveda.vault_address,
        "estado_actual": boveda.estado,
        "tx_hash":       tx_hash,
        "lat":           lat,
        "lon":           lon,
        "status":        "pending_chainlink",
        "mensaje":       "Solicitud enviada a Chainlink. El oracle resolverá en ~30 segundos según datos reales de precipitación.",
    }


async def obtener_estado_oracle(
    vault_address: str,
    logger_message: str,
) -> dict:
    """Lee el estado actual del oráculo para un vault_address en el contrato MockOracle."""
    w3 = get_web3_client()

    if not w3.oracle_contract:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contrato MockOracle no disponible — verifica ORACLE_CONTRACT_ADDRESS en .env"
        )

    oracle_state = await w3.call_contract(
        lambda: w3.oracle_contract.functions.getState(vault_address)
    )
    logger.info(
        f"{logger_message} [SUCCESS] Estado oráculo para vault={vault_address}: "
        f"{ORACLE_STATE_NAMES.get(oracle_state)}"
    )
    return {
        "vault_address":       vault_address,
        "oracle_state":        oracle_state,
        "oracle_state_nombre": ORACLE_STATE_NAMES.get(oracle_state, "DESCONOCIDO"),
    }
