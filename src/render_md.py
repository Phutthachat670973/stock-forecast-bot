def render_ticker_markdown(r: dict) -> str:
    ticker = r.get("ticker", "N/A")
    asof = r.get("asof", "N/A")
    src = r.get("data_source", "N/A")
    horizon = r.get("horizon_days", "N/A")
    p = r.get("proba_up_next_day", None)
    signal = r.get("signal", "N/A")

    if isinstance(p, (int, float)):
        p_txt = f"{p*100:.2f}%"
    else:
        p_txt = "N/A"

    emoji = "🟢" if signal == "UP" else ("🔴" if signal == "DOWN" else "⚪")
    reasons = r.get("reasons", []) or []
    reasons_md = "\n".join([f"- {x.lstrip('- ').strip()}" for x in reasons]) if reasons else "- (ไม่มีเหตุผล)"

    return f"""# 📈 Forecast — {ticker}

**As of:** `{asof}`  
**Data source:** `{src}`  
**Horizon:** `{horizon} day(s)`  
**Signal:** {emoji} **{signal}**  
**Probability (UP):** **{p_txt}**

---

## 🧠 Reasons (Top Drivers)
{reasons_md}
"""
