"""
This module defines the `Endpoint` model.
"""

# python libraries
from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator


class Endpoint(models.Model):

    id = fields.IntField(pk=True)
    ruta = fields.CharField(max_length=255)
    metodo = fields.CharField(max_length=10)
    descripcion = fields.CharField(50)
    creacion = fields.DatetimeField(auto_now_add=True)
    actualizado = fields.DatetimeField(auto_now=True)

    async def save_model(self):
        await self.save()
        return self

    @classmethod
    async def create_model(cls, ruta: str,   metodo: str, descripcion: str):
        instance = cls(ruta=ruta, method=  metodo, description=descripcion)
        return await instance.save_model()

    async def update_model(self, ruta: str = None, metodo: str = None, descripcion: str = None):
        if ruta is not None:
            self.ruta = ruta
        if metodo is not None:
            self.metodo = metodo
        if descripcion is not None:
            self.descripcion = descripcion
        await self.save()
        return self

    async def delete_model(self):
        await self.delete()
        return self
   
    def get_by_rol(self):
        return {
            "id": self.id,
            "ruta": self.ruta,
            "metodo": self.metodo,
            "descripcion": self.descripcion,
            "creacion": self.creacion,
            "actualizado": self.actualizado
        }

    class Meta:
        table = "endpoints"

Endpoint_Pydantic = pydantic_model_creator(Endpoint, name="Endpoint")
EndpointIn_Pydantic = pydantic_model_creator(Endpoint, name="EndpointIn", exclude_readonly=True)

