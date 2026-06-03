import requests
import pandas as pd

# =====================================
# CONFIG
# =====================================

SYMBOL = "BTCUSDT"
PERIOD = "1h"
LIMIT = 500

BASE_URL = "https://fapi.binance.com"

# =====================================
# DESCARGA OPEN INTEREST HISTÓRICO
# =====================================

url = f"{BASE_URL}/futures/data/openInterestHist"

params = {
    "symbol": SYMBOL,
    "period": PERIOD,
    "limit": LIMIT
}

response = requests.get(url, params=params, timeout=20)
response.raise_for_status()

data = response.json()

df = pd.DataFrame(data)

df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")

df["sumOpenInterest"] = pd.to_numeric(df["sumOpenInterest"], errors="coerce")
df["sumOpenInterestValue"] = pd.to_numeric(df["sumOpenInterestValue"], errors="coerce")

df = df.sort_values("datetime")

# =====================================
# CÁLCULOS
# =====================================

df["oi_change_1"] = df["sumOpenInterest"].pct_change() * 100
df["oi_change_6"] = df["sumOpenInterest"].pct_change(6) * 100
df["oi_change_24"] = df["sumOpenInterest"].pct_change(24) * 100

latest = df.iloc[-1]

oi_1 = latest["oi_change_1"]
oi_6 = latest["oi_change_6"]
oi_24 = latest["oi_change_24"]

# =====================================
# ESTADO
# =====================================

oi_score = 0
notes = []

if oi_1 > 1:
    oi_score += 20
    notes.append(f"Open Interest subió fuerte en 1h: {oi_1:.2f}%")
elif oi_1 < -1:
    oi_score -= 10
    notes.append(f"Open Interest cayó fuerte en 1h: {oi_1:.2f}%")

if oi_6 > 3:
    oi_score += 30
    notes.append(f"Open Interest subió fuerte en 6h: {oi_6:.2f}%")
elif oi_6 < -3:
    oi_score -= 15
    notes.append(f"Open Interest cayó fuerte en 6h: {oi_6:.2f}%")

if oi_24 > 6:
    oi_score += 30
    notes.append(f"Open Interest subió fuerte en 24h: {oi_24:.2f}%")
elif oi_24 < -6:
    oi_score -= 20
    notes.append(f"Open Interest cayó fuerte en 24h: {oi_24:.2f}%")

if oi_score >= 50:
    oi_state = "OI_EXPANDING_STRONG"
elif oi_score >= 25:
    oi_state = "OI_EXPANDING"
elif oi_score <= -20:
    oi_state = "OI_DECREASING"
else:
    oi_state = "OI_NEUTRAL"

if not notes:
    notes.append("Open Interest sin cambios extremos.")

# =====================================
# EXPORT
# =====================================

df.to_csv("data/btc_open_interest_1h.csv", index=False)

report = pd.DataFrame([{
    "symbol": SYMBOL,
    "period": PERIOD,
    "latest_datetime": latest["datetime"],
    "latest_open_interest": latest["sumOpenInterest"],
    "latest_open_interest_value": latest["sumOpenInterestValue"],
    "oi_change_1h": oi_1,
    "oi_change_6h": oi_6,
    "oi_change_24h": oi_24,
    "oi_score": oi_score,
    "oi_state": oi_state,
    "notes": " | ".join(notes)
}])

report.to_csv("reports/open_interest_report.csv", index=False)

# =====================================
# OUTPUT
# =====================================

print("\n" + "=" * 70)
print("OPEN INTEREST ENGINE v0.1")
print("=" * 70)

print(f"Símbolo: {SYMBOL}")
print(f"Período: {PERIOD}")
print(f"Último dato: {latest['datetime']}")
print(f"Open Interest: {latest['sumOpenInterest']:,.2f}")
print(f"Open Interest Value: {latest['sumOpenInterestValue']:,.2f}")

print("\nCambios:")
print(f"1h: {oi_1:.2f}%")
print(f"6h: {oi_6:.2f}%")
print(f"24h: {oi_24:.2f}%")

print("\nOI Score:")
print(f"{oi_score}/100")

print("Estado:")
print(oi_state)

print("\nNotas:")
for n in notes:
    print(f"- {n}")

print("\nArchivos generados:")
print("data/btc_open_interest_1h.csv")
print("reports/open_interest_report.csv")