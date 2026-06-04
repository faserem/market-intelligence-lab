import pandas as pd

# =====================================
# DATOS
# =====================================

btc = pd.read_csv("data/btc_daily.csv")

for col in ["Open","High","Low","Close","Volume"]:
    btc[col] = pd.to_numeric(btc[col], errors="coerce")

btc = btc.dropna()

zones = pd.read_csv("reports/confluence_zones.csv")

current_price = btc["Close"].iloc[-1]

# =====================================
# SOPORTE MÁS CERCANO
# =====================================

supports = zones[zones["zone_high"] < current_price].copy()

supports["distance_pct"] = (
    (current_price - supports["zone_high"])
    / current_price
) * 100

nearest_support = supports.sort_values(
    "distance_pct"
).head(1)

# =====================================
# RESISTENCIA MÁS CERCANA
# =====================================

resistances = zones[zones["zone_low"] > current_price].copy()

resistances["distance_pct"] = (
    (resistances["zone_low"] - current_price)
    / current_price
) * 100

nearest_resistance = resistances.sort_values(
    "distance_pct"
).head(1)

# =====================================
# MOMENTUM
# =====================================

close_1 = btc["Close"].iloc[-1]
close_5 = btc["Close"].iloc[-5]
close_20 = btc["Close"].iloc[-20]

momentum_5 = ((close_1 - close_5) / close_5) * 100
momentum_20 = ((close_1 - close_20) / close_20) * 100

# =====================================
# SCORE
# =====================================

bull_score = 0
bear_score = 0

if momentum_5 > 0:
    bull_score += 15
else:
    bear_score += 15

if momentum_20 > 0:
    bull_score += 25
else:
    bear_score += 25

if not nearest_support.empty:
    support_dist = nearest_support.iloc[0]["distance_pct"]

    if support_dist < 3:
        bull_score += 20

if not nearest_resistance.empty:
    resistance_dist = nearest_resistance.iloc[0]["distance_pct"]

    if resistance_dist < 3:
        bear_score += 20

# =====================================
# RESULTADO
# =====================================

if bull_score > bear_score + 15:
    pressure_state = "BULLISH"

elif bear_score > bull_score + 15:
    pressure_state = "BEARISH"

else:
    pressure_state = "NEUTRAL"

# =====================================
# EXPORT
# =====================================

report = pd.DataFrame([{
    "current_price": current_price,
    "momentum_5": momentum_5,
    "momentum_20": momentum_20,
    "bull_score": bull_score,
    "bear_score": bear_score,
    "pressure_state": pressure_state
}])

report.to_csv(
    "reports/market_pressure_report.csv",
    index=False
)

# =====================================
# OUTPUT
# =====================================

print("\n")
print("=" * 70)
print("MARKET PRESSURE ENGINE v0.2")
print("=" * 70)

print(f"Precio actual: {current_price:,.2f}")
print(f"Momentum 5 días: {momentum_5:.2f}%")
print(f"Momentum 20 días: {momentum_20:.2f}%")

print("\nBull Score:", bull_score)
print("Bear Score:", bear_score)

print("\nPresión detectada:", pressure_state)

if not nearest_support.empty:
    print(
        "\nSoporte cercano:",
        round(nearest_support.iloc[0]["zone_low"],2),
        "-",
        round(nearest_support.iloc[0]["zone_high"],2)
    )

if not nearest_resistance.empty:
    print(
        "Resistencia cercana:",
        round(nearest_resistance.iloc[0]["zone_low"],2),
        "-",
        round(nearest_resistance.iloc[0]["zone_high"],2)
    )

print("\nArchivo generado:")
print("reports/market_pressure_report.csv")