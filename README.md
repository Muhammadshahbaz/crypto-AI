# APEX v4 Binance — AI-Assisted Crypto Trading Bot

Capital-first Binance bot starter built from your APEX v3 prompt. It defaults to **DRY_RUN=true** and **BINANCE_TESTNET=true**.

## What is included

- FastAPI backend
- Binance connector through CCXT
- Market scanner with EMA, RSI, MACD, ATR, Bollinger Bands, VWAP-like approximation
- Regime detector
- Strategy selector: trend following, breakout, mean reversion
- AI decision hooks: OpenAI + Claude, optional
- Weighted consensus engine
- Risk manager with hard blocks
- Paper/live execution switch
- SQLite database logs
- Telegram alerts
- Docker deployment
- Simple backtest runner

## Safety defaults

The bot will not place real orders unless:

1. `DRY_RUN=false`
2. `BINANCE_TESTNET=false` if using real live keys
3. Binance API keys have trading permission
4. Risk validation passes

Never enable withdrawal permission on your Binance API key.

## Quick start

```bash
cp .env.example .env
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Run one scan

```bash
curl -X POST http://127.0.0.1:8000/api/scan-once
```

## Run worker loop

```bash
python scripts/run_worker.py
```

## Docker

```bash
docker compose up --build
```

## Recommended rollout

1. DRY_RUN=true for 2 weeks.
2. Binance testnet with tiny size.
3. Live keys, spot only, 0.25% to 0.5% risk.
4. Futures only after profitable history.

No bot can guarantee profit. This system is designed to reduce reckless trades and force risk discipline.
