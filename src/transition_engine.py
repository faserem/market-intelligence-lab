import pandas as pd

# =====================================
# CARGA DE DATOS
# =====================================

btc = pd.read_csv("data/btc_daily.csv")
zones = pd.read_csv("reports/confluence_zones.csv")
volatility = pd.read_csv("reports/volatility_report.csv").iloc[0]
opportunity = pd.read_csv("reports/opportunity_report.csv").iloc[0]

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
# DISTANCIA A ZONAS
# =====================================

zone_rows = []

for _, zone in zones.iterrows():

    zone_low = zone["zone_low"]
    zone_high = zone["zone_high"]

    if zone_low <= current_price <= zone_high:
        relation = "INSIDE_ZONE"
        distance_pct = 0

    elif current_price < zone_low:
        relation = "BELOW_ZONE"
        distance_pct = ((zone_low - current_price) / current_price) * 100

    else:
        relation = "ABOVE_ZONE"
        distance_pct = ((current_price - zone_high) / current_price) * 100

    zone_rows.append({
        "zone_type": zone["zone_type"],
        "zone_low": zone_low,
        "zone_high": zone_high,
        "relation": relation,
        "distance_pct": distance_pct,
        "avg_score": zone["avg_score"],
        "levels_inside": zone["levels_inside"],
        "total_touches": zone["total_touches"]
    })

zone_distance_df = pd.DataFrame(zone_rows)

nearest_zone = zone_distance_df.sort_values(
    by=["distance_pct", "avg_score"],
    ascending=[True, False]
).iloc[0]

# =====================================
# TRANSITION SCORE
# =====================================

transition_score = 0
bear_transition = 0
bull_transition = 0
notes = []

# 1) Cercanía a zona clave
if nearest_zone["distance_pct"] == 0:
    transition_score += 30
    notes.append(
        f"Precio dentro de zona clave: {nearest_zone['zone_low']} - {nearest_zone['zone_high']}"
    )

elif nearest_zone["distance_pct"] <= 1:
    transition_score += 25
    notes.append(
        f"Precio muy cerca de zona clave: {nearest_zone['zone_low']} - {nearest_zone['zone_high']} "
        f"({nearest_zone['distance_pct']:.2f}%)"
    )

elif nearest_zone["distance_pct"] <= 3:
    transition_score += 15
    notes.append(
        f"Precio cerca de zona clave: {nearest_zone['zone_low']} - {nearest_zone['zone_high']} "
        f"({nearest_zone['distance_pct']:.2f}%)"
    )

# 2) Momentum direccional
if momentum_5 < -5:
    transition_score += 15
    bear_transition += 20
    notes.append(f"Momentum bajista 5 días fuerte: {momentum_5:.2f}%")

elif momentum_5 > 5:
    transition_score += 15
    bull_transition += 20
    notes.append(f"Momentum alcista 5 días fuerte: {momentum_5:.2f}%")

if momentum_20 < -10:
    transition_score += 20
    bear_transition += 30
    notes.append(f"Momentum bajista 20 días fuerte: {momentum_20:.2f}%")

elif momentum_20 > 10:
    transition_score += 20
    bull_transition += 30
    notes.append(f"Momentum alcista 20 días fuerte: {momentum_20:.2f}%")

# 3) Volatilidad
vol_state = volatility["volatility_state"]

if vol_state == "COMPRESSED":
    transition_score += 25
    notes.append("Volatilidad comprimida: alta posibilidad de expansión futura.")

elif vol_state == "NORMAL":
    transition_score += 15
    notes.append("Volatilidad normal: todavía hay espacio para expansión.")

elif vol_state == "EXPANDING":
    transition_score += 5
    notes.append("Volatilidad expandida: riesgo de estar persiguiendo el movimiento.")

# 4) Lectura de zona según dirección
if nearest_zone["relation"] == "ABOVE_ZONE":
    if momentum_5 < 0 and momentum_20 < 0:
        bear_transition += 15
        notes.append("Precio apenas arriba de zona relevante con momentum bajista: posible test/pérdida de soporte.")

if nearest_zone["relation"] == "BELOW_ZONE":
    if momentum_5 > 0 and momentum_20 > 0:
        bull_transition += 15
        notes.append("Precio apenas debajo de zona relevante con momentum alcista: posible test/ruptura de resistencia.")

if nearest_zone["relation"] == "INSIDE_ZONE":
    if momentum_5 < 0 and momentum_20 < 0:
        bear_transition += 10
        notes.append("Precio dentro de zona clave con presión bajista.")
    elif momentum_5 > 0 and momentum_20 > 0:
        bull_transition += 10
        notes.append("Precio dentro de zona clave con presión alcista.")

# =====================================
# CLASIFICACIÓN
# =====================================

transition_score = min(100, transition_score)

if bear_transition > bull_transition + 10:
    direction = "BEARISH_TRANSITION"
elif bull_transition > bear_transition + 10:
    direction = "BULLISH_TRANSITION"
else:
    direction = "NEUTRAL_TRANSITION"

if transition_score >= 80:
    transition_label = "TRANSICIÓN FUERTE"
elif transition_score >= 60:
    transition_label = "TRANSICIÓN MEDIA/ALTA"
elif transition_score >= 40:
    transition_label = "TRANSICIÓN MEDIA"
else:
    transition_label = "SIN TRANSICIÓN CLARA"

# =====================================
# LECTURA OPERATIVA
# =====================================

if direction == "BEARISH_TRANSITION":
    operative_read = (
        "El mercado muestra transición bajista potencial. "
        "No implica entrada automática. Vigilar pérdida clara de la zona cercana "
        "y confirmación con volumen/liquidez."
    )

elif direction == "BULLISH_TRANSITION":
    operative_read = (
        "El mercado muestra transición alcista potencial. "
        "No implica entrada automática. Vigilar recuperación/ruptura de resistencia "
        "y confirmación con volumen/liquidez."
    )

else:
    operative_read = (
        "No hay transición direccional clara. Esperar mejor ubicación o confirmación."
    )

# =====================================
# EXPORT
# =====================================

report = pd.DataFrame([{
    "current_price": current_price,
    "transition_score": transition_score,
    "transition_label": transition_label,
    "direction": direction,
    "bear_transition": bear_transition,
    "bull_transition": bull_transition,
    "nearest_zone_low": nearest_zone["zone_low"],
    "nearest_zone_high": nearest_zone["zone_high"],
    "nearest_zone_relation": nearest_zone["relation"],
    "nearest_zone_distance_pct": nearest_zone["distance_pct"],
    "volatility_state": vol_state,
    "momentum_5": momentum_5,
    "momentum_20": momentum_20,
    "operative_read": operative_read,
    "notes": " | ".join(notes)
}])

report.to_csv("reports/transition_report.csv", index=False)

# =====================================
# OUTPUT
# =====================================

print("\n" + "=" * 70)
print("TRANSITION ENGINE v0.1")
print("=" * 70)

print(f"Precio actual BTC: {current_price:,.2f}")
print(f"Transition Score: {transition_score}/100")
print(f"Etiqueta: {transition_label}")
print(f"Dirección: {direction}")

print("\nScores internos:")
print(f"Bull Transition: {bull_transition}")
print(f"Bear Transition: {bear_transition}")

print("\nZona más cercana:")
print(f"{nearest_zone['zone_low']} - {nearest_zone['zone_high']}")
print(f"Relación: {nearest_zone['relation']}")
print(f"Distancia: {nearest_zone['distance_pct']:.2f}%")

print("\nContexto:")
print(f"Momentum 5 días: {momentum_5:.2f}%")
print(f"Momentum 20 días: {momentum_20:.2f}%")
print(f"Volatilidad: {vol_state}")

print("\nLectura operativa:")
print(operative_read)

print("\nNotas:")
for n in notes:
    print(f"- {n}")

print("\nArchivo generado:")
print("reports/transition_report.csv")