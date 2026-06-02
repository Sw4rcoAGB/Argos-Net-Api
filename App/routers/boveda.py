from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

import App.services.boveda as BovedaService
from App.schemas.boveda import AbrirBovedaSchema, EstadoChainBovedaSchema, PaginacionBovedaSchema, RespuestaBovedaSchema
from App.utils.auth import get_current_user
from App.utils.auth_check import check_permissions
from App.utils.logger import MyLogger

router = APIRouter(
    prefix="/boveda",
    tags=["boveda"],
    responses={404: {"description": "Not found"}},
)
logger = MyLogger.__call__().get_logger()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RespuestaBovedaSchema)
async def abrir_boveda(
    data: AbrirBovedaSchema,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        return await BovedaService.abrir_boveda(data, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al abrir bóveda: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("", response_model=PaginacionBovedaSchema)
async def obtener_todas_bovedas(
    request: Request,
    user=Depends(get_current_user),
    estado: Optional[str] = Query(None, description="Filtrar por estado: OPEN, FUNDED, ACTIVE, LIQUIDATED, DEFAULTED"),
    page: Optional[int] = Query(None, ge=1),
    per_page: Optional[int] = Query(None, ge=1, le=100),
):
    logger_message = await check_permissions(user, request)
    try:
        return await BovedaService.obtener_todas_bovedas(logger_message, estado, page, per_page)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al listar bóvedas: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/cosecha/{cosecha_id}", response_model=RespuestaBovedaSchema)
async def obtener_boveda_por_cosecha(
    cosecha_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        return await BovedaService.obtener_boveda_por_cosecha(cosecha_id, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{boveda_id}", response_model=RespuestaBovedaSchema)
async def obtener_boveda(
    boveda_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        return await BovedaService.obtener_boveda(boveda_id, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{boveda_id}/chain", response_model=EstadoChainBovedaSchema)
async def estado_chain(
    boveda_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        return await BovedaService.obtener_estado_chain(boveda_id, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al leer estado chain: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
