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
from App.utils.logger import MyLogger

# my models
from App.models.usuario import Usuario

# my settings
import App.core.settings as config

# my services
import App.services.token as Token

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

router = APIRouter(
    prefix="/token",
    tags=["token"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

User_Pydantic = pydantic_model_creator(Usuario, name='User')

logger = MyLogger.__call__().get_logger()

# # enfpoint to send otpcode
# @router.post('')
# async def generate_otpcode(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
#     '''
#     Esta función autentica a un usuario y genera tokens de acceso y actualización JWT.

#     Parámetros:

#         request (Request): Objeto que realiza la solicitud HTTP.
#         form_data: Las credenciales de inicio de sesión del usuario (nombre de usuario y contraseña).

#     Retorno: 
        
#         dict: Un diccionario que contiene: El token de acceso JWT y el token de actualización JWT.
#     '''
#     try:
#         user_obj = await authenticate_user(form_data.username, form_data.password)

#         # Generate payload for access_token and refresh_token
#       #  await generate_verification_code(user_obj.correo, user_obj.usuario, redis_client)
#         logger.info(f"[SUCCESS] Se genero un código de verificación para el usuario {user_obj.id}")
#         return {"detail": "Código de verificación enviado al correo electrónico"}
#     except Exception as e:
#         logger.debug("This is the problem" + str(e))
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=str(e)
#         )


# endpoint to generate token
@router.post('')
async def generate_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    '''
    Esta función autentica a un usuario y genera tokens de acceso y actualización JWT.

    Parámetros:

        request (Request): Objeto que realiza la solicitud HTTP.
        form_data: Las credenciales de inicio de sesión del usuario (nombre de usuario y contraseña).

    Retorno: 
        
        dict: Un diccionario que contiene: El token de acceso JWT y el token de actualización JWT.
    '''

    try:
        message = await Token.generate_token(
            request = request,
            form_data = form_data
        )
        return message

    except Exception as e:
        logger.debug("This is the problem" + str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    
# @router.post('/recovery')
# async def recovery_password(correo: str , entorno:str ,request: Request):
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
       
    #   #  correo = verify_magic_link_token(token)
    #     # key = f"magic_link:{correo}"
    #     # usuario = await Usuario.get_or_none(correo=correo, eliminado = False)

    #     jwt_token = redis_client.get(key)

    #     if not jwt_token:
    #         logger.error(f"token invalido o vencido: {jwt_token}")
    #         raise HTTPException(
    #             {"status_code":status.HTTP_400_BAD_REQUEST, "detail":str(f"Token vencido o invalido")}
    #         )
        
    #     if not usuario:
    #         logger.error(f"Usuario no encontrado: {usuario.id}")
    #         raise HTTPException(
    #             {"status_code":status.HTTP_404_NOT_FOUND, "detail":str(f"Usuario no encontrado")}
    #         )
        
    #     if password !=confirm_password:
    #         logger.error(f"Las contraseñas no coinciden.")
    #         raise HTTPException(
    #             {"status_code":status.HTTP_403_FORBIDDEN, "detail":str(f"Las contraseñas no coinciden")}
    #         )
        
    #     redis_client.delete(key)
    #     usuario.password_hash=bcrypt.hash(password.encode("utf-8"))
    #     await usuario.save()
    #     logger.info(f"[SUCCESS] Contraseña cambiada por usuario: {usuario.id}")
        # return({"status_code":status.HTTP_200_OK,"detail":str(f"Su contraseña ha sido cambiada exitosamente.")})
          
    # except HTTPException as http_exc:
    #     raise http_exc
    # except Exception as e:
    #     logger.error(f"Error al cambiar la contraseña de el usuario: {str(e)}")
    #     raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al cambiar la contraseña de el usuario: {str(e)}")

@router.post("/renovacion")
async def renew_access_token(request: Request, refresh_token: str):

    '''
    Esta función renueva un token de acceso utilizando un token de actualización válido.

    Parámetros:

        request (Request): Objeto que realiza la solicitud HTTP.
        refresh_token: El token de actualización JWT, utilizado para generar un nuevo token de acceso.

    Retorno: dict: Un diccionario que contiene: El token de acceso JWT recién generado y el mismo token de actualización, si es válido.
    '''

    message = await Token.renew_access_token(
        refresh_token = refresh_token,
        request = request,  
    )

    return message

@router.post("/revocacion")
async def revoke_token(token: str):
    '''
    Esta función revoca un token determinado y cierra la sesión del usuario.
    
    Parámetros:

        token: El token de acceso JWT que se va a revocar.

    Retorno: La sesión se ha cerrado correctamente.
    '''

    try:
        message = await Token.revoke_token(
            token = token
        )
        return message
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error en el cierre de sesion")
