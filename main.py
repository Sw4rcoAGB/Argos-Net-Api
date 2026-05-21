"""
    Main application to run uvicorn server with FastAPIBase application
"""

# libraries
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.sessions import SessionMiddleware
from functools import lru_cache
from App.setup.setup import(
    create_routes,
    create_default_roles,
    create_default_admin,
    assign_role_to_admin_user,
    assign_endpoint_to_admin_role
)
from contextlib import asynccontextmanager

# routers
from App.routers import token
from App.routers import usuarios
from App.routers import roles
from App.routers import endpoints

# utils
from App.utils.logger import MyLogger

# configuration
import App.core.settings as settings
from App.core.database import init, close

# classes to secure docs and redoc
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
import secrets

# TODO: responder que es esto?
@lru_cache
def get_settings():
    return settings.Settings()

# Generate FastAPI Application
app = FastAPI(
    servers=[
        {"url": settings.settings.api_base_url, "descripcion": settings.settings.api_base_description},
    ],
    root_path_in_servers=False,
    title="FastAPI-Base",
    docs_url=None,
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

app.add_middleware(SessionMiddleware, secret_key=settings.settings.secret_key, max_age=60*60)

# SECURING: Securing /docs and /redoc paths

security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    correct_username = secrets.compare_digest(credentials.username, settings.settings.swagger_username)
    correct_password = secrets.compare_digest(credentials.password, settings.settings.swagger_password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/docs", response_class=HTMLResponse)
async def get_docs(username: str = Depends(get_current_username)) -> HTMLResponse:
    print(username)
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title="docs")


@app.get("/redoc", response_class=HTMLResponse)
async def get_redoc(username: str = Depends(get_current_username)) -> HTMLResponse:
    return get_redoc_html(openapi_url="/api/openapi.json", title="redoc")
# END SECURING: end of /redoc and /docs securing


# TODO: que hace la parte de Annotated y Depends?
# Routers to include from API

app.include_router(token.router)
app.include_router(usuarios.router)
app.include_router(roles.router)
app.include_router(endpoints.router)

# Create the logger
logger = MyLogger.__call__().get_logger()

# TODO: Que hace realmente esto?
origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@asynccontextmanager
async def lifespan(app:FastAPI):
    #T0d0 despues de aqui se inicializa 
    await init()
    if settings.settings.skip_setup == False:
        await create_default_roles()
        await create_routes(app)
        await create_default_admin()
        await assign_role_to_admin_user()
        await assign_endpoint_to_admin_role()

    yield
    #T0d0 despues de aqui se finaliza 
    await close()

if get_settings().create_configuration:
    app.router.lifespan_context = lifespan


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


