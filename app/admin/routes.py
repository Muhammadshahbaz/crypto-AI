from fastapi import APIRouter
from app.config import settings
from app.admin.service import (
    get_all_settings,
    save_risk_settings,
    list_exchanges,
    save_exchange,
    list_ai_settings,
    save_ai_settings,
    bot_status,
    set_bot_running,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/status")
async def admin_status():
    status = await bot_status()
    return {
        **status,
        "app": settings.app_name,
        "env_exchange": settings.exchange,
        "dry_run": settings.dry_run,
    }

@router.post("/bot/start")
async def start_bot():
    return await set_bot_running(True)

@router.post("/bot/stop")
async def stop_bot():
    return await set_bot_running(False)

@router.get("/settings")
async def admin_settings():
    return await get_all_settings()

@router.post("/risk")
async def admin_risk(payload: dict):
    return await save_risk_settings(payload)

@router.get("/exchanges")
async def admin_exchanges():
    return await list_exchanges()

@router.post("/exchanges")
async def admin_save_exchange(payload: dict):
    return await save_exchange(payload)

@router.get("/ai")
async def admin_ai():
    return await list_ai_settings()

@router.post("/ai")
async def admin_save_ai(payload: dict):
    return await save_ai_settings(payload)
