import math

WEIGHTS = {
    "close_vs_sma20": 3.0,
    "sma10_vs_sma20": 2.0,
    "sma20_vs_sma50": 1.5,
    "ret_5": 2.5,
    "ret_10": 1.5,
    "rsi_14": 2.0,
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
    contribs = []

    for f in ["close_vs_sma20", "sma10_vs_sma20", "sma20_vs_sma50", "ret_5", "ret_10", "vol_vs_avg20"]:
        v = float(latest_row.get(f, 0.0))
        w = WEIGHTS[f]
        c = w * v
        contribs.append((f, v, c, "หนุนขึ้น" if c > 0 else "กดลง"))

    rsi = float(latest_row.get("rsi_14", 50.0))
    if rsi < 30:
        rsi_effect, rsi_note = +1.0, "หนุนขึ้น (oversold มีโอกาสเด้ง)"
    elif rsi > 70:
        rsi_effect, rsi_note = -1.0, "กดลง (overbought เสี่ยงย่อ)"
    else:
        rsi_effect, rsi_note = 0.0, "กลางๆ"

    rsi_c = WEIGHTS["rsi_14"] * rsi_effect
    contribs.append(("rsi_14", rsi, rsi_c, rsi_note))

    score = sum(c for _, _, c, _ in contribs)
    proba_up = _sigmoid(score)
    signal = "UP" if proba_up >= 0.5 else "DOWN"

    contribs_sorted = sorted(contribs, key=lambda x: abs(x[2]), reverse=True)[:top_k]
    reasons = []
    for f, v, c, note in contribs_sorted:
        name = FRIENDLY.get(f, f)
        reasons.append(f"- {name} = {v:.4f} → {note}")

    return float(proba_up), signal, reasons
