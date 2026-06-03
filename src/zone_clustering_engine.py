import pandas as pd
import numpy as np

# =====================================
# CARGA DE DATOS
# =====================================

btc = pd.read_csv("data/btc_daily.csv")

for col in ["Open", "High", "Low", "Close", "Volume"]:
    btc[col] = pd.to_numeric(btc[col], errors="coerce")

btc = btc.dropna()

current_price = btc["Close"].iloc[-1]

zones = pd.read_csv("reports/confluence_scores.csv")

# =====================================
# FILTROS
# =====================================

zones["distance_pct"] = (
    abs(zones["center"] - current_price) / current_price
) * 100

# Nos quedamos con niveles útiles para el régimen actual
zones = zones[
    (zones["score_final"] >= 50) &
    (zones["distance_pct"] <= 25)
].copy()

zones = zones.sort_values("center")

# =====================================
# PARAMETROS
# =====================================

ZONE_DISTANCE_PCT = 0.03  # 3%

# =====================================
# CLUSTERING
# =====================================

clusters = []

for _, row in zones.iterrows():

    level = row["center"]
    added = False

    for cluster in clusters:

        center = cluster["center"]
        distance = abs(level - center) / center

        if distance <= ZONE_DISTANCE_PCT:

            cluster["levels"].append(level)
            cluster["scores"].append(row["score_final"])
            cluster["types"].append(row["type"])
            cluster["touches"].append(row["touches"])

            cluster["center"] = np.mean(cluster["levels"])
            added = True
            break

    if not added:

        clusters.append({
            "center": level,
            "levels": [level],
            "scores": [row["score_final"]],
            "types": [row["type"]],
            "touches": [row["touches"]]
        })

# =====================================
# ARMADO DE ZONAS
# =====================================

output = []

for cluster in clusters:

    min_level = min(cluster["levels"])
    max_level = max(cluster["levels"])

    avg_score = np.mean(cluster["scores"])
    total_touches = sum(cluster["touches"])

    supports = cluster["types"].count("support")
    resistances = cluster["types"].count("resistance")

    if supports > resistances:
        zone_type = "support"
    elif resistances > supports:
        zone_type = "resistance"
    else:
        zone_type = "mixed"

    if current_price < min_level:
        position_vs_price = "above_price"
    elif current_price > max_level:
        position_vs_price = "below_price"
    else:
        position_vs_price = "price_inside_zone"

    distance_to_zone = min(
        abs(current_price - min_level),
        abs(current_price - max_level)
    ) / current_price * 100

    output.append({
        "zone_type": zone_type,
        "zone_low": round(min_level, 2),
        "zone_high": round(max_level, 2),
        "position_vs_price": position_vs_price,
        "distance_to_zone_pct": round(distance_to_zone, 2),
        "levels_inside": len(cluster["levels"]),
        "total_touches": total_touches,
        "avg_score": round(avg_score, 2)
    })

zones_df = pd.DataFrame(output)

zones_df = zones_df.sort_values(
    by=["distance_to_zone_pct", "avg_score"],
    ascending=[True, False]
)

zones_df.to_csv(
    "reports/confluence_zones.csv",
    index=False
)

# =====================================
# OUTPUT
# =====================================

print("\n")
print(f"Precio actual BTC: {current_price:,.2f}")
print("=" * 70)
print("ZONAS DE CONFLUENCIA RELEVANTES")
print("=" * 70)

print(zones_df)

print("\nArchivo generado:")
print("reports/confluence_zones.csv")