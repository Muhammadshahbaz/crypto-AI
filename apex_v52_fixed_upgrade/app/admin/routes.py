from fastapi import APIRouter, Body
from app.admin.service import (
    get_all_settings,
    save_admin_settings,
    get_exchange_settings,
    save_exchange_settings,
    get_risk_settings,
    save_risk_settings,
    get_ai_settings,
    save_ai_settings,
    get_telegram_settings,
    save_telegram_settings,
    list_exchanges,
    test_exchange_connection,
    get_trading_mode,
    save_trading_mode,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/settings")
async def api_get_all_settings():
    return await get_all_settings()

@router.post("/settings")
async def api_save_admin_settings(payload: dict = Body(default={})): 
    return await save_admin_settings(payload)

@router.get("/exchanges")
async def api_list_exchanges():
    return await list_exchanges()

@router.get("/exchange-settings")
async def api_get_exchange_settings():
    return await get_exchange_settings()

@router.post("/exchange-settings")
async def api_save_exchange_settings(payload: dict = Body(default={})): 
    return await save_exchange_settings(payload)

@router.post("/exchange-test/{exchange}")
async def api_test_exchange(exchange: str):
    return await test_exchange_connection(exchange)

@router.get("/trading-mode")
async def api_get_trading_mode():
    return await get_trading_mode()

@router.post("/trading-mode")
async def api_save_trading_mode(payload: dict = Body(default={})): 
    return await save_trading_mode(payload)

@router.get("/risk")
async def api_get_risk_settings():
    return await get_risk_settings()

@router.post("/risk")
async def api_save_risk_settings(payload: dict = Body(default={})): 
    return await save_risk_settings(payload)

@router.get("/ai")
async def api_get_ai_settings():
    return await get_ai_settings()

@router.post("/ai")
async def api_save_ai_settings(payload: dict = Body(default={})): 
    return await save_ai_settings(payload)

@router.get("/telegram")
async def api_get_telegram_settings():
    return await get_telegram_settings()

@router.post("/telegram")
async def api_save_telegram_settings(payload: dict = Body(default={})): 
    return await save_telegram_settings(payload)
