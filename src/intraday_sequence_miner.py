import pandas as pd
import numpy as np

DATA_PATH = "data/intraday/BTCUSDT_5m.csv"

df = pd.read_csv(DATA_PATH)

df["open_time"] = pd.to_datetime(df["open_time"])

for col in df.columns:
    if col not in ["open_time", "close_time"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna().reset_index(drop=True)

# ======================================
# CONFIG
# ======================================

LOOKBACK_BARS = 12      # 1 hora previa
FORWARD_BARS = 12       # 1 hora futura

MOVE_THRESHOLDS = [
    1.0,
    1.5,
    2.0,
    3.0
]

# ======================================
# FUTURE MOVE
# ======================================

df["future_high"] = (
    df["high"]
    .shift(-1)
    .rolling(FORWARD_BARS)
    .max()
    .shift(-(FORWARD_BARS-1))
)

df["future_low"] = (
    df["low"]
    .shift(-1)
    .rolling(FORWARD_BARS)
    .min()
    .shift(-(FORWARD_BARS-1))
)

df["future_up_pct"] = (
    (df["future_high"] - df["close"])
    / df["close"]
) * 100

df["future_down_pct"] = (
    (df["future_low"] - df["close"])
    / df["close"]
) * 100

# ======================================
# SECUENCIAS
# ======================================

rows = []

for threshold in MOVE_THRESHOLDS:

    up_events = df[
        df["future_up_pct"] >= threshold
    ].index

    down_events = df[
        df["future_down_pct"] <= -threshold
    ].index

    for direction, events in [
        ("UP", up_events),
        ("DOWN", down_events)
    ]:

        samples = []

        for idx in events:

            if idx < LOOKBACK_BARS:
                continue

            seq = df.iloc[idx-LOOKBACK_BARS:idx]

            sample = {
                "threshold": threshold,
                "direction": direction
            }

            sample["avg_volume_ratio"] = (
                seq["volume_ratio_20"].mean()
            )

            sample["max_volume_ratio"] = (
                seq["volume_ratio_20"].max()
            )

            sample["avg_trades_ratio"] = (
                seq["trades_ratio_20"].mean()
            )

            sample["avg_taker_buy_ratio"] = (
                seq["taker_buy_ratio"].mean()
            )

            sample["last_taker_buy_ratio"] = (
                seq["taker_buy_ratio"].iloc[-1]
            )

            sample["avg_body_pct"] = (
                seq["body_pct"].mean()
            )

            sample["avg_range_pct"] = (
                seq["range_pct"].mean()
            )

            sample["price_change_seq_pct"] = (
                (
                    seq["close"].iloc[-1]
                    -
                    seq["close"].iloc[0]
                )
                /
                seq["close"].iloc[0]
            ) * 100

            sample["volume_acceleration"] = (
                seq["volume_ratio_20"].tail(3).mean()
                -
                seq["volume_ratio_20"].head(3).mean()
            )

            sample["trades_acceleration"] = (
                seq["trades_ratio_20"].tail(3).mean()
                -
                seq["trades_ratio_20"].head(3).mean()
            )

            samples.append(sample)

        if len(samples) == 0:
            continue

        samples = pd.DataFrame(samples)

        rows.append({
            "direction": direction,
            "threshold": threshold,
            "events": len(samples),

            "avg_volume_ratio":
                samples["avg_volume_ratio"].mean(),

            "max_volume_ratio":
                samples["max_volume_ratio"].mean(),

            "avg_trades_ratio":
                samples["avg_trades_ratio"].mean(),

            "avg_taker_buy_ratio":
                samples["avg_taker_buy_ratio"].mean(),

            "last_taker_buy_ratio":
                samples["last_taker_buy_ratio"].mean(),

            "avg_body_pct":
                samples["avg_body_pct"].mean(),

            "avg_range_pct":
                samples["avg_range_pct"].mean(),

            "price_change_seq_pct":
                samples["price_change_seq_pct"].mean(),

            "volume_acceleration":
                samples["volume_acceleration"].mean(),

            "trades_acceleration":
                samples["trades_acceleration"].mean()
        })

result = pd.DataFrame(rows)

result.to_csv(
    "reports/intraday_sequence_patterns.csv",
    index=False
)

print("\n" + "="*70)
print("INTRADAY SEQUENCE MINER")
print("="*70)

print(result.to_string(index=False))

print("\nArchivo generado:")
print("reports/intraday_sequence_patterns.csv")