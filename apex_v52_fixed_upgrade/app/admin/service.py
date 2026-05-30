from __future__ import annotations

from typing import Any
from app.config import settings

# v5.2 in-memory admin settings. Later this should be moved to encrypted DB storage.
_STORE: dict[str, Any] = {
    "exchange": {
        "active_exchange": getattr(settings, "exchange", "bitget"),
        "trading_mode": "paper",  # paper | demo | live
        "live_trading_enabled": False,
        "bitget": {
            "enabled": True,
            "mode": "paper",
            "api_key": "",
            "api_secret": "",
            "api_password": "",
        },
        "binance": {
            "enabled": False,
            "mode": "paper",
            "api_key": "",
            "api_secret": "",
        },
        "bybit": {"enabled": False, "mode": "paper"},
        "okx": {"enabled": False, "mode": "paper"},
        "kucoin": {"enabled": False, "mode": "paper"},
    },
    "risk": {
        "max_risk_per_trade": getattr(settings, "max_risk_per_trade", 0.005),
        "max_daily_loss": getattr(settings, "max_daily_loss", 0.03),
        "max_weekly_loss": getattr(settings, "max_weekly_loss", 0.08),
        "max_concurrent_trades": getattr(settings, "max_concurrent_trades", 3),
        "default_leverage": getattr(settings, "default_leverage", 1),
        "max_leverage": getattr(settings, "max_leverage", 3),
    },
    "ai": {
        "openai_enabled": getattr(settings, "ai_openai_enabled", False),
        "claude_enabled": getattr(settings, "ai_claude_enabled", False),
        "openai_api_key": "",
        "anthropic_api_key": "",
    },
    "telegram": {
        "enabled": bool(getattr(settings, "telegram_bot_token", "")),
        "bot_token": "",
        "chat_id": getattr(settings, "telegram_chat_id", ""),
    },
}


def _merge_dict(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge_dict(base[key], value)
        else:
            base[key] = value
    return base


def _masked(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "********"
    return value[:4] + "********" + value[-4:]


def _safe_settings() -> dict[str, Any]:
    data = dict(_STORE)
    data["exchange"] = dict(_STORE["exchange"])
    for ex in ["bitget", "binance"]:
        data["exchange"][ex] = dict(_STORE["exchange"].get(ex, {}))
        for secret_key in ["api_key", "api_secret", "api_password"]:
            if secret_key in data["exchange"][ex]:
                data["exchange"][ex][secret_key] = _masked(data["exchange"][ex].get(secret_key))
    data["ai"] = dict(_STORE["ai"])
    data["ai"]["openai_api_key"] = _masked(data["ai"].get("openai_api_key"))
    data["ai"]["anthropic_api_key"] = _masked(data["ai"].get("anthropic_api_key"))
    data["telegram"] = dict(_STORE["telegram"])
    data["telegram"]["bot_token"] = _masked(data["telegram"].get("bot_token"))
    return data


async def get_all_settings():
    return _safe_settings()


async def save_admin_settings(data=None):
    if isinstance(data, dict):
        _merge_dict(_STORE, data)
    return {"ok": True, "settings": _safe_settings()}


async def get_exchange_settings():
    return _safe_settings()["exchange"]


async def save_exchange_settings(data=None):
    if isinstance(data, dict):
        _merge_dict(_STORE["exchange"], data)
    return {"ok": True, "exchange": _safe_settings()["exchange"]}


async def get_risk_settings():
    return _STORE["risk"]


async def save_risk_settings(data=None):
    if isinstance(data, dict):
        _merge_dict(_STORE["risk"], data)
    return {"ok": True, "risk": _STORE["risk"]}


async def get_ai_settings():
    return _safe_settings()["ai"]


async def save_ai_settings(data=None):
    if isinstance(data, dict):
        _merge_dict(_STORE["ai"], data)
    return {"ok": True, "ai": _safe_settings()["ai"]}


async def get_telegram_settings():
    return _safe_settings()["telegram"]


async def save_telegram_settings(data=None):
    if isinstance(data, dict):
        _merge_dict(_STORE["telegram"], data)
    return {"ok": True, "telegram": _safe_settings()["telegram"]}


async def list_exchanges():
    exchange_settings = _STORE["exchange"]
    active = exchange_settings.get("active_exchange", "bitget")
    rows = []
    for name in ["bitget", "binance", "bybit", "okx", "kucoin"]:
        item = exchange_settings.get(name, {})
        rows.append({
            "name": name,
            "enabled": bool(item.get("enabled", name == "bitget")),
            "mode": item.get("mode", exchange_settings.get("trading_mode", "paper")),
            "active": active == name,
            "has_api_key": bool(item.get("api_key")),
        })
    return rows


async def test_exchange_connection(exchange: str = "bitget"):
    # Safe placeholder: real authenticated test will be wired to encrypted DB keys in next version.
    exchange = (exchange or "bitget").lower()
    configured = _STORE["exchange"].get(exchange, {})
    return {
        "ok": True,
        "exchange": exchange,
        "mode": configured.get("mode", _STORE["exchange"].get("trading_mode", "paper")),
        "has_api_key": bool(configured.get("api_key")),
        "message": "Admin settings saved. Live authenticated balance wiring is handled by server .env in this build.",
    }


async def get_trading_mode():
    return {
        "mode": _STORE["exchange"].get("trading_mode", "paper"),
        "live_trading_enabled": bool(_STORE["exchange"].get("live_trading_enabled", False)),
        "safety": "Live orders are blocked unless live_trading_enabled=true.",
    }


async def save_trading_mode(data=None):
    if isinstance(data, dict):
        mode = data.get("mode", "paper")
        if mode not in {"paper", "demo", "live"}:
            return {"ok": False, "message": "mode must be paper, demo, or live"}
        live_enabled = bool(data.get("live_trading_enabled", False))
        if mode == "live" and not live_enabled:
            return {"ok": False, "message": "Live mode requires live_trading_enabled=true"}
        _STORE["exchange"]["trading_mode"] = mode
        _STORE["exchange"]["live_trading_enabled"] = live_enabled
    return {"ok": True, "trading_mode": await get_trading_mode()}
