import pandas as pd
import numpy as np
import os

FILE = "data/tardis/binance-futures_derivative_ticker_2026-06-01_BTCUSDT.csv"

OUT_FILE = "reports/out_of_sample_validator.csv"

TARGET = 1.5
STOP = 0.5
LOOKAHEAD_MINUTES = 180
COOLDOWN_MINUTES = 30

# HIGH_CONF ganador:
P15 = 0.20
OI15 = -0.08
P5 = 0.08
OI5 = -0.03
P30 = 0.30
OI30 = -0.10

os.makedirs("reports", exist_ok=True)

df = pd.read_csv(FILE)
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="us")
df = df.dropna(subset=["open_interest", "mark_price"])

df = (
    df.set_index("timestamp")
    .sort_index()
    .resample("1min")
    .agg({
        "open_interest": "last",
        "mark_price": "last",
        "funding_rate": "last"
    })
    .dropna()
)

for w in [5, 15, 30]:
    df[f"price_change_{w}m"] = df["mark_price"].pct_change(w) * 100
    df[f"oi_change_{w}m"] = df["open_interest"].pct_change(w) * 100

df = df.dropna().reset_index()

signals = []
last_signal_time = None

for _, row in df.iterrows():
    ts = row["timestamp"]

    if last_signal_time is not None:
        diff = (ts - last_signal_time).total_seconds() / 60
        if diff < COOLDOWN_MINUTES:
            continue

    bear = 0
    reasons = []

    if row["price_change_15m"] >= P15 and row["oi_change_15m"] <= OI15:
        bear += 45
        reasons.append("15m precio sube + OI baja")

    if row["price_change_5m"] >= P5 and row["oi_change_5m"] <= OI5:
        bear += 15
        reasons.append("5m confirma")

    if row["price_change_30m"] >= P30 and row["oi_change_30m"] <= OI30:
        bear += 20
        reasons.append("30m confirma")

    if bear >= 60:
        signals.append({
            "timestamp": ts,
            "price": row["mark_price"],
            "decision": "SHORT",
            "confidence": bear,
            "reasons": " | ".join(reasons)
        })

        last_signal_time = ts

signals = pd.DataFrame(signals)

trades = []

for _, sig in signals.iterrows():
    entry_time = sig["timestamp"]
    entry = sig["price"]

    future = df[
        (df["timestamp"] > entry_time) &
        (df["timestamp"] <= entry_time + pd.Timedelta(minutes=LOOKAHEAD_MINUTES))
    ]

    if future.empty:
        continue

    pnl = None
    exit_reason = None
    exit_price = None
    exit_time = None

    for _, row in future.iterrows():
        px = row["mark_price"]
        pnl_now = ((entry - px) / entry) * 100

        if pnl_now >= TARGET:
            pnl = TARGET
            exit_reason = "TARGET"
            exit_price = px
            exit_time = row["timestamp"]
            break

        if pnl_now <= -STOP:
            pnl = -STOP
            exit_reason = "STOP"
            exit_price = px
            exit_time = row["timestamp"]
            break

    if pnl is None:
        last = future.iloc[-1]
        exit_price = last["mark_price"]
        exit_time = last["timestamp"]
        pnl = ((entry - exit_price) / entry) * 100
        exit_reason = "TIME_EXIT"

    trades.append({
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry": entry,
        "exit": exit_price,
        "pnl_pct": pnl,
        "exit_reason": exit_reason,
        "confidence": sig["confidence"],
        "reasons": sig["reasons"]
    })

trades = pd.DataFrame(trades)
trades.to_csv(OUT_FILE, index=False)

print("\n" + "=" * 70)
print("OUT OF SAMPLE VALIDATOR")
print("=" * 70)

print("Dataset: 2026-06-01")
print(f"Filas 1m: {len(df)}")
print(f"Señales: {len(signals)}")
print(f"Trades evaluados: {len(trades)}")

if not trades.empty:
    wins = trades[trades["pnl_pct"] > 0]
    losses = trades[trades["pnl_pct"] <= 0]

    gross_profit = wins["pnl_pct"].sum() if len(wins) else 0
    gross_loss = abs(losses["pnl_pct"].sum()) if len(losses) else 0

    pf = gross_profit / gross_loss if gross_loss > 0 else np.nan
    win_rate = len(wins) / len(trades) * 100

    print("\nRESULTADO OUT OF SAMPLE")
    print(f"Win rate: {win_rate:.2f}%")
    print(f"Profit factor: {pf:.2f}")
    print(f"Avg PnL: {trades['pnl_pct'].mean():.4f}%")
    print(f"Total PnL units: {trades['pnl_pct'].sum():.4f}%")
    print(f"Best trade: {trades['pnl_pct'].max():.4f}%")
    print(f"Worst trade: {trades['pnl_pct'].min():.4f}%")

    print("\nTrades:")
    print(trades.to_string(index=False))

print("\nArchivo generado:")
print(OUT_FILE)