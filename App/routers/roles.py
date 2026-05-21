# python libraries
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Q
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query
from typing import Optional

# my models
from App.models.usuario import Usuario
from App.models.rol import Rol
from App.models.endpoint import Endpoint

# utils
from App.utils.auth import get_current_user
import App.services.roles as Roles
from App.utils.logger import MyLogger
from App.utils.auth_check import check_permissions


# my schemas
from App.schemas.roles import RolBase, RespuestaRolSchema, PaginacionRolSchema


router = APIRouter(
    prefix="/roles",
    tags=["roles"],
    responses={404: {"description": "Not found"}},
)

logger = MyLogger.__call__().get_logger()

@router.post('', response_model=RespuestaRolSchema)
async def crear_rol(request: Request, role: RolBase, current_user = Depends(get_current_user)): # type: ignore
    '''
    Esta función registra un rol en la base de datos.

    Parámetros:

        role: Esquema con los datos necesarios para registrar un rol.
        current_user: Autentifíquese para realizar la solicitud.

    Retorno: Rol añadido correctamente e información del rol.
    '''
    logger_message = await check_permissions(current_user, request)
    try:
        rol = await Roles.crear_rol(
            logger_message = logger_message,
            role = role
        )
        return rol
    
    except Exception as e:
        logger.error(f"{logger_message} Error al crear rol: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al crear rol: {str(e)}")


@router.post("/{rol_id}/agregar_endpoint/{endpoint_id}")
async def agregar_endpoint_rol(request: Request,endpoint_id: int, rol_id: int, current_user = Depends(get_current_user)): # type: ignore
    '''
    Esta función añade un endpoint a una función de base de datos.

    Parámetros:

        endpoint_id: Esquema con el identificador del punto final.
        role_id: Esquema con el identificador de rol
        current_user (User): Authenticates to make the request.

    Retorno: Autentica para realizar la solicitud..
    '''
    logger_message = await check_permissions(current_user, request)
    try:
        message = await Roles.agregar_endpoint_rol(
            endpoint_id = endpoint_id,
            logger_message = logger_message,
            rol_id = rol_id
        )
        return message
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al agregar endpoint: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al agregar endpoint: {str(e)}")


@router.post("/{rol_id}/remover_endpoint/{endpoint_id}")
async def remover_endpoint_rol(request: Request, endpoint_id: int, rol_id: int, current_user = Depends(get_current_user)): # type: ignore
    '''
    Esta función elimina el endpoint del rol al que pertenece y se almacena en la base de datos.
    
    Parámetros:

        endpoint_id: Esquema con el identificador del punto final.
        rol_id: Esquema con el identificador de rol.
        current_user: Autentica para realizar la solicitud.

    Retorno: Elimina el punto final asociado con la función.
    '''
    logger_message = await check_permissions(current_user, request)
    try:
        message = await Roles.remover_endpoint_rol(
            endpoint_id = endpoint_id,
            logger_message = logger_message,
            rol_id = rol_id
        )
        return message
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al remover endpoint: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al remover endpoint: {str(e)}")


@router.get("/{role_id}/endpoints")
async def obtener_endpoints_rol(role_id: int,request: Request,  current_user = Depends(get_current_user)): # type: ignore
    '''
    Esta función obtiene los endpoints asociados a una función especial.
    
    Parámetros:

        rol_id: Identificador de rol
        current_user: Autentica para realizar la solicitud.

    Retorno: Obtenga los puntos relacionados con el rol.
    '''
    logger_message = await check_permissions(current_user, request)
    try:
        message = await Roles.obtener_endpoints_rol(
            logger_message = logger_message,
            role_id = role_id
        )
        return message

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener endpoints: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener endpoints: {str(e)}")

@router.get('', response_model=PaginacionRolSchema)
async def obtener_roles(request: Request, current_user = Depends(get_current_user), page: Optional[int] = Query(None, ge=1), per_page: Optional[int] = Query(None, ge=1, le=100)): # type: ignore
    '''
    Esta función obtiene la información de los roles de la base de datos.

    Parámetros:

        current_user: Autentica para realizar la solicitud.      

    Retorno: Obtiene la información correspondiente a los roles.
    '''
    logger_message = await check_permissions(current_user, request)
    try:
        roles = await Roles.obtener_roles(
            logger_message = logger_message,
            page = page,
            per_page = per_page,
        )

        return roles
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener roles: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener roles: {str(e)}")

@router.get('/{rol_id}')
async def obtener_rol_por_id(rol_id: int,request:Request, current_user = Depends(get_current_user)): # type: ignore
    '''
    Esta función obtiene la información del rol dependiendo del identificador de la base de datos.

    Parámetros:

        rol_id: Identificador de rol.
        current_user: Autentica para realizar la solicitud.

    Retorno: Obtiene la información del rol al que corresponde el identificador.
    '''
    logger_message = await check_permissions(current_user, request)
    try:
        role = await Roles.obtener_rol_por_id(
            logger_message = logger_message,
            rol_id = rol_id
        )
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener rol: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener rol: {str(e)}")

@router.put('/{rol_id}', response_model=RespuestaRolSchema)
async def actualizar_rol(request: Request, rol_id: int ,role_schema: RolBase, current_user = Depends(get_current_user)): # type: ignore
    '''
    Esta función actualiza el rol almacenado en la base de datos.

    Parámetros:

        role_shema: Schema of the data to be modified, including its rol identifier.
        current_user: Autentica para realizar la solicitud.

    Retorno: Actualizar los roles almacenados en la base de datos.
    '''
    logger_message = await check_permissions(current_user, request)
    # get the role Administrator want to change
    try:
        rol = await Roles.actualizar_rol(
            logger_message = logger_message,
            rol_id = rol_id,
            role_schema = role_schema,
        )

        return rol
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al actualizar rol: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al actualizar rol: {str(e)}")

@router.post('/{rol_id}/eliminar')
async def eliminar_rol(rol_id: int, request:Request, response: Response, current_user = Depends(get_current_user)): # type: ignore
    '''
    Esta función elimina el rol almacenado en la base de datos.

    Parámetros:

        rol_id: Identificador de rol.
        response: Respuesta del objeto fastapi para poder modificar la respuesta http.
        current_user: Autentica para realizar la solicitud.

    Retorno: Elimina el rol almacenado en la base de datos.
    '''
    logger_message = await check_permissions(current_user, request)
    
    try:
        message = await Roles.eliminar_rol(
            logger_message = logger_message,
            response = response,
            rol_id = rol_id,
        )
        
        return message
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al eliminar rol: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al eliminar rol: {str(e)}")