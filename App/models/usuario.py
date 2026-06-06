"""
This module defines the `User` model.
"""

# python libraries
from tortoise import fields, models
import bcrypt
from typing import List

# from api.models import Role
from App.models.rol import Rol


class Usuario(models.Model):
   
    id = fields.IntField(pk=True)
    usuario = fields.CharField(255, unique=True)
    nombres = fields.CharField(255)
    apellidos = fields.CharField(255)
    correo = fields.CharField(255, unique= True)
    password_hash = fields.CharField(255)
    roles: fields.ManyToManyRelation[Rol] = fields.ManyToManyField(
        "models.Rol",
        related_name="usuarios",
        through="usuarios_roles",
        forward_key="rol_id",
        backward_key="usuario_id"
    )
    rol            = fields.CharField(max_length=20, default="inversor")
    wallet_address = fields.CharField(max_length=42, null=True, default=None)
    eliminado = fields.BooleanField(default=False)
    creacion = fields.DatetimeField(auto_now_add=True, null=True)
    actualizacion = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "usuarios"

    @staticmethod
    def hash_password(password):
        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds = 12)
        )
        return hashed.decode("utf-8")
        
    def verify_password(self, password) -> bool:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            self.password_hash.encode("utf-8"),
        )

    async def get_roles(self) -> List[Rol]:
        return await self.roles.all()

    async def get_role(self, role) -> List[Rol]:
        return await self.roles.filter(id=role)

    async def remove_role(self):
        return await self.roles.remove()

