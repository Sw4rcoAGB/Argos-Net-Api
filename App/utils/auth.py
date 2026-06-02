""" Authentication utilities """

# python libraries
import jwt  # pip3 install pyjwt
from fastapi import Depends, HTTPException, status  # , Body
from fastapi.security import OAuth2PasswordBearer, OAuth2AuthorizationCodeBearer  # , OAuth2PasswordRequestForm
from tortoise.contrib.pydantic import pydantic_model_creator
from functools import lru_cache
from datetime import datetime
import time
import redis
from tortoise.exceptions import DoesNotExist

# utils
from App.utils.auth_check import  endpoint_authorization

# my models
from App.models.usuario import Usuario



# my settings
import App.core.settings as config


# TODO: responder que es esto?
@lru_cache
def get_settings():
    return config.Settings()


# get settings
settings = get_settings()

# create authentication objects
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')
User_Pydantic = pydantic_model_creator(Usuario, name='User')

redis_client = redis.StrictRedis(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db)

# authenticate_user function to return if a user is valid or not
async def authenticate_user(username: str, password: str):
    from App.models.usuario import Usuario
    try:
        # Try by username first, then fall back to email
        user = await Usuario.get_or_none(usuario=username, eliminado=False)
        if user is None:
            user = await Usuario.get_or_none(correo=username, eliminado=False)

        if not user:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Credenciales Invalidas'
            )
        
        if user.eliminado == True:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Usuario Eliminado'
            )
           
        # convert the user from tortoise orm to user_obj which is a pydantic object
        user_obj = await User_Pydantic.from_tortoise_orm(user)

        user_obj.__dict__.update({
           # "employee_id": user.employee_id
        })

        user_obj.__dict__.update({"endpoints": await get_endpoints(user)})
        # remove password_hash from dictionary to generate bearer token
        del user_obj.__dict__['password_hash']
        del user_obj.__dict__['actualizacion']
        del user_obj.__dict__['creacion']


    except DoesNotExist as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Credenciales Invalidas'
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error" + str(e)
        )
    if not user.verify_password(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Credenciales Invalidas'
        )
   
    return user_obj


async def get_endpoints(user: Usuario):
    endpoints = []
    for role in await user.roles.all():
        try:
            for endpoint in await role.endpoints.all():
                print(endpoint.path)
                endpoints.append(endpoint.path)
        except Exception as e:
            print('Exception: ', e)
    return endpoints


# function to get user information based on oauth_scheme and the jwt token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        revoked = redis_client.get(token)
        # VERIFY IF THE TOKEN IS REVOKED
        if revoked is not None:
            raise ValueError(
                {
                    "status": 498,
                    "detail": str(f"Sesion expirada, inicie sesion nuevamente.")
                }
            )

        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.algorithm])

        user = await Usuario.get(id=payload.get('id'))

        valid_token = redis_client.hget("valid_tokens", f"{payload.get('id')}").decode('utf-8')
        # CHECK IF IT ISN'T THE CURRENT TOKEN
        if valid_token  is None or valid_token != token:
            raise ValueError(
                {
                    "status": 498,
                    "detail": str(f"Sesion expirada, inicie sesion nuevamente.")
                }
            )
        del user.password_hash
        return user

    except ValueError as e:
        e = e.args[0]
        
        raise HTTPException(
            status_code=e["status"],
            detail=e["detail"]
        )
    except Exception as e:
        print(e)
        # use HTTPException to rise an error based in class status from fastapi,
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate credentials: ' + str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

async def authorization(token: str = Depends(oauth2_scheme)):
    try:

        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.algorithm])

        endpoints = payload.get("endpoints")
        # user = await User.get(id=payload.get('id'))

        authorized = await endpoint_authorization(endpoints, endpoint_path="/users/some-secure-endpoint")

        return authorized

    except Exception as e:
        print(e)
        # use HTTPException to rise an error based in class status from fastapi,
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate credentials: ' + str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

async def tokenOut(token: str):
    redis_client.set(token, "revoked", ex=settings.redis_exp)
    return {"detail": "Token revoked"}
