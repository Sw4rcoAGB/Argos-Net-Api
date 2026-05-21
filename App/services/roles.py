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
from App.utils.logger import MyLogger
from App.utils.auth_check import check_permissions


# my schemas
from App.schemas.roles import RolBase, RespuestaRolSchema, PaginacionRolSchema

logger = MyLogger.__call__().get_logger()

async def crear_rol(
    role: RolBase,
    logger_message: str
): 
    '''
    Esta función registra un rol en la base de datos.

    Parámetros:

        role: Esquema con los datos necesarios para registrar un rol.
        current_user: Autentifíquese para realizar la solicitud.

    Retorno: Rol añadido correctamente e información del rol.
    '''

    role_obj = Rol(
        nombre=role.nombre,
        descripcion=role.descripcion
    )

    await role_obj.save()
    logger.info(f"{logger_message} [SUCCESS] Rol: {role_obj.id} creado.")
    return RespuestaRolSchema.model_validate(role_obj)
    
async def agregar_endpoint_rol(
    endpoint_id: int, 
    rol_id: int,
    logger_message: str,
): 
    '''
    Esta función añade un endpoint a una función de base de datos.

    Parámetros:

        endpoint_id: Esquema con el identificador del punto final.
        role_id: Esquema con el identificador de rol
        current_user (User): Authenticates to make the request.

    Retorno: Autentica para realizar la solicitud..
    '''

    role = await Rol.get_or_none(id=rol_id, eliminado=False)
    if not role:
        logger.error(f"{logger_message} Rol no encontrado {str(rol_id)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")

    endpoint = await Endpoint.get_or_none(id=endpoint_id)
    if not endpoint:
        logger.error(f"{logger_message} Endpoint no encontrado {str(endpoint_id)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint no encontrado")

    await role.endpoints.add(endpoint)
    logger.info(f"{logger_message} [SUCCESS] Endpoint: {endpoint_id} agregado al rol: {rol_id}.")
    return {"mensaje": "Endpoint agregado al rol selececcionado."}
    
async def remover_endpoint_rol(
    logger_message: str,
    endpoint_id: int, 
    rol_id: int, 
): 
    '''
    Esta función elimina el endpoint del rol al que pertenece y se almacena en la base de datos.
    
    Parámetros:

        endpoint_id: Esquema con el identificador del punto final.
        rol_id: Esquema con el identificador de rol.
        current_user: Autentica para realizar la solicitud.

    Retorno: Elimina el punto final asociado con la función.
    '''

    role = await Rol.get_or_none(id=rol_id, eliminado=False)
    if not role:
        logger.error(f"{logger_message} Rol no encontrado {str(rol_id)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")

    endpoint = await Endpoint.get_or_none(id=endpoint_id)
    if not endpoint:
        logger.error(f"{logger_message} Endpoint no encontrado {str(endpoint_id)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint no encontrado.")

    await role.endpoints.remove(endpoint)
    logger.info(f"{logger_message} [SUCCESS] Endpoint: {endpoint_id} removido del role: {rol_id}.")
    return {"mensaje": "Endpoint retirado del rol seleccionado"}

async def obtener_endpoints_rol(
    logger_message: str,
    role_id: int,
):
    '''
    Esta función obtiene los endpoints asociados a una función especial.
    
    Parámetros:

        rol_id: Identificador de rol
        current_user: Autentica para realizar la solicitud.

    Retorno: Obtenga los puntos relacionados con el rol.
    '''

    # Verificar que el usuario existe
    role = await Rol.get_or_none(id=role_id, eliminado=False)
    if not role:
        logger.error(f"{logger_message} Rol no encontrado {str(role_id)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")

    endpoints = await role.get_endpoints()
    endpoints_names = [endpoint.ruta for endpoint in endpoints]
    logger.info(f"{logger_message} [SUCCESS] Nombre de los endpoints obtenidos")
    logger.info(f"{logger_message} Se han obtenido el rol correctamente.")
    return {"endpoints": endpoints_names}

async def obtener_roles(
    logger_message: str,
    page: Optional[int] = None,
    per_page: Optional[int] = None
): 
    '''
    Esta función obtiene la información de los roles de la base de datos.

    Parámetros:

        current_user: Autentica para realizar la solicitud.      

    Retorno: Obtiene la información correspondiente a los roles.
    '''

    total = await Rol.all().count()
    
    query = Rol.all()

    if page and per_page:
        offset = (page - 1) * per_page
        roles = await query.offset(offset).limit(per_page)
        pages = (total + per_page - 1) // per_page
    else:
        pages = None
        roles = await query

    if not roles:
        logger.error(f"{logger_message} No se encontraron usuarios")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No se encontraron usuarios.")
    
    logger.info(f"{logger_message} [SUCCESS] Roles obtenidos.")
    return PaginacionRolSchema(
        page=page,
        per_page=per_page,
        total=total,
        pages=pages,
        data=[RespuestaRolSchema.from_orm(r) for r in roles]
    )
    
async def obtener_rol_por_id(
   logger_message: str,
    rol_id: int,
): 
    '''
    Esta función obtiene la información del rol dependiendo del identificador de la base de datos.

    Parámetros:

        rol_id: Identificador de rol.
        current_user: Autentica para realizar la solicitud.

    Retorno: Obtiene la información del rol al que corresponde el identificador.
    '''

    role = await Rol.filter(id=rol_id, eliminado=False)
    if not role:
        logger.error(f"{logger_message} Rol no encontrado, rol_id: {str(rol_id)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Rol no encontrado'
        )
    else:
        logger.info(f"{logger_message} [SUCCESS] Rol: {rol_id} obtenido.")
        return role

async def actualizar_rol(
    logger_message: str, 
    rol_id: int ,
    role_schema: RolBase,
): 
    '''
    Esta función actualiza el rol almacenado en la base de datos.

    Parámetros:

        role_shema: Schema of the data to be modified, including its rol identifier.
        current_user: Autentica para realizar la solicitud.

    Retorno: Actualizar los roles almacenados en la base de datos.
    '''

    existing_role = await Rol.get(id=rol_id, eliminado=False)
    if not existing_role:
        logger.error(f"{logger_message} Rol no encontrado, rol_id: {str(rol_id)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Rol no encontrado'
        )

    # Update the fields if they exist in the input schema
    if role_schema.nombre:
        existing_role.nombre = role_schema.nombre
    if role_schema.descripcion:
        existing_role.descripcion = role_schema.descripcion

    # Save the changes to the database
    await existing_role.save()
    logger.info(f"{logger_message} [SUCCESS] Role: {rol_id} actualizado.")
    return RespuestaRolSchema.model_validate(existing_role)

async def eliminar_rol(
    rol_id: int,
    logger_message: str,
    response: Response,
): 
    '''
    Esta función elimina el rol almacenado en la base de datos.

    Parámetros:

        rol_id: Identificador de rol.
        response: Respuesta del objeto fastapi para poder modificar la respuesta http.
        current_user: Autentica para realizar la solicitud.

    Retorno: Elimina el rol almacenado en la base de datos.
    '''

    role_check = await Rol.filter(id=rol_id, eliminado=False)
    if not role_check:
        logger.error(f"{logger_message} Rol no encontrado, rol_id: {str(rol_id)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Rol no encontrado'
        )

    _role_to_delete = role_check[0].__dict__
    _role_to_delete_name = _role_to_delete["nombre"]

    # check if users have the role, users should be none to delete role
    users_in_role = await Usuario.all().prefetch_related("roles")
    print(users_in_role)
    for user in users_in_role:
        # verify if user have the selected role from _role_to_delete_name
        for role in user.roles:
            if str(_role_to_delete_name) == str(role):
                # do not delete
                logger.error(f"{logger_message} Error al borrar el rol {str(rol_id)}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='No se puede borrar el rol ya que está asociado a usuarios existentes'
                )
            # else, if it doesn't have users with role then continue

    if str(_role_to_delete_name) in ["AUD", "ADM", "USR"]:
        logger.error(f"{logger_message} Error al borrar el rol {str(rol_id)}")
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail='No se puede borrar el rol ya que está asociado a usuarios existentes'
        )
    else:
        role = await Rol.get_or_none(id=rol_id)
        role.eliminado = True
        await role.save()
        response.status_code = status.HTTP_200_OK
        logger.info(f"{logger_message} [SUCCESS] Role: {rol_id} eliminado.")
        return {"mensaje": f"Rol {rol_id} eliminado"}
        
