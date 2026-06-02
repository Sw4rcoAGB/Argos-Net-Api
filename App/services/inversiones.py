from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, Query, status

from App.models.boveda import Boveda
from App.models.cosecha import Cosecha
from App.models.inversion import Inversion
from App.models.usuario import Usuario
from App.schemas.inversiones import InvertirSchema, PaginacionInversionesSchema, RespuestaInversionSchema
from App.services.web3_client import get_web3_client
from App.utils.logger import MyLogger

logger = MyLogger.__call__().get_logger()


async def invertir(
    user: Usuario,
    data: InvertirSchema,
    logger_message: str,
) -> RespuestaInversionSchema:
    """
    Realiza una inversión en nombre del usuario autenticado:
    1. Valida que la bóveda esté OPEN
    2. Aprueba al contrato AgroNest para gastar USDC del API wallet
    3. Llama agronest.deposit(vaultId, amount, investor_wallet)
    4. Guarda la Inversion en Postgres
    """
    w3 = get_web3_client()
    w3.assert_connected()

    cosecha = await Cosecha.get_or_none(id=data.cosecha_id, eliminado=False)
    if not cosecha:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cosecha no encontrada")

    boveda = await Boveda.get_or_none(cosecha_id=data.cosecha_id, estado="OPEN")
    if not boveda or not boveda.vault_address:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="La bóveda no está abierta para inversiones")

    if data.monto_usdc <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="El monto debe ser mayor a cero")

    amount_wei   = int(data.monto_usdc * 10 ** 6)
    vault = w3.get_vault_contract(boveda.vault_address)

    # Aprobar al CropVault para gastar USDC del API wallet
    await w3.send_transaction(
        lambda: w3.usdc_contract.functions.approve(boveda.vault_address, amount_wei)
    )

    # Depositar: CropVault toma USDC del API wallet y acredita bCROP al inversor
    tx_hash = await w3.send_transaction(
        lambda: vault.functions.deposit(
            amount_wei,
            w3.api_account.address,  # investor = API wallet (custodial)
        )
    )
    receipt = await w3.wait_for_receipt(tx_hash)
    if receipt.get("status") != 1:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="La transacción de depósito falló en la blockchain")

    inversion = Inversion(
        inversor_id=user.id,
        cosecha_id=data.cosecha_id,
        monto_usdc=data.monto_usdc,
        bcrop_recibido=data.monto_usdc,  # ratio 1:1
        tx_hash_deposit=tx_hash,
    )
    await inversion.save()

    boveda.total_recaudado = Decimal(str(boveda.total_recaudado)) + data.monto_usdc
    await boveda.save()

    logger.info(f"{logger_message} [SUCCESS] Inversión {inversion.id} registrada: {data.monto_usdc} USDC en cosecha {data.cosecha_id}")
    return RespuestaInversionSchema.model_validate(inversion)


async def reclamar_retorno(
    user: Usuario,
    inversion_id: int,
    logger_message: str,
) -> RespuestaInversionSchema:
    """
    Reclama el retorno de una inversión:
    1. Valida que la inversión pertenezca al usuario y no esté reclamada
    2. Valida que la bóveda esté LIQUIDATED o DEFAULTED
    3. Llama agronest.claimReturns(vaultId, investor) on-chain
    4. Actualiza la Inversion en Postgres con el monto reclamado
    """
    w3 = get_web3_client()
    w3.assert_connected()

    inversion = await Inversion.get_or_none(id=inversion_id, inversor_id=user.id)
    if not inversion:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Inversión no encontrada")
    if inversion.reclamado:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="El retorno de esta inversión ya fue reclamado")

    boveda = await Boveda.get_or_none(cosecha_id=inversion.cosecha_id)
    if not boveda or not boveda.vault_address:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Bóveda asociada no encontrada")
    if boveda.estado not in ("LIQUIDATED", "DEFAULTED"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"La bóveda no está en estado de liquidación. Estado actual: {boveda.estado}"
        )

    vault = w3.get_vault_contract(boveda.vault_address)
    tx_hash = await w3.send_transaction(
        lambda: vault.functions.claimReturns(
            w3.api_account.address,
        )
    )
    receipt = await w3.wait_for_receipt(tx_hash)
    if receipt.get("status") != 1:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="La transacción de reclamo falló en la blockchain")

    # Extraer el monto del evento ReturnsClaimed
    payout = Decimal(str(inversion.monto_usdc))
    try:
        logs = vault.events.ReturnsClaimed().process_receipt(receipt)
        if logs:
            payout = Decimal(logs[0]["args"]["usdcAmount"]) / 10 ** 6
    except Exception:
        pass

    inversion.reclamado       = True
    inversion.monto_reclamado = payout
    inversion.tx_hash_claim   = tx_hash
    await inversion.save()

    logger.info(f"{logger_message} [SUCCESS] Inversión {inversion_id} reclamada: {payout} USDC")
    return RespuestaInversionSchema.model_validate(inversion)


async def obtener_mis_inversiones(
    user: Usuario,
    logger_message: str,
    page: Optional[int] = Query(None, ge=1),
    per_page: Optional[int] = Query(None, ge=1, le=100),
) -> PaginacionInversionesSchema:
    query = Inversion.filter(inversor_id=user.id)
    total = await query.count()

    if page and per_page:
        offset = (page - 1) * per_page
        inversiones = await query.offset(offset).limit(per_page)
        pages = (total + per_page - 1) // per_page
    else:
        inversiones = await query
        pages = None

    logger.info(f"{logger_message} [SUCCESS] {total} inversiones obtenidas para usuario {user.id}")
    return PaginacionInversionesSchema(
        page=page,
        per_page=per_page,
        total=total,
        pages=pages,
        data=[RespuestaInversionSchema.model_validate(i) for i in inversiones],
    )


async def obtener_inversiones_cosecha(
    cosecha_id: int,
    logger_message: str,
) -> list[RespuestaInversionSchema]:
    inversiones = await Inversion.filter(cosecha_id=cosecha_id).all()
    logger.info(f"{logger_message} [SUCCESS] Inversiones de cosecha {cosecha_id} obtenidas")
    return [RespuestaInversionSchema.model_validate(i) for i in inversiones]
