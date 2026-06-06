from tortoise import fields, models


class Cosecha(models.Model):
    id                = fields.IntField(pk=True)
    farm_id           = fields.CharField(max_length=100, unique=True)
    propietario       = fields.ForeignKeyField("models.Usuario", related_name="cosechas")
    tipo_grano        = fields.CharField(max_length=100)
    hectareas         = fields.DecimalField(max_digits=10, decimal_places=2)
    rendimiento_kg    = fields.IntField()
    capital_requerido = fields.DecimalField(max_digits=18, decimal_places=6)
    fecha_cosecha     = fields.DatetimeField()
    nft_token_id      = fields.IntField(null=True)
    tx_hash_mint      = fields.CharField(max_length=66, null=True)
    # PENDIENTE → MINTED → ACTIVE → MATURE → LIQUIDATED / DEFAULTED
    estado            = fields.CharField(max_length=20, default="PENDIENTE")
    latitud           = fields.FloatField(null=True, default=None)
    longitud          = fields.FloatField(null=True, default=None)
    eliminado         = fields.BooleanField(default=False)
    creacion          = fields.DatetimeField(auto_now_add=True, null=True)
    actualizacion     = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "cosechas"
