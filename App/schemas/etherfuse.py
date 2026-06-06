from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime


class IniciarOnboardingSchema(BaseModel):
    wallet_address: Optional[str] = None


class RespuestaOnboardingSchema(BaseModel):
    customer_id: str
    bank_account_id: str
    kyc_status: str
    presigned_url: Optional[str] = None


class RespuestaClienteSchema(BaseModel):
    id: int
    customer_id: str
    bank_account_id: Optional[str] = None
    kyc_status: str
    wallet_address: Optional[str] = None
    creacion: Optional[datetime] = None

    class Config:
        from_attributes = True


class ActualizarWalletSchema(BaseModel):
    wallet_address: str


class CrearQuoteSchema(BaseModel):
    tipo: str          # onramp | offramp
    source_asset: str  # MXN o identificador de CETES
    target_asset: str  # identificador de CETES o MXN
    amount: Decimal


class RespuestaQuoteSchema(BaseModel):
    quote_id: str
    tipo: str
    source_asset: str
    target_asset: str
    amount: Decimal
    exchange_rate: Optional[Decimal] = None
    fee_bps: Optional[int] = None
    fee_amount: Optional[Decimal] = None
    destination_amount: Optional[Decimal] = None
    expires_at: Optional[str] = None


class CrearOrdenSchema(BaseModel):
    quote_id: str
    wallet_address: str


class RespuestaOrdenSchema(BaseModel):
    id: int
    order_id: str
    quote_id: str
    tipo: str
    status: str
    source_asset: str
    target_asset: str
    source_amount: Decimal
    destination_amount: Optional[Decimal] = None
    exchange_rate: Optional[Decimal] = None
    fee_bps: Optional[int] = None
    fee_amount: Optional[Decimal] = None
    deposit_clabe: Optional[str] = None
    burn_transaction: Optional[str] = None
    status_page_url: Optional[str] = None
    creacion: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginacionOrdenesSchema(BaseModel):
    page: Optional[int] = None
    per_page: Optional[int] = None
    total: int
    pages: Optional[int] = None
    data: list[RespuestaOrdenSchema]


class WebhookEventSchema(BaseModel):
    event: str
    order_id: Optional[str] = None
    data: Optional[dict] = None
