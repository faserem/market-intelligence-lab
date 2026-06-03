import pandas as pd

# =====================================
# CARGA DE DATOS
# =====================================

btc = pd.read_csv("data/btc_daily.csv")
zones = pd.read_csv("reports/confluence_zones.csv")
transition = pd.read_csv("reports/transition_report.csv").iloc[0]
volatility = pd.read_csv("reports/volatility_report.csv").iloc[0]

for col in ["Open", "High", "Low", "Close", "Volume"]:
    btc[col] = pd.to_numeric(btc[col], errors="coerce")

btc = btc.dropna()

current_price = btc["Close"].iloc[-1]

close_1 = btc["Close"].iloc[-1]
close_5 = btc["Close"].iloc[-5]
close_20 = btc["Close"].iloc[-20]

momentum_5 = ((close_1 - close_5) / close_5) * 100
momentum_20 = ((close_1 - close_20) / close_20) * 100

# =====================================
# IDENTIFICAR ZONAS MÁS CERCANAS
# =====================================

supports = zones[zones["zone_high"] < current_price].copy()
resistances = zones[zones["zone_low"] > current_price].copy()

supports["distance_pct"] = (
    (current_price - supports["zone_high"]) / current_price
) * 100

resistances["distance_pct"] = (
    (resistances["zone_low"] - current_price) / current_price
) * 100

nearest_support = supports.sort_values("distance_pct").head(1)
nearest_resistance = resistances.sort_values("distance_pct").head(1)

# =====================================
# BREAKOUT SCORES
# =====================================

down_breakout_score = 0
up_breakout_score = 0
notes = []

# -------------------------------------
# SOPORTE CERCANO = RIESGO DE RUPTURA BAJISTA
# -------------------------------------

if not nearest_support.empty:

    s = nearest_support.iloc[0]

    if s["distance_pct"] <= 1:
        down_breakout_score += 30
        notes.append(
            f"Soporte muy cercano: {s['zone_low']} - {s['zone_high']} "
            f"({s['distance_pct']:.2f}% debajo)"
        )

    elif s["distance_pct"] <= 3:
        down_breakout_score += 20
        notes.append(
            f"Soporte cercano: {s['zone_low']} - {s['zone_high']} "
            f"({s['distance_pct']:.2f}% debajo)"
        )

    if s["avg_score"] >= 65:
        down_breakout_score += 15
        notes.append("Soporte con score alto.")

    if s["total_touches"] >= 10:
        down_breakout_score += 10
        notes.append("Soporte con muchas reacciones históricas.")

# -------------------------------------
# RESISTENCIA CERCANA = RIESGO DE RUPTURA ALCISTA
# -------------------------------------

if not nearest_resistance.empty:

    r = nearest_resistance.iloc[0]

    if r["distance_pct"] <= 1:
        up_breakout_score += 30
        notes.append(
            f"Resistencia muy cercana: {r['zone_low']} - {r['zone_high']} "
            f"({r['distance_pct']:.2f}% arriba)"
        )

    elif r["distance_pct"] <= 3:
        up_breakout_score += 20
        notes.append(
            f"Resistencia cercana: {r['zone_low']} - {r['zone_high']} "
            f"({r['distance_pct']:.2f}% arriba)"
        )

    if r["avg_score"] >= 65:
        up_breakout_score += 15
        notes.append("Resistencia con score alto.")

    if r["total_touches"] >= 10:
        up_breakout_score += 10
        notes.append("Resistencia con muchas reacciones históricas.")

# -------------------------------------
# MOMENTUM
# -------------------------------------

if momentum_5 < -5:
    down_breakout_score += 15
    notes.append(f"Momentum bajista 5 días fuerte: {momentum_5:.2f}%")

elif momentum_5 > 5:
    up_breakout_score += 15
    notes.append(f"Momentum alcista 5 días fuerte: {momentum_5:.2f}%")

if momentum_20 < -10:
    down_breakout_score += 20
    notes.append(f"Momentum bajista 20 días fuerte: {momentum_20:.2f}%")

elif momentum_20 > 10:
    up_breakout_score += 20
    notes.append(f"Momentum alcista 20 días fuerte: {momentum_20:.2f}%")

# -------------------------------------
# TRANSITION ENGINE
# -------------------------------------

transition_direction = transition["direction"]
transition_score = transition["transition_score"]

if transition_direction == "BEARISH_TRANSITION":
    down_breakout_score += transition_score * 0.25
    notes.append(
        f"Transition Engine detecta transición bajista: {transition_score}/100"
    )

elif transition_direction == "BULLISH_TRANSITION":
    up_breakout_score += transition_score * 0.25
    notes.append(
        f"Transition Engine detecta transición alcista: {transition_score}/100"
    )

# -------------------------------------
# VOLATILIDAD
# -------------------------------------

vol_state = volatility["volatility_state"]

if vol_state == "COMPRESSED":
    down_breakout_score += 10
    up_breakout_score += 10
    notes.append("Volatilidad comprimida: posible expansión.")

elif vol_state == "NORMAL":
    down_breakout_score += 5
    up_breakout_score += 5
    notes.append("Volatilidad normal: puede haber expansión.")

elif vol_state == "EXPANDING":
    notes.append("Volatilidad expandida: cuidado con perseguir ruptura.")

# =====================================
# RESULTADOS
# =====================================

down_breakout_score = min(100, round(down_breakout_score, 2))
up_breakout_score = min(100, round(up_breakout_score, 2))

if down_breakout_score > up_breakout_score + 15:
    breakout_direction = "DOWN_BREAKOUT_RISK"
    breakout_score = down_breakout_score

elif up_breakout_score > down_breakout_score + 15:
    breakout_direction = "UP_BREAKOUT_RISK"
    breakout_score = up_breakout_score

else:
    breakout_direction = "MIXED_BREAKOUT_RISK"
    breakout_score = max(down_breakout_score, up_breakout_score)

if breakout_score >= 80:
    breakout_label = "RIESGO DE RUPTURA ALTO"
elif breakout_score >= 60:
    breakout_label = "RIESGO DE RUPTURA MEDIO/ALTO"
elif breakout_score >= 40:
    breakout_label = "RIESGO DE RUPTURA MEDIO"
else:
    breakout_label = "RIESGO DE RUPTURA BAJO"

# =====================================
# LECTURA OPERATIVA
# =====================================

if breakout_direction == "DOWN_BREAKOUT_RISK":
    operative_read = (
        "Riesgo dominante de ruptura bajista. "
        "Vigilar pérdida clara del soporte cercano y confirmación con volumen/liquidez."
    )

elif breakout_direction == "UP_BREAKOUT_RISK":
    operative_read = (
        "Riesgo dominante de ruptura alcista. "
        "Vigilar recuperación/ruptura clara de la resistencia cercana y confirmación con volumen/liquidez."
    )

else:
    operative_read = (
        "Riesgo de ruptura mixto. Esperar definición clara del precio."
    )

# =====================================
# EXPORT
# =====================================

report = pd.DataFrame([{
    "current_price": current_price,
    "breakout_score": breakout_score,
    "breakout_label": breakout_label,
    "breakout_direction": breakout_direction,
    "down_breakout_score": down_breakout_score,
    "up_breakout_score": up_breakout_score,
    "momentum_5": momentum_5,
    "momentum_20": momentum_20,
    "transition_direction": transition_direction,
    "transition_score": transition_score,
    "volatility_state": vol_state,
    "operative_read": operative_read,
    "notes": " | ".join(notes)
}])

report.to_csv("reports/breakout_report.csv", index=False)

# =====================================
# OUTPUT
# =====================================

print("\n" + "=" * 70)
print("BREAKOUT ENGINE v0.1")
print("=" * 70)

print(f"Precio actual BTC: {current_price:,.2f}")
print(f"Breakout Score: {breakout_score}/100")
print(f"Etiqueta: {breakout_label}")
print(f"Dirección: {breakout_direction}")

print("\nScores internos:")
print(f"Down Breakout Score: {down_breakout_score}")
print(f"Up Breakout Score: {up_breakout_score}")

print("\nContexto:")
print(f"Momentum 5 días: {momentum_5:.2f}%")
print(f"Momentum 20 días: {momentum_20:.2f}%")
print(f"Transition: {transition_direction} ({transition_score}/100)")
print(f"Volatilidad: {vol_state}")

print("\nLectura operativa:")
print(operative_read)

print("\nNotas:")
for n in notes:
    print(f"- {n}")

print("\nArchivo generado:")
print("reports/breakout_report.csv")