from typing import Optional, List
from pydantic import BaseModel


class EndpointBase(BaseModel):
    ruta: Optional[str]
    metodo: Optional[str]
    descripcion: Optional[str]

    class Config:
        from_attributes = True

class RespuestaEndpointSchema(EndpointBase):
    id: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "ruta": "/usuarios",
                "metodo": "GET",
                "descripcion": "Obtener todos los usuarios"
            }
        }
    }

class RespuestaEndpointSchema(EndpointBase):
    id: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "ruta": "/usuarios",
                "metodo": "GET",
                "descripcion": "Obtener todos los usuarios"
            }
        }
    }

class PaginacionEdnpointSchema(BaseModel):
    page: Optional[int] = None
    per_page: Optional[int] = None
    total: int
    pages: Optional[int] = None
    data: List[RespuestaEndpointSchema]

    model_config = {
        "json_schema_extra": {
            "example": {
                "page": 1,
                "per_page": 10,
                "total": 2,
                "pages": 20,
                "data": [
                    {"id": 1,"ruta": "/usuarios","metodo": "GET","descripcion": "obtener usuarios"},
                    {"id": 2,"ruta": "/usuarios","metodo": "POST","descripcion": "crear usuario"},
                ]
            }
        }
    }