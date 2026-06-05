from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any


class ChatMessage(BaseModel):
    rol: Literal["user", "assistant"]
    contenido: str


class ChatRequest(BaseModel):
    mensaje: str
    historial: list[ChatMessage] = []
    contexto_cosecha: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    respuesta: str
