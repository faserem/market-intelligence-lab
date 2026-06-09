import os
import pandas as pd
import numpy as np

# ============================================================
# SIGNAL ENGINE FINAL
# Setup operativo:
# OI_SHORT_COVERING_FADE
#
# Entrada:
# Precio sube + Open Interest baja
#
# Salida sugerida:
# TIME EXIT 360 minutos
#
# Basado en:
# - moe_fast_signals.csv
# - time_exit_study.csv
# ============================================================

DATA_FILE = "data/moe_dataset_1m.csv"

OUT_CURRENT = "reports/moe_current_signal.csv"
OUT_HISTORY = "reports/signal_history.csv"

SYMBOL = "BTCUSDT"

TIME_EXIT_MINUTES = 360

# Config HIGH_CONF ganadora
P15 = 0.20
OI15 = -0.08

P5 = 0.08
OI5 = -0.03

P30 = 0.30
OI30 = -0.10

COOLDOWN_MINUTES = 30

EXPECTED_PF = 3.39
EXPECTED_WR = 67.40
EXPECTED_TRADES = 181

os.makedirs("reports", exist_ok=True)

df = pd.read_csv(DATA_FILE)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)

latest = df.iloc[-1]

price = latest["mark_price"]

bear = 0
reasons = []

if latest["price_change_15m"] >= P15 and latest["oi_change_15m"] <= OI15:
    bear += 45
    reasons.append("15m precio sube + OI baja")

if latest["price_change_5m"] >= P5 and latest["oi_change_5m"] <= OI5:
    bear += 15
    reasons.append("5m confirma")

if latest["price_change_30m"] >= P30 and latest["oi_change_30m"] <= OI30:
    bear += 20
    reasons.append("30m confirma")

if bear >= 60:
    decision = "SHORT"
    setup = "OI_SHORT_COVERING_FADE"
    confidence = bear
    entry = price

    # Ya no usamos TP/SL principal. La salida base es por tiempo.
    stop = np.nan
    target_1 = np.nan
    target_2 = np.nan

    exit_plan = f"TIME_EXIT_{TIME_EXIT_MINUTES}_MIN"

else:
    decision = "NO_TRADE"
    setup = "NONE"
    confidence = bear
    entry = np.nan
    stop = np.nan
    target_1 = np.nan
    target_2 = np.nan
    exit_plan = "NONE"

report = pd.DataFrame([{
    "timestamp": latest["timestamp"],
    "symbol": SYMBOL,
    "decision": decision,
    "setup": setup,
    "confidence": confidence,
    "price": price,
    "entry": entry,
    "stop": stop,
    "target_1": target_1,
    "target_2": target_2,
    "exit_plan": exit_plan,
    "time_exit_minutes": TIME_EXIT_MINUTES,
    "expected_pf": EXPECTED_PF,
    "expected_win_rate": EXPECTED_WR,
    "expected_trades": EXPECTED_TRADES,
    "price_change_5m": latest["price_change_5m"],
    "oi_change_5m": latest["oi_change_5m"],
    "price_change_15m": latest["price_change_15m"],
    "oi_change_15m": latest["oi_change_15m"],
    "price_change_30m": latest["price_change_30m"],
    "oi_change_30m": latest["oi_change_30m"],
    "reasons": " | ".join(reasons) if reasons else "Sin señal suficiente"
}])

report.to_csv(OUT_CURRENT, index=False)

if decision != "NO_TRADE":
    if os.path.exists(OUT_HISTORY):
        old = pd.read_csv(OUT_HISTORY)
        history = pd.concat([old, report], ignore_index=True)
        history = history.drop_duplicates(subset=["timestamp", "decision", "setup"])
    else:
        history = report.copy()

    history.to_csv(OUT_HISTORY, index=False)

print("\n" + "=" * 70)
print("SIGNAL ENGINE FINAL")
print("=" * 70)

print(f"Símbolo: {SYMBOL}")
print(f"Timestamp: {latest['timestamp']}")
print(f"Precio: {price:,.2f}")

print("\nDecisión:")
print(decision)

print("\nSetup:")
print(setup)

print(f"\nConfianza: {confidence}/100")

print("\nMétricas:")
print(f"Price 5m: {latest['price_change_5m']:.2f}% | OI 5m: {latest['oi_change_5m']:.2f}%")
print(f"Price 15m: {latest['price_change_15m']:.2f}% | OI 15m: {latest['oi_change_15m']:.2f}%")
print(f"Price 30m: {latest['price_change_30m']:.2f}% | OI 30m: {latest['oi_change_30m']:.2f}%")

if decision == "SHORT":
    print("\nPlan:")
    print(f"Entrada SHORT: {entry:,.2f}")
    print(f"Salida: cerrar a los {TIME_EXIT_MINUTES} minutos")
    print(f"PF esperado histórico: {EXPECTED_PF}")
    print(f"Win rate esperado histórico: {EXPECTED_WR}%")

print("\nRazones:")
for r in reasons:
    print(f"- {r}")

if not reasons:
    print("- Sin señal suficiente.")

print("\nArchivos generados:")
print(OUT_CURRENT)
print(OUT_HISTORY)