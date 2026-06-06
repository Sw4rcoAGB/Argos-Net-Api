from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

import App.services.oracle as OracleService
from App.utils.auth import get_current_user
from App.utils.auth_check import check_permissions
from App.utils.logger import MyLogger

router = APIRouter(
    prefix="/oracle",
    tags=["oracle"],
    responses={404: {"description": "Not found"}},
)
logger = MyLogger.__call__().get_logger()


class AvanzarEstadoSchema(BaseModel):
    cosecha_id: int
    exito: bool = True


class ChainlinkResolverSchema(BaseModel):
    cosecha_id: int
    lat: str = "19.4326"
    lon: str = "-99.1332"


@router.post("/avanzar")
async def avanzar_estado(
    data: AvanzarEstadoSchema,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Admin-only: avanza el estado del ciclo de vida de una cosecha en el oráculo simulado.
    - exito=true  → LIQUIDATED (la cosecha se completó y vendió exitosamente)
    - exito=false → DEFAULTED  (pérdida de cosecha, inversores recuperan solo la reserva)
    """
    logger_message = await check_permissions(user, request)
    try:
        return await OracleService.avanzar_estado(data.cosecha_id, data.exito, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al avanzar estado del oráculo: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/avanzar-chainlink")
async def avanzar_chainlink(
    data: ChainlinkResolverSchema,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Admin-only: solicita resolución automática de una bóveda MATURE vía Chainlink Functions.

    Envía una transacción que hace que los nodos Chainlink consulten Open-Meteo (sin API key)
    para determinar si hubo sequía en las coordenadas indicadas. El callback on-chain llega
    en ~30 segundos y dispara liquidate() o triggerDefault() según precipitación real.

    Requiere ChainlinkOracle.sol desplegado (ver contracts/contracts/ChainlinkOracle.sol).
    lat/lon: coordenadas de la zona agrícola (default: CDMX para demo).
    """
    logger_message = await check_permissions(user, request)
    try:
        return await OracleService.solicitar_resolucion_chainlink(
            data.cosecha_id, data.lat, data.lon, logger_message
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error("%s Error al solicitar resolución Chainlink: %s", logger_message, e)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/estado/{vault_address}")
async def estado_oracle(
    vault_address: str,
    request: Request,
    user=Depends(get_current_user),
):
    """Consulta el estado actual del oráculo para un vault_address."""
    logger_message = await check_permissions(user, request)
    try:
        return await OracleService.obtener_estado_oracle(vault_address, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al consultar estado del oráculo: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
