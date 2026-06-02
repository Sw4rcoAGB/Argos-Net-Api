from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class InvertirSchema(BaseModel):
    cosecha_id: int
    monto_usdc: Decimal

    class Config:
        from_attributes = True


class RespuestaInversionSchema(BaseModel):
    id:              int
    inversor_id:     int
    cosecha_id:      int
    monto_usdc:      Decimal
    bcrop_recibido:  Decimal
    tx_hash_deposit: Optional[str]
    reclamado:       bool
    monto_reclamado: Optional[Decimal]
    tx_hash_claim:   Optional[str]
    creacion:        Optional[datetime]

    class Config:
        from_attributes = True


class PaginacionInversionesSchema(BaseModel):
    page:     Optional[int]
    per_page: Optional[int]
    total:    int
    pages:    Optional[int]
    data:     list[RespuestaInversionSchema]
