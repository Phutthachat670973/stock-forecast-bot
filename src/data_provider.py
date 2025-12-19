import io
import pandas as pd
import requests

def _stooq_symbol(ticker: str) -> str:
    t = ticker.strip().lower()
    if "." in t:
        return t
    return f"{t}.us"  # default US

def download_daily_ohlcv_stooq(ticker: str) -> pd.DataFrame:
    sym = _stooq_symbol(ticker)
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    r = requests.get(url, headers={"User-Agent": "stock-forecast-bot/1.0"}, timeout=30)
    r.raise_for_status()

    text = r.text.strip()
    if "Date" not in text:
        return pd.DataFrame()

    df = pd.read_csv(io.StringIO(text))
    if df.empty:
        return pd.DataFrame()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date").sort_index()

    df = df.rename(columns={c: c.title() for c in df.columns})
    need = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in df.columns for c in need):
        return pd.DataFrame()

    return df[need].copy()
