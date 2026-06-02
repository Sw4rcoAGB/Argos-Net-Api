from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class AbrirBovedaSchema(BaseModel):
    cosecha_id:             int
    plazo_dias:             int
    porcentaje_reserva:     int = 5
    porcentaje_rendimiento: int = 12

    class Config:
        from_attributes = True


class RespuestaBovedaSchema(BaseModel):
    id:                     int
    cosecha_id:             int
    vault_id:               Optional[int]
    vault_address:          Optional[str]
    bcrop_address:          Optional[str]
    meta_financiamiento:    Decimal
    plazo_dias:             int
    porcentaje_reserva:     int
    porcentaje_rendimiento: int
    fecha_limite:           datetime
    estado:                 str
    total_recaudado:        Decimal
    tx_hash_open:           Optional[str]
    creacion:               Optional[datetime]

    class Config:
        from_attributes = True


class PaginacionBovedaSchema(BaseModel):
    page:     Optional[int]
    per_page: Optional[int]
    total:    int
    pages:    Optional[int]
    data:     list[RespuestaBovedaSchema]


class EstadoChainBovedaSchema(BaseModel):
    vault_address:      str
    status_chain:       int
    status_nombre:      str
    total_raised_usdc:  Decimal
    funding_goal_usdc:  Decimal
    funding_deadline:   datetime
    reserve_percent:    int
    yield_percent:      int
