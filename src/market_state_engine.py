import pandas as pd

# =====================================
# CARGA DE DATOS
# =====================================

btc = pd.read_csv("data/btc_daily.csv")
zones = pd.read_csv("reports/confluence_zones.csv")

for col in ["Open", "High", "Low", "Close", "Volume"]:
    btc[col] = pd.to_numeric(btc[col], errors="coerce")

btc = btc.dropna()

current_price = btc["Close"].iloc[-1]
previous_close = btc["Close"].iloc[-2]

daily_change_pct = ((current_price - previous_close) / previous_close) * 100

# =====================================
# IDENTIFICAR ZONA ACTUAL
# =====================================

current_zone = None

for _, zone in zones.iterrows():
    if zone["zone_low"] <= current_price <= zone["zone_high"]:
        current_zone = zone
        break

# =====================================
# SOPORTES Y RESISTENCIAS CERCANAS
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
# MARKET STATE
# =====================================

state = "neutral"
attention_score = 0
notes = []

if current_zone is not None:
    state = "inside_key_zone"
    attention_score += 45
    notes.append(
        f"El precio está dentro de una zona clave: "
        f"{current_zone['zone_low']} - {current_zone['zone_high']}"
    )

else:
    notes.append("El precio no está dentro de una zona clave.")

if not nearest_support.empty:
    s = nearest_support.iloc[0]
    notes.append(
        f"Soporte cercano: {s['zone_low']} - {s['zone_high']} "
        f"({s['distance_pct']:.2f}% debajo)"
    )

if not nearest_resistance.empty:
    r = nearest_resistance.iloc[0]
    notes.append(
        f"Resistencia cercana: {r['zone_low']} - {r['zone_high']} "
        f"({r['distance_pct']:.2f}% arriba)"
    )

if abs(daily_change_pct) >= 3:
    attention_score += 25
    notes.append(
        f"Movimiento diario fuerte: {daily_change_pct:.2f}%"
    )
elif abs(daily_change_pct) >= 1.5:
    attention_score += 15
    notes.append(
        f"Movimiento diario moderado: {daily_change_pct:.2f}%"
    )
else:
    notes.append(
        f"Movimiento diario bajo/moderado: {daily_change_pct:.2f}%"
    )

# =====================================
# INTERPRETACIÓN
# =====================================

if attention_score >= 70:
    opportunity_label = "ALTA ATENCIÓN"
elif attention_score >= 45:
    opportunity_label = "ATENCIÓN MEDIA"
else:
    opportunity_label = "BAJA ATENCIÓN"

# =====================================
# REPORT
# =====================================

report = {
    "current_price": current_price,
    "previous_close": previous_close,
    "daily_change_pct": daily_change_pct,
    "state": state,
    "attention_score": attention_score,
    "opportunity_label": opportunity_label,
    "notes": " | ".join(notes)
}

report_df = pd.DataFrame([report])
report_df.to_csv("reports/market_state_report.csv", index=False)

# =====================================
# OUTPUT
# =====================================

print("\n" + "=" * 70)
print("MARKET STATE ENGINE v0.1")
print("=" * 70)

print(f"Precio actual BTC: {current_price:,.2f}")
print(f"Cambio diario: {daily_change_pct:.2f}%")
print(f"Estado: {state}")
print(f"Opportunity / Attention Score: {attention_score}/100")
print(f"Etiqueta: {opportunity_label}")

print("\nLectura:")
for n in notes:
    print(f"- {n}")

print("\nArchivo generado:")
print("reports/market_state_report.csv")