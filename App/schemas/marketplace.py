from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime


class CrearListingSchema(BaseModel):
    cosecha_id: int
    precio: Decimal
    currency: str = "ETH"
    tipo: str = "FIXED"      # FIXED | AUCTION
    auction_horas: Optional[int] = None


class RespuestaListingSchema(BaseModel):
    id: int
    cosecha_id: int
    vendedor_id: int
    token_id: int
    contract_address: str
    precio: Optional[Decimal] = None
    currency: str
    tipo: str
    estado: str
    listing_id: Optional[str] = None
    auction_end_time: Optional[datetime] = None
    tx_hash: Optional[str] = None
    creacion: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginacionListingsSchema(BaseModel):
    page: Optional[int] = None
    per_page: Optional[int] = None
    total: int
    pages: Optional[int] = None
    data: list[RespuestaListingSchema]


class CrearOfertaSchema(BaseModel):
    listing_id: int
    monto: Decimal
    currency: str = "ETH"
    tx_hash: Optional[str] = None
