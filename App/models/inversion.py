from tortoise import fields, models


class Inversion(models.Model):
    id               = fields.IntField(pk=True)
    inversor         = fields.ForeignKeyField("models.Usuario", related_name="inversiones")
    cosecha          = fields.ForeignKeyField("models.Cosecha", related_name="inversiones")
    monto_usdc       = fields.DecimalField(max_digits=18, decimal_places=6)
    bcrop_recibido   = fields.DecimalField(max_digits=18, decimal_places=6)
    tx_hash_deposit  = fields.CharField(max_length=66, null=True)
    reclamado        = fields.BooleanField(default=False)
    monto_reclamado  = fields.DecimalField(max_digits=18, decimal_places=6, null=True)
    tx_hash_claim    = fields.CharField(max_length=66, null=True)
    creacion         = fields.DatetimeField(auto_now_add=True, null=True)
    actualizacion    = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "inversiones"
