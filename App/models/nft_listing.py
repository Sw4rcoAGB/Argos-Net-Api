from tortoise import fields, models


class NftListing(models.Model):
    id               = fields.IntField(pk=True)
    cosecha          = fields.ForeignKeyField("models.Cosecha", related_name="listings")
    vendedor         = fields.ForeignKeyField("models.Usuario", related_name="nft_listings")
    token_id         = fields.IntField()
    contract_address = fields.CharField(max_length=42)
    precio           = fields.DecimalField(max_digits=18, decimal_places=6, null=True)
    currency         = fields.CharField(max_length=10, default="ETH")
    tipo             = fields.CharField(max_length=20, default="FIXED")  # FIXED | AUCTION
    estado           = fields.CharField(max_length=20, default="ACTIVE")  # ACTIVE | SOLD | CANCELLED
    # Rare Protocol on-chain listing ID
    listing_id       = fields.CharField(max_length=66, null=True)
    auction_end_time = fields.DatetimeField(null=True)
    tx_hash          = fields.CharField(max_length=66, null=True)
    creacion         = fields.DatetimeField(auto_now_add=True, null=True)
    actualizacion    = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "nft_listings"
