import uuid
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from fastapi import Query

from App.models.cosecha import Cosecha
from App.models.usuario import Usuario
from App.schemas.cosechas import CrearCosechaSchema, RespuestaCosechaSchema, PaginacionCosechasSchema
from App.services.web3_client import get_web3_client
from App.utils.logger import MyLogger

logger = MyLogger.__call__().get_logger()


async def registrar_cosecha(
    user: Usuario,
    data: CrearCosechaSchema,
    logger_message: str,
) -> RespuestaCosechaSchema:
    """
    Registra una nueva cosecha:
    1. Genera un UUID farm_id
    2. Llama AgroNestCrop.mintCrop() en la blockchain
    3. Extrae el tokenId del evento CropMinted
    4. Guarda la Cosecha en Postgres con los datos on-chain
    """
    w3 = get_web3_client()
    w3.assert_connected()
    farm_id      = str(uuid.uuid4())
    capital_wei  = int(data.capital_requerido * 10 ** 6)
    harvest_ts   = int(data.fecha_cosecha.timestamp())
    hectares_int = int(data.hectareas * 100)

    if not w3.crop_contract:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Contrato AgroNestCrop no disponible — verifica CROP_CONTRACT_ADDRESS en .env"
        )

    tx_hash = await w3.send_transaction(
        lambda: w3.crop_contract.functions.mintCrop(
            w3.api_account.address,
            farm_id,
            hectares_int,
            data.tipo_grano,
            data.rendimiento_kg,
            capital_wei,
            harvest_ts,
        )
    )

    receipt = await w3.wait_for_receipt(tx_hash)
    if receipt.get("status") != 1:
        logger.error(f"{logger_message} Transacción mintCrop falló: {tx_hash}")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="La transacción de minteo falló en la blockchain")

    logs = w3.crop_contract.events.CropMinted().process_receipt(receipt)
    if not logs:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="No se encontró el evento CropMinted en el receipt")
    token_id = logs[0]["args"]["tokenId"]

    cosecha = Cosecha(
        farm_id=farm_id,
        propietario_id=user.id,
        tipo_grano=data.tipo_grano,
        hectareas=data.hectareas,
        rendimiento_kg=data.rendimiento_kg,
        capital_requerido=data.capital_requerido,
        fecha_cosecha=data.fecha_cosecha,
        nft_token_id=token_id,
        tx_hash_mint=tx_hash,
        estado="MINTED",
        latitud=data.latitud,
        longitud=data.longitud,
    )
    await cosecha.save()
    logger.info(f"{logger_message} [SUCCESS] Cosecha {cosecha.id} creada, NFT #{token_id}, tx: {tx_hash}")
    return RespuestaCosechaSchema.model_validate(cosecha)


async def obtener_mis_cosechas(
    user: Usuario,
    logger_message: str,
    page: Optional[int] = Query(None, ge=1),
    per_page: Optional[int] = Query(None, ge=1, le=100),
) -> PaginacionCosechasSchema:
    query = Cosecha.filter(propietario_id=user.id, eliminado=False)
    total = await query.count()

    if page and per_page:
        offset = (page - 1) * per_page
        cosechas = await query.offset(offset).limit(per_page)
        pages = (total + per_page - 1) // per_page
    else:
        cosechas = await query
        pages = None

    logger.info(f"{logger_message} [SUCCESS] {total} cosechas obtenidas para usuario {user.id}")
    return PaginacionCosechasSchema(
        page=page,
        per_page=per_page,
        total=total,
        pages=pages,
        data=[RespuestaCosechaSchema.model_validate(c) for c in cosechas],
    )


async def obtener_todas_cosechas(
    logger_message: str,
    page: Optional[int] = Query(None, ge=1),
    per_page: Optional[int] = Query(None, ge=1, le=100),
) -> PaginacionCosechasSchema:
    query = Cosecha.filter(eliminado=False)
    total = await query.count()

    if page and per_page:
        offset = (page - 1) * per_page
        cosechas = await query.offset(offset).limit(per_page)
        pages = (total + per_page - 1) // per_page
    else:
        cosechas = await query
        pages = None

    logger.info(f"{logger_message} [SUCCESS] {total} cosechas obtenidas")
    return PaginacionCosechasSchema(
        page=page,
        per_page=per_page,
        total=total,
        pages=pages,
        data=[RespuestaCosechaSchema.model_validate(c) for c in cosechas],
    )


async def obtener_cosecha(
    cosecha_id: int,
    logger_message: str,
) -> RespuestaCosechaSchema:
    cosecha = await Cosecha.get_or_none(id=cosecha_id, eliminado=False)
    if not cosecha:
        logger.error(f"{logger_message} Cosecha {cosecha_id} no encontrada")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cosecha no encontrada")
    logger.info(f"{logger_message} [SUCCESS] Cosecha {cosecha_id} obtenida")
    return RespuestaCosechaSchema.model_validate(cosecha)


async def eliminar_cosecha(
    cosecha_id: int,
    user: Usuario,
    logger_message: str,
) -> dict:
    cosecha = await Cosecha.get_or_none(id=cosecha_id, propietario_id=user.id, eliminado=False)
    if not cosecha:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cosecha no encontrada")
    if cosecha.estado not in ("PENDIENTE", "MINTED"):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="No se puede eliminar una cosecha con bóveda activa")
    cosecha.eliminado = True
    await cosecha.save()
    logger.info(f"{logger_message} [SUCCESS] Cosecha {cosecha_id} eliminada")
    return {"detail": f"Cosecha {cosecha_id} eliminada correctamente"}
