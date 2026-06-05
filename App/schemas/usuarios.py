from pydantic import BaseModel
from typing import Optional
from typing import List
from datetime import datetime

class UsuarioBase(BaseModel):
    usuario: str
    nombres: str
    apellidos: Optional[str] = None
    correo: str
    
    class Config:
        from_attributes = True

class CrearUsuarioSchema(UsuarioBase):
    password_hash: Optional[str] = None
    rol: str = "inversor"

class ActualizarUsuario(BaseModel):
    usuario: Optional[str] = None
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    correo: Optional[str] = None
    password_hash: Optional[str] = None
    
    class Config:
        from_attributes = True
    

class RespuestaUsuario(UsuarioBase):
    eliminado: bool
    id: int
    rol: str = "inversor"

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "usuario": "John Doe",
                "nombres": "John",
                "apellidos": "Doe",
                "correo": "john@example.com",
                "telefono": "1234567890",
                "activo": True
            }
        }
    }

class UsuarioRolSchema(BaseModel):
    user_id: int
    role_id: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": 1,
                "role_id": 1,
            }
        }
    }

class PaginacionUsuariosSchema(BaseModel):
    page: Optional[int] = None
    per_page: Optional[int] = None
    total: int
    pages: Optional[int] = None
    data: List[RespuestaUsuario]

    model_config = {
        "json_schema_extra": {
            "example": {
                "page": 1,
                "per_page": 10,
                "total": 2,
                "pages": 20,
                "data": [
                    {"id": 1,"usuario": "John Doe","nombres": "John","apellidos": "Doe","correo": "john@example.com","telefono": "1234567890","activo": True},
                    {"id": 2,"usuario": "Ana López","nombres": "Ana","apellidos": "López","correo": "ana@example.com","telefono": "1234567890","activo": True},
                ]
            }
        }
    }