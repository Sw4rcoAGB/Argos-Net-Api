# python libraries
from tortoise.contrib.pydantic import pydantic_model_creator
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status, Response, Request, Query
from datetime import datetime
from typing import Optional

# my models
from App.models.rol import Rol
from App.models.usuario import Usuario
from App.models.endpoint import Endpoint
from App.schemas.endpoints import EndpointBase, RespuestaEndpointSchema, PaginacionEdnpointSchema

# my utils
from App.utils.logger import MyLogger


logger = MyLogger.__call__().get_logger()

async def crear_endpoint(
    endpoint: EndpointBase,
    logger_message: str,
): # type: ignore
    '''
    Esta función registra un endpoint en la base de datos, tomando la ruta, el método y la descripción.

    Parámetros:

        request (Request): Objeto que realiza la solicitud HTTP.
        _user (User): Usuario autenticado para realizar la solicitud.

    Retorno: Se agregaron correctamente el punto final y la información del punto final
    '''

    endpoint_obj = Endpoint(
        ruta=endpoint.ruta,
        metodo=endpoint.metodo,
        descripcion=endpoint.descripcion
    )
    await endpoint_obj.save()
    logger.info(f"{logger_message} [SUCCESS] Endpoint: {endpoint_obj.id} creado correctamente.")
    return RespuestaEndpointSchema.model_validate(endpoint_obj)
    
async def update_endpoint(
    endpoint_id: int,
    logger_message: str,
    endpoint: EndpointBase,
): 
    '''
    Esta función actualiza el punto final almacenado en la base de datos.

    Parámetros:

        endpoint_id: Identificador endpoint.
        endpoint: Genera automáticamente un esquema basado en el modelo de base de datos.
        request (Request): Objeto que realiza la solicitud HTTP.
        _user (User): Usuario autenticado para realizar la solicitud.

    Retorno: Actualizar el endpoint almacenado en la base de datos
    '''

    endpoint_data = endpoint.dict(exclude_unset=True)
    logger.info(f"{logger_message} DISTRICT DATA", endpoint_data)
    endpoint_data["actualizacion"] = datetime.now()

    existing_endpoint = await Endpoint.get_or_none(id=endpoint_id)
    if not existing_endpoint:
        logger.error(f"{logger_message} Endpoint {str(endpoint_id)} no encontrado")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint con el id {endpoint_id} no encontrado"
        )
    for key, value in endpoint_data.items():
        setattr(existing_endpoint, key, value)
    await existing_endpoint.save()
    del endpoint_data["actualizacion"]
    logger.info(f"{logger_message} [SUCCESS] Endpoint: {endpoint_id} actualizado.")
    return RespuestaEndpointSchema.model_validate(existing_endpoint)


async def get_endpoints(
    logger_message: str,
    page: Optional[int] = None,
    per_page: Optional[int] = None
): 
    '''
    Esta función obtiene la información del los endpoints de la base de datos.

    Parámetros:

        request (Request): Objeto que realiza la solicitud HTTP.
        _user (User): Usuario autenticado para realizar la solicitud.

    Retorno: Obtiene la información de los endpoints.
    '''

    total = await Endpoint.all().count()
    query = Endpoint.all()

    if page and per_page:
        offset = (page - 1) * per_page
        endpoints = await query.offset(offset).limit(per_page)
        pages = (total + per_page - 1) // per_page
    else:
        pages = None
        endpoints = await query

    if not endpoints:
        logger.error(f"{logger_message} Endpoints no encontrados")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoints no encontrados"
        )

    logger.info(f"{logger_message} [SUCCESS] Endpoints obtenidos correctamente.")
    return PaginacionEdnpointSchema(
        page=page,
        per_page=per_page,
        total=total,
        pages=pages,
        data=[RespuestaEndpointSchema.from_orm(e) for e in endpoints]
    )

async def obtener_endpoints_por_rol(
    role_id: int, 
    logger_message: str,
): 
    '''
    Esta función obtiene la información de los endpoints asociados a un rol de la base de datos.

    Parámetros:

        role_id: Identificador de rol.
        request (Request): Objeto que realiza la solicitud HTTP.
        _user (User): Usuario autenticado para realizar la solicitud.

    Retorno: Obtiene todos los endpoints asociados con el rol.
    '''
    role = await Rol.get(id=role_id).prefetch_related("endpoints")

    if not role.endpoints:
        logger.error(f"{logger_message} Endpoints no encontrados")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoints no encontrados"
        )

    endpoints_diccionario = [endpoint.get_by_rol() for endpoint in role.endpoints]
    logger.info(f"{logger_message} [SUCCESS] Endpoints del rol: {role_id} obtenidos correctamente.")
    return [RespuestaEndpointSchema.model_validate(e) for e in endpoints_diccionario]

async def obtener_endpoint_por_id(
    endpoint_id: int,
    logger_message: str
): 
    '''
    Esta función obtiene la informacion de el endpoint almacenado en la base de datos.

    Parameters:

        endpoint_id: Identificador de endpoint.
        request (Request): Objeto que realiza la solicitud HTTP.
        _user (User): Usuario autenticado para realizar la solicitud.

    Retorno: Información del endpoint almacenada en la base de datos.
    '''

    endpoint = await Endpoint.filter(id=endpoint_id)
    if not endpoint:
        logger.error(f"{logger_message} Endpoint {str(endpoint_id)} no encontrado")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Endpoint no encontrado'
        )
    else:
        logger.info(f"{logger_message} [SUCCESS] Endpoint: {endpoint_id} obtenido.")
        return endpoint

async def eliminar_endpoint(
    endpoint_id: int,
    logger_message: str,
):
    '''
    Esta función elimina el endpoint almacenado en la base de datos.

    Parámetros:

        endpoint_id: Identificador de endpoint.
        request (Request): Objeto que realiza la solicitud HTTP.
        _user (User): Usuario autenticado para realizar la solicitud.

    Retorno: Elimina el endpoint almacenado en la base de datos
    '''
    
    deleted_count = await Endpoint.filter(id=endpoint_id).delete()  # Eliminar todos los registros con ese id
    if deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Endpoint not found")
    logger.info(f"{logger_message} [SUCCESS] Endpoint: {endpoint_id} eliminado correctamente.")
    return {"detail": "Endpoint deleted"}