from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "APEX AI Trading Platform"
    env: str = "dev"
    dry_run: bool = True

    exchange: str = "bitget"
    trading_mode: str = "paper"  # paper, demo/testnet, live

    binance_testnet: bool = True
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_market_type: str = "spot"

    bitget_api_key: str = ""
    bitget_api_secret: str = ""
    bitget_api_password: str = ""
    bitget_market_type: str = "spot"

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ai_openai_enabled: bool = False
    ai_claude_enabled: bool = False

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/apex.db"

    scan_interval_seconds: int = 60
    max_risk_per_trade: float = 0.005
    max_daily_loss: float = 0.03
    max_weekly_loss: float = 0.08
    max_concurrent_trades: int = 3
    default_leverage: int = 1
    max_leverage: int = 3
    consensus_threshold: float = 0.65
    min_confidence_score: float = 0.70
    signal_confluence_required: int = 4
    preferred_pairs: str = "BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,AVAX/USDT"

    @property
    def pairs(self) -> list[str]:
        return [p.strip() for p in self.preferred_pairs.split(",") if p.strip()]

settings = Settings()
