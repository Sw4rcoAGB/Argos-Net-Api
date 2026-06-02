from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class BalanceSchema(BaseModel):
    address:       str
    eth_balance:   Decimal
    usdc_balance:  Decimal
    bcrop_balance: Optional[Decimal] = None


class TxStatusSchema(BaseModel):
    tx_hash:      str
    status:       str
    block_number: Optional[int] = None
    gas_used:     Optional[int] = None
