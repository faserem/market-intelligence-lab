import os
import pandas as pd
import numpy as np
from datetime import datetime

PAPER_FILE = "reports/paper_trades.csv"
DATA_FILE = "data/moe_dataset_1m.csv"

TIME_EXIT_MINUTES = 60

print("\n" + "=" * 70)
print("PAPER TRADE EVALUATOR v0.1")
print("=" * 70)

if not os.path.exists(PAPER_FILE):
    raise FileNotFoundError(f"No existe {PAPER_FILE}")

if not os.path.exists(DATA_FILE):
    raise FileNotFoundError(f"No existe {DATA_FILE}")

paper = pd.read_csv(PAPER_FILE)
data = pd.read_csv(DATA_FILE)

data["timestamp"] = pd.to_datetime(data["timestamp"])
paper["signal_timestamp"] = pd.to_datetime(paper["signal_timestamp"])

for col in ["entry", "stop", "target_1", "target_2"]:
    paper[col] = pd.to_numeric(paper[col], errors="coerce")

data = data.sort_values("timestamp").reset_index(drop=True)

updated = []

for idx, trade in paper.iterrows():

    if str(trade["status"]).upper() != "OPEN":
        updated.append(trade)
        continue

    signal_time = trade["signal_timestamp"]
    direction = trade["decision"]

    entry = trade["entry"]
    stop = trade["stop"]
    target_1 = trade["target_1"]
    target_2 = trade["target_2"]

    future = data[
        (data["timestamp"] > signal_time) &
        (data["timestamp"] <= signal_time + pd.Timedelta(minutes=TIME_EXIT_MINUTES))
    ].copy()

    if future.empty:
        updated.append(trade)
        continue

    closed = False

    for _, row in future.iterrows():

        px = row["mark_price"]
        ts = row["timestamp"]

        if direction == "SHORT":

            if px >= stop:
                trade["status"] = "CLOSED"
                trade["result"] = "STOP"
                trade["exit_price"] = px
                trade["exit_time"] = ts
                trade["pnl_pct"] = ((entry - px) / entry) * 100
                closed = True
                break

            if px <= target_2:
                trade["status"] = "CLOSED"
                trade["result"] = "TARGET_2"
                trade["exit_price"] = px
                trade["exit_time"] = ts
                trade["pnl_pct"] = ((entry - px) / entry) * 100
                closed = True
                break

            if px <= target_1:
                trade["status"] = "CLOSED"
                trade["result"] = "TARGET_1"
                trade["exit_price"] = px
                trade["exit_time"] = ts
                trade["pnl_pct"] = ((entry - px) / entry) * 100
                closed = True
                break

        elif direction == "LONG":

            if px <= stop:
                trade["status"] = "CLOSED"
                trade["result"] = "STOP"
                trade["exit_price"] = px
                trade["exit_time"] = ts
                trade["pnl_pct"] = ((px - entry) / entry) * 100
                closed = True
                break

            if px >= target_2:
                trade["status"] = "CLOSED"
                trade["result"] = "TARGET_2"
                trade["exit_price"] = px
                trade["exit_time"] = ts
                trade["pnl_pct"] = ((px - entry) / entry) * 100
                closed = True
                break

            if px >= target_1:
                trade["status"] = "CLOSED"
                trade["result"] = "TARGET_1"
                trade["exit_price"] = px
                trade["exit_time"] = ts
                trade["pnl_pct"] = ((px - entry) / entry) * 100
                closed = True
                break

    if not closed:
        last = future.iloc[-1]
        px = last["mark_price"]
        ts = last["timestamp"]

        trade["status"] = "CLOSED"
        trade["result"] = "TIME_EXIT"
        trade["exit_price"] = px
        trade["exit_time"] = ts

        if direction == "SHORT":
            trade["pnl_pct"] = ((entry - px) / entry) * 100
        else:
            trade["pnl_pct"] = ((px - entry) / entry) * 100

    updated.append(trade)

updated_df = pd.DataFrame(updated)
updated_df.to_csv(PAPER_FILE, index=False)

closed = updated_df[updated_df["status"] == "CLOSED"].copy()

print(f"Trades totales: {len(updated_df)}")
print(f"Trades cerrados: {len(closed)}")
print(f"Trades abiertos: {(updated_df['status'] == 'OPEN').sum()}")

if not closed.empty:
    closed["pnl_pct"] = pd.to_numeric(closed["pnl_pct"], errors="coerce")

    wins = closed[closed["pnl_pct"] > 0]
    losses = closed[closed["pnl_pct"] <= 0]

    gross_profit = wins["pnl_pct"].sum() if len(wins) else 0
    gross_loss = abs(losses["pnl_pct"].sum()) if len(losses) else 0

    pf = gross_profit / gross_loss if gross_loss > 0 else np.nan
    win_rate = len(wins) / len(closed) * 100

    print("\nResumen paper:")
    print(f"Win rate: {win_rate:.2f}%")
    print(f"Profit factor: {pf:.2f}")
    print(f"PnL total: {closed['pnl_pct'].sum():.4f}%")
    print(f"Mejor trade: {closed['pnl_pct'].max():.4f}%")
    print(f"Peor trade: {closed['pnl_pct'].min():.4f}%")

    print("\nÚltimos trades cerrados:")
    cols = [
        "trade_id",
        "decision",
        "setup",
        "entry",
        "exit_price",
        "result",
        "pnl_pct",
        "exit_time"
    ]
    print(closed[cols].tail(10).to_string(index=False))

print("\nArchivo actualizado:")
print(PAPER_FILE)
