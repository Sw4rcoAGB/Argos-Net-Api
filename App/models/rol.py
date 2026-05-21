"""
This module defines the `Role` model.
"""

# python libraries
from tortoise import fields
from tortoise.models import Model
from typing import List

# models
from App.models.endpoint import Endpoint



class Rol(Model):
    
    id = fields.IntField(pk=True)
    nombre = fields.CharField(max_length=255)
    descripcion = fields.CharField(max_length=255)
    eliminado = fields.BooleanField(default=False)
    endpoints: fields.ManyToManyRelation["Endpoint"] = fields.ManyToManyField(
        "models.Endpoint",
        related_name="roles",
        through="role_endpoints"
    )
    creacion = fields.DatetimeField(auto_now_add=True)
    actualizacion = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "roles"

    async def get_endpoints(self) -> List[Endpoint]:
        return await self.endpoints.all()

