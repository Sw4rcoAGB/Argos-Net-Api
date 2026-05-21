"""
This is the setup script to generate all the roles, endpoints and mermissions asociated with an admin user
"""

# libraries
from fastapi import FastAPI
from fastapi.routing import APIRoute
from passlib.hash import bcrypt

# models
from App.models.endpoint import Endpoint
from App.models.rol import Rol
from App.models.usuario import Usuario


# helpers
from App.utils.logger import MyLogger


# Create the logger
logger = MyLogger.__call__().get_logger()


async def create_routes(app: FastAPI):
    """
    Function to generate endpoints in database on startup.
    :return: route_list: list of endpoints
    """
    route_list = []
    _result_list = ""
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = ",".join(route.methods)
            endpoint = f"{route.path}"
            route_list.append(endpoint)

            exists = await Endpoint.filter(ruta=endpoint).exists()
            if exists:
                logger.debug(str(endpoint) + " existe, no es necesario crearlo.")
                # TODO: update if necessary
                continue
            else:
                # create
                logger.debug(str(endpoint) + "  endpoint creado...ok")
                endpoint_obj = Endpoint(
                    ruta=endpoint,
                    metodo=methods,
                    descripcion=""
                )
                await endpoint_obj.save()
            _role = await Rol.get(nombre="Admin")
            _endpoint_permission_obj = await _role.endpoints.add(endpoint_obj)
            logger.debug(str(endpoint) + ", role, " + str("Admin") + ":  endpoint permiso creado...ok")

    return _result_list


async def create_default_roles():
    """
    Function to generate basic roles on startup.
    :return: _result: Result message with roles list
    """

    exists = await Rol.filter(nombre="Admin").exists()
    if exists:
        # TODO: update if necessary
        logger.debug("El rol de administrador existe, no es necesario crearlo.")
        pass
    else:
        # create
        role_obj = Rol(
            nombre="Admin",
            descripcion="Administrador de Sistema"
        )
        await role_obj.save()
        logger.debug("Rol de administrador creado... ok")

    exists = await Rol.filter(nombre="user").exists()
    if exists:
        # TODO: update if necessary
        _result = logger.debug("El rol de usuario existe, no es necesario crearlo")
        pass
    else:
        # create
        role_obj = Rol(
            nombre="usuario",
            descripcion="Usuario de sistema"
        )
        await role_obj.save()
        logger.debug("Rol de usuario creado... ok")


async def create_default_admin():
    """
    Function to generate default admin
    :return: _result: ok message that the user was created or if already exists
    """

    exists = await Usuario.filter(usuario="Admin").exists()
    if exists:
        # TODO: update if necessary
        logger.debug("El usuario administrador existe, no hay necesidad de crear.")
        pass
    else:
        # create
        _user_obj = Usuario(
            usuario="Admin",
            nombres="Admin de Sistema",
            apellidos="Administrator",
            correo="admin@admin.com",
            password_hash=Usuario.hash_password("Password.."),
            activo=True
        )
        await _user_obj.save()
        logger.debug("Usuario administrador creado correctamente.")


async def assign_role_to_admin_user():
    """
    Asign the admin role to admin user
    :return:
    """

    _role_exists = await Rol.get_or_none(
        nombre="Admin"
    )

    _user_exists = await Usuario.get_or_none(
        usuario="Admin"
    )

    if _user_exists.usuario == "Admin" and _role_exists.nombre == "Admin":

        await _user_exists.roles.add(_role_exists)

    else:
        pass


async def assign_endpoint_to_admin_role():
    
    # Obtiene la lista de todos los endpoints
    _endpoints = await Endpoint.all()

    # Verifica si existe el rol "admin"
    _role_exists = await Rol.get_or_none(nombre="Admin")

    # Si existe el rol y hay endpoints en la base de datos
    if _role_exists and _endpoints:
        # Limpia las relaciones existentes (opcional)
        await _role_exists.endpoints.clear()
        # Agrega los endpoints al rol
        await _role_exists.endpoints.add(*_endpoints)
