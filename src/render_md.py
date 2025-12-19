# src/render_md.py
from explain_simple import label_value

def _stance_emoji(s: str) -> str:
    s = (s or "").lower()
    return {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}.get(s, "🟡")

def _signal_badge(signal: str) -> str:
    if signal == "UP":
        return "🟢 UP (มีแนวโน้มบวก)"
    if signal == "DOWN":
        return "🔴 DOWN (มีแนวโน้มลบ)"
    return "🟡 NEUTRAL"

def render_ticker_markdown(r: dict) -> str:
    ticker = r.get("ticker", "N/A")
    asof = r.get("asof", "N/A")
    src = r.get("data_source", "N/A")
    horizon = r.get("horizon_days", "N/A")
    p = r.get("proba_up_next_day", None)
    signal = r.get("signal", "N/A")

    p_txt = f"{p*100:.2f}%" if isinstance(p, (int, float)) else "N/A"

    # ===== Reasons (parse จากข้อความเดิม "- ชื่อ = ค่า → ข้อความ")
    reasons = r.get("reasons", []) or []
    parsed = []
    for line in reasons:
        # ตัวอย่าง: "- โมเมนตัม 5 วัน = -0.0210 → กดลง"
        s = line.lstrip("-").strip()
        if "=" in s:
            left, right = s.split("=", 1)
            name = left.strip()
            rest = right.strip()
            # rest: "-0.0210 → กดลง"
            val_str = rest.split("→")[0].strip()
            try:
                v = float(val_str)
            except Exception:
                v = None
            parsed.append((name, v, s))
        else:
            parsed.append((None, None, s))

    # ทำ bullet แบบ “แปลเป็นภาษาคน”
    friendly_lines = []
    for name, v, raw in parsed:
        if name is None or v is None:
            friendly_lines.append(f"- 🟡 {raw}")
            continue
        tag, human = label_value(name, v)
        friendly_lines.append(f"- {tag} **{name}**: {human}  \n  <sub>ค่า = {v:.4f}</sub>")

    reasons_md = "\n".join(friendly_lines) if friendly_lines else "- (ไม่มีเหตุผล)"

    # ===== Headlines
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

    # ===== AI summary
    ai = r.get("ai_news", None)
    if ai and ai.get("picks"):
        overall = ai.get("overall", {})
        overall_md = f"{_stance_emoji(overall.get('stance'))} **ภาพรวมข่าว:** {overall.get('note','')} (conf {overall.get('confidence',50)}/100)"

        pick_lines = []
        for p2 in ai.get("picks", []):
            em = _stance_emoji(p2.get("stance"))
            pick_lines.append(
                f"- {em} อ้างอิงข่าว [{p2.get('idx')}] | conf {p2.get('confidence')}/100  \n"
                f"  - สรุปสั้นๆ: {p2.get('summary')}  \n"
                f"  - ทำไมสำคัญ: {p2.get('why')}"
            )
        ai_md = overall_md + "\n\n" + "\n".join(pick_lines)
    else:
        ai_md = "_(ยังไม่ได้ใช้ AI หรือ AI ใช้งานไม่ได้ในรอบนี้ → แสดงข่าวแบบ RSS อย่างเดียว)_"

    return f"""# 📌 สรุปวันนี้ — {ticker}

**วันที่ข้อมูล (As of):** `{asof}`  
**แหล่งข้อมูลราคา:** `{src}`  
**ระยะที่มอง (Horizon):** `{horizon} วัน`  
**สัญญาณ:** **{_signal_badge(signal)}**  
**โอกาสขึ้น (Probability UP):** **{p_txt}**

> อ่านง่ายๆ: ถ้า % ใกล้ 50% = ยัง “ก้ำกึ่ง” ไม่ชัดเจนมาก

---

## ✅ ทำไมระบบถึงมองแบบนี้ (สรุปแบบมือใหม่)
{reasons_md}

---

## 📰 ข่าวที่อาจเกี่ยวข้อง (เปิดอ่านได้)
{headlines_md}

---

## 🤖 สรุปข่าวแบบ AI (ถ้ามี)
{ai_md}

---

### ⚠️ หมายเหตุสำคัญ
- นี่คือระบบ “ช่วยมองแนวโน้ม” ไม่ใช่คำแนะนำการลงทุน  
- ข่าวเป็น “ปัจจัยที่อาจเกี่ยวข้อง” ไม่ได้ยืนยันว่าเป็นสาเหตุที่ทำให้ราคาขึ้น/ลงจริง
"""
