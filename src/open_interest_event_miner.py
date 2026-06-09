import pandas as pd
import numpy as np

FILE = "data/tardis/binance-futures_derivative_ticker_2026-01-01_BTCUSDT.csv"

df = pd.read_csv(FILE)

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    unit="us"
)

df = df.dropna(
    subset=["open_interest", "mark_price"]
)

# ====================================
# RESAMPLE 1 MIN
# ====================================

df = (
    df
    .set_index("timestamp")
    .resample("1min")
    .agg({
        "open_interest": "last",
        "mark_price": "last"
    })
)

df = df.dropna()

# ====================================
# FUTURE MOVE
# ====================================

LOOKAHEAD = 60

df["future_high"] = (
    df["mark_price"]
    .shift(-1)
    .rolling(LOOKAHEAD)
    .max()
    .shift(-(LOOKAHEAD-1))
)

df["future_low"] = (
    df["mark_price"]
    .shift(-1)
    .rolling(LOOKAHEAD)
    .min()
    .shift(-(LOOKAHEAD-1))
)

df["future_up_pct"] = (
    (df["future_high"] - df["mark_price"])
    / df["mark_price"]
) * 100

df["future_down_pct"] = (
    (df["future_low"] - df["mark_price"])
    / df["mark_price"]
) * 100

# ====================================
# OI FEATURES
# ====================================

df["oi_change_5m"] = (
    df["open_interest"]
    .pct_change(5)
) * 100

df["oi_change_15m"] = (
    df["open_interest"]
    .pct_change(15)
) * 100

df["oi_change_30m"] = (
    df["open_interest"]
    .pct_change(30)
) * 100

# ====================================
# EVENTS
# ====================================

rows = []

for threshold in [1, 2, 3]:

    up = df[
        df["future_up_pct"] >= threshold
    ]

    down = df[
        df["future_down_pct"] <= -threshold
    ]

    rows.append({
        "direction": "UP",
        "threshold": threshold,
        "events": len(up),

        "avg_oi_5m":
            up["oi_change_5m"].mean(),

        "avg_oi_15m":
            up["oi_change_15m"].mean(),

        "avg_oi_30m":
            up["oi_change_30m"].mean()
    })

    rows.append({
        "direction": "DOWN",
        "threshold": threshold,
        "events": len(down),

        "avg_oi_5m":
            down["oi_change_5m"].mean(),

        "avg_oi_15m":
            down["oi_change_15m"].mean(),

        "avg_oi_30m":
            down["oi_change_30m"].mean()
    })

out = pd.DataFrame(rows)

print("\n" + "="*70)
print("OPEN INTEREST EVENT MINER")
print("="*70)

print(out.to_string(index=False))