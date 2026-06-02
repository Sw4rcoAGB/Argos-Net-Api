from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

import App.services.cosechas as CosechaService
from App.schemas.cosechas import CrearCosechaSchema, PaginacionCosechasSchema, RespuestaCosechaSchema
from App.utils.auth import get_current_user
from App.utils.auth_check import check_permissions
from App.utils.logger import MyLogger

router = APIRouter(
    prefix="/cosechas",
    tags=["cosechas"],
    responses={404: {"description": "Not found"}},
)
logger = MyLogger.__call__().get_logger()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RespuestaCosechaSchema)
async def registrar_cosecha(
    data: CrearCosechaSchema,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        return await CosechaService.registrar_cosecha(user, data, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al registrar cosecha: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/mis_cosechas", response_model=PaginacionCosechasSchema)
async def mis_cosechas(
    request: Request,
    user=Depends(get_current_user),
    page: Optional[int] = Query(None, ge=1),
    per_page: Optional[int] = Query(None, ge=1, le=100),
):
    logger_message = await check_permissions(user, request)
    try:
        return await CosechaService.obtener_mis_cosechas(user, logger_message, page, per_page)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener cosechas: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("", response_model=PaginacionCosechasSchema)
async def todas_cosechas(
    request: Request,
    user=Depends(get_current_user),
    page: Optional[int] = Query(None, ge=1),
    per_page: Optional[int] = Query(None, ge=1, le=100),
):
    logger_message = await check_permissions(user, request)
    try:
        return await CosechaService.obtener_todas_cosechas(logger_message, page, per_page)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener cosechas: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{cosecha_id}", response_model=RespuestaCosechaSchema)
async def obtener_cosecha(
    cosecha_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        return await CosechaService.obtener_cosecha(cosecha_id, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener cosecha: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{cosecha_id}/eliminar")
async def eliminar_cosecha(
    cosecha_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        return await CosechaService.eliminar_cosecha(cosecha_id, user, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al eliminar cosecha: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
