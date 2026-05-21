# python libraries
from tortoise.contrib.pydantic import pydantic_model_creator
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status, Response, Request, Query
from datetime import datetime
from typing import Optional

# my models
from App.models.rol import Rol
from App.models.usuario import Usuario
from App.models.endpoint import Endpoint
# from App.models.endpoint_permission import EndpointPermission

from App.schemas.endpoints import EndpointBase, RespuestaEndpointSchema, PaginacionEdnpointSchema
import App.services.endpoints as Endpoint
# my utils
from App.utils.auth import get_current_user
from App.utils.auth_check import check_permissions
from App.utils.logger import MyLogger

router = APIRouter(
    prefix="/endpoints",
    tags=["endpoints"],
    responses={404: {"description": "Not found"}},
)

logger = MyLogger.__call__().get_logger()

# CRUD create = create, read = get, update = DISABLED, delete = delete
# @router.post('/create_endpoint', dependencies=[Depends(allow_get_resource)])
# async def create_endpoint(endpoint: EndpointIn_Pydantic = Depends(), current_user: User_Pydantic = Depends(get_current_user)):
@router.post('', response_model=RespuestaEndpointSchema)
async def crear_endpoint(request: Request, endpoint: EndpointBase, _user=Depends(get_current_user)): # type: ignore
    '''
    Esta función registra un endpoint en la base de datos, tomando la ruta, el método y la descripción.

    Parámetros:

        request (Request): Objeto que realiza la solicitud HTTP.
        _user (User): Usuario autenticado para realizar la solicitud.

    Retorno: Se agregaron correctamente el punto final y la información del punto final
    '''

    logger_message = await check_permissions(_user, request)
    # Not authorized, raise exception
    try:

        endpoint = await Endpoint.crear_endpoint(
            endpoint = endpoint,
            logger_message = logger_message,
        )

        return endpoint
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al crear endpoint: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al crear endpoint: {str(e)}")
    

# endpoint to update existing user
@router.put('/{endpoint_id}', response_model=RespuestaEndpointSchema)
async def update_endpoint(endpoint_id: int, request: Request, endpoint: EndpointBase, _user=Depends(get_current_user)): # type: ignore
    '''
    Esta función actualiza el punto final almacenado en la base de datos.

    Parámetros:

        endpoint_id: Identificador endpoint.
        endpoint: Genera automáticamente un esquema basado en el modelo de base de datos.
        request (Request): Objeto que realiza la solicitud HTTP.
        _user (User): Usuario autenticado para realizar la solicitud.

    Retorno: Actualizar el endpoint almacenado en la base de datos
    '''

    logger_message = await check_permissions(_user, request)
    # Not authorized, raise exception
    try:
        endpoint_ = await Endpoint.update_endpoint(
            endpoint_id = endpoint_id,
            logger_message = logger_message,
            endpoint= endpoint
        )
        return endpoint_
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al actualizar endpoint: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al crear endpoint: {str(e)}")


@router.get('', response_model=PaginacionEdnpointSchema)
async def get_endpoints(request: Request, _user=Depends(get_current_user), page: Optional[int] = Query(None, ge=1), per_page: Optional[int] = Query(None, ge=1, le=100)): # type: ignore
    '''
    Esta función obtiene la información del los endpoints de la base de datos.

    Parámetros:

        request (Request): Objeto que realiza la solicitud HTTP.
        _user (User): Usuario autenticado para realizar la solicitud.

    Retorno: Obtiene la información de los endpoints.
    '''

    logger_message = await check_permissions(_user, request)
    # Not authorized, raise exception
    try:

        endpoints = await Endpoint.get_endpoints(
            logger_message = logger_message,
            page = page,
            per_page = per_page,
        )

        return endpoints
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener los endpoints: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener los endpoints: {str(e)}")

@router.get('/por_rol/{role_id}')
async def obtener_endpoints_por_rol(role_id: int, request: Request, _user=Depends(get_current_user)): # type: ignore
    '''
    Esta función obtiene la información de los endpoints asociados a un rol de la base de datos.

    Parámetros:

        role_id: Identificador de rol.
        request (Request): Objeto que realiza la solicitud HTTP.
        _user (User): Usuario autenticado para realizar la solicitud.

    Retorno: Obtiene todos los endpoints asociados con el rol.
    '''

    logger_message = await check_permissions(_user, request)
    try:
        endpoints_by_role = await Endpoint.obtener_endpoints_por_rol(
            logger_message = logger_message,
            role_id = role_id,
        )

        return endpoints_by_role
    
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener los endpoints por rol: {str(e)}")

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")

@router.get('/{endpoint_id}')
async def obtener_endpoint_por_id(endpoint_id: int, request: Request, _user=Depends(get_current_user)): # type: ignore
    '''
    Esta función obtiene la informacion de el endpoint almacenado en la base de datos.

    Parameters:

        endpoint_id: Identificador de endpoint.
        request (Request): Objeto que realiza la solicitud HTTP.
        _user (User): Usuario autenticado para realizar la solicitud.

    Retorno: Información del endpoint almacenada en la base de datos.
    '''

    logger_message = await check_permissions(_user, request)
    # Not authorized, raise exception
    try:

        endpoint = await Endpoint.obtener_endpoint_por_id(
            endpoint_id = endpoint_id,
            logger_message  = logger_message
        )
        return endpoint
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener el endpoint: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener el endpoint: {str(e)}")


@router.delete('/{endpoint_id}')
async def eliminar_endpoint(endpoint_id: int, request: Request, _user=Depends(get_current_user)): # type: ignore
    '''
    Esta función elimina el endpoint almacenado en la base de datos.

    Parámetros:

        endpoint_id: Identificador de endpoint.
        request (Request): Objeto que realiza la solicitud HTTP.
        _user (User): Usuario autenticado para realizar la solicitud.

    Retorno: Elimina el endpoint almacenado en la base de datos
    '''
    
    logger_message = await check_permissions(_user, request)
    # Not authorized, raise exception
    try:
        message =  await Endpoint.eliminar_endpoint(
            endpoint_id = endpoint_id,
            logger_message = logger_message
        )

        return message
    
    except Exception as e:
        logger.error(f"{logger_message} Error al eliminar el endpoint: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al eliminar el endpoints: {str(e)}")

