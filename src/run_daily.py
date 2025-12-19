import json
import os
from datetime import datetime
import pytz
import pandas as pd

from data_provider import download_daily_ohlcv_stooq
from features import make_features
from strategy_rules import score_and_explain
from news_rss import fetch_news_rss
from ai_news import summarize_news_with_ai
from render_md import render_ticker_markdown

def _now_str(tzname: str) -> str:
    tz = pytz.timezone(tzname)
    return datetime.now(tz).strftime("%Y-%m-%d")

def run_one_ticker(ticker: str, cfg: dict) -> dict:
    lookback_days = int(cfg.get("lookback_days", 1200))
    top_k = int(cfg.get("report_top_reasons", 5))
    horizon_days = int(cfg.get("horizon_days", 5))

    # ----- price + features -----
    df = download_daily_ohlcv_stooq(ticker)
    if df.empty:
        raise RuntimeError("No data from Stooq")

    if len(df) > lookback_days:
        df = df.tail(lookback_days).copy()

    feat = make_features(df)
    latest = feat.iloc[-1]

    proba_up, signal, reasons = score_and_explain(latest, top_k=top_k)

    # ----- news (rss + optional ai) -----
    news_cfg = cfg.get("news", {})
    ai_cfg = cfg.get("ai", {})
    company_map = cfg.get("company_names", {})

    mode = (news_cfg.get("mode") or "rss_only").lower()
    company = company_map.get(ticker, ticker)

    suffix = news_cfg.get("query_suffix", "stock")
    query = f"{company} {ticker} {suffix}"

    headlines = []
    ai_news = None

    try:
        headlines = fetch_news_rss(
            query=query,
            max_items=int(news_cfg.get("max_items", 8)),
            days=int(news_cfg.get("days", 7)),
            hl=news_cfg.get("hl", "en-US"),
            gl=news_cfg.get("gl", "US"),
            ceid=news_cfg.get("ceid", "US:en"),
        )
    except Exception:
        headlines = []

    if mode == "rss_plus_ai" and headlines:
        try:
            ai_news = summarize_news_with_ai(ticker=ticker, company=company, headlines=headlines, ai_cfg=ai_cfg)
        except Exception:
            ai_news = None

    return {
        "ticker": ticker,
        "asof": str(feat.index[-1].date()),
        "data_source": "stooq",
        "proba_up_next_day": round(float(proba_up), 4),
        "signal": signal,
        "horizon_days": horizon_days,
        "reasons": reasons,
        "headlines": headlines,
        "ai_news": ai_news
    }

def main():
    with open("config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    out_date = _now_str(cfg.get("timezone", "Asia/Bangkok"))
    out_dir = os.path.join("outputs", out_date)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs("outputs/latest", exist_ok=True)

    summary = []
    errors = []

    index_lines = [f"# 📅 Daily Forecast — {out_date}", ""]

    for t in cfg.get("tickers", []):
        try:
            r = run_one_ticker(t, cfg)

            # save json (audit)
            with open(os.path.join(out_dir, f"{t}_result.json"), "w", encoding="utf-8") as jf:
                json.dump(r, jf, ensure_ascii=False, indent=2)

            # save markdown per ticker
            md_text = render_ticker_markdown(r)
            with open(os.path.join(out_dir, f"{t}_README.md"), "w", encoding="utf-8") as f:
                f.write(md_text)
            with open(os.path.join("outputs", "latest", f"{t}_README.md"), "w", encoding="utf-8") as f:
                f.write(md_text)

            summary.append({
                "date": out_date,
                "ticker": r["ticker"],
                "asof": r["asof"],
                "proba_up_next_day": r["proba_up_next_day"],
                "signal": r["signal"],
                "data_source": r["data_source"]
            })

            index_lines.append(
                f"- **{t}** → `{t}_README.md` | Signal: **{r['signal']}** | P(UP): **{r['proba_up_next_day']}**"
            )

        except Exception as e:
            errors.append({"ticker": t, "error": str(e)})
            index_lines.append(f"- **{t}** → ❌ {e}")

    # write summary + index readme
    pd.DataFrame(summary).to_csv(os.path.join(out_dir, "summary.csv"), index=False, encoding="utf-8-sig")
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    pd.DataFrame(summary).to_csv("outputs/latest/summary.csv", index=False, encoding="utf-8-sig")
    with open("outputs/latest/README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    with open(os.path.join(out_dir, "errors.json"), "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)
    with open("outputs/latest/errors.json", "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)

    if len(summary) == 0:
        raise RuntimeError("All tickers failed. Check outputs/latest/errors.json")

if __name__ == "__main__":
    main()
