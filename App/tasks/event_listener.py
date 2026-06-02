"""
Background task que sincroniza el estado de las bóvedas entre la blockchain y Postgres.
Se ejecuta como una tarea asyncio en el lifespan de FastAPI.
Cada 15 segundos consulta el estado on-chain de cada bóveda activa y actualiza Postgres si difiere.
"""

import asyncio

from App.utils.logger import MyLogger

logger = MyLogger.__call__().get_logger()

VAULT_STATUS_MAP = {
    0: "OPEN",
    1: "FUNDED",
    2: "ACTIVE",
    3: "LIQUIDATED",
    4: "DEFAULTED",
}


async def poll_vault_events(interval_seconds: int = 15):
    """
    Polling periódico de eventos on-chain para sincronizar Postgres.
    Se ejecuta en segundo plano durante toda la vida del servidor.
    """
    # Importaciones diferidas para evitar importaciones circulares en el startup
    from App.models.boveda import Boveda
    from App.models.cosecha import Cosecha
    from App.services.web3_client import get_web3_client

    logger.info("Event listener iniciado — sincronizando estados de bóvedas cada %ds", interval_seconds)

    while True:
        try:
            await _sync_all_vaults(get_web3_client, Boveda, Cosecha)
        except Exception as e:
            logger.error("Event listener: error inesperado en el loop: %s", e)

        await asyncio.sleep(interval_seconds)


async def _sync_all_vaults(get_web3_client_fn, Boveda, Cosecha):
    """Sincroniza todas las bóvedas activas con el estado on-chain."""
    active_bovedas = await Boveda.filter(
        estado__in=["OPEN", "FUNDED", "ACTIVE"]
    ).prefetch_related("cosecha").all()

    if not active_bovedas:
        return

    w3 = get_web3_client_fn()
    if not w3.w3.is_connected():
        logger.warning("Event listener: nodo blockchain no disponible, omitiendo sync")
        return

    for boveda in active_bovedas:
        if not boveda.vault_address:
            continue
        await _sync_single_vault(w3, boveda)


async def _sync_single_vault(w3, boveda):
    """Sincroniza el estado de una bóveda individual leyendo CropVault por su vault_address."""
    try:
        vault = w3.get_vault_contract(boveda.vault_address)
        vault_config = await w3.call_contract(
            lambda: vault.functions.getVaultState()
        )
        chain_status = vault_config[6]  # VaultStatus enum index
        chain_estado = VAULT_STATUS_MAP.get(chain_status)

        if chain_estado and chain_estado != boveda.estado:
            logger.info(
                "Event listener: bóveda %s %s → %s",
                boveda.id, boveda.estado, chain_estado
            )
            boveda.estado = chain_estado
            await boveda.save()

            cosecha = await boveda.cosecha
            if cosecha and cosecha.estado != chain_estado:
                cosecha.estado = chain_estado
                await cosecha.save()

    except Exception as e:
        logger.error("Event listener: error al sincronizar bóveda %s (vault_address=%s): %s",
                     boveda.id, boveda.vault_address, e)
