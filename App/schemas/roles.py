from pydantic import BaseModel
from typing import Optional, List


class RolBase(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None

    class Config:
        from_attributes = True

class RespuestaRolSchema(RolBase):
    id: int
    eliminado: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "nombre": "Usuario",
                "descripcion": "Rol de usuario",
            }
        }
    }

class PaginacionRolSchema(BaseModel):
    page: Optional[int] = None
    per_page: Optional[int] = None
    total: int
    pages: Optional[int] = None
    data: List[RespuestaRolSchema]

    model_config = {
        "json_schema_extra": {
            "example": {
                "page": 1,
                "per_page": 10,
                "total": 2,
                "pages": 20,
                "data": [
                    {"id": 1,"nombre": "Admin","descripcion": "Admin"},
                    {"id": 2,"nombre": "Usuario","descripcion": "Usuario"},
                ]
            }
        }
    }
    