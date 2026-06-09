import glob
import pandas as pd
import numpy as np

# =========================
# CONFIG
# =========================

SYMBOL = "BTCUSDT"

FILES = glob.glob("data/tardis/binance-futures_derivative_ticker_*_BTCUSDT.csv")

OUT_SIGNAL = "reports/current_signal_report.csv"
OUT_HISTORY = "reports/signal_history.csv"

TARGET_1 = 0.5
TARGET_2 = 1.0
STOP = 0.5

if not FILES:
    raise FileNotFoundError("No encontré archivos derivative_ticker en data/tardis/")

# =========================
# LOAD OI DATA
# =========================

dfs = []

for file in FILES:
    df = pd.read_csv(file)
    df["source_file"] = file
    dfs.append(df)

raw = pd.concat(dfs, ignore_index=True)

raw["timestamp"] = pd.to_datetime(raw["timestamp"], unit="us")
raw = raw.dropna(subset=["open_interest", "mark_price"])

df = (
    raw
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

for w in [5, 15, 30]:
    df[f"price_change_{w}m"] = df["mark_price"].pct_change(w) * 100
    df[f"oi_change_{w}m"] = df["open_interest"].pct_change(w) * 100

df = df.dropna()

latest = df.iloc[-1]
latest_time = df.index[-1]

price = latest["mark_price"]

pc5 = latest["price_change_5m"]
oi5 = latest["oi_change_5m"]

pc15 = latest["price_change_15m"]
oi15 = latest["oi_change_15m"]

pc30 = latest["price_change_30m"]
oi30 = latest["oi_change_30m"]

# =========================
# SIGNAL LOGIC
# =========================

bull_score = 0
bear_score = 0
reasons = []
setup = "NONE"
decision = "NO_TRADE"

# Setup principal descubierto:
# Precio sube y OI baja.
# Posible short covering agotándose.

if pc15 > 0.10 and oi15 < -0.03:
    bear_score += 45
    setup = "OI_SHORT_COVERING_FADE"
    reasons.append(f"15m: precio +{pc15:.2f}% y OI {oi15:.2f}%")

if pc5 > 0.05 and oi5 < -0.02:
    bear_score += 15
    reasons.append(f"5m confirma: precio +{pc5:.2f}% y OI {oi5:.2f}%")

if pc30 > 0.15 and oi30 < -0.05:
    bear_score += 20
    reasons.append(f"30m confirma: precio +{pc30:.2f}% y OI {oi30:.2f}%")

# Posible setup long futuro, todavía no validado como principal.
if pc15 < -0.15 and oi15 < -0.05:
    bull_score += 35
    reasons.append(f"15m posible rebote: precio {pc15:.2f}% y OI {oi15:.2f}%")

if pc5 < -0.08 and oi5 < -0.03:
    bull_score += 15
    reasons.append(f"5m confirma posible rebote: precio {pc5:.2f}% y OI {oi5:.2f}%")

# =========================
# DECISION
# =========================

if bear_score >= 60 and bear_score >= bull_score + 25:
    decision = "SHORT"
    confidence = min(100, bear_score)

elif bull_score >= 65 and bull_score >= bear_score + 25:
    decision = "LONG"
    confidence = min(100, bull_score)

elif max(bull_score, bear_score) >= 40:
    decision = "WATCH"
    confidence = max(bull_score, bear_score)

else:
    decision = "NO_TRADE"
    confidence = max(bull_score, bear_score)

# =========================
# TRADE PLAN
# =========================

if decision == "SHORT":
    entry = price
    stop_price = entry * (1 + STOP / 100)
    target_1 = entry * (1 - TARGET_1 / 100)
    target_2 = entry * (1 - TARGET_2 / 100)

elif decision == "LONG":
    entry = price
    stop_price = entry * (1 - STOP / 100)
    target_1 = entry * (1 + TARGET_1 / 100)
    target_2 = entry * (1 + TARGET_2 / 100)

else:
    entry = np.nan
    stop_price = np.nan
    target_1 = np.nan
    target_2 = np.nan

# =========================
# REPORT
# =========================

report = pd.DataFrame([{
    "timestamp": latest_time,
    "symbol": SYMBOL,
    "setup": setup,
    "decision": decision,
    "confidence": confidence,
    "price": price,
    "entry": entry,
    "stop": stop_price,
    "target_1": target_1,
    "target_2": target_2,
    "bull_score": bull_score,
    "bear_score": bear_score,
    "price_change_5m": pc5,
    "oi_change_5m": oi5,
    "price_change_15m": pc15,
    "oi_change_15m": oi15,
    "price_change_30m": pc30,
    "oi_change_30m": oi30,
    "reasons": " | ".join(reasons)
}])

report.to_csv(OUT_SIGNAL, index=False)

# Agregar al historial sólo si hay señal real o watch
if decision in ["SHORT", "LONG", "WATCH"]:
    try:
        old = pd.read_csv(OUT_HISTORY)
        history = pd.concat([old, report], ignore_index=True)
        history = history.drop_duplicates(subset=["timestamp", "decision", "setup"])
    except FileNotFoundError:
        history = report.copy()

    history.to_csv(OUT_HISTORY, index=False)

# =========================
# OUTPUT
# =========================

print("\n" + "=" * 70)
print("SIGNAL ENGINE v0.1")
print("=" * 70)

print(f"Símbolo: {SYMBOL}")
print(f"Timestamp: {latest_time}")
print(f"Precio: {price:,.2f}")

print("\nSetup:")
print(setup)

print("\nDecisión:")
print(decision)

print(f"\nConfianza: {confidence}/100")

print("\nScores:")
print(f"Bull: {bull_score}")
print(f"Bear: {bear_score}")

if decision in ["SHORT", "LONG"]:
    print("\nPlan:")
    print(f"Entrada: {entry:,.2f}")
    print(f"Stop: {stop_price:,.2f}")
    print(f"Target 1: {target_1:,.2f}")
    print(f"Target 2: {target_2:,.2f}")

print("\nMétricas:")
print(f"Price 5m: {pc5:.2f}% | OI 5m: {oi5:.2f}%")
print(f"Price 15m: {pc15:.2f}% | OI 15m: {oi15:.2f}%")
print(f"Price 30m: {pc30:.2f}% | OI 30m: {oi30:.2f}%")

print("\nRazones:")
if reasons:
    for r in reasons:
        print(f"- {r}")
else:
    print("- Sin razones suficientes.")

print("\nArchivos generados:")
print(OUT_SIGNAL)
print(OUT_HISTORY)