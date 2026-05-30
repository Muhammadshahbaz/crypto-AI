def detect_regime(row: dict) -> str:
    price = row['close']
    atr_pct = row['atr_14'] / price if price else 0
    bull = row['ema_50'] > row['ema_200'] and price > row['ema_50']
    bear = row['ema_50'] < row['ema_200'] and price < row['ema_50']

    if atr_pct > 0.04:
        return 'HIGH_VOLATILITY'
    if atr_pct < 0.01:
        return 'LOW_VOLATILITY'
    if bull:
        return 'TRENDING_BULL'
    if bear:
        return 'TRENDING_BEAR'
    return 'RANGING'
