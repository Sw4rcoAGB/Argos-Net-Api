from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

import App.services.rare_protocol as MarketplaceService
from App.models.cosecha import Cosecha
from App.schemas.marketplace import (
    CrearListingSchema,
    CrearOfertaSchema,
    PaginacionListingsSchema,
    RespuestaListingSchema,
)
from App.utils.auth import get_current_user
from App.utils.auth_check import check_permissions
from App.utils.logger import MyLogger

router = APIRouter(
    prefix="/marketplace",
    tags=["marketplace"],
    responses={404: {"description": "Not found"}},
)
logger = MyLogger.__call__().get_logger()


@router.get("", response_model=PaginacionListingsSchema)
async def listar_nfts(
    request: Request,
    user=Depends(get_current_user),
    page: Optional[int] = Query(None, ge=1),
    per_page: Optional[int] = Query(None, ge=1, le=100),
    estado: str = Query("ACTIVE"),
):
    logger_message = await check_permissions(user, request)
    try:
        listings, total = await MarketplaceService.obtener_listings(page, per_page, estado)
        pages = (total + per_page - 1) // per_page if (page and per_page and total) else None
        logger.info(f"{logger_message} [SUCCESS] {total} listings obtenidos")
        return PaginacionListingsSchema(
            page=page,
            per_page=per_page,
            total=total,
            pages=pages,
            data=[RespuestaListingSchema.model_validate(l) for l in listings],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener listings: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{listing_id}", response_model=RespuestaListingSchema)
async def obtener_listing(
    listing_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        listing = await MarketplaceService.obtener_listing(listing_id)
        logger.info(f"{logger_message} [SUCCESS] Listing {listing_id} obtenido")
        return RespuestaListingSchema.model_validate(listing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener listing: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RespuestaListingSchema)
async def crear_listing(
    data: CrearListingSchema,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    cosecha = await Cosecha.get_or_none(id=data.cosecha_id, eliminado=False)
    if not cosecha:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Cosecha no encontrada.")
    try:
        listing = await MarketplaceService.crear_listing(
            cosecha=cosecha,
            vendedor=user,
            precio=data.precio,
            currency=data.currency,
            tipo=data.tipo,
            auction_horas=data.auction_horas,
        )
        logger.info(f"{logger_message} [SUCCESS] Listing creado para cosecha {data.cosecha_id}")
        return RespuestaListingSchema.model_validate(listing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{logger_message} Error al crear listing: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{listing_id}/confirm", response_model=RespuestaListingSchema)
async def confirmar_listing(
    listing_id: int,
    chain_listing_id: str,
    tx_hash: str,
    request: Request,
    user=Depends(get_current_user),
):
    """Confirma el listing on-chain después de que el usuario firma la transacción con MetaMask."""
    logger_message = await check_permissions(user, request)
    try:
        listing = await MarketplaceService.confirmar_listing_onchain(listing_id, chain_listing_id, tx_hash)
        logger.info(f"{logger_message} [SUCCESS] Listing {listing_id} confirmado on-chain")
        return RespuestaListingSchema.model_validate(listing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{logger_message} Error al confirmar listing: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{listing_id}/cancel", response_model=RespuestaListingSchema)
async def cancelar_listing(
    listing_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        listing = await MarketplaceService.cancelar_listing(listing_id, user)
        logger.info(f"{logger_message} [SUCCESS] Listing {listing_id} cancelado")
        return RespuestaListingSchema.model_validate(listing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{logger_message} Error al cancelar listing: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{listing_id}/sold")
async def marcar_vendido(
    listing_id: int,
    tx_hash: str,
    request: Request,
    user=Depends(get_current_user),
):
    """Marca el listing como vendido tras confirmación on-chain."""
    logger_message = await check_permissions(user, request)
    try:
        listing = await MarketplaceService.marcar_vendido(listing_id, tx_hash)
        logger.info(f"{logger_message} [SUCCESS] Listing {listing_id} marcado como vendido")
        return RespuestaListingSchema.model_validate(listing)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{logger_message} Error al marcar vendido: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
