# src/features.py
import numpy as np
import pandas as pd

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss.replace(0, np.nan))
    return 100 - (100 / (1 + rs))

def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    df ต้องมีคอลัมน์: Open, High, Low, Close, Volume และ index เป็น DatetimeIndex
    """
    out = df.copy()

    # Returns / Momentum
    out["ret_1"] = out["Close"].pct_change(1)
    out["ret_5"] = out["Close"].pct_change(5)
    out["ret_10"] = out["Close"].pct_change(10)

    # Moving Averages
    out["sma_10"] = out["Close"].rolling(10).mean()
    out["sma_20"] = out["Close"].rolling(20).mean()
    out["sma_50"] = out["Close"].rolling(50).mean()

    out["close_vs_sma20"] = (out["Close"] / out["sma_20"]) - 1
    out["sma10_vs_sma20"] = (out["sma_10"] / out["sma_20"]) - 1
    out["sma20_vs_sma50"] = (out["sma_20"] / out["sma_50"]) - 1

    # Volatility
    out["vol_10"] = out["ret_1"].rolling(10).std()
    out["vol_20"] = out["ret_1"].rolling(20).std()

    # Volume
    out["vol_chg"] = out["Volume"].pct_change(1)
    out["vol_vs_avg20"] = (out["Volume"] / out["Volume"].rolling(20).mean()) - 1

    # RSI
    out["rsi_14"] = _rsi(out["Close"], 14)

    # Target: ทิศทางวันถัดไป (ขึ้น=1 ลง/เท่าเดิม=0)
    out["target_up_next"] = (out["Close"].shift(-1) > out["Close"]).astype(int)

    out = out.dropna().copy()
    return out

