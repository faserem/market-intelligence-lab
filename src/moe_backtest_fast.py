import os
import pandas as pd
import numpy as np

DATA_FILE = "data/moe_dataset_1m.csv"

OUT_BACKTEST = "reports/moe_fast_backtest.csv"
OUT_SIGNALS = "reports/moe_fast_signals.csv"
OUT_CURRENT = "reports/moe_current_signal.csv"

os.makedirs("reports", exist_ok=True)

df = pd.read_csv(DATA_FILE)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)

LOOKAHEAD = 60

CONFIGS = [
    {
        "name": "BASE",
        "p15": 0.10,
        "oi15": -0.03,
        "p5": 0.05,
        "oi5": -0.02,
        "p30": 0.15,
        "oi30": -0.05,
        "cooldown": 15
    },
    {
        "name": "STRICT",
        "p15": 0.15,
        "oi15": -0.05,
        "p5": 0.05,
        "oi5": -0.02,
        "p30": 0.20,
        "oi30": -0.08,
        "cooldown": 20
    },
    {
        "name": "HIGH_CONF",
        "p15": 0.20,
        "oi15": -0.08,
        "p5": 0.08,
        "oi5": -0.03,
        "p30": 0.30,
        "oi30": -0.10,
        "cooldown": 30
    },
]

TARGETS = [0.5, 0.8, 1.0]
STOPS = [0.3, 0.5, 0.8]

def generate_signals(data, cfg):
    signals = []
    last_signal_time = None

    for _, row in data.iterrows():
        ts = row["timestamp"]

        if last_signal_time is not None:
            diff = (ts - last_signal_time).total_seconds() / 60
            if diff < cfg["cooldown"]:
                continue

        bear = 0
        reasons = []

        if row["price_change_15m"] >= cfg["p15"] and row["oi_change_15m"] <= cfg["oi15"]:
            bear += 45
            reasons.append("15m precio sube + OI baja")

        if row["price_change_5m"] >= cfg["p5"] and row["oi_change_5m"] <= cfg["oi5"]:
            bear += 15
            reasons.append("5m confirma")

        if row["price_change_30m"] >= cfg["p30"] and row["oi_change_30m"] <= cfg["oi30"]:
            bear += 20
            reasons.append("30m confirma")

        if bear >= 60:
            signals.append({
                "timestamp": ts,
                "price": row["mark_price"],
                "decision": "SHORT",
                "setup": "OI_SHORT_COVERING_FADE",
                "confidence": bear,
                "config": cfg["name"],
                "price_change_5m": row["price_change_5m"],
                "oi_change_5m": row["oi_change_5m"],
                "price_change_15m": row["price_change_15m"],
                "oi_change_15m": row["oi_change_15m"],
                "price_change_30m": row["price_change_30m"],
                "oi_change_30m": row["oi_change_30m"],
                "reasons": " | ".join(reasons)
            })

            last_signal_time = ts

    return pd.DataFrame(signals)

def simulate_trade(data, sig, target, stop):
    entry_time = sig["timestamp"]
    entry_price = sig["price"]

    future = data[
        (data["timestamp"] > entry_time) &
        (data["timestamp"] <= entry_time + pd.Timedelta(minutes=LOOKAHEAD))
    ]

    if future.empty:
        return None

    for _, row in future.iterrows():
        px = row["mark_price"]
        pnl = ((entry_price - px) / entry_price) * 100

        if pnl >= target:
            return target

        if pnl <= -stop:
            return -stop

    last_px = future["mark_price"].iloc[-1]
    return ((entry_price - last_px) / entry_price) * 100

all_signals = []
rows = []

print("\nMOE BACKTEST FAST")
print("=" * 70)

for cfg in CONFIGS:
    print(f"Probando config: {cfg['name']}", flush=True)

    signals = generate_signals(df, cfg)

    if signals.empty:
        print("Sin señales.")
        continue

    all_signals.append(signals)

    for target in TARGETS:
        for stop in STOPS:
            pnls = []

            for _, sig in signals.iterrows():
                pnl = simulate_trade(df, sig, target, stop)
                if pnl is not None:
                    pnls.append(pnl)

            if len(pnls) < 10:
                continue

            arr = np.array(pnls)
            wins = arr[arr > 0]
            losses = arr[arr <= 0]

            gross_profit = wins.sum() if len(wins) else 0
            gross_loss = abs(losses.sum()) if len(losses) else 0

            pf = gross_profit / gross_loss if gross_loss > 0 else np.nan
            win_rate = len(wins) / len(arr) * 100

            rows.append({
                "config": cfg["name"],
                "trades": len(arr),
                "target": target,
                "stop": stop,
                "win_rate_pct": win_rate,
                "profit_factor": pf,
                "avg_pnl_pct": arr.mean(),
                "total_pnl_units": arr.sum(),
                "best_trade": arr.max(),
                "worst_trade": arr.min()
            })

backtest = pd.DataFrame(rows)

if backtest.empty:
    print("No hubo resultados.")
    raise SystemExit

signals_out = pd.concat(all_signals, ignore_index=True)

backtest = backtest.sort_values(
    ["profit_factor", "avg_pnl_pct"],
    ascending=False
)

backtest.to_csv(OUT_BACKTEST, index=False)
signals_out.to_csv(OUT_SIGNALS, index=False)

best = backtest.iloc[0]
last_signal = signals_out[signals_out["config"] == best["config"]].tail(1)

if last_signal.empty:
    current = pd.DataFrame([{
        "decision": "NO_TRADE"
    }])
else:
    sig = last_signal.iloc[0]
    entry = sig["price"]

    current = pd.DataFrame([{
        "timestamp": sig["timestamp"],
        "symbol": "BTCUSDT",
        "decision": sig["decision"],
        "setup": sig["setup"],
        "confidence": sig["confidence"],
        "entry": entry,
        "stop": entry * (1 + best["stop"] / 100),
        "target_1": entry * (1 - 0.5 / 100),
        "target_2": entry * (1 - best["target"] / 100),
        "best_config": best["config"],
        "best_pf": best["profit_factor"],
        "best_win_rate": best["win_rate_pct"],
        "best_trades": best["trades"],
        "reasons": sig["reasons"]
    }])

current.to_csv(OUT_CURRENT, index=False)

print("\nTOP CONFIGURACIONES")
print(backtest.head(20).to_string(index=False))

print("\nSEÑAL ACTUAL / ÚLTIMA SEÑAL")
print(current.to_string(index=False))

print("\nArchivos generados:")
print(OUT_BACKTEST)
print(OUT_SIGNALS)
print(OUT_CURRENT)