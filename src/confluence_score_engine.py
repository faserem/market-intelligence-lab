import pandas as pd
import numpy as np

# ==========================
# PRECIO ACTUAL
# ==========================

btc = pd.read_csv("data/btc_daily.csv")

for col in ["Open","High","Low","Close","Volume"]:
    btc[col] = pd.to_numeric(btc[col], errors="coerce")

btc = btc.dropna()

current_price = btc["Close"].iloc[-1]

print(f"\nPrecio actual BTC: {current_price:,.2f}\n")

# ==========================
# REACTION ZONES
# ==========================

zones = pd.read_csv("reports/reaction_zones.csv")

# ==========================
# SCORE BASE
# ==========================

zones["score_final"] = zones["score"]

# ==========================
# DISTANCIA AL PRECIO ACTUAL
# ==========================

zones["distance_pct"] = (
    abs(zones["center"] - current_price)
    / current_price
) * 100

# ==========================
# BONUS POR CERCANIA
# ==========================

def proximity_score(distance):

    if distance <= 5:
        return 40

    elif distance <= 10:
        return 30

    elif distance <= 20:
        return 20

    elif distance <= 40:
        return 10

    return 0

zones["score_final"] += zones["distance_pct"].apply(
    proximity_score
)

# ==========================
# BONUS POR TOQUES
# ==========================

zones["score_final"] += zones["touches"] * 3

# ==========================
# TOP NIVELES
# ==========================

zones = zones.sort_values(
    by="score_final",
    ascending=False
)

supports = zones[
    zones["type"] == "support"
].head(10)

resistances = zones[
    zones["type"] == "resistance"
].head(10)

print("="*60)
print("TOP SOPORTES")
print("="*60)

print(
    supports[
        [
            "center",
            "touches",
            "distance_pct",
            "score_final"
        ]
    ]
)

print("\n")

print("="*60)
print("TOP RESISTENCIAS")
print("="*60)

print(
    resistances[
        [
            "center",
            "touches",
            "distance_pct",
            "score_final"
        ]
    ]
)

# ==========================
# EXPORT
# ==========================

zones.to_csv(
    "reports/confluence_scores.csv",
    index=False
)

print("\n")
print(
    "Archivo generado:"
)
print(
    "reports/confluence_scores.csv"
)