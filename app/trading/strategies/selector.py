def _targets(entry: float, side: str, atr: float, rr_base: float = 2.0) -> dict:
    risk = max(atr * 1.5, entry * 0.004)
    if side == 'LONG':
        sl = entry - risk
        return {'stop_loss': sl, 'tp1': entry + risk*2, 'tp2': entry + risk*3, 'tp3': entry + risk*5}
    sl = entry + risk
    return {'stop_loss': sl, 'tp1': entry - risk*2, 'tp2': entry - risk*3, 'tp3': entry - risk*5}


def build_signal(pair: str, row: dict, regime: str) -> dict:
    price = row['close']
    confluence = 0
    direction = 'SKIP'
    strategy = 'none'
    reasons = []

    bullish_trend = row['ema_9'] > row['ema_21'] > row['ema_50'] and price > row['ema_200']
    bearish_trend = row['ema_9'] < row['ema_21'] < row['ema_50'] and price < row['ema_200']

    if bullish_trend:
        confluence += 2; reasons.append('EMA stack bullish')
    if bearish_trend:
        confluence += 2; reasons.append('EMA stack bearish')
    if 50 <= row['rsi_14'] <= 70:
        confluence += 1; reasons.append('RSI bullish momentum')
    if 30 <= row['rsi_14'] <= 50:
        confluence += 1; reasons.append('RSI bearish/weak momentum')
    if row['macd'] > row['macd_signal']:
        confluence += 1; reasons.append('MACD bullish')
    if row['macd'] < row['macd_signal']:
        confluence += 1; reasons.append('MACD bearish')
    if row['volume'] > row['vol_avg_20'] * 1.3:
        confluence += 1; reasons.append('Volume expansion')
    if price > row['vwap']:
        confluence += 1; reasons.append('Price above VWAP')
    if price < row['vwap']:
        confluence += 1; reasons.append('Price below VWAP')

    if regime in ['TRENDING_BULL', 'HIGH_VOLATILITY'] and bullish_trend and row['macd'] > row['macd_signal']:
        direction = 'LONG'; strategy = 'trend_following'
    elif regime in ['TRENDING_BEAR', 'HIGH_VOLATILITY'] and bearish_trend and row['macd'] < row['macd_signal']:
        direction = 'SHORT'; strategy = 'trend_following'
    elif regime == 'RANGING' and row['rsi_14'] < 30 and price <= row['bb_lower']:
        direction = 'LONG'; strategy = 'mean_reversion'
    elif regime == 'RANGING' and row['rsi_14'] > 70 and price >= row['bb_upper']:
        direction = 'SHORT'; strategy = 'mean_reversion'

    targets = _targets(price, direction if direction != 'SKIP' else 'LONG', row['atr_14'])
    return {
        'pair': pair,
        'direction': direction,
        'strategy': strategy,
        'regime': regime,
        'entry': float(price),
        **{k: float(v) for k, v in targets.items()},
        'confluence': confluence,
        'confidence': min(0.95, 0.45 + confluence * 0.08),
        'reasons': reasons[:5],
        'raw': {k: float(row[k]) for k in ['close','ema_9','ema_21','ema_50','ema_200','rsi_14','macd','macd_signal','atr_14']}
    }
