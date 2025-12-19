# src/explain.py
import numpy as np
import pandas as pd

def explain_one(model, X_row: pd.DataFrame, top_k: int = 5):
    """
    คืน list เหตุผล top_k ว่าอะไรผลักให้ขึ้น/ลง
    """
    scaler = model.named_steps["scaler"]
    clf = model.named_steps["clf"]

    x = X_row.values.astype(float)
    x_scaled = scaler.transform(x)

    coefs = clf.coef_[0]  # (n_features,)
    contrib = x_scaled[0] * coefs

    cols = list(X_row.columns)
    items = list(zip(cols, contrib))

    # แยกแรงบวก/ลบ
    items_sorted = sorted(items, key=lambda t: abs(t[1]), reverse=True)[:top_k]

    reasons = []
    for name, c in items_sorted:
        direction = "หนุนขึ้น" if c > 0 else "กดลง"
        reasons.append({"feature": name, "impact": float(c), "note": direction})

    return reasons

def humanize_reasons(latest_row_raw: pd.Series, reasons):
    """
    แปลงชื่อฟีเจอร์เป็นคำอธิบายอ่านง่าย
    """
    mapping = {
        "ret_1": "ผลตอบแทน 1 วันล่าสุด",
        "ret_5": "โมเมนตัม 5 วัน",
        "ret_10": "โมเมนตัม 10 วัน",
        "close_vs_sma20": "ราคาปัจจุบันเทียบเส้นเฉลี่ย 20 วัน",
        "sma10_vs_sma20": "เส้นเฉลี่ย 10 วันเทียบ 20 วัน",
        "sma20_vs_sma50": "เส้นเฉลี่ย 20 วันเทียบ 50 วัน",
        "vol_10": "ความผันผวน 10 วัน",
        "vol_20": "ความผันผวน 20 วัน",
        "vol_chg": "การเปลี่ยนแปลง Volume ล่าสุด",
        "vol_vs_avg20": "Volume เทียบค่าเฉลี่ย 20 วัน",
        "rsi_14": "RSI 14 วัน"
    }

    pretty = []
    for r in reasons:
        f = r["feature"]
        val = float(latest_row_raw.get(f, np.nan))
        pretty.append(
            f"- {mapping.get(f,f)} = {val:.4f} → {r['note']}"
        )
    return pretty

