# src/run_daily.py
import io
import json
import os
import random
import time
from datetime import datetime

import pandas as pd
import pytz
import requests
import yfinance as yf

from features import make_features
from model import train_direction_model, predict_proba_up, FEATURE_COLS
from explain import explain_one, humanize_reasons

# yfinance rate limit exception (บางเวอร์ชัน import path ต่างกัน)
try:
    from yfinance.exceptions import YFRateLimitError
except Exception:  # pragma: no cover
    class YFRateLimitError(Exception):
        pass


def _now_str(tzname: str) -> str:
    tz = pytz.timezone(tzname)
    return datetime.now(tz).strftime("%Y-%m-%d")


def _download_yahoo_with_retry(ticker: str, lookback_days: int, max_tries: int = 6) -> pd.DataFrame:
    """
    ดึงจาก Yahoo ผ่าน yfinance + retry/backoff
    """
    base_sleep = 2.0
    for attempt in range(1, max_tries + 1):
        try:
            df = yf.download(
                ticker,
                period=f"{lookback_days}d",
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=False,  # ลด burst
            )
            if df is not None and not df.empty:
                return df
        except YFRateLimitError:
            pass
        except Exception:
            # ถ้า error อื่นๆ ให้ retry เหมือนกัน
            pass

        # exponential backoff + jitter
        sleep_s = base_sleep * (2 ** (attempt - 1)) + random.uniform(0.0, 1.5)
        time.sleep(min(sleep_s, 45.0))

    return pd.DataFrame()


def _stooq_symbol(ticker: str) -> str:
    """
    Stooq ใช้สัญลักษณ์แบบ aapl.us สำหรับหุ้น US :contentReference[oaicite:3]{index=3}
    """
    t = ticker.strip().lower()
    if t.startswith("^"):  # index บางตัวอาจไม่ตรง format
        return t.lstrip("^")
    # ถ้าใส่ suffix มาแล้วก็ใช้ตามนั้น
    if "." in t:
        return t
    # ค่าเริ่มต้น: หุ้น US
    return f"{t}.us"


def _download_stooq_daily(ticker: str) -> pd.DataFrame:
    """
    ดึง historical daily OHLCV จาก Stooq (CSV)
    Stooq มีข้อมูลแบบดาวน์โหลด CSV ผ่านเว็บ :contentReference[oaicite:4]{index=4}
    """
    sym = _stooq_symbol(ticker)
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; stock-forecast-bot/1.0)"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()

    text = r.text.strip()
    # กรณีไม่มีข้อมูล บางครั้งจะได้ไฟล์สั้นๆ/ไม่ใช่ตาราง
    if "Date" not in text or len(text) < 20:
        return pd.DataFrame()

    df = pd.read_csv(io.StringIO(text))
    if df.empty or "Date" not in df.columns:
        return pd.DataFrame()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date").sort_index()

    # ให้ชื่อคอลัมน์ตรงกับ pipeline
    # Stooq มักเป็น: Open, High, Low, Close, Volume
    cols = {c: c.title() for c in df.columns}
    df = df.rename(columns=cols)

    needed = ["Open", "High", "Low", "Close", "Volume"]
    for c in needed:
        if c not in df.columns:
            return pd.DataFrame()

    df = df[needed].copy()
    return df


def download_prices(ticker: str, lookback_days: int) -> tuple[pd.DataFrame, str]:
    """
    return (df, source)
    """
    df = _download_yahoo_with_retry(ticker, lookback_days)
    if df is not None and not df.empty:
        # yfinance columns: Open High Low Close Adj Close Volume
        df = df.rename(columns=lambda c: c.strip())
        if "Adj Close" in df.columns:
            df = df.drop(columns=["Adj Close"])
        return df, "yahoo(yfinance)"

    # fallback: Stooq
    try:
        df2 = _download_stooq_daily(ticker)
        if df2 is not None and not df2.empty:
            return df2, "stooq"
    except Exception:
        pass

    return pd.DataFrame(), "none"


def run_one_ticker(ticker: str, cfg: dict) -> dict:
    lookback_days = int(cfg["lookback_days"])
    train_window_days = int(cfg["train_window_days"])
    horizon_days = int(cfg["horizon_days"])
    top_k = int(cfg["report_top_reasons"])

    df, source = download_prices(ticker, lookback_days)
    if df.empty:
        raise RuntimeError(f"No data for {ticker} (source tried: {source})")

    data = make_features(df)

    data_train = data.tail(train_window_days).copy()
    model = train_direction_model(data_train)

    latest = data.iloc[-1].copy()
    latest_X = pd.DataFrame([latest[FEATURE_COLS].values], columns=FEATURE_COLS)

    proba_up = predict_proba_up(model, latest_X)
    direction = "UP" if proba_up >= 0.5 else "DOWN"

    reasons_raw = explain_one(model, latest_X, top_k=top_k)
    reasons_text = humanize_reasons(latest[FEATURE_COLS], reasons_raw)

    return {
        "ticker": ticker,
        "asof": str(data.index[-1].date()),
        "data_source": source,
        "proba_up_next_day": round(proba_up, 4),
        "signal": direction,
        "horizon_days": horizon_days,
        "reasons": reasons_text,
    }


def main():
    with open("config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    out_date = _now_str(cfg.get("timezone", "Asia/Bangkok"))
    out_dir = os.path.join("outputs", out_date)
    os.makedirs(out_dir, exist_ok=True)

    summary_rows = []
    errors = []

    md_lines = [f"# Daily Stock Forecast ({out_date})", ""]

    for t in cfg["tickers"]:
        try:
            r = run_one_ticker(t, cfg)

            summary_rows.append({
                "date": out_date,
                "ticker": r["ticker"],
                "asof": r["asof"],
                "data_source": r["data_source"],
                "proba_up_next_day": r["proba_up_next_day"],
                "signal": r["signal"],
            })

            md_lines += [
                f"## {r['ticker']}",
                f"- As of: **{r['asof']}**",
                f"- Data source: **{r['data_source']}**",
                f"- P(ขึ้นวันถัดไป): **{r['proba_up_next_day']}**",
                f"- Signal: **{r['signal']}**",
                "",
                "เหตุผล (ตัวแปรที่มีอิทธิพลมากสุด):",
                *r["reasons"],
                "",
            ]

            with open(os.path.join(out_dir, f"{t}_result.json"), "w", encoding="utf-8") as jf:
                json.dump(r, jf, ensure_ascii=False, indent=2)

        except Exception as e:
            errors.append({"ticker": t, "error": str(e)})
            md_lines += [
                f"## {t}",
                f"- ❌ Error: `{e}`",
                "",
            ]

    # เขียนไฟล์สรุป/รายงาน แม้มีบางตัวพัง
    pd.DataFrame(summary_rows).to_csv(os.path.join(out_dir, "summary.csv"), index=False, encoding="utf-8-sig")
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    with open(os.path.join(out_dir, "errors.json"), "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)

    # latest
    os.makedirs("outputs/latest", exist_ok=True)
    pd.DataFrame(summary_rows).to_csv("outputs/latest/summary.csv", index=False, encoding="utf-8-sig")
    with open("outputs/latest/report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    with open("outputs/latest/errors.json", "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)

    # ถ้า “ทุกตัว” ล้ม ค่อย fail เพื่อให้รู้ว่าระบบพังจริง
    if len(summary_rows) == 0:
        raise RuntimeError("All tickers failed. See outputs/latest/errors.json")


if __name__ == "__main__":
    main()
