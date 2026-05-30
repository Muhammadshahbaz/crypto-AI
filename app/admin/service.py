from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import AdminSetting, ExchangeCredential
from app.admin.security import encrypt_secret, mask_secret

async def get_setting(key: str, default: str = "") -> str:
    async with AsyncSessionLocal() as db:
        row = await db.get(AdminSetting, key)
        return row.value if row else default

async def set_setting(key: str, value: str) -> dict:
    async with AsyncSessionLocal() as db:
        row = await db.get(AdminSetting, key)
        if not row:
            row = AdminSetting(key=key, value=str(value))
            db.add(row)
        else:
            row.value = str(value)
        await db.commit()
    return {"key": key, "value": value}

async def get_all_settings() -> dict:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(AdminSetting))).scalars().all()
    return {r.key: r.value for r in rows}

async def save_risk_settings(payload: dict) -> dict:
    allowed = [
        "max_risk_per_trade", "max_daily_loss", "max_weekly_loss",
        "max_concurrent_trades", "default_leverage", "max_leverage",
        "consensus_threshold", "min_confidence_score", "signal_confluence_required",
        "preferred_pairs",
    ]
    saved = {}
    for key in allowed:
        if key in payload:
            await set_setting(key, str(payload[key]))
            saved[key] = payload[key]
    return {"saved": saved}

async def list_exchanges() -> list[dict]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(ExchangeCredential).order_by(ExchangeCredential.id.desc()))).scalars().all()
    return [{
        "id": r.id,
        "exchange": r.exchange,
        "label": r.label,
        "market_type": r.market_type,
        "mode": r.mode,
        "enabled": r.enabled,
        "api_key": mask_secret(r.api_key_encrypted),
        "api_secret": mask_secret(r.api_secret_encrypted),
        "api_password": mask_secret(r.api_password_encrypted),
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    } for r in rows]

async def save_exchange(payload: dict) -> dict:
    exchange_id = payload.get("id")
    now_values = {
        "exchange": payload.get("exchange", "bitget").lower().strip(),
        "label": payload.get("label", "Default"),
        "market_type": payload.get("market_type", "spot"),
        "mode": payload.get("mode", "paper"),
        "enabled": bool(payload.get("enabled", True)),
    }

    async with AsyncSessionLocal() as db:
        row = await db.get(ExchangeCredential, exchange_id) if exchange_id else None
        if not row:
            row = ExchangeCredential(**now_values)
            db.add(row)
        else:
            for k, v in now_values.items():
                setattr(row, k, v)

        if payload.get("api_key"):
            row.api_key_encrypted = encrypt_secret(payload["api_key"])
        if payload.get("api_secret"):
            row.api_secret_encrypted = encrypt_secret(payload["api_secret"])
        if payload.get("api_password"):
            row.api_password_encrypted = encrypt_secret(payload["api_password"])

        await db.commit()
        await db.refresh(row)

    return {"id": row.id, "exchange": row.exchange, "label": row.label, "enabled": row.enabled}

async def list_ai_settings() -> dict:
    settings = await get_all_settings()
    return {
        "openai_enabled": settings.get("openai_enabled", "false"),
        "claude_enabled": settings.get("claude_enabled", "false"),
        "openai_api_key": "saved" if settings.get("openai_api_key") else "",
        "anthropic_api_key": "saved" if settings.get("anthropic_api_key") else "",
    }

async def save_ai_settings(payload: dict) -> dict:
    if "openai_enabled" in payload:
        await set_setting("openai_enabled", str(payload["openai_enabled"]).lower())
    if "claude_enabled" in payload:
        await set_setting("claude_enabled", str(payload["claude_enabled"]).lower())
    if payload.get("openai_api_key"):
        await set_setting("openai_api_key", encrypt_secret(payload["openai_api_key"]))
    if payload.get("anthropic_api_key"):
        await set_setting("anthropic_api_key", encrypt_secret(payload["anthropic_api_key"]))
    return await list_ai_settings()

async def bot_status() -> dict:
    settings = await get_all_settings()
    return {
        "running": settings.get("bot_running", "false") == "true",
        "active_exchange": settings.get("active_exchange", ""),
        "mode": settings.get("bot_mode", "paper"),
    }

async def set_bot_running(running: bool) -> dict:
    await set_setting("bot_running", "true" if running else "false")
    return await bot_status()
