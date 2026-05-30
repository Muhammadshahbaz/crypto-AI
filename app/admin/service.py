from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.database.models import BotState
from app.config import settings


SAFE_ENV_KEYS = {
    "APP_NAME",
    "EXCHANGE",
    "TRADING_MODE",
    "DRY_RUN",
    "BINANCE_TESTNET",
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "BINANCE_MARKET_TYPE",
    "BITGET_API_KEY",
    "BITGET_API_SECRET",
    "BITGET_API_PASSWORD",
    "BITGET_MARKET_TYPE",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AI_OPENAI_ENABLED",
    "AI_CLAUDE_ENABLED",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "MAX_RISK_PER_TRADE",
    "MAX_DAILY_LOSS",
    "MAX_WEEKLY_LOSS",
    "DEFAULT_LEVERAGE",
    "MAX_LEVERAGE",
    "CONSENSUS_THRESHOLD",
    "MIN_CONFIDENCE_SCORE",
    "SIGNAL_CONFLUENCE_REQUIRED",
    "PREFERRED_PAIRS",
}


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    value = str(value)
    if len(value) <= 8:
        return "****"
    return value[:4] + "..." + value[-4:]


def mode_flags(trading_mode: str) -> dict[str, Any]:
    mode = (trading_mode or "paper").lower().strip()
    return {
        "trading_mode": mode,
        "is_paper": mode == "paper",
        "is_exchange_demo": mode in {"demo", "testnet"},
        "is_live": mode == "live",
        "live_warning": mode == "live",
    }


def normalize_payload(payload: dict[str, Any]) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, value in payload.items():
        key = str(key).upper().strip()
        if key not in SAFE_ENV_KEYS:
            continue
        if value is None:
            value = ""
        clean[key] = str(value).strip()
    return clean


async def set_bot_state(key: str, value: str) -> None:
    async with AsyncSessionLocal() as db:
        row = (await db.execute(select(BotState).where(BotState.key == key))).scalars().first()
        if row:
            row.value = value
        else:
            db.add(BotState(key=key, value=value))
        await db.commit()


async def get_bot_state(key: str, default: str = "") -> str:
    async with AsyncSessionLocal() as db:
        row = (await db.execute(select(BotState).where(BotState.key == key))).scalars().first()
        return row.value if row else default


async def save_admin_settings(payload: dict[str, Any]) -> dict[str, Any]:
    clean = normalize_payload(payload)

    for key, value in clean.items():
        await set_bot_state(key, value)

    update_env_file(clean)

    return {
        "ok": True,
        "saved_keys": sorted(clean.keys()),
        "restart_required": True,
        "message": "Settings saved. Restart Docker container for exchange/API config changes to fully apply.",
    }


async def load_admin_settings() -> dict[str, Any]:
    exchange = await get_bot_state("EXCHANGE", getattr(settings, "exchange", "bitget"))
    trading_mode = await get_bot_state("TRADING_MODE", getattr(settings, "trading_mode", "paper"))

    data = {
        "APP_NAME": getattr(settings, "app_name", "APEX AI Trading Platform"),
        "EXCHANGE": exchange,
        "TRADING_MODE": trading_mode,
        "DRY_RUN": str(getattr(settings, "dry_run", True)).lower(),
        "BINANCE_TESTNET": str(getattr(settings, "binance_testnet", True)).lower(),
        "BINANCE_MARKET_TYPE": getattr(settings, "binance_market_type", "spot"),
        "BITGET_MARKET_TYPE": getattr(settings, "bitget_market_type", "spot"),
        "AI_OPENAI_ENABLED": str(getattr(settings, "ai_openai_enabled", False)).lower(),
        "AI_CLAUDE_ENABLED": str(getattr(settings, "ai_claude_enabled", False)).lower(),
        "MAX_RISK_PER_TRADE": str(getattr(settings, "max_risk_per_trade", 0.005)),
        "MAX_DAILY_LOSS": str(getattr(settings, "max_daily_loss", 0.03)),
        "MAX_WEEKLY_LOSS": str(getattr(settings, "max_weekly_loss", 0.08)),
        "DEFAULT_LEVERAGE": str(getattr(settings, "default_leverage", 1)),
        "MAX_LEVERAGE": str(getattr(settings, "max_leverage", 3)),
        "CONSENSUS_THRESHOLD": str(getattr(settings, "consensus_threshold", 0.65)),
        "MIN_CONFIDENCE_SCORE": str(getattr(settings, "min_confidence_score", 0.70)),
        "SIGNAL_CONFLUENCE_REQUIRED": str(getattr(settings, "signal_confluence_required", 4)),
        "PREFERRED_PAIRS": getattr(settings, "preferred_pairs", "BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,AVAX/USDT"),
        "BINANCE_API_KEY_MASKED": mask_secret(getattr(settings, "binance_api_key", "")),
        "BITGET_API_KEY_MASKED": mask_secret(getattr(settings, "bitget_api_key", "")),
        "OPENAI_API_KEY_MASKED": mask_secret(getattr(settings, "openai_api_key", "")),
        "ANTHROPIC_API_KEY_MASKED": mask_secret(getattr(settings, "anthropic_api_key", "")),
        "TELEGRAM_BOT_TOKEN_MASKED": mask_secret(getattr(settings, "telegram_bot_token", "")),
    }
    data.update(mode_flags(trading_mode))
    return data


def update_env_file(values: dict[str, str]) -> None:
    env_path = Path(".env")
    existing: dict[str, str] = {}

    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if not line.strip() or line.strip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            existing[k.strip()] = v.strip()

    existing.update(values)

    mode = existing.get("TRADING_MODE", "paper").lower()
    if mode == "paper":
        existing["DRY_RUN"] = "true"
    elif mode in {"demo", "testnet"}:
        existing["DRY_RUN"] = "false"
        existing["BINANCE_TESTNET"] = "true"
    elif mode == "live":
        existing["DRY_RUN"] = "false"
        existing["BINANCE_TESTNET"] = "false"

    order = [
        "APP_NAME", "ENV", "DRY_RUN", "EXCHANGE", "TRADING_MODE",
        "BINANCE_TESTNET", "BINANCE_API_KEY", "BINANCE_API_SECRET", "BINANCE_MARKET_TYPE",
        "BITGET_API_KEY", "BITGET_API_SECRET", "BITGET_API_PASSWORD", "BITGET_MARKET_TYPE",
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AI_OPENAI_ENABLED", "AI_CLAUDE_ENABLED",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        "DATABASE_URL", "SCAN_INTERVAL_SECONDS",
        "MAX_RISK_PER_TRADE", "MAX_DAILY_LOSS", "MAX_WEEKLY_LOSS",
        "MAX_CONCURRENT_TRADES", "DEFAULT_LEVERAGE", "MAX_LEVERAGE",
        "CONSENSUS_THRESHOLD", "MIN_CONFIDENCE_SCORE", "SIGNAL_CONFLUENCE_REQUIRED", "PREFERRED_PAIRS",
    ]

    lines = []
    for key in order:
        if key in existing:
            lines.append(f"{key}={existing[key]}")

    for key in sorted(existing.keys()):
        if key not in order:
            lines.append(f"{key}={existing[key]}")

    env_path.write_text("\n".join(lines) + "\n")
