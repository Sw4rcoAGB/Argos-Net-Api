from pydantic import BaseModel
from typing import Literal


class ChatMessage(BaseModel):
    rol: Literal["user", "assistant"]
    contenido: str


class ChatRequest(BaseModel):
    mensaje: str
    historial: list[ChatMessage] = []


class ChatResponse(BaseModel):
    respuesta: str
