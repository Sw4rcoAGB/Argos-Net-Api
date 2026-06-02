from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status

import App.core.settings as config
from App.models.boveda import Boveda
from App.models.cosecha import Cosecha
from App.schemas.boveda import AbrirBovedaSchema, EstadoChainBovedaSchema, PaginacionBovedaSchema, RespuestaBovedaSchema
from App.services.web3_client import get_web3_client
from App.utils.logger import MyLogger

logger = MyLogger.__call__().get_logger()

VAULT_STATUS_NAMES = {
    0: "OPEN",
    1: "FUNDED",
    2: "ACTIVE",
    3: "LIQUIDATED",
    4: "DEFAULTED",
}


async def abrir_boveda(
    data: AbrirBovedaSchema,
    logger_message: str,
) -> RespuestaBovedaSchema:
    """
    Abre una bóveda de financiamiento para una cosecha MINTED.
    Despliega bCROPToken + CropVault, configura permisos, abre la ronda y registra en el oráculo.
    """
    w3 = get_web3_client()
    w3.assert_connected()

    if not w3.crop_contract or not w3.oracle_contract or not w3.usdc_contract:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contratos no disponibles — verifica CROP/ORACLE/USDC_CONTRACT_ADDRESS en .env"
        )

    cosecha = await Cosecha.get_or_none(id=data.cosecha_id, eliminado=False)
    if not cosecha:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cosecha no encontrada")
    if cosecha.estado != "MINTED":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"La cosecha debe estar en estado MINTED para abrir una bóveda. Estado actual: {cosecha.estado}"
        )

    existing = await Boveda.get_or_none(cosecha_id=data.cosecha_id)
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Ya existe una bóveda para esta cosecha")

    fecha_limite = datetime.utcnow() + timedelta(days=data.plazo_dias)
    funding_goal = int(cosecha.capital_requerido * 10 ** 6)
    deadline_ts  = int(fecha_limite.timestamp())

    # ── 1. Cargar artifacts para despliegue ─────────────────────────────────
    bcrop_artifact  = w3.load_artifact("bCROPToken.json")
    vault_artifact  = w3.load_artifact("CropVault.json")

    # ── 2. Desplegar bCROPToken ──────────────────────────────────────────────
    bcrop_address = await w3.deploy_contract(
        bcrop_artifact["abi"],
        bcrop_artifact["bytecode"],
        w3.api_account.address,  # initialOwner
    )
    logger.info(f"{logger_message} bCROPToken desplegado en {bcrop_address}")

    # ── 3. Desplegar CropVault ───────────────────────────────────────────────
    vault_address = await w3.deploy_contract(
        vault_artifact["abi"],
        vault_artifact["bytecode"],
        w3.api_account.address,       # owner
        w3.usdc_contract.address,     # USDC
        w3.crop_contract.address,     # NFT crop
        w3.oracle_contract.address,   # oracle
    )
    logger.info(f"{logger_message} CropVault desplegado en {vault_address}")

    vault_contract = w3.get_vault_contract(vault_address)
    bcrop_contract = w3.w3.eth.contract(
        address=w3.w3.to_checksum_address(bcrop_address),
        abi=bcrop_artifact["abi"],
    )

    # ── 4. Autorizar al vault para mintear/quemar bCROP ──────────────────────
    await w3.send_transaction(
        lambda: bcrop_contract.functions.setVault(vault_address)
    )

    # ── 5. Aprobar al vault para transferir el NFT colateral ─────────────────
    await w3.send_transaction(
        lambda: w3.crop_contract.functions.approve(vault_address, cosecha.nft_token_id)
    )

    # ── 6. Abrir la ronda de financiamiento ──────────────────────────────────
    await w3.send_transaction(
        lambda: vault_contract.functions.openRound(
            cosecha.nft_token_id,
            funding_goal,
            deadline_ts,
            data.porcentaje_reserva,
            data.porcentaje_rendimiento,
            bcrop_address,
            w3.api_account.address,  # farmer = API wallet (custodial)
        )
    )

    # ── 7. Registrar en el oráculo ────────────────────────────────────────────
    await w3.send_transaction(
        lambda: w3.oracle_contract.functions.registerVault(vault_address)
    )

    boveda = Boveda(
        cosecha_id=data.cosecha_id,
        vault_id=None,                          # ya no aplica en arquitectura split
        vault_address=vault_address,
        bcrop_address=bcrop_address,
        meta_financiamiento=cosecha.capital_requerido,
        plazo_dias=data.plazo_dias,
        porcentaje_reserva=data.porcentaje_reserva,
        porcentaje_rendimiento=data.porcentaje_rendimiento,
        fecha_limite=fecha_limite,
        estado="OPEN",
        tx_hash_open=vault_address,             # usamos la address como referencia
    )
    await boveda.save()

    cosecha.estado = "ACTIVE"
    await cosecha.save()

    logger.info(f"{logger_message} [SUCCESS] Bóveda abierta en {vault_address} para cosecha {data.cosecha_id}")
    return RespuestaBovedaSchema.model_validate(boveda)


async def obtener_boveda(
    boveda_id: int,
    logger_message: str,
) -> RespuestaBovedaSchema:
    boveda = await Boveda.get_or_none(id=boveda_id)
    if not boveda:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Bóveda no encontrada")
    logger.info(f"{logger_message} [SUCCESS] Bóveda {boveda_id} obtenida")
    return RespuestaBovedaSchema.model_validate(boveda)


async def obtener_boveda_por_cosecha(
    cosecha_id: int,
    logger_message: str,
) -> RespuestaBovedaSchema:
    boveda = await Boveda.get_or_none(cosecha_id=cosecha_id)
    if not boveda:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No existe bóveda para esta cosecha")
    logger.info(f"{logger_message} [SUCCESS] Bóveda para cosecha {cosecha_id} obtenida")
    return RespuestaBovedaSchema.model_validate(boveda)


async def obtener_todas_bovedas(
    logger_message: str,
    estado: Optional[str] = None,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
) -> PaginacionBovedaSchema:
    query = Boveda.all() if estado is None else Boveda.filter(estado=estado)
    total = await query.count()

    if page and per_page:
        offset = (page - 1) * per_page
        bovedas = await query.offset(offset).limit(per_page)
        pages = (total + per_page - 1) // per_page
    else:
        bovedas = await query
        pages = None

    logger.info(f"{logger_message} [SUCCESS] {total} bóvedas obtenidas")
    return PaginacionBovedaSchema(
        page=page,
        per_page=per_page,
        total=total,
        pages=pages,
        data=[RespuestaBovedaSchema.model_validate(b) for b in bovedas],
    )


async def obtener_estado_chain(
    boveda_id: int,
    logger_message: str,
) -> EstadoChainBovedaSchema:
    """Lee el estado actual de la bóveda directamente desde el contrato CropVault."""
    boveda = await Boveda.get_or_none(id=boveda_id)
    if not boveda or not boveda.vault_address:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Bóveda no encontrada o sin vault_address")

    w3 = get_web3_client()
    vault = w3.get_vault_contract(boveda.vault_address)

    # getVaultState() retorna VaultConfig struct:
    # (cropTokenId, fundingGoal, fundingDeadline, reservePercent, yieldPercent, totalRaised, status)
    vault_config = await w3.call_contract(lambda: vault.functions.getVaultState())
    status_idx = vault_config[6]  # VaultStatus enum index

    logger.info(f"{logger_message} [SUCCESS] Estado chain de bóveda {boveda_id}: {VAULT_STATUS_NAMES.get(status_idx)}")
    return EstadoChainBovedaSchema(
        vault_address=boveda.vault_address,
        status_chain=status_idx,
        status_nombre=VAULT_STATUS_NAMES.get(status_idx, "DESCONOCIDO"),
        total_raised_usdc=Decimal(vault_config[5]) / 10 ** 6,
        funding_goal_usdc=Decimal(vault_config[1]) / 10 ** 6,
        funding_deadline=datetime.fromtimestamp(vault_config[2]),
        reserve_percent=vault_config[3],
        yield_percent=vault_config[4],
    )
