# src/run_daily.py
import json
import os
from datetime import datetime
import pytz
import pandas as pd
import yfinance as yf

from features import make_features
from model import train_direction_model, predict_proba_up, FEATURE_COLS
from explain import explain_one, humanize_reasons

def _now_str(tzname: str) -> str:
    tz = pytz.timezone(tzname)
    return datetime.now(tz).strftime("%Y-%m-%d")

def run_one_ticker(ticker: str, cfg: dict) -> dict:
    lookback_days = int(cfg["lookback_days"])
    train_window_days = int(cfg["train_window_days"])
    horizon_days = int(cfg["horizon_days"])
    top_k = int(cfg["report_top_reasons"])

    df = yf.download(ticker, period=f"{lookback_days}d", interval="1d", auto_adjust=False, progress=False)
    if df.empty:
        raise RuntimeError(f"No data for {ticker}")

    # yfinance columns: Open High Low Close Adj Close Volume
    df = df.rename(columns=lambda c: c.strip())
    if "Adj Close" in df.columns:
        df = df.drop(columns=["Adj Close"])

    data = make_features(df)

    # ใช้หน้าต่างเทรนล่าสุดแบบ rolling
    data_train = data.tail(train_window_days).copy()

    model = train_direction_model(data_train)

    latest = data.iloc[-1].copy()
    latest_X = pd.DataFrame([latest[FEATURE_COLS].values], columns=FEATURE_COLS)

    proba_up = predict_proba_up(model, latest_X)

    # ทำ “ฟอร์แคสต์” แบบทิศทาง (ไม่ได้ทำนายราคาเป๊ะ) สำหรับ horizon วัน = ใช้ proba เดิมเป็น baseline
    # ถ้าจะให้ดีขึ้น: ทำ walk-forward simulate ได้ แต่จะหนักขึ้น
    direction = "UP" if proba_up >= 0.5 else "DOWN"

    reasons_raw = explain_one(model, latest_X, top_k=top_k)
    reasons_text = humanize_reasons(latest[FEATURE_COLS], reasons_raw)

    result = {
        "ticker": ticker,
        "asof": str(data.index[-1].date()),
        "proba_up_next_day": round(proba_up, 4),
        "signal": direction,
        "horizon_days": horizon_days,
        "reasons": reasons_text
    }
    return result

def main():
    with open("config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    out_date = _now_str(cfg.get("timezone","Asia/Bangkok"))
    out_dir = os.path.join("outputs", out_date)
    os.makedirs(out_dir, exist_ok=True)

    summary_rows = []
    md_lines = [f"# Daily Stock Forecast ({out_date})", ""]

    for t in cfg["tickers"]:
        r = run_one_ticker(t, cfg)
        summary_rows.append({
            "date": out_date,
            "ticker": r["ticker"],
            "asof": r["asof"],
            "proba_up_next_day": r["proba_up_next_day"],
            "signal": r["signal"]
        })

        md_lines += [
            f"## {r['ticker']}",
            f"- As of: **{r['asof']}**",
            f"- P(ขึ้นวันถัดไป): **{r['proba_up_next_day']}**",
            f"- Signal: **{r['signal']}**",
            "",
            "เหตุผล (ตัวแปรที่มีอิทธิพลมากสุด):",
            *r["reasons"],
            ""
        ]

        # per-ticker json
        with open(os.path.join(out_dir, f"{t}_result.json"), "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)

    # summary csv + markdown report
    pd.DataFrame(summary_rows).to_csv(os.path.join(out_dir, "summary.csv"), index=False, encoding="utf-8-sig")
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # also keep latest copies
    os.makedirs("outputs/latest", exist_ok=True)
    pd.DataFrame(summary_rows).to_csv("outputs/latest/summary.csv", index=False, encoding="utf-8-sig")
    with open("outputs/latest/report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

if __name__ == "__main__":
    main()

