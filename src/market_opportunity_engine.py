import glob
import os
import pandas as pd
import numpy as np

SYMBOL = "BTCUSDT"
FILES = sorted(glob.glob("data/tardis/binance-futures_derivative_ticker_*_BTCUSDT.csv"))

REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)

OUT_SIGNALS = f"{REPORT_DIR}/moe_v2_signals.csv"
OUT_BACKTEST = f"{REPORT_DIR}/moe_v2_backtest.csv"
OUT_CURRENT = f"{REPORT_DIR}/moe_v2_current_signal.csv"

LOOKAHEAD_MINUTES = 60

CONFIGS = [
    {"name": "BASE", "p15": 0.10, "oi15": -0.03, "p5": 0.05, "oi5": -0.02, "p30": 0.15, "oi30": -0.05, "cooldown": 15},
    {"name": "STRICT", "p15": 0.15, "oi15": -0.05, "p5": 0.05, "oi5": -0.02, "p30": 0.20, "oi30": -0.08, "cooldown": 20},
    {"name": "AGGRESSIVE", "p15": 0.08, "oi15": -0.02, "p5": 0.03, "oi5": -0.01, "p30": 0.10, "oi30": -0.03, "cooldown": 10},
    {"name": "HIGH_CONF", "p15": 0.20, "oi15": -0.08, "p5": 0.08, "oi5": -0.03, "p30": 0.30, "oi30": -0.10, "cooldown": 30},
]

TARGETS = [0.5, 0.8, 1.0]
STOPS = [0.3, 0.5, 0.8]

if not FILES:
    raise FileNotFoundError("No encontré derivative_ticker en data/tardis/")

dfs = []
for file in FILES:
    temp = pd.read_csv(file)
    temp["source_file"] = file
    dfs.append(temp)

raw = pd.concat(dfs, ignore_index=True)
raw["timestamp"] = pd.to_datetime(raw["timestamp"], unit="us")
raw = raw.dropna(subset=["open_interest", "mark_price"])

df = (
    raw.set_index("timestamp")
    .sort_index()
    .resample("1min")
    .agg({
        "open_interest": "last",
        "mark_price": "last",
        "funding_rate": "last"
    })
    .dropna()
)

for w in [5, 15, 30, 60]:
    df[f"price_change_{w}m"] = df["mark_price"].pct_change(w) * 100
    df[f"oi_change_{w}m"] = df["open_interest"].pct_change(w) * 100

df = df.dropna()

def generate_signals(data, cfg):
    signals = []
    last_signal_time = None

    for ts, row in data.iterrows():
        if last_signal_time is not None:
            diff = (ts - last_signal_time).total_seconds() / 60
            if diff < cfg["cooldown"]:
                continue

        bear = 0
        bull = 0
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

        if row["price_change_15m"] <= -0.15 and row["oi_change_15m"] <= -0.05:
            bull += 35
            reasons.append("15m posible rebote")

        if row["price_change_5m"] <= -0.08 and row["oi_change_5m"] <= -0.03:
            bull += 15
            reasons.append("5m rebote confirma")

        if bear >= 60 and bear >= bull + 25:
            decision = "SHORT"
            setup = "OI_SHORT_COVERING_FADE"
            confidence = min(100, bear)
        elif bull >= 65 and bull >= bear + 25:
            decision = "LONG"
            setup = "OI_REBOUND_PRELIMINARY"
            confidence = min(100, bull)
        else:
            continue

        signals.append({
            "timestamp": ts,
            "price": row["mark_price"],
            "decision": decision,
            "setup": setup,
            "confidence": confidence,
            "bull_score": bull,
            "bear_score": bear,
            "price_change_5m": row["price_change_5m"],
            "oi_change_5m": row["oi_change_5m"],
            "price_change_15m": row["price_change_15m"],
            "oi_change_15m": row["oi_change_15m"],
            "price_change_30m": row["price_change_30m"],
            "oi_change_30m": row["oi_change_30m"],
            "reasons": " | ".join(reasons),
            "config": cfg["name"]
        })

        last_signal_time = ts

    return pd.DataFrame(signals)

def simulate_trade(data, sig, target, stop):
    entry_time = sig["timestamp"]
    entry = sig["price"]
    direction = sig["decision"]

    future = data.loc[
        (data.index > entry_time) &
        (data.index <= entry_time + pd.Timedelta(minutes=LOOKAHEAD_MINUTES))
    ]

    if future.empty:
        return None

    for exit_time, row in future.iterrows():
        px = row["mark_price"]

        if direction == "SHORT":
            pnl = ((entry - px) / entry) * 100
        else:
            pnl = ((px - entry) / entry) * 100

        if pnl >= target:
            return target, "TARGET", exit_time

        if pnl <= -stop:
            return -stop, "STOP", exit_time

    last_px = future["mark_price"].iloc[-1]

    if direction == "SHORT":
        pnl = ((entry - last_px) / entry) * 100
    else:
        pnl = ((last_px - entry) / entry) * 100

    return pnl, "TIME_EXIT", future.index[-1]

rows = []
all_signals = []

print("\n" + "=" * 70)
print("MARKET OPPORTUNITY ENGINE v2 FAST")
print("=" * 70)
print(f"Archivos leídos: {len(FILES)}")
print(f"Filas 1m: {len(df)}")

for cfg in CONFIGS:
    print(f"\nProbando config: {cfg['name']}")
    signals = generate_signals(df, cfg)

    if signals.empty:
        continue

    all_signals.append(signals)

    for target in TARGETS:
        for stop in STOPS:
            pnls = []
            exits = []

            for _, sig in signals.iterrows():
                result = simulate_trade(df, sig, target, stop)
                if result is None:
                    continue

                pnl, reason, exit_time = result
                pnls.append(pnl)
                exits.append(reason)

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
                "worst_trade": arr.min(),
                "short_trades": (signals["decision"] == "SHORT").sum(),
                "long_trades": (signals["decision"] == "LONG").sum(),
            })

backtest = pd.DataFrame(rows)

if backtest.empty:
    print("No hubo resultados suficientes.")
    raise SystemExit

backtest = backtest.sort_values(
    ["profit_factor", "avg_pnl_pct", "trades"],
    ascending=[False, False, False]
)

signals_out = pd.concat(all_signals, ignore_index=True) if all_signals else pd.DataFrame()

backtest.to_csv(OUT_BACKTEST, index=False)
signals_out.to_csv(OUT_SIGNALS, index=False)

best = backtest.iloc[0]
best_config_name = best["config"]

best_signals = signals_out[signals_out["config"] == best_config_name].copy()
last_signal = best_signals.tail(1)

if last_signal.empty:
    current = pd.DataFrame([{
        "timestamp": df.index[-1],
        "symbol": SYMBOL,
        "decision": "NO_TRADE",
        "setup": "NONE",
        "confidence": 0,
        "price": df["mark_price"].iloc[-1],
        "reasons": "Sin señal"
    }])
else:
    sig = last_signal.iloc[-1]
    entry = sig["price"]

    if sig["decision"] == "SHORT":
        stop_price = entry * (1 + best["stop"] / 100)
        target_1 = entry * (1 - 0.5 / 100)
        target_2 = entry * (1 - best["target"] / 100)
    else:
        stop_price = entry * (1 - best["stop"] / 100)
        target_1 = entry * (1 + 0.5 / 100)
        target_2 = entry * (1 + best["target"] / 100)

    current = pd.DataFrame([{
        "timestamp": sig["timestamp"],
        "symbol": SYMBOL,
        "decision": sig["decision"],
        "setup": sig["setup"],
        "confidence": sig["confidence"],
        "price": entry,
        "entry": entry,
        "stop": stop_price,
        "target_1": target_1,
        "target_2": target_2,
        "best_config": best_config_name,
        "best_pf": best["profit_factor"],
        "best_win_rate": best["win_rate_pct"],
        "best_trades": best["trades"],
        "reasons": sig["reasons"]
    }])

current.to_csv(OUT_CURRENT, index=False)

print("\nMEJOR CONFIGURACIÓN")
print(best.to_string())

print("\nTOP 20 CONFIGURACIONES")
print(backtest.head(20).to_string(index=False))

print("\nSEÑAL ACTUAL / ÚLTIMA SEÑAL")
print(current.to_string(index=False))

print("\nArchivos generados:")
print(OUT_BACKTEST)
print(OUT_SIGNALS)
print(OUT_CURRENT)