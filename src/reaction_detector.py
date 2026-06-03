import pandas as pd
import numpy as np

df = pd.read_csv("data/btc_daily.csv")
df["Date"] = pd.to_datetime(df["Date"])

for col in ["Open", "High", "Low", "Close", "Volume"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna().reset_index(drop=True)

# Parámetros
window = 3          # velas a izquierda/derecha para detectar swing
zone_pct = 0.005    # agrupar niveles cercanos dentro de 0.5%

levels = []

# Detectar swing highs/lows
for i in range(window, len(df) - window):
    high = df.loc[i, "High"]
    low = df.loc[i, "Low"]

    prev_highs = df.loc[i-window:i-1, "High"]
    next_highs = df.loc[i+1:i+window, "High"]

    prev_lows = df.loc[i-window:i-1, "Low"]
    next_lows = df.loc[i+1:i+window, "Low"]

    if high > prev_highs.max() and high > next_highs.max():
        levels.append({
            "date": df.loc[i, "Date"],
            "level": high,
            "type": "resistance"
        })

    if low < prev_lows.min() and low < next_lows.min():
        levels.append({
            "date": df.loc[i, "Date"],
            "level": low,
            "type": "support"
        })

levels_df = pd.DataFrame(levels)

# Agrupar niveles cercanos en zonas
zones = []

for _, row in levels_df.iterrows():
    level = row["level"]
    level_type = row["type"]

    matched = False

    for zone in zones:
        distance = abs(level - zone["center"]) / zone["center"]

        if distance <= zone_pct and level_type == zone["type"]:
            zone["levels"].append(level)
            zone["dates"].append(row["date"])
            zone["center"] = np.mean(zone["levels"])
            zone["touches"] += 1
            matched = True
            break

    if not matched:
        zones.append({
            "center": level,
            "type": level_type,
            "levels": [level],
            "dates": [row["date"]],
            "touches": 1
        })

zones_df = pd.DataFrame([
    {
        "type": z["type"],
        "center": round(z["center"], 2),
        "touches": z["touches"],
        "first_date": min(z["dates"]),
        "last_date": max(z["dates"]),
        "score": min(100, z["touches"] * 10)
    }
    for z in zones
])

zones_df = zones_df.sort_values(by=["score", "touches"], ascending=False)

zones_df.to_csv("reports/reaction_zones.csv", index=False)

print("Reaction Detector v0.1 ejecutado correctamente.")
print("Archivo generado: reports/reaction_zones.csv")
print("\nTop 20 zonas de reacción:")
print(zones_df.head(20))