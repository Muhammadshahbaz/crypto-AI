import pandas as pd
import numpy as np


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    for span in [9, 21, 50, 200]:
        df[f'ema_{span}'] = close.ewm(span=span, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

    tr = pd.concat([(high-low), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(14).mean()

    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    df['bb_mid'] = mid
    df['bb_upper'] = mid + 2 * std
    df['bb_lower'] = mid - 2 * std
    df['vol_avg_20'] = volume.rolling(20).mean()
    df['vwap'] = (close * volume).cumsum() / volume.cumsum()
    return df.dropna()
