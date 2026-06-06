from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

import App.services.etherfuse as EtherfuseService
from App.models.etherfuse_cliente import EtherfuseCliente
from App.models.etherfuse_orden import EtherfuseOrden
from App.schemas.etherfuse import (
    ActualizarWalletSchema,
    CrearOrdenSchema,
    CrearQuoteSchema,
    IniciarOnboardingSchema,
    PaginacionOrdenesSchema,
    RespuestaClienteSchema,
    RespuestaOnboardingSchema,
    RespuestaOrdenSchema,
    RespuestaQuoteSchema,
    WebhookEventSchema,
)
from App.utils.auth import get_current_user
from App.utils.auth_check import check_permissions
from App.utils.logger import MyLogger

router = APIRouter(
    prefix="/etherfuse",
    tags=["etherfuse"],
    responses={404: {"description": "Not found"}},
)
logger = MyLogger.__call__().get_logger()


@router.post("/onboarding", status_code=status.HTTP_201_CREATED, response_model=RespuestaOnboardingSchema)
async def iniciar_onboarding(
    data: IniciarOnboardingSchema,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    # Idempotente: si ya existe el cliente, devuelve los datos actuales
    existing = await EtherfuseCliente.get_or_none(usuario_id=user.id)
    if existing:
        logger.info(f"{logger_message} Cliente Etherfuse ya existe para usuario {user.id}")
        return RespuestaOnboardingSchema(
            customer_id=str(existing.customer_id),
            bank_account_id=str(existing.bank_account_id) if existing.bank_account_id else "",
            kyc_status=existing.kyc_status,
            presigned_url=existing.presigned_url,
        )

    customer_id = str(uuid4())
    bank_account_id = str(uuid4())

    try:
        presigned_url = await EtherfuseService.get_presigned_url(customer_id, bank_account_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{logger_message} Error inesperado en onboarding Etherfuse: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    cliente = EtherfuseCliente(
        usuario_id=user.id,
        customer_id=customer_id,
        bank_account_id=bank_account_id,
        kyc_status="PENDING",
        wallet_address=data.wallet_address,
        presigned_url=presigned_url,
    )
    await cliente.save()
    logger.info(f"{logger_message} [SUCCESS] Cliente Etherfuse creado: {customer_id}")
    return RespuestaOnboardingSchema(
        customer_id=customer_id,
        bank_account_id=bank_account_id,
        kyc_status="PENDING",
        presigned_url=presigned_url,
    )


@router.get("/customer", response_model=RespuestaClienteSchema)
async def obtener_cliente(
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    cliente = await EtherfuseCliente.get_or_none(usuario_id=user.id)
    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cliente Etherfuse no encontrado. Inicia el onboarding primero.")
    logger.info(f"{logger_message} [SUCCESS] Cliente Etherfuse obtenido para usuario {user.id}")
    return RespuestaClienteSchema.model_validate(cliente)


@router.put("/customer/wallet", response_model=RespuestaClienteSchema)
async def actualizar_wallet(
    data: ActualizarWalletSchema,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    cliente = await EtherfuseCliente.get_or_none(usuario_id=user.id)
    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cliente Etherfuse no encontrado.")
    cliente.wallet_address = data.wallet_address
    await cliente.save()
    logger.info(f"{logger_message} [SUCCESS] Wallet actualizada para cliente {cliente.id}")
    return RespuestaClienteSchema.model_validate(cliente)


@router.get("/assets")
async def obtener_activos(
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        assets = await EtherfuseService.get_assets()
        logger.info(f"{logger_message} [SUCCESS] Activos Etherfuse obtenidos")
        return assets
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener activos: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/quote", response_model=RespuestaQuoteSchema)
async def crear_quote(
    data: CrearQuoteSchema,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    cliente = await EtherfuseCliente.get_or_none(usuario_id=user.id)
    if not cliente:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Completa el onboarding KYC primero.")

    try:
        result = await EtherfuseService.create_quote(
            tipo=data.tipo,
            source_asset=data.source_asset,
            target_asset=data.target_asset,
            amount=data.amount,
            customer_id=str(cliente.customer_id),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{logger_message} Error al crear quote: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    logger.info(f"{logger_message} [SUCCESS] Quote creado: {result.get('quoteId', result.get('id', ''))}")
    return RespuestaQuoteSchema(
        quote_id=result.get("quoteId") or result.get("id") or "",
        tipo=data.tipo,
        source_asset=data.source_asset,
        target_asset=data.target_asset,
        amount=data.amount,
        exchange_rate=Decimal(str(result["exchangeRate"])) if result.get("exchangeRate") else None,
        fee_bps=result.get("feeBps"),
        fee_amount=Decimal(str(result["feeAmount"])) if result.get("feeAmount") else None,
        destination_amount=Decimal(str(result["destinationAmount"])) if result.get("destinationAmount") else None,
        expires_at=result.get("expiresAt"),
    )


@router.post("/order", status_code=status.HTTP_201_CREATED, response_model=RespuestaOrdenSchema)
async def crear_orden(
    data: CrearOrdenSchema,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    cliente = await EtherfuseCliente.get_or_none(usuario_id=user.id)
    if not cliente:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Completa el onboarding KYC primero.")
    if not cliente.bank_account_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cuenta bancaria no vinculada.")

    try:
        result = await EtherfuseService.create_order(
            quote_id=data.quote_id,
            customer_id=str(cliente.customer_id),
            bank_account_id=str(cliente.bank_account_id),
            wallet_address=data.wallet_address,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{logger_message} Error al crear orden: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    orden = EtherfuseOrden(
        cliente_id=cliente.id,
        order_id=result.get("orderId") or result.get("id") or str(uuid4()),
        quote_id=data.quote_id,
        tipo=result.get("type", "onramp"),
        status=result.get("status", "created"),
        source_asset=result.get("sourceAsset", ""),
        target_asset=result.get("targetAsset", ""),
        source_amount=Decimal(str(result.get("sourceAmount", 0))),
        destination_amount=Decimal(str(result["destinationAmount"])) if result.get("destinationAmount") else None,
        exchange_rate=Decimal(str(result["exchangeRate"])) if result.get("exchangeRate") else None,
        fee_bps=result.get("feeBps"),
        fee_amount=Decimal(str(result["feeAmount"])) if result.get("feeAmount") else None,
        deposit_clabe=result.get("depositClabe"),
        burn_transaction=result.get("burnTransaction"),
        status_page_url=result.get("statusPage"),
    )
    await orden.save()
    logger.info(f"{logger_message} [SUCCESS] Orden creada: {orden.order_id}")
    return RespuestaOrdenSchema.model_validate(orden)


@router.post("/order/{order_id}/simulate")
async def simular_fiat(
    order_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    cliente = await EtherfuseCliente.get_or_none(usuario_id=user.id)
    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

    orden = await EtherfuseOrden.get_or_none(order_id=order_id, cliente_id=cliente.id)
    if not orden:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Orden no encontrada.")

    try:
        result = await EtherfuseService.simulate_fiat_received(order_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{logger_message} Error al simular fiat: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    orden.status = "funded"
    await orden.save()
    logger.info(f"{logger_message} [SUCCESS] Fiat simulado para orden {order_id}")
    return {"detail": "Fiat simulado correctamente", "order_id": order_id, "response": result}


@router.get("/orders", response_model=PaginacionOrdenesSchema)
async def listar_ordenes(
    request: Request,
    user=Depends(get_current_user),
    page: Optional[int] = Query(None, ge=1),
    per_page: Optional[int] = Query(None, ge=1, le=100),
):
    logger_message = await check_permissions(user, request)
    cliente = await EtherfuseCliente.get_or_none(usuario_id=user.id)
    if not cliente:
        return PaginacionOrdenesSchema(page=page, per_page=per_page, total=0, pages=0, data=[])

    query = EtherfuseOrden.filter(cliente_id=cliente.id)
    total = await query.count()

    if page and per_page:
        offset = (page - 1) * per_page
        ordenes = await query.offset(offset).limit(per_page)
        pages = (total + per_page - 1) // per_page
    else:
        ordenes = await query
        pages = None

    logger.info(f"{logger_message} [SUCCESS] {total} órdenes Etherfuse obtenidas")
    return PaginacionOrdenesSchema(
        page=page,
        per_page=per_page,
        total=total,
        pages=pages,
        data=[RespuestaOrdenSchema.model_validate(o) for o in ordenes],
    )


@router.get("/orders/{order_id}", response_model=RespuestaOrdenSchema)
async def obtener_orden(
    order_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    cliente = await EtherfuseCliente.get_or_none(usuario_id=user.id)
    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

    orden = await EtherfuseOrden.get_or_none(order_id=order_id, cliente_id=cliente.id)
    if not orden:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Orden no encontrada.")

    logger.info(f"{logger_message} [SUCCESS] Orden {order_id} obtenida")
    return RespuestaOrdenSchema.model_validate(orden)


@router.post("/webhook")
async def recibir_webhook(data: WebhookEventSchema):
    # Endpoint público — Etherfuse lo llama con firma HMAC-SHA256
    if data.event == "order_updated" and data.order_id and data.data:
        orden = await EtherfuseOrden.get_or_none(order_id=data.order_id)
        if orden:
            new_status = data.data.get("status")
            if new_status:
                orden.status = new_status
            burn_tx = data.data.get("burnTransaction")
            if burn_tx:
                orden.burn_transaction = burn_tx
            await orden.save()

    logger.info(f"Webhook Etherfuse recibido: {data.event} orden={data.order_id}")
    return {"received": True}
