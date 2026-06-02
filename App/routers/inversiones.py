from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

import App.services.inversiones as InversionService
from App.schemas.inversiones import InvertirSchema, PaginacionInversionesSchema, RespuestaInversionSchema
from App.utils.auth import get_current_user
from App.utils.auth_check import check_permissions
from App.utils.logger import MyLogger

router = APIRouter(
    prefix="/inversiones",
    tags=["inversiones"],
    responses={404: {"description": "Not found"}},
)
logger = MyLogger.__call__().get_logger()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RespuestaInversionSchema)
async def invertir(
    data: InvertirSchema,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        return await InversionService.invertir(user, data, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al invertir: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("", response_model=PaginacionInversionesSchema)
async def mis_inversiones(
    request: Request,
    user=Depends(get_current_user),
    page: Optional[int] = Query(None, ge=1),
    per_page: Optional[int] = Query(None, ge=1, le=100),
):
    logger_message = await check_permissions(user, request)
    try:
        return await InversionService.obtener_mis_inversiones(user, logger_message, page, per_page)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener inversiones: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/cosecha/{cosecha_id}", response_model=list[RespuestaInversionSchema])
async def inversiones_por_cosecha(
    cosecha_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        return await InversionService.obtener_inversiones_cosecha(cosecha_id, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{inversion_id}/reclamar", response_model=RespuestaInversionSchema)
async def reclamar_retorno(
    inversion_id: int,
    request: Request,
    user=Depends(get_current_user),
):
    logger_message = await check_permissions(user, request)
    try:
        return await InversionService.reclamar_retorno(user, inversion_id, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al reclamar retorno: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
