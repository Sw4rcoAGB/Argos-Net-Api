from uuid import uuid4
from tortoise import fields, models


class EtherfuseCliente(models.Model):
    id              = fields.IntField(pk=True)
    usuario         = fields.ForeignKeyField("models.Usuario", related_name="etherfuse_clientes")
    customer_id     = fields.UUIDField(default=uuid4, unique=True)
    bank_account_id = fields.UUIDField(null=True)
    kyc_status      = fields.CharField(max_length=20, default="PENDING")
    wallet_address  = fields.CharField(max_length=42, null=True)
    presigned_url   = fields.TextField(null=True)
    creacion        = fields.DatetimeField(auto_now_add=True, null=True)
    actualizacion   = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "etherfuse_clientes"
