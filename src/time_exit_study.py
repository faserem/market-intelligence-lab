import pandas as pd
import numpy as np

SIGNALS_FILE = "reports/moe_fast_signals.csv"
DATA_FILE = "data/moe_dataset_1m.csv"

TIME_WINDOWS = [
    30,
    60,
    120,
    180,
    240,
    360,
]

signals = pd.read_csv(SIGNALS_FILE)
data = pd.read_csv(DATA_FILE)

signals["timestamp"] = pd.to_datetime(signals["timestamp"])
data["timestamp"] = pd.to_datetime(data["timestamp"])

results = []

print("\n" + "=" * 70)
print("TIME EXIT STUDY")
print("=" * 70)

for window in TIME_WINDOWS:

    pnls = []

    for _, sig in signals.iterrows():

        if sig["decision"] != "SHORT":
            continue

        entry_time = sig["timestamp"]
        entry = sig["price"]

        future = data[
            (data["timestamp"] > entry_time)
            & (
                data["timestamp"]
                <= entry_time + pd.Timedelta(minutes=window)
            )
        ]

        if future.empty:
            continue

        exit_price = future.iloc[-1]["mark_price"]

        pnl = ((entry - exit_price) / entry) * 100

        pnls.append(pnl)

    if len(pnls) == 0:
        continue

    arr = np.array(pnls)

    wins = arr[arr > 0]
    losses = arr[arr <= 0]

    win_rate = len(wins) / len(arr) * 100

    gross_profit = wins.sum() if len(wins) else 0
    gross_loss = abs(losses.sum()) if len(losses) else 0

    pf = (
        gross_profit / gross_loss
        if gross_loss > 0
        else np.nan
    )

    results.append({
        "minutes": window,
        "trades": len(arr),
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(pf, 2),
        "avg_pnl_pct": round(arr.mean(), 4),
        "median_pnl_pct": round(np.median(arr), 4),
        "best_trade": round(arr.max(), 4),
        "worst_trade": round(arr.min(), 4),
        "total_pnl_pct": round(arr.sum(), 4),
    })

out = pd.DataFrame(results)

out = out.sort_values(
    ["profit_factor", "avg_pnl_pct"],
    ascending=False
)

print("\nRESULTADOS\n")
print(out.to_string(index=False))

out.to_csv(
    "reports/time_exit_study.csv",
    index=False
)

print("\nArchivo generado:")
print("reports/time_exit_study.csv")