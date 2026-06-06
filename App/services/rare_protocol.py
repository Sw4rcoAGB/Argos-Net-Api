"""
Rare Protocol / SuperRare marketplace service.

Handles listing creation, offer tracking, and on-chain interaction
with the Rare Protocol marketplace contracts.

Contract interactions (listing/buying) are executed client-side via MetaMask.
This service manages the off-chain index and minting via the Rare CLI contract.
"""
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status

from App.core.settings import settings
from App.models.cosecha import Cosecha
from App.models.nft_listing import NftListing
from App.models.usuario import Usuario
from App.utils.logger import MyLogger

logger = MyLogger.__call__().get_logger()

# Rare Protocol SuperRare Bazaar addresses (testnet)
# Deploy via: rare deploy --network base-sepolia
RARE_CONTRACT_ADDRESS = settings.rare_contract_address


async def crear_listing(
    cosecha: Cosecha,
    vendedor: Usuario,
    precio: Decimal,
    currency: str,
    tipo: str,
    auction_horas: Optional[int],
) -> NftListing:
    if not cosecha.nft_token_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="La cosecha no tiene un NFT minteado. Registra y mintea la cosecha primero.",
        )
    if cosecha.propietario_id != vendedor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Solo el propietario puede listar este NFT.")

    existing = await NftListing.get_or_none(cosecha_id=cosecha.id, estado="ACTIVE")
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Este NFT ya tiene un listing activo.")

    auction_end = None
    if tipo == "AUCTION" and auction_horas:
        from datetime import datetime, timedelta, timezone
        auction_end = datetime.now(timezone.utc) + timedelta(hours=auction_horas)

    listing = NftListing(
        cosecha_id=cosecha.id,
        vendedor_id=vendedor.id,
        token_id=cosecha.nft_token_id,
        contract_address=RARE_CONTRACT_ADDRESS or "",
        precio=precio,
        currency=currency,
        tipo=tipo,
        estado="ACTIVE",
        auction_end_time=auction_end,
    )
    await listing.save()
    logger.info(f"Listing creado para cosecha {cosecha.id}, token #{cosecha.nft_token_id}")
    return listing


async def confirmar_listing_onchain(listing_id: int, chain_listing_id: str, tx_hash: str) -> NftListing:
    listing = await NftListing.get_or_none(id=listing_id)
    if not listing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Listing no encontrado.")
    listing.listing_id = chain_listing_id
    listing.tx_hash = tx_hash
    await listing.save()
    return listing


async def cancelar_listing(listing_id: int, user: Usuario) -> NftListing:
    listing = await NftListing.get_or_none(id=listing_id, vendedor_id=user.id, estado="ACTIVE")
    if not listing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Listing activo no encontrado.")
    listing.estado = "CANCELLED"
    await listing.save()
    return listing


async def marcar_vendido(listing_id: int, tx_hash: str) -> NftListing:
    listing = await NftListing.get_or_none(id=listing_id, estado="ACTIVE")
    if not listing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Listing no encontrado.")
    listing.estado = "SOLD"
    listing.tx_hash = tx_hash
    await listing.save()
    return listing


async def obtener_listings(
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    estado: str = "ACTIVE",
) -> tuple[list[NftListing], int]:
    query = NftListing.filter(estado=estado)
    total = await query.count()

    if page and per_page:
        offset = (page - 1) * per_page
        listings = await query.offset(offset).limit(per_page).prefetch_related("cosecha", "vendedor")
    else:
        listings = await query.prefetch_related("cosecha", "vendedor")

    return listings, total


async def obtener_listing(listing_id: int) -> NftListing:
    listing = await NftListing.get_or_none(id=listing_id)
    if not listing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Listing no encontrado.")
    await listing.fetch_related("cosecha", "vendedor")
    return listing
