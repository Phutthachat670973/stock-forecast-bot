import math

# น้ำหนัก (ปรับได้ตามที่คุณชอบ)
WEIGHTS = {
    "close_vs_sma20": 3.0,
    "sma10_vs_sma20": 2.0,
    "sma20_vs_sma50": 1.5,
    "ret_5": 2.5,
    "ret_10": 1.5,
    "rsi_14": 2.0,         # ใช้แบบ “โซน”
    "vol_vs_avg20": 0.8,
}

FRIENDLY = {
    "close_vs_sma20": "ราคาต่ำ/สูงกว่าเส้นเฉลี่ย 20 วัน",
    "sma10_vs_sma20": "เส้นเฉลี่ย 10 วันเทียบ 20 วัน",
    "sma20_vs_sma50": "เส้นเฉลี่ย 20 วันเทียบ 50 วัน",
    "ret_5": "โมเมนตัม 5 วัน",
    "ret_10": "โมเมนตัม 10 วัน",
    "rsi_14": "RSI 14 วัน",
    "vol_vs_avg20": "Volume เทียบค่าเฉลี่ย 20 วัน",
}

def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))

def score_and_explain(latest_row, top_k: int = 5):
    """
    คืน: proba_up (0-1), signal, reasons(list[str])
    """
    contribs = []

    # 1) trend/momentum signals (ใช้ค่าจริง)
    for f in ["close_vs_sma20", "sma10_vs_sma20", "sma20_vs_sma50", "ret_5", "ret_10", "vol_vs_avg20"]:
        v = float(latest_row.get(f, 0.0))
        w = WEIGHTS[f]
        c = w * v
        contribs.append((f, v, c))

    # 2) RSI ใช้แบบโซน (ให้อธิบายง่าย + ไม่แกว่ง)
    rsi = float(latest_row.get("rsi_14", 50.0))
    if rsi < 30:
        rsi_effect = +1.0   # oversold → หนุนเด้ง
        rsi_note = "หนุนขึ้น (oversold มีโอกาสเด้ง)"
    elif rsi > 70:
        rsi_effect = -1.0   # overbought → เสี่ยงย่อ
        rsi_note = "กดลง (overbought เสี่ยงย่อ)"
    else:
        # ช่วงกลาง ๆ ให้ผลน้อย
        rsi_effect = 0.0
        rsi_note = "กลางๆ"

    rsi_c = WEIGHTS["rsi_14"] * rsi_effect
    contribs.append(("rsi_14", rsi, rsi_c, rsi_note))

    # รวมคะแนน
    score = 0.0
    for item in contribs:
        score += item[2]

    proba_up = _sigmoid(score)  # map เป็น 0-1
    signal = "UP" if proba_up >= 0.5 else "DOWN"

    # จัดเหตุผล top_k จาก abs(contribution)
    flat = []
    for item in contribs:
        if item[0] == "rsi_14":
            f, v, c, note = item
        else:
            f, v, c = item
            note = "หนุนขึ้น" if c > 0 else "กดลง"

        flat.append((f, v, c, note))

    flat = sorted(flat, key=lambda x: abs(x[2]), reverse=True)[:top_k]

    reasons = []
    for f, v, c, note in flat:
        name = FRIENDLY.get(f, f)
        # ทำให้รูปแบบคล้ายที่คุณโชว์ในรูป
        reasons.append(f"- {name} = {v:.4f} → {note}")

    return proba_up, signal, reasons
