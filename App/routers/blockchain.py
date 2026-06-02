from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

import App.services.blockchain as BlockchainService
from App.schemas.blockchain import BalanceSchema, TxStatusSchema
from App.utils.auth import get_current_user
from App.utils.auth_check import check_permissions
from App.utils.logger import MyLogger

router = APIRouter(
    prefix="/blockchain",
    tags=["blockchain"],
    responses={404: {"description": "Not found"}},
)
logger = MyLogger.__call__().get_logger()


@router.get("/balance/{address}", response_model=BalanceSchema)
async def get_balance(
    address: str,
    request: Request,
    user=Depends(get_current_user),
    vault_id: Optional[int] = None,
):
    """Consulta balances de ETH, USDC y bCROP (opcional: vault_id) para una dirección Ethereum."""
    logger_message = await check_permissions(user, request)
    try:
        return await BlockchainService.get_balances(address, logger_message, vault_id)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener balances: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/tx/{tx_hash}", response_model=TxStatusSchema)
async def get_tx_status(
    tx_hash: str,
    request: Request,
    user=Depends(get_current_user),
):
    """Consulta el estado de una transacción por su hash."""
    logger_message = await check_permissions(user, request)
    try:
        return await BlockchainService.get_tx_status(tx_hash, logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al consultar transacción: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/wallet", response_model=BalanceSchema)
async def get_api_wallet(
    request: Request,
    user=Depends(get_current_user),
):
    """Retorna la dirección y balances del API wallet (cuenta custodial)."""
    logger_message = await check_permissions(user, request)
    try:
        return await BlockchainService.get_api_wallet_info(logger_message)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"{logger_message} Error al obtener info del wallet: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
