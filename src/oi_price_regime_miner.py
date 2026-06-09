import pandas as pd
import glob
import numpy as np

FILES = glob.glob("data/tardis/binance-futures_derivative_ticker_*_BTCUSDT.csv")

if not FILES:
    raise FileNotFoundError("No encontré derivative_ticker en data/tardis/")

dfs = []

for file in FILES:
    df = pd.read_csv(file)
    df["source_file"] = file
    dfs.append(df)

df = pd.concat(dfs, ignore_index=True)

df["timestamp"] = pd.to_datetime(df["timestamp"], unit="us")

df = df.dropna(subset=["open_interest", "mark_price"])

df = (
    df
    .set_index("timestamp")
    .sort_index()
    .resample("1min")
    .agg({
        "open_interest": "last",
        "mark_price": "last",
        "funding_rate": "last"
    })
)

df = df.dropna()

# =========================
# FEATURES
# =========================

for w in [5, 15, 30, 60]:
    df[f"price_change_{w}m"] = df["mark_price"].pct_change(w) * 100
    df[f"oi_change_{w}m"] = df["open_interest"].pct_change(w) * 100

LOOKAHEAD = 60

df["future_high"] = (
    df["mark_price"]
    .shift(-1)
    .rolling(LOOKAHEAD)
    .max()
    .shift(-(LOOKAHEAD - 1))
)

df["future_low"] = (
    df["mark_price"]
    .shift(-1)
    .rolling(LOOKAHEAD)
    .min()
    .shift(-(LOOKAHEAD - 1))
)

df["future_up_pct"] = ((df["future_high"] - df["mark_price"]) / df["mark_price"]) * 100
df["future_down_pct"] = ((df["future_low"] - df["mark_price"]) / df["mark_price"]) * 100

# =========================
# REGIMES
# =========================

def classify(row, w):
    pc = row[f"price_change_{w}m"]
    oi = row[f"oi_change_{w}m"]

    if pd.isna(pc) or pd.isna(oi):
        return None

    if pc > 0 and oi > 0:
        return "PRICE_UP_OI_UP"
    if pc > 0 and oi < 0:
        return "PRICE_UP_OI_DOWN"
    if pc < 0 and oi > 0:
        return "PRICE_DOWN_OI_UP"
    if pc < 0 and oi < 0:
        return "PRICE_DOWN_OI_DOWN"

    return "FLAT"

rows = []

for w in [5, 15, 30, 60]:

    df[f"regime_{w}m"] = df.apply(lambda row: classify(row, w), axis=1)

    for regime in [
        "PRICE_UP_OI_UP",
        "PRICE_UP_OI_DOWN",
        "PRICE_DOWN_OI_UP",
        "PRICE_DOWN_OI_DOWN"
    ]:

        subset = df[df[f"regime_{w}m"] == regime].copy()

        for move in [0.3, 0.5, 0.8, 1.0]:

            if len(subset) < 50:
                continue

            up_hit = (subset["future_up_pct"] >= move).mean() * 100
            down_hit = (subset["future_down_pct"] <= -move).mean() * 100

            rows.append({
                "window_minutes": w,
                "regime": regime,
                "samples": len(subset),
                "future_move_threshold": move,
                "up_hit_rate": up_hit,
                "down_hit_rate": down_hit,
                "edge_up": up_hit - down_hit,
                "edge_down": down_hit - up_hit,
                "avg_future_up_pct": subset["future_up_pct"].mean(),
                "avg_future_down_pct": subset["future_down_pct"].mean(),
                "avg_price_change": subset[f"price_change_{w}m"].mean(),
                "avg_oi_change": subset[f"oi_change_{w}m"].mean(),
            })

out = pd.DataFrame(rows)

out = out.sort_values(
    ["future_move_threshold", "edge_up"],
    ascending=[False, False]
)

out.to_csv("reports/oi_price_regime_miner.csv", index=False)

print("\n" + "=" * 70)
print("OI PRICE REGIME MINER")
print("=" * 70)

print("\nTOP EDGE UP")
print(
    out.sort_values("edge_up", ascending=False)
    .head(20)
    .to_string(index=False)
)

print("\nTOP EDGE DOWN")
print(
    out.sort_values("edge_down", ascending=False)
    .head(20)
    .to_string(index=False)
)

print("\nArchivo generado:")
print("reports/oi_price_regime_miner.csv")
