from tortoise import fields, models


class Boveda(models.Model):
    id                      = fields.IntField(pk=True)
    cosecha                 = fields.OneToOneField("models.Cosecha", related_name="boveda")
    vault_id                = fields.IntField(null=True)
    vault_address           = fields.CharField(max_length=42, null=True)
    bcrop_address           = fields.CharField(max_length=42, null=True)
    meta_financiamiento     = fields.DecimalField(max_digits=18, decimal_places=6)
    plazo_dias              = fields.IntField()
    porcentaje_reserva      = fields.IntField(default=5)
    porcentaje_rendimiento  = fields.IntField(default=12)
    fecha_limite            = fields.DatetimeField()
    # PENDIENTE → OPEN → FUNDED → ACTIVE → LIQUIDATED / DEFAULTED
    estado                  = fields.CharField(max_length=20, default="PENDIENTE")
    total_recaudado         = fields.DecimalField(max_digits=18, decimal_places=6, default=0)
    tx_hash_open            = fields.CharField(max_length=66, null=True)
    creacion                = fields.DatetimeField(auto_now_add=True, null=True)
    actualizacion           = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "bovedas"
