import pandas as pd

# =====================================
# CARGA DE REPORTES
# =====================================

market_state = pd.read_csv("reports/market_state_report.csv").iloc[0]
volatility = pd.read_csv("reports/volatility_report.csv").iloc[0]
zones = pd.read_csv("reports/confluence_zones.csv")
btc = pd.read_csv("data/btc_daily.csv")

for col in ["Open", "High", "Low", "Close", "Volume"]:
    btc[col] = pd.to_numeric(btc[col], errors="coerce")

btc = btc.dropna()

current_price = btc["Close"].iloc[-1]
previous_close = btc["Close"].iloc[-2]

# =====================================
# MOMENTUM
# =====================================

close_1 = btc["Close"].iloc[-1]
close_5 = btc["Close"].iloc[-5]
close_20 = btc["Close"].iloc[-20]

momentum_5 = ((close_1 - close_5) / close_5) * 100
momentum_20 = ((close_1 - close_20) / close_20) * 100

# =====================================
# ZONAS CERCANAS
# =====================================

current_zone = None

for _, zone in zones.iterrows():
    if zone["zone_low"] <= current_price <= zone["zone_high"]:
        current_zone = zone
        break

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
# SCORING
# =====================================

opportunity_score = 0
bear_score = 0
bull_score = 0
notes = []

# 1) Precio dentro de zona clave
if current_zone is not None:
    opportunity_score += 25
    notes.append(
        f"Precio dentro de zona clave: "
        f"{current_zone['zone_low']} - {current_zone['zone_high']}"
    )

# 2) Momentum
if momentum_5 < 0:
    bear_score += 15
else:
    bull_score += 15

if momentum_20 < 0:
    bear_score += 25
else:
    bull_score += 25

if abs(momentum_5) >= 5:
    opportunity_score += 15
    notes.append(f"Momentum 5 días fuerte: {momentum_5:.2f}%")

if abs(momentum_20) >= 10:
    opportunity_score += 20
    notes.append(f"Momentum 20 días fuerte: {momentum_20:.2f}%")

# 3) Volatilidad
vol_state = volatility["volatility_state"]
vol_score = volatility["volatility_score"]

if vol_state == "COMPRESSED":
    opportunity_score += 25
    notes.append("Volatilidad comprimida: posible expansión futura.")

elif vol_state == "NORMAL":
    opportunity_score += 15
    notes.append("Volatilidad normal: todavía puede haber expansión.")

elif vol_state == "EXPANDING":
    opportunity_score += 5
    notes.append("Volatilidad expandida: cuidado con perseguir el movimiento.")

# 4) Cercanía a soporte/resistencia
if not nearest_support.empty:
    s = nearest_support.iloc[0]
    if s["distance_pct"] <= 3:
        bull_score += 15
        opportunity_score += 10
        notes.append(
            f"Soporte cercano: {s['zone_low']} - {s['zone_high']} "
            f"({s['distance_pct']:.2f}% debajo)"
        )

if not nearest_resistance.empty:
    r = nearest_resistance.iloc[0]
    if r["distance_pct"] <= 3:
        bear_score += 15
        opportunity_score += 10
        notes.append(
            f"Resistencia cercana: {r['zone_low']} - {r['zone_high']} "
            f"({r['distance_pct']:.2f}% arriba)"
        )

# =====================================
# SESGO
# =====================================

if bear_score > bull_score + 10:
    bias = "BEARISH"
elif bull_score > bear_score + 10:
    bias = "BULLISH"
else:
    bias = "NEUTRAL"

# =====================================
# CLASIFICACIÓN
# =====================================

opportunity_score = min(100, opportunity_score)

if opportunity_score >= 80:
    label = "OPORTUNIDAD ALTA"
elif opportunity_score >= 60:
    label = "OPORTUNIDAD MEDIA/ALTA"
elif opportunity_score >= 40:
    label = "OPORTUNIDAD MEDIA"
else:
    label = "BAJA OPORTUNIDAD"

# =====================================
# LECTURA OPERATIVA
# =====================================

if bias == "BEARISH" and current_zone is not None:
    operative_read = (
        "Sesgo bajista con precio en zona clave. "
        "No perseguir sin confirmación. Vigilar pérdida clara de la zona actual."
    )
elif bias == "BULLISH" and current_zone is not None:
    operative_read = (
        "Sesgo alcista con precio en zona clave. "
        "Vigilar recuperación y ruptura de resistencia cercana."
    )
else:
    operative_read = (
        "Contexto mixto. Esperar ruptura o rechazo claro antes de asumir riesgo."
    )

# =====================================
# EXPORT
# =====================================

report = pd.DataFrame([{
    "current_price": current_price,
    "opportunity_score": opportunity_score,
    "label": label,
    "bias": bias,
    "bull_score": bull_score,
    "bear_score": bear_score,
    "volatility_state": vol_state,
    "momentum_5": momentum_5,
    "momentum_20": momentum_20,
    "operative_read": operative_read,
    "notes": " | ".join(notes)
}])

report.to_csv("reports/opportunity_report.csv", index=False)

# =====================================
# OUTPUT
# =====================================

print("\n" + "=" * 70)
print("OPPORTUNITY ENGINE v0.1")
print("=" * 70)

print(f"Precio actual BTC: {current_price:,.2f}")
print(f"Opportunity Score: {opportunity_score}/100")
print(f"Etiqueta: {label}")
print(f"Sesgo: {bias}")

print("\nScores internos:")
print(f"Bull Score: {bull_score}")
print(f"Bear Score: {bear_score}")

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
print("reports/opportunity_report.csv")