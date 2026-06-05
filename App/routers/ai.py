from fastapi import APIRouter, Depends, HTTPException, status
import google.generativeai as genai

from App.core.settings import settings
from App.schemas.ai import ChatRequest, ChatResponse
from App.utils.auth import get_current_user
from App.utils.logger import MyLogger

router = APIRouter(prefix="/ai", tags=["ai"])
logger = MyLogger.__call__().get_logger()

SYSTEM_PROMPT = """Eres AgroAI, el asistente inteligente de AgroNest — una plataforma DeFi agrícola descentralizada.

AgroNest permite:
- A los AGRICULTORES registrar cosechas como NFTs y obtener financiamiento de inversores en USDC.
- A los INVERSORES financiar cosechas y recibir rendimientos en bCROP tokens.

Conceptos clave:
- USDC: Stablecoin usada para realizar inversiones en cosechas.
- bCROP: Token de rendimiento (Bond Crop) que acredita la inversión y el futuro retorno.
- NFT: Cada cosecha se mintea como un token no fungible en blockchain (Sepolia testnet).
- Bóveda (vault): Contrato inteligente que gestiona los fondos de una cosecha.
- Oracle: Administrador que avanza el estado de las cosechas manualmente.

Estados de una cosecha: PENDIENTE → MINTED → ACTIVE → MATURE → LIQUIDATED (exitosa) o DEFAULTED (pérdida).

Responde siempre en español, de forma clara, concisa y amigable. Si el usuario hace preguntas técnicas de DeFi o blockchain, explica los conceptos de forma sencilla. Si pide ayuda para usar la plataforma, guíalo paso a paso."""

_MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest"]


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, _=Depends(get_current_user)):
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de IA no está configurado.",
        )
    try:
        genai.configure(api_key=settings.gemini_api_key)
        history = [
            {"role": "user" if m.rol == "user" else "model", "parts": [m.contenido]}
            for m in req.historial
        ]

        if req.contexto_cosecha:
            ctx = req.contexto_cosecha
            system = SYSTEM_PROMPT + f"""

CONTEXTO ACTUAL DE LA COSECHA:
- Tipo: {ctx.get('tipo_grano', 'N/A')}
- Hectáreas: {ctx.get('hectareas', 'N/A')}
- Capital requerido: ${ctx.get('capital_requerido', 'N/A')} USDC
- Estado actual: {ctx.get('estado', 'N/A')}
- Rendimiento estimado: {ctx.get('rendimiento_kg', 'N/A')} kg
El usuario está viendo esta cosecha ahora mismo. Responde con análisis específico de estos datos."""
        else:
            system = SYSTEM_PROMPT

        last_error: Exception | None = None
        for model_name in _MODELS:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system,
                )
                chat_session = model.start_chat(history=history)
                response = chat_session.send_message(req.mensaje)
                return ChatResponse(respuesta=response.text)
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                last_error = e

        raise last_error  # type: ignore[misc]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al contactar el servicio de IA.",
        )
