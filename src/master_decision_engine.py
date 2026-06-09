import glob
import pandas as pd
import numpy as np

# =========================
# CONFIG
# =========================

INTRADAY_FILE = "data/live_btc_5m.csv"
OI_FILES = glob.glob("data/tardis/binance-futures_derivative_ticker_*_BTCUSDT.csv")

SYMBOL = "BTCUSDT"

# =========================
# LOAD 5M DATA
# =========================

price = pd.read_csv(INTRADAY_FILE)
price["open_time"] = pd.to_datetime(price["open_time"])

for col in price.columns:
    if col not in ["open_time", "close_time"]:
        price[col] = pd.to_numeric(price[col], errors="coerce")

price = price.dropna().sort_values("open_time").reset_index(drop=True)

last = price.iloc[-1]

# =========================
# PRICE / VOLUME SENSORS
# =========================

price["ema20"] = price["close"].ewm(span=20, adjust=False).mean()
price["ema50"] = price["close"].ewm(span=50, adjust=False).mean()

price["ret_3"] = price["close"].pct_change(3) * 100
price["ret_6"] = price["close"].pct_change(6) * 100
price["ret_12"] = price["close"].pct_change(12) * 100

price["vol_ratio_20"] = price["volume"] / price["volume"].rolling(20).mean()
price["trades_ratio_20"] = price["number_of_trades"] / price["number_of_trades"].rolling(20).mean()

price["range_pct"] = (price["high"] - price["low"]) / price["open"] * 100
price["body_pct"] = abs(price["close"] - price["open"]) / price["open"] * 100

price["range_ma_20"] = price["range_pct"].rolling(20).mean()
price["range_ma_100"] = price["range_pct"].rolling(100).mean()

price["compressed"] = price["range_ma_20"] < price["range_ma_100"] * 0.75

p = price.iloc[-1]

bull_score = 0
bear_score = 0
notes = []

# =========================
# MOMENTUM SENSOR
# =========================

if p["ret_3"] > 0.25 and p["ret_6"] > 0.4:
    bull_score += 15
    notes.append("Momentum corto alcista.")

if p["ret_3"] < -0.25 and p["ret_6"] < -0.4:
    bear_score += 15
    notes.append("Momentum corto bajista.")

# =========================
# EMA POSITION SENSOR
# =========================

if p["close"] > p["ema20"] > p["ema50"]:
    bull_score += 12
    notes.append("Precio sobre EMA20 y EMA50.")

if p["close"] < p["ema20"] < p["ema50"]:
    bear_score += 12
    notes.append("Precio bajo EMA20 y EMA50.")

# =========================
# VOLUME / ACTIVITY SENSOR
# =========================

if p["vol_ratio_20"] >= 1.5 and p["trades_ratio_20"] >= 1.5:
    bull_score += 8
    bear_score += 8
    notes.append("Actividad elevada: volumen y cantidad de trades altos.")

if p["vol_ratio_20"] >= 2.5 and p["trades_ratio_20"] >= 2.5:
    bull_score += 10
    bear_score += 10
    notes.append("Actividad extrema detectada.")

# =========================
# TAKER PRESSURE SENSOR
# =========================

if p["taker_buy_ratio"] >= 0.58:
    bull_score += 12
    notes.append("Presión compradora agresiva.")

if p["taker_buy_ratio"] <= 0.42:
    bear_score += 12
    notes.append("Presión vendedora agresiva.")

# =========================
# COMPRESSION SENSOR
# =========================

if bool(p["compressed"]):
    bull_score += 6
    bear_score += 6
    notes.append("Compresión previa detectada.")

# =========================
# OPEN INTEREST SENSOR
# =========================

oi_available = False

using_live_price = "live_btc_5m.csv" in INTRADAY_FILE

if OI_FILES and not using_live_price:
    dfs = []

    for file in OI_FILES:
        df = pd.read_csv(file)
        dfs.append(df)

    oi = pd.concat(dfs, ignore_index=True)
    oi["timestamp"] = pd.to_datetime(oi["timestamp"], unit="us")

    oi = oi.dropna(subset=["open_interest", "mark_price"])

    oi = (
        oi
        .set_index("timestamp")
        .sort_index()
        .resample("1min")
        .agg({
            "open_interest": "last",
            "mark_price": "last",
            "funding_rate": "last"
        })
    )

    oi = oi.dropna()

    if len(oi) > 20:
        oi_available = True

        oi["price_change_15m"] = oi["mark_price"].pct_change(15) * 100
        oi["oi_change_15m"] = oi["open_interest"].pct_change(15) * 100

        o = oi.iloc[-1]

        price_change_15m = o["price_change_15m"]
        oi_change_15m = o["oi_change_15m"]

        # Hallazgo principal del laboratorio:
        # Precio sube + OI baja = posible suba por cierre de shorts, sesgo posterior bajista.
        if price_change_15m > 0 and oi_change_15m < 0:
            bear_score += 35
            notes.append(
                f"OI Sensor SHORT: precio +{price_change_15m:.2f}% en 15m con OI {oi_change_15m:.2f}%. Posible short covering."
            )

        # Precio baja + OI sube = apertura de shorts, puede continuar o liquidarse.
        if price_change_15m < 0 and oi_change_15m > 0:
            bear_score += 18
            notes.append(
                f"OI Sensor bajista: precio {price_change_15m:.2f}% con OI +{oi_change_15m:.2f}%."
            )

        # Precio sube + OI sube = nuevos longs entrando.
        if price_change_15m > 0 and oi_change_15m > 0:
            bull_score += 18
            notes.append(
                f"OI Sensor alcista: precio +{price_change_15m:.2f}% con OI +{oi_change_15m:.2f}%."
            )

        # Precio baja + OI baja = cierre/liquidación de longs, posible rebote.
        if price_change_15m < 0 and oi_change_15m < 0:
            bull_score += 18
            notes.append(
                f"OI Sensor posible rebote: precio {price_change_15m:.2f}% con OI {oi_change_15m:.2f}%."
            )

else:
    notes.append("OI no usado porque el precio live no coincide temporalmente con los archivos Tardis.")

# =========================
# FINAL DECISION
# =========================

score_diff = abs(bull_score - bear_score)

if bull_score >= bear_score + 25:
    decision = "LONG_WATCH"
    confidence = min(100, 50 + score_diff)

elif bear_score >= bull_score + 25:
    decision = "SHORT_WATCH"
    confidence = min(100, 50 + score_diff)

elif max(bull_score, bear_score) >= 45:
    decision = "MIXED / WAIT"
    confidence = 45

else:
    decision = "NO_TRADE"
    confidence = 30

# =========================
# ENTRY PLAN
# =========================

recent_high = price["high"].tail(6).max()
recent_low = price["low"].tail(6).min()
current_price = p["close"]

if decision == "SHORT_WATCH":
    trigger = f"Confirmar SHORT sólo si pierde {recent_low:.2f}"
    stop = f"Stop sobre {recent_high:.2f}"
    targets = "Targets: -0.5%, -1.0%, -1.5%"

elif decision == "LONG_WATCH":
    trigger = f"Confirmar LONG sólo si supera {recent_high:.2f}"
    stop = f"Stop bajo {recent_low:.2f}"
    targets = "Targets: +0.5%, +1.0%, +1.5%"

else:
    trigger = "Sin entrada."
    stop = "Sin stop."
    targets = "Sin targets."

# =========================
# EXPORT
# =========================

report = pd.DataFrame([{
    "symbol": SYMBOL,
    "current_price": current_price,
    "bull_score": bull_score,
    "bear_score": bear_score,
    "decision": decision,
    "confidence": confidence,
    "trigger": trigger,
    "stop": stop,
    "targets": targets,
    "notes": " | ".join(notes)
}])

report.to_csv("reports/master_decision_report.csv", index=False)

# =========================
# OUTPUT
# =========================

print("\n" + "=" * 70)
print("MASTER DECISION ENGINE v0.1")
print("=" * 70)

print(f"Símbolo: {SYMBOL}")
print(f"Precio actual: {current_price:,.2f}")

print("\nScores:")
print(f"Bull Score: {bull_score}")
print(f"Bear Score: {bear_score}")

print("\nDecisión:")
print(decision)

print(f"\nConfianza: {confidence}/100")

print("\nPlan:")
print(trigger)
print(stop)
print(targets)

print("\nNotas:")
for n in notes:
    print(f"- {n}")

print("\nArchivo generado:")
print("reports/master_decision_report.csv")