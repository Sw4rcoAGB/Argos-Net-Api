from tortoise import fields, models


class EtherfuseOrden(models.Model):
    id                 = fields.IntField(pk=True)
    cliente            = fields.ForeignKeyField("models.EtherfuseCliente", related_name="ordenes")
    order_id           = fields.CharField(max_length=36, unique=True)
    quote_id           = fields.CharField(max_length=36)
    tipo               = fields.CharField(max_length=10)   # onramp | offramp
    status             = fields.CharField(max_length=20, default="created")
    source_asset       = fields.CharField(max_length=100)
    target_asset       = fields.CharField(max_length=200)
    source_amount      = fields.DecimalField(max_digits=18, decimal_places=6)
    destination_amount = fields.DecimalField(max_digits=18, decimal_places=6, null=True)
    exchange_rate      = fields.DecimalField(max_digits=20, decimal_places=8, null=True)
    fee_bps            = fields.IntField(null=True)
    fee_amount         = fields.DecimalField(max_digits=18, decimal_places=6, null=True)
    deposit_clabe      = fields.CharField(max_length=30, null=True)
    burn_transaction   = fields.TextField(null=True)
    status_page_url    = fields.TextField(null=True)
    creacion           = fields.DatetimeField(auto_now_add=True, null=True)
    actualizacion      = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "etherfuse_ordenes"
