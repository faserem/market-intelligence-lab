import pandas as pd

# =====================================
# DATOS
# =====================================

btc = pd.read_csv("data/btc_daily.csv")
zones = pd.read_csv("reports/confluence_zones.csv")

for col in ["Open", "High", "Low", "Close", "Volume"]:
    btc[col] = pd.to_numeric(btc[col], errors="coerce")

btc = btc.dropna()

current_price = btc["Close"].iloc[-1]

# =====================================
# BUSCAR ZONA ACTUAL
# =====================================

current_zone = None

for _, zone in zones.iterrows():

    if zone["zone_low"] <= current_price <= zone["zone_high"]:
        current_zone = zone
        break

# =====================================
# CALCULO
# =====================================

if current_zone is not None:

    zone_low = current_zone["zone_low"]
    zone_high = current_zone["zone_high"]

    zone_size = zone_high - zone_low

    position_pct = (
        (current_price - zone_low)
        / zone_size
    ) * 100

    if position_pct >= 80:
        zone_state = "UPPER_ZONE"

    elif position_pct <= 20:
        zone_state = "LOWER_ZONE"

    else:
        zone_state = "MIDDLE_ZONE"

else:

    zone_low = None
    zone_high = None
    position_pct = None
    zone_state = "OUTSIDE_ZONE"

# =====================================
# EXPORT
# =====================================

report = pd.DataFrame([{
    "current_price": current_price,
    "zone_low": zone_low,
    "zone_high": zone_high,
    "position_pct": position_pct,
    "zone_state": zone_state
}])

report.to_csv(
    "reports/zone_position_report.csv",
    index=False
)

# =====================================
# OUTPUT
# =====================================

print("\n")
print("=" * 70)
print("ZONE POSITION ENGINE v0.1")
print("=" * 70)

print(f"Precio actual: {current_price:,.2f}")

if current_zone is not None:

    print(
        f"Zona: {zone_low:.2f} - {zone_high:.2f}"
    )

    print(
        f"Posición dentro de la zona: "
        f"{position_pct:.2f}%"
    )

    print(
        f"Estado: {zone_state}"
    )

else:

    print("Precio fuera de zonas relevantes.")

print("\nArchivo generado:")
print("reports/zone_position_report.csv")