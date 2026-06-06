""" Token routes to do token operations """

# python libraries
import ast
from passlib.hash import bcrypt
import jwt  # pip3 install pyjwt
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form  # , Body
from fastapi.security import OAuth2PasswordRequestForm  # , OAuth2PasswordBearer
from tortoise.contrib.pydantic import pydantic_model_creator
from datetime import datetime, timedelta
import time
from functools import lru_cache
import redis
from pydantic import BaseModel

# my utils

from App.utils.auth import authenticate_user, tokenOut  # , get_current_user
from App.utils.logger import MyLogger

# my models
from App.models.usuario import Usuario

# my settings
import App.core.settings as config

# my services
# from api.services.email.email_service import generate_verification_code, verify_verification_code
# from api.services.email.email_service import generate_magic_link,verify_magic_link_token,create_magic_token,generate_magic_link_email

class TokenRefreshRequest(BaseModel):
    refresh_token: str

# TODO: responder que es esto?
@lru_cache
def get_settings():
    return config.Settings()

# get settings
settings = get_settings()
redis_client = redis.StrictRedis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db)

User_Pydantic = pydantic_model_creator(Usuario, name='User')

logger = MyLogger.__call__().get_logger()


async def create_access_token(
    request: Request, 
    user_obj
):
    '''
    Esta función genera un token de acceso JWT para un usuario determinado.
    
    Parámetros:

        request (Request): Objeto que realiza la solicitud HTTP.
        user_obj: Un diccionario que contiene información del usuario, incluido el nombre de usuario.

    Retorno: 
    
        Un token de acceso JWT que contiene datos del usuario y la fecha de caducidad..
    '''

    # client_ip
    client_ip = request.client.host

    # You can also check if there is a reverse proxy (e.g. Nginx) and look at the X-Forwarded-For header
    forwarded_ip = request.headers.get('X-Forwarded-For')
    real_ip = forwarded_ip.split(',')[0] if forwarded_ip else client_ip

    log = ', Login Attempt:' + str(user_obj['usuario']) + ", client_host:" + client_ip + ", client_real_ip:" + real_ip
    logger.info(log)

    # Set access token expiration
    current_datetime = datetime.now()
    expiration = current_datetime + timedelta(minutes=config.settings.jwt_token_expiration)

    # convert to epoch time
    epoch_expiration = int(time.mktime(expiration.timetuple()))

    payload = user_obj
    payload.update({"exp": epoch_expiration})


    # Generate access token
    access_token = jwt.encode(payload, config.settings.jwt_secret, algorithm=config.settings.algorithm)

    # Generate log
    log = 'Token generado:  ' + str(payload) + ', Expiracion token: ' + str(expiration) + ", timestamp:" + \
          str(epoch_expiration) + ", access_token " + str(access_token)
    logger.debug(log)

    # return {'access_token': access_token, 'token_type': 'bearer', 'token_expires': epoch_expiration}
    return access_token


# Función para crear un Refresh Token
async def create_refresh_token(user_obj):
    '''
    Esta función genera un token de actualización JWT para un usuario determinado.

    Parámetros:

        user_obj: Un diccionario que contiene información del usuario, incluyendo su identificación..

    Retorno: 
        
        Un token de actualización JWT que se puede utilizar para generar un nuevo token de acceso.    
    '''

    # Set access token expiration
    current_datetime = datetime.now()
    expiration = current_datetime + timedelta(minutes=config.settings.jwt_renew_expiration)

    # convert to epoch time
    epoch_expiration = int(time.mktime(expiration.timetuple()))

    payload = user_obj

    payload.update({"exp": epoch_expiration})
   

    refresh_token = jwt.encode(payload, config.settings.jwt_secret_renew, algorithm=config.settings.algorithm)
    return refresh_token

# endpoint to generate token

async def generate_token(
    request: Request, 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    
    '''
    Esta función autentica a un usuario y genera tokens de acceso y actualización JWT.

    Parámetros:

        request (Request): Objeto que realiza la solicitud HTTP.
        form_data: Las credenciales de inicio de sesión del usuario (nombre de usuario y contraseña).

    Retorno: 
        
        dict: Un diccionario que contiene: El token de acceso JWT y el token de actualización JWT.
    '''

    # Autenticar usuario
    user_obj = await authenticate_user(form_data.username, form_data.password)

    #   await verify_verification_code(email=user_obj.correo,verification_code=code,redis_client=redis_client)

    # Generate payload for access_token and refresh_token
    payload = user_obj.dict()

    # Add endpoints to access_token and refresh_token

    access_token = await create_access_token(request, payload)
    refresh_token = await create_refresh_token(payload)

    try:
        redis_client.hset("valid_tokens", user_obj.id, access_token)
    except redis.exceptions.ConnectionError:
        logger.warning("Redis no disponible — token no registrado en sesiones activas")

    return {
        'access_token': access_token,
        'refresh_token': refresh_token
    }

# async def recovery_password(
#     correo: str , entorno:str ,request: Request
# ):
#     """
#     Esta función genera una liga magica enviada por correo para restablecer su contraseña

#     Parámetros:

#         correo: Identificador de usuario.
#         entorno: Identificador de entorno.
#         request (Request): Objeto que realiza la solicitud HTTP.

#     Retorno: Genera un magic link por correo.
#     """
#     try:
#         usuario = await Usuario.filter(correo=correo, eliminado = False).first()

#         if not entorno in config.settings.environment_base_url:
#             logger.error(f"El tipo {entorno} no se encuentra en el entorno")
#             raise Exception(
#                 {"status_code":status.HTTP_404_NOT_FOUND, "detail":str(f"El tipo  {entorno} no se encuentra en el entorno.")}
#             )
#         if not usuario:
#             logger.error(f"Usuario con correo: {correo} no encontrado")
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
        
#         # token=create_magic_token(correo,redis_client)
#         # magic_link= generate_magic_link(request,token,entorno)
#         # subject="Restablecimiento de contraseña"
#         # generate_magic_link_email(usuario=usuario.usuario,email=usuario.correo,magic_link=magic_link,subject=subject)

#         logger.info(f"[SUCCESS] Se genero magic link para el usuario {usuario.id}")
#         return({"status_code":status.HTTP_200_OK,"detail":str(f"magic link enviado correctamentes")})
        
        
#     except HTTPException as http_exc:
#         raise http_exc
#     except Exception as e:
#         logger.error(f"Error al mandar el correo: {str(e)}")
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al mandar el correo: {str(e)}")
    
# @router.post('/reset-psw')
# async def reset_password(password: str , confirm_password:str, token: str):
#     """
#     Esta función permite restablecer la contraseña 

#     Parámetros:

#         password: Contraseña nueva 
#         confirm_password: Confirmación de contraseña
#         token: Identificador en Magic Link

#     Retorno:Cambia la contraseña correctamente.
#     """
#     try:
       
#     #   #  correo = verify_magic_link_token(token)
#     #     # key = f"magic_link:{correo}"
#     #     # usuario = await Usuario.get_or_none(correo=correo, eliminado = False)

#     #     jwt_token = redis_client.get(key)

#     #     if not jwt_token:
#     #         logger.error(f"token invalido o vencido: {jwt_token}")
#     #         raise HTTPException(
#     #             {"status_code":status.HTTP_400_BAD_REQUEST, "detail":str(f"Token vencido o invalido")}
#     #         )
        
#     #     if not usuario:
#     #         logger.error(f"Usuario no encontrado: {usuario.id}")
#     #         raise HTTPException(
#     #             {"status_code":status.HTTP_404_NOT_FOUND, "detail":str(f"Usuario no encontrado")}
#     #         )
        
#     #     if password !=confirm_password:
#     #         logger.error(f"Las contraseñas no coinciden.")
#     #         raise HTTPException(
#     #             {"status_code":status.HTTP_403_FORBIDDEN, "detail":str(f"Las contraseñas no coinciden")}
#     #         )
        
#     #     redis_client.delete(key)
#     #     usuario.password_hash=bcrypt.hash(password.encode("utf-8"))
#     #     await usuario.save()
#     #     logger.info(f"[SUCCESS] Contraseña cambiada por usuario: {usuario.id}")
#         return({"status_code":status.HTTP_200_OK,"detail":str(f"Su contraseña ha sido cambiada exitosamente.")})
          
    # except HTTPException as http_exc:
    #     raise http_exc
    # except Exception as e:
    #     logger.error(f"Error al cambiar la contraseña de el usuario: {str(e)}")
    #     raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al cambiar la contraseña de el usuario: {str(e)}")

async def renew_access_token(
    request: Request, 
    refresh_token: str
):

    '''
    Esta función renueva un token de acceso utilizando un token de actualización válido.

    Parámetros:

        request (Request): Objeto que realiza la solicitud HTTP.
        refresh_token: El token de actualización JWT, utilizado para generar un nuevo token de acceso.

    Retorno: dict: Un diccionario que contiene: El token de acceso JWT recién generado y el mismo token de actualización, si es válido.
    '''

    try:
        payload = jwt.decode(refresh_token, config.settings.jwt_secret_renew, algorithms=[config.settings.algorithm])
        username = payload.get("usuario")

        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Renovacion de token invalida")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Renovacion de token invalida")

    # generate new access token
    access_token = await create_access_token(request, payload)

    try:
        redis_client.hset("valid_tokens", payload.get("id"), access_token)
    except redis.exceptions.ConnectionError:
        logger.warning("Redis no disponible — token renovado sin registrar en sesiones activas")

    return {
        'access_token': access_token,
        'refresh_token': refresh_token
    }

async def revoke_token(
    token: str
):
    '''
    Esta función revoca un token determinado y cierra la sesión del usuario.
    
    Parámetros:

        token: El token de acceso JWT que se va a revocar.

    Retorno: La sesión se ha cerrado correctamente.
    '''

    await tokenOut(token)

    return {
        'detail': "Sesion cerrada"
    }
