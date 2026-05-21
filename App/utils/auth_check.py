from fastapi import Depends, HTTPException, status, Request
from App.models.usuario import Usuario
from urllib.parse import urlparse


from App.utils.logger import MyLogger

logger = MyLogger.__call__().get_logger()

# async def get_current_user(user_id: int) -> User:
#     user = await User.get_or_none(id=user_id).prefetch_related("roles__endpoints")
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user


async def check_permissions(user, request: Request):

    # # Obtener la ruta de la URL sin el query parameter

    base_path = request.url.path
    for key, value in request.path_params.items():
        base_path = base_path.replace(f"/{value}", f"/{{{key}}}", 1)


    for role in await user.roles.all():
        try:
            for endpoint in await role.endpoints.all():
                # if endpoint.path == request.url.path:
                if endpoint.ruta == base_path:
                    return True

        except Exception as e:
            # TODO: Averiguar como borrar esto sin afectar el flujo
            print('Exception: ', e)
    logger.error(f"El usuario {user.usuario} no cuenta con los suficientes permisos para {request.url.path}.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"El usuario {user.usuario} no cuenta con los suficientes permisos para {request.url.path}.")


async def endpoint_authorization(endpoints, endpoint_path: str):
    try:
        print("Endpoints:", endpoints)
        print("Looking for:", endpoint_path)
        for endpoint in endpoints:
            print(endpoint)
            if endpoint == endpoint_path:

                return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se cuenta con los suficientes permisos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print('Exception: ', e)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No se cuenta con los suficientes permisos.")