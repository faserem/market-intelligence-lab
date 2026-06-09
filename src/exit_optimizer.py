import os
import pandas as pd
import numpy as np

SIGNALS_FILE = "reports/moe_fast_signals.csv"
DATA_FILE = "data/moe_dataset_1m.csv"

OUT_FILE = "reports/exit_optimizer.csv"

os.makedirs("reports", exist_ok=True)

TIME_WINDOWS = [30, 60, 90, 120, 180, 240]

TARGETS = [0.3, 0.5, 0.8, 1.0, 1.2, 1.5]
STOPS = [0.3, 0.5, 0.8, 1.0]

print("\n" + "=" * 70)
print("EXIT OPTIMIZER v0.1")
print("=" * 70)

signals = pd.read_csv(SIGNALS_FILE)
data = pd.read_csv(DATA_FILE)

signals["timestamp"] = pd.to_datetime(signals["timestamp"])
data["timestamp"] = pd.to_datetime(data["timestamp"])

data = data.sort_values("timestamp").reset_index(drop=True)

rows = []

for time_window in TIME_WINDOWS:
    for target in TARGETS:
        for stop in STOPS:

            results = []
            exit_reasons = []

            for _, sig in signals.iterrows():

                entry_time = sig["timestamp"]
                entry = sig["price"]
                direction = sig["decision"]

                future = data[
                    (data["timestamp"] > entry_time) &
                    (data["timestamp"] <= entry_time + pd.Timedelta(minutes=time_window))
                ]

                if future.empty:
                    continue

                pnl = None
                exit_reason = None

                for _, row in future.iterrows():

                    px = row["mark_price"]

                    if direction == "SHORT":
                        pnl_now = ((entry - px) / entry) * 100
                    else:
                        pnl_now = ((px - entry) / entry) * 100

                    if pnl_now >= target:
                        pnl = target
                        exit_reason = "TARGET"
                        break

                    if pnl_now <= -stop:
                        pnl = -stop
                        exit_reason = "STOP"
                        break

                if pnl is None:
                    last_px = future["mark_price"].iloc[-1]

                    if direction == "SHORT":
                        pnl = ((entry - last_px) / entry) * 100
                    else:
                        pnl = ((last_px - entry) / entry) * 100

                    exit_reason = "TIME_EXIT"

                results.append(pnl)
                exit_reasons.append(exit_reason)

            if len(results) < 20:
                continue

            arr = np.array(results)

            wins = arr[arr > 0]
            losses = arr[arr <= 0]

            gross_profit = wins.sum() if len(wins) else 0
            gross_loss = abs(losses.sum()) if len(losses) else 0

            pf = gross_profit / gross_loss if gross_loss > 0 else np.nan
            win_rate = len(wins) / len(arr) * 100

            rows.append({
                "time_window_minutes": time_window,
                "target_pct": target,
                "stop_pct": stop,
                "trades": len(arr),
                "win_rate_pct": win_rate,
                "profit_factor": pf,
                "avg_pnl_pct": arr.mean(),
                "total_pnl_units": arr.sum(),
                "best_trade": arr.max(),
                "worst_trade": arr.min(),
                "target_exits": exit_reasons.count("TARGET"),
                "stop_exits": exit_reasons.count("STOP"),
                "time_exits": exit_reasons.count("TIME_EXIT"),
            })

out = pd.DataFrame(rows)

out = out.sort_values(
    ["profit_factor", "avg_pnl_pct"],
    ascending=False
)

out.to_csv(OUT_FILE, index=False)

print("\nTOP 30 SALIDAS")
print(out.head(30).to_string(index=False))

print("\nArchivo generado:")
print(OUT_FILE)
