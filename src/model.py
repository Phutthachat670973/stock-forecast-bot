# src/model.py
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

FEATURE_COLS = [
    "ret_1","ret_5","ret_10",
    "close_vs_sma20","sma10_vs_sma20","sma20_vs_sma50",
    "vol_10","vol_20",
    "vol_chg","vol_vs_avg20",
    "rsi_14"
]

def train_direction_model(data: pd.DataFrame):
    X = data[FEATURE_COLS]
    y = data["target_up_next"].astype(int)

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000))
    ])
    pipe.fit(X, y)
    return pipe

def predict_proba_up(model, row: pd.DataFrame) -> float:
    # row = 1 แถว DataFrame ที่มี FEATURE_COLS
    proba = model.predict_proba(row[FEATURE_COLS])[0, 1]
    return float(proba)

