def _stance_emoji(s: str) -> str:
    s = (s or "").lower()
    return {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}.get(s, "🟡")

def render_ticker_markdown(r: dict) -> str:
    ticker = r.get("ticker", "N/A")
    asof = r.get("asof", "N/A")
    src = r.get("data_source", "N/A")
    horizon = r.get("horizon_days", "N/A")
    p = r.get("proba_up_next_day", None)
    signal = r.get("signal", "N/A")

    p_txt = f"{p*100:.2f}%" if isinstance(p, (int, float)) else "N/A"
    emoji = "🟢" if signal == "UP" else ("🔴" if signal == "DOWN" else "⚪")

    reasons = r.get("reasons", []) or []
    reasons_md = "\n".join([f"- {x.lstrip('- ').strip()}" for x in reasons]) if reasons else "- (ไม่มีเหตุผล)"

    headlines = r.get("headlines", []) or []
    if headlines:
        hl_lines = []
        for i, h in enumerate(headlines, start=1):
            title = h.get("title","").strip()
            link = h.get("link","").strip()
            pub = h.get("published","").strip()
            src2 = h.get("source","").strip()
            hl_lines.append(f"- [{i}] [{title}]({link})  \n  <sub>{src2} | {pub}</sub>")
        headlines_md = "\n".join(hl_lines)
    else:
        headlines_md = "- (ไม่พบข่าว หรือดึงข่าวไม่ได้)"

    ai = r.get("ai_news", None)
    if ai and ai.get("picks"):
        overall = ai.get("overall", {})
        overall_md = f"{_stance_emoji(overall.get('stance'))} **{overall.get('stance','neutral').upper()}** (confidence {overall.get('confidence',50)}/100) — {overall.get('note','')}".strip()

        pick_lines = []
        for p2 in ai.get("picks", []):
            em = _stance_emoji(p2.get("stance"))
            pick_lines.append(
                f"- {em} อ้างอิงข่าว [{p2.get('idx')}] | conf {p2.get('confidence')}/100\n"
                f"  - สรุป: {p2.get('summary')}\n"
                f"  - เหตุผล: {p2.get('why')}"
            )
        ai_md = overall_md + "\n\n" + "\n".join(pick_lines)
    else:
        ai_md = "_(AI summary ไม่พร้อมใช้งาน หรือ fallback เป็น rss_only)_"

    return f"""# 📈 Forecast — {ticker}

**As of:** `{asof}`  
**Data source:** `{src}`  
**Horizon:** `{horizon} day(s)`  
**Signal:** {emoji} **{signal}**  
**Probability (UP):** **{p_txt}**

---

## 🧠 Technical Reasons (Rule-based)
{reasons_md}

---

## 📰 Top Headlines (with links)
{headlines_md}

---

## 🤖 AI News Summary (based on headlines above)
{ai_md}

> หมายเหตุ: ส่วน AI ใช้ “หัวข้อข่าวที่ดึงมา” เท่านั้น และอ้างอิงเลขข่าวเพื่อให้ตรวจสอบย้อนกลับได้
"""
