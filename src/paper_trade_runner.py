import os
import pandas as pd
from datetime import datetime

SIGNAL_FILE = "reports/moe_current_signal.csv"
PAPER_FILE = "reports/paper_trades.csv"

os.makedirs("reports", exist_ok=True)

print("\n" + "=" * 70)
print("PAPER TRADE RUNNER v0.1")
print("=" * 70)

if not os.path.exists(SIGNAL_FILE):
    raise FileNotFoundError(f"No existe {SIGNAL_FILE}")

signal = pd.read_csv(SIGNAL_FILE)

if signal.empty:
    raise ValueError("Archivo de señal vacío")

sig = signal.iloc[0]

if sig["decision"] == "NO_TRADE":
    print("No hay señal.")
    raise SystemExit

trade_id = (
    str(sig["timestamp"])
    + "_"
    + str(sig["decision"])
)

new_trade = {
    "trade_id": trade_id,
    "created_at": datetime.utcnow(),
    "signal_timestamp": sig["timestamp"],
    "symbol": sig["symbol"],
    "setup": sig["setup"],
    "decision": sig["decision"],
    "confidence": sig["confidence"],
    "entry": sig["entry"],
    "stop": sig["stop"],
    "target_1": sig["target_1"],
    "target_2": sig["target_2"],
    "status": "OPEN",
    "result": "",
    "exit_price": "",
    "pnl_pct": "",
    "notes": sig["reasons"]
}

if os.path.exists(PAPER_FILE):
    paper = pd.read_csv(PAPER_FILE)

    if trade_id in paper["trade_id"].astype(str).values:
        print("Trade ya registrado.")
        print(trade_id)
        raise SystemExit

    paper = pd.concat(
        [paper, pd.DataFrame([new_trade])],
        ignore_index=True
    )

else:
    paper = pd.DataFrame([new_trade])

paper.to_csv(PAPER_FILE, index=False)

print("\nTrade agregado:")
print(f"ID: {trade_id}")
print(f"Setup: {sig['setup']}")
print(f"Decision: {sig['decision']}")
print(f"Entry: {sig['entry']}")
print(f"Stop: {sig['stop']}")
print(f"TP1: {sig['target_1']}")
print(f"TP2: {sig['target_2']}")

print("\nArchivo actualizado:")
print(PAPER_FILE)