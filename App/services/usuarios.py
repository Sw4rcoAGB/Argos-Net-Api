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

# my schemas
from App.schemas.usuarios import CrearUsuarioSchema, RespuestaUsuario,ActualizarUsuario, PaginacionUsuariosSchema
# my utils. User authentication method
from App.utils.logger import MyLogger


# settings
import App.core.settings as config
import json


# TODO: responder que es esto?
@lru_cache
def get_settings():
    return config.Settings()

logger = MyLogger.__call__().get_logger()

async def crear_usuario(
    user_data: CrearUsuarioSchema
):
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

    email_validate = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_validate, user_data.correo):
        logger.error(f" El correo ingresado no es válido: {str(user_data.correo)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El correo ingrasado no es válido")

    user_obj = Usuario(
        usuario = user_data.usuario,
        nombres = user_data.nombres,
        apellidos = user_data.apellidos,
        correo = user_data.correo,
        password_hash = Usuario.hash_password(user_data.password_hash),
    )

    try:
        await user_obj.save()
        del user_obj.__dict__['password_hash']
        log = 'Usuario creado' + user_obj.usuario
        logger.debug(log)
        rol = await Rol.filter(id=1, eliminado = False).first()
        await user_obj.roles.add(rol)
        logger.info(f"[SUCCESS] Usuario: {user_obj.id} creado  correctamente.")
        return RespuestaUsuario.model_validate(user_obj)
    except Exception as e:
        del user_obj.__dict__['creacion']
        del user_obj.__dict__['actualizacion']
        logger.error(f"Error al crear usuario: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def mi_info(
    logger_message: str,
    user: Usuario
):
    '''
    La función retorna los datos del usuario autenticado.

    Parámetros:

        request (Request): La petición HTTP realizada.
        user (User): El usuario autenticado que hizo la petición.

    Retorno: 

        La información del usuario.
    '''

    response_json = {}
    _user = await Usuario.get(id=user.id)
    creacion = json.dumps(_user.creacion,default=str)
    response_json['id'] = _user.id
    response_json["usuario"] = _user.usuario
    response_json["nombres"] = _user.nombres
    response_json["apellidos"] = _user.apellidos
    response_json["correo"] = _user.correo
    response_json["creacion"] = creacion
    response_json["eliminado"] = _user.eliminado

    logger.info(f" [SUCCESS] Usuario obtenido.")
    return JSONResponse(
        content=response_json,
        media_type="application/json; charset=utf-8"
    )

async def obtener_todos(
    logger_message: str,
    page: Optional[int] = Query(None, ge=1),
    per_page: Optional[int] = Query(None, ge=1, le=100)
):
    '''
    Esta función retorna todos los usuarios registrados en la base de datos.

    Parámetros:

        request (Request): La petición HTTP realizada.
        user (User): El usuario autenticado que hizo la petición.

    Retorno: 
    
        La información de los usuarios obtenidos.
    '''

    total = await Usuario.all().count()
    
    query = Usuario.all()

    if page and per_page:
        offset = (page - 1) * per_page
        usuarios = await query.offset(offset).limit(per_page)
        pages = (total + per_page - 1) // per_page
    else:
        pages = None
        usuarios = await query

    if not usuarios:
        logger.error(f"{logger_message} No se encontraron usuarios")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No se encontraron usuarios.")
    
    logger.info(f"{logger_message} [SUCCESS] Usuarios obtenidos correctamente.")
    return PaginacionUsuariosSchema(
        page=page, 
        per_page=per_page, 
        total=total, 
        pages=pages, 
        data=[RespuestaUsuario.from_orm(usuario) for usuario in usuarios]
    )

async def obtener_usuario(
    usuario_id: int,
    logger_message: str,
):
    '''
    Esta función retorna la información de un usuario registrados en la base de datos.

    Parámetros:

        usuario_id: Identificador del usuario a obtener
        request (Request): La petición HTTP realizada.
        user (User): El usuario autenticado que hizo la petición.

    Retorno: 
    
        La información de los usuarios obtenidos.
    '''

    user = await Usuario.get_or_none(id=usuario_id)

    if not user:
        logger.error(f"{logger_message} Usuario {usuario_id} no encontrado")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    
    logger.info(f"{logger_message} [SUCCESS] Usuario {usuario_id} obtenido por usuario autenticado: {user.id}")
    return RespuestaUsuario.model_validate(user)

async def actualizar_usuario(
    usuario_id: int ,
    logger_message: str,
    usuario_schema: ActualizarUsuario,
):
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

    existing_user = await Usuario.get(id=usuario_id)
    if not existing_user:
        logger.error(f"{logger_message} Usuario {usuario_id} no encontrado")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    # Update the fields if they exist in the input schema
    if usuario_schema.usuario:
        existing_user.usuario = usuario_schema.usuario
    if usuario_schema.nombres:
        existing_user.nombres = usuario_schema.nombres
    if usuario_schema.apellidos:
        existing_user.apellidos = usuario_schema.apellidos
    if usuario_schema.correo:
        email_validate = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_validate, usuario_schema.correo):
            logger.error(f"{logger_message} El email ingresado no es valido: {str(usuario_schema.correo)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The email entered is not valid")
        existing_user.correo = usuario_schema.correo
    if usuario_schema.password_hash:
        existing_user.password_hash = Usuario.hash_password(usuario_schema.password_hash)

    # Save the changes to the database
    await existing_user.save()
    logger.info(f"{logger_message} [SUCCESS] Usuario {usuario_id} actualizado.")
    return RespuestaUsuario.model_validate(existing_user)

async def eliminar_usuario(
    usuario_id: int, 
    logger_message: str,
):
    '''
    Esta funcion elimina logicamente a un usuario.

    Parameters:

        usuario_id: Identificador del usuario a eliminar
        request (Request): La petición HTTP realizada.
        user (User): El usuario autenticado que hizo la petición.

    Return: 
    
        Eliminación logica del usuario.
    '''

    user_ = await Usuario.get_or_none(id=usuario_id, eliminado=False)
    if not user_:
        logger.error(f"{logger_message} Usuario {usuario_id} no encontrado")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    user_.eliminado = True
    await user_.save()
    logger.info(f"{logger_message} [SUCCESS] Usuario: {user_.id} eliminado")
    return {"detail": f"Usuario {user_.id} eliminado correctamente."}

async def recuperar_usuario(
    logger_message: str,
    usuario_id: int,
):
    '''
    Esta funcion recupera a un usuario de la eliminación lógica

    Parámetros:

        usuario_id: Identificador del usuario a recuperar
        request (Request): La petición HTTP realizada.
        user (User): El usuario autenticado que hizo la petición.

    Return: 
    
        Recuperación de un usuario eliminado lógicamente.
    '''

    user_ = await Usuario.get_or_none(id=usuario_id, eliminado=True)
    if not user_:
        logger.error(f"{logger_message} Usuario {usuario_id} no encontrado")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    
    user_.eliminado = False
    await user_.save()
    logger.info(f"{logger_message} [SUCCESS] Usuario: {user_.id} recuperado")
    return {"detail": f"Usuario {user_.id} recuperado correctamente."}
    



    
