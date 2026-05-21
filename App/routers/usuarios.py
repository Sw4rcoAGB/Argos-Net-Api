""" This is the router file for users to create users and get user information """

# python libraries
import re
from passlib.hash import bcrypt
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import DoesNotExist
from fastapi import APIRouter, HTTPException, status
from fastapi import Depends, Request, Query
from tortoise.transactions import in_transaction
import hashlib
from functools import lru_cache
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from typing import Optional

# my models
from App.models.usuario import Usuario
from App.models.rol import Rol
import App.services.usuarios as Usuarios

# my schemas
from App.schemas.usuarios import CrearUsuarioSchema, RespuestaUsuario,ActualizarUsuario, PaginacionUsuariosSchema
# my utils. User authentication method
from App.utils.auth import get_current_user
from App.utils.logger import MyLogger
from App.utils.auth_check import check_permissions

# settings
import App.core.settings as config
import json


# TODO: responder que es esto?
@lru_cache
def get_settings():
    return config.Settings()

# generate the users router
router = APIRouter(
    prefix="/usuarios",
    tags=["usuarios"],
    responses={404: {"description": "Not found"}},
)

logger = MyLogger.__call__().get_logger()


@router.post('', status_code=status.HTTP_201_CREATED, response_model=RespuestaUsuario)
async def crear_usuario(user_data: CrearUsuarioSchema):
    '''
    Esta función registra un nuevo usuario en la base de datos.

    Parámetros:

        user_data: La información del usuario que se quiere registrar.
        request (Request): La petición HTTP realizada.
        _user (User): El usuario autenticado que hizo la petición.

    Retorno: 
    
        Retorna el objeto creado del usuario sin la contraseña.
    '''
   # logger_message = await check_permissions(_user, request)

    usuario = await Usuarios.crear_usuario(
        user_data = user_data    
    )

    return usuario

@router.get('/mi_info', response_model=RespuestaUsuario)
async def mi_info(request: Request, user=Depends(get_current_user)):
    '''
    La función retorna los datos del usuario autenticado.

    Parámetros:

        request (Request): La petición HTTP realizada.
        user (User): El usuario autenticado que hizo la petición.

    Retorno: 

        La información del usuario.
    '''

    logger_message = await check_permissions(user, request)
    try:
        usuario = await Usuarios.mi_info(
            logger_message = logger_message,
            user = user,
        )
        return usuario
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error disabling user: {str(e)}")
    



@router.get('', response_model=PaginacionUsuariosSchema)
async def obtener_todos(request: Request, user=Depends(get_current_user), page: Optional[int] = Query(None, ge=1), per_page: Optional[int] = Query(None, ge=1, le=100)):
    '''
    Esta función retorna todos los usuarios registrados en la base de datos.

    Parámetros:

        request (Request): La petición HTTP realizada.
        user (User): El usuario autenticado que hizo la petición.

    Retorno: 
    
        La información de los usuarios obtenidos.
    '''
    logger_message = await check_permissions(user, request)
    try:
        usuarios = await Usuarios.obtener_todos(
            logger_message = logger_message,
            page = page,
            per_page = per_page,
        )
        return usuarios
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener todos los usuarios: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener todos los usuarios: {str(e)}")

@router.get('/{usuario_id}', response_model=RespuestaUsuario)
async def obtener_usuario(usuario_id: int, request: Request, user=Depends(get_current_user)):
    '''
    Esta función retorna la información de un usuario registrados en la base de datos.

    Parámetros:

        usuario_id: Identificador del usuario a obtener
        request (Request): La petición HTTP realizada.
        user (User): El usuario autenticado que hizo la petición.

    Retorno: 
    
        La información de los usuarios obtenidos.
    '''
    logger_message = await check_permissions(user, request)
    try:
        usuario = await Usuarios.obtener_usuario(
            logger_message = logger_message,
            usuario_id = usuario_id,
        )
        return usuario

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener el usuario: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al actualizar el usuario: {str(e)}")

@router.put('/{usuario_id}', response_model=RespuestaUsuario)
async def actualizar_usuario(usuario_id: int ,usuario_schema: ActualizarUsuario, request: Request, user=Depends(get_current_user)):
    '''
    Esta función actualiza el registro de un usuario en la base de datos.

    Parámetros:

        user_schema: Es esquema con los datos a modificar del usuario.
        request (Request): La petición HTTP realizada.
        user (User): El usuario autenticado que hizo la petición.

    Retorno: 
    
        La información del usuario actualizado.
    '''

    # Fetch the existing user from the database

    logger_message = await check_permissions(user, request)

    try:
        usuario = await Usuarios.actualizar_usuario(
            logger_message = logger_message,
            usuario_id = usuario_id,
            usuario_schema = usuario_schema,
        )

        return usuario
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al actualizar el usuario: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al actualizar el usuario: {str(e)}")

@router.post("/{usuario_id}/eliminar")
async def eliminar_usuario(usuario_id: int, request: Request, _user=Depends(get_current_user)):
    '''
    Esta funcion elimina logicamente a un usuario.

    Parameters:

        usuario_id: Identificador del usuario a eliminar
        request (Request): La petición HTTP realizada.
        user (User): El usuario autenticado que hizo la petición.

    Return: 
    
        Eliminación logica del usuario.
    '''

    logger_message = await check_permissions(_user, request)
    try:
        message = await Usuarios.eliminar_usuario(
            logger_message = logger_message,
            usuario_id= usuario_id,
        )
        return message
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al eliminar el usuario: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al eliminar el usuario: {str(e)}")

@router.post("/{usuario_id}/recuperar")
async def recuperar_usuario(usuario_id: int, request: Request, _user=Depends(get_current_user)):
    '''
    Esta funcion recupera a un usuario de la eliminación lógica

    Parámetros:

        usuario_id: Identificador del usuario a recuperar
        request (Request): La petición HTTP realizada.
        user (User): El usuario autenticado que hizo la petición.

    Return: 
    
        Recuperación de un usuario eliminado lógicamente.
    '''

    logger_message = await check_permissions(_user, request)
    try:
        message = await Usuarios.recuperar_usuario(
            logger_message = logger_message,
            usuario_id = usuario_id,
        )
        return message
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al recuperar el usuario: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al recuperar el usuario: {str(e)}")



    
