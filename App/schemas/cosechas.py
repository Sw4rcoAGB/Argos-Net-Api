from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class CrearCosechaSchema(BaseModel):
    tipo_grano:        str
    hectareas:         Decimal
    rendimiento_kg:    int
    capital_requerido: Decimal
    fecha_cosecha:     datetime

    class Config:
        from_attributes = True


class RespuestaCosechaSchema(BaseModel):
    id:                int
    farm_id:           str
    propietario_id:    int
    tipo_grano:        str
    hectareas:         Decimal
    rendimiento_kg:    int
    capital_requerido: Decimal
    fecha_cosecha:     datetime
    nft_token_id:      Optional[int]
    tx_hash_mint:      Optional[str]
    estado:            str
    creacion:          Optional[datetime]

    class Config:
        from_attributes = True


class PaginacionCosechasSchema(BaseModel):
    page:     Optional[int]
    per_page: Optional[int]
    total:    int
    pages:    Optional[int]
    data:     list[RespuestaCosechaSchema]
