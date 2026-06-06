from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import HTTPException, status

from App.core.settings import settings
from App.utils.logger import MyLogger

logger = MyLogger.__call__().get_logger()


def _headers() -> dict:
    return {
        "Authorization": settings.etherfuse_api_key,
        "Content-Type": "application/json",
    }


def _base() -> str:
    return settings.etherfuse_base_url.rstrip("/")


def _is_mock() -> bool:
    return not settings.etherfuse_api_key


# ---------------------------------------------------------------------------
# Mock helpers — usados cuando ETHERFUSE_API_KEY no está configurado
# ---------------------------------------------------------------------------

_MOCK_ASSETS = [
    {
        "asset": "CETES28",
        "name": "CETES 28 días",
        "currency": "MXN",
        "type": "onchain",
        "network": "solana",
        "decimals": 6,
        "annualYield": 10.25,
        "minimumAmount": 100,
        "contract": "EF28CEThBSMock1111111111111111111111111111",
    },
    {
        "asset": "CETES91",
        "name": "CETES 91 días",
        "currency": "MXN",
        "type": "onchain",
        "network": "solana",
        "decimals": 6,
        "annualYield": 10.52,
        "minimumAmount": 100,
        "contract": "EF91CEThBSMock2222222222222222222222222222",
    },
    {
        "asset": "CETES182",
        "name": "CETES 182 días",
        "currency": "MXN",
        "type": "onchain",
        "network": "solana",
        "decimals": 6,
        "annualYield": 10.68,
        "minimumAmount": 100,
        "contract": "EF182ETMock333333333333333333333333333333",
    },
]


def _mock_quote(tipo: str, source: str, target: str, amount: Decimal) -> dict:
    rate = Decimal("17.25")  # tipo de cambio MXN/USD demo
    fee_bps = 50
    if tipo == "onramp":
        dest_amount = (amount / rate) * Decimal("0.995")
    else:
        dest_amount = amount * rate * Decimal("0.995")
    fee_amount = amount * Decimal("0.005")
    return {
        "quoteId": f"mock-quote-{uuid4().hex[:12]}",
        "type": tipo,
        "sourceAsset": source,
        "targetAsset": target,
        "amount": str(amount),
        "destinationAmount": str(dest_amount.quantize(Decimal("0.000001"))),
        "exchangeRate": str(rate),
        "feeBps": fee_bps,
        "feeAmount": str(fee_amount.quantize(Decimal("0.01"))),
        "expiresAt": "2099-01-01T00:00:00Z",
    }


def _mock_order(quote_id: str, wallet: str) -> dict:
    order_id = f"mock-order-{uuid4().hex[:12]}"
    return {
        "orderId": order_id,
        "quoteId": quote_id,
        "type": "onramp",
        "status": "created",
        "sourceAsset": "MXN",
        "targetAsset": "CETES28",
        "sourceAmount": "1000",
        "destinationAmount": "57.971014",
        "exchangeRate": "17.25",
        "feeBps": 50,
        "feeAmount": "5.00",
        "depositClabe": "646180320100000001",
        "walletAddress": wallet,
        "statusPage": f"https://sandbox.etherfuse.com/orders/{order_id}",
    }


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

async def get_presigned_url(customer_id: str, bank_account_id: str) -> str:
    if _is_mock():
        logger.warning("Etherfuse MOCK MODE: get_presigned_url")
        return f"https://sandbox.etherfuse.com/kyc/{customer_id}?mock=true"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_base()}/ramp/customer/onboard",
            headers=_headers(),
            json={"customerId": customer_id, "bankAccountId": bank_account_id},
        )
    if resp.status_code not in (200, 201):
        logger.error(f"Etherfuse onboard error {resp.status_code}: {resp.text}")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Etherfuse KYC error: {resp.text}")
    return resp.json().get("presignedUrl") or resp.json().get("url") or ""


async def get_assets() -> list:
    if _is_mock():
        logger.warning("Etherfuse MOCK MODE: get_assets")
        return _MOCK_ASSETS

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{_base()}/ramp/assets", headers=_headers())
    if resp.status_code != 200:
        logger.error(f"Etherfuse assets error {resp.status_code}: {resp.text}")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Etherfuse assets error: {resp.text}")
    return resp.json()


async def create_quote(
    tipo: str,
    source_asset: str,
    target_asset: str,
    amount: Decimal,
    customer_id: str | None = None,
) -> dict:
    if _is_mock():
        logger.warning("Etherfuse MOCK MODE: create_quote")
        return _mock_quote(tipo, source_asset, target_asset, amount)

    body: dict = {
        "type": tipo,
        "sourceAsset": source_asset,
        "targetAsset": target_asset,
        "amount": str(amount),
    }
    if customer_id:
        body["customerId"] = customer_id

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{_base()}/ramp/quote", headers=_headers(), json=body)
    if resp.status_code not in (200, 201):
        logger.error(f"Etherfuse quote error {resp.status_code}: {resp.text}")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Etherfuse quote error: {resp.text}")
    return resp.json()


async def create_order(
    quote_id: str,
    customer_id: str,
    bank_account_id: str,
    wallet_address: str,
) -> dict:
    if _is_mock():
        logger.warning("Etherfuse MOCK MODE: create_order")
        return _mock_order(quote_id, wallet_address)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_base()}/ramp/order",
            headers=_headers(),
            json={
                "quoteId": quote_id,
                "customerId": customer_id,
                "bankAccountId": bank_account_id,
                "walletAddress": wallet_address,
            },
        )
    if resp.status_code not in (200, 201):
        logger.error(f"Etherfuse order error {resp.status_code}: {resp.text}")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Etherfuse order error: {resp.text}")
    return resp.json()


async def simulate_fiat_received(order_id: str) -> dict:
    if _is_mock():
        logger.warning("Etherfuse MOCK MODE: simulate_fiat_received")
        return {"orderId": order_id, "status": "funded", "mock": True}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_base()}/ramp/order/fiat_received",
            headers=_headers(),
            json={"orderId": order_id},
        )
    if resp.status_code not in (200, 201):
        logger.error(f"Etherfuse simulate error {resp.status_code}: {resp.text}")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Etherfuse simulate error: {resp.text}")
    return resp.json()


async def register_webhook(url: str) -> dict:
    if _is_mock():
        logger.warning("Etherfuse MOCK MODE: register_webhook")
        return {"webhookId": f"mock-wh-{uuid4().hex[:8]}", "url": url, "mock": True}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_base()}/ramp/webhook",
            headers=_headers(),
            json={"url": url, "events": ["order_updated"]},
        )
    if resp.status_code not in (200, 201):
        logger.error(f"Etherfuse webhook error {resp.status_code}: {resp.text}")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=f"Etherfuse webhook error: {resp.text}")
    return resp.json()
