import pandas as pd
from app.market.indicators import add_indicators
from app.market.regime_detector import detect_regime
from app.trading.strategies.selector import build_signal


def run_backtest(csv_path: str, pair: str = 'BTC/USDT') -> dict:
    df = pd.read_csv(csv_path)
    df = add_indicators(df)
    trades = []
    for _, row in df.iterrows():
        signal = build_signal(pair, row.to_dict(), detect_regime(row.to_dict()))
        if signal['direction'] != 'SKIP' and signal['confluence'] >= 4:
            trades.append(signal)
    return {'signals': len(trades), 'sample': trades[:5]}
