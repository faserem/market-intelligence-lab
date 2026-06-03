import requests
import pandas as pd

SYMBOL = "BTCUSDT"
LIMIT = 100
BASE_URL = "https://fapi.binance.com"

url = f"{BASE_URL}/fapi/v1/fundingRate"
params = {"symbol": SYMBOL, "limit": LIMIT}

try:
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data)

    df["fundingTime"] = pd.to_numeric(df["fundingTime"], errors="coerce")
    df["datetime"] = pd.to_datetime(df["fundingTime"], unit="ms")
    df["fundingRate"] = pd.to_numeric(df["fundingRate"], errors="coerce")

    df = df.sort_values("datetime")

    latest = df.iloc[-1]
    latest_funding = latest["fundingRate"]

    avg_3 = df["fundingRate"].tail(3).mean()
    avg_10 = df["fundingRate"].tail(10).mean()
    avg_30 = df["fundingRate"].tail(30).mean()

    funding_score = 0
    notes = []

    if latest_funding > 0:
        funding_score += 10
        notes.append("Funding actual positivo: predominio/costo para longs.")
    elif latest_funding < 0:
        funding_score -= 10
        notes.append("Funding actual negativo: predominio/costo para shorts.")

    if avg_10 > 0:
        funding_score += 15
        notes.append("Promedio funding 10 períodos positivo.")
    elif avg_10 < 0:
        funding_score -= 15
        notes.append("Promedio funding 10 períodos negativo.")

    if avg_30 > 0:
        funding_score += 15
        notes.append("Promedio funding 30 períodos positivo.")
    elif avg_30 < 0:
        funding_score -= 15
        notes.append("Promedio funding 30 períodos negativo.")

    if latest_funding > 0.0005:
        funding_score += 20
        notes.append("Funding positivo elevado: posible exceso de longs.")
    elif latest_funding < -0.0005:
        funding_score -= 20
        notes.append("Funding negativo elevado: posible exceso de shorts.")

    if funding_score >= 30:
        funding_state = "LONGS_DOMINANT"
    elif funding_score <= -30:
        funding_state = "SHORTS_DOMINANT"
    else:
        funding_state = "NEUTRAL"

    df.to_csv("data/btc_funding_rate.csv", index=False)

except Exception as e:
    latest_funding = None
    avg_3 = None
    avg_10 = None
    avg_30 = None
    funding_score = 0
    funding_state = "UNAVAILABLE"
    notes = [f"Funding no disponible desde este entorno. Motivo: {e}"]

report = pd.DataFrame([{
    "symbol": SYMBOL,
    "latest_funding": latest_funding,
    "avg_funding_3": avg_3,
    "avg_funding_10": avg_10,
    "avg_funding_30": avg_30,
    "funding_score": funding_score,
    "funding_state": funding_state,
    "notes": " | ".join(notes)
}])

report.to_csv("reports/funding_report.csv", index=False)

print("\n" + "=" * 70)
print("FUNDING ENGINE v0.1")
print("=" * 70)

print(f"Símbolo: {SYMBOL}")
print(f"Estado: {funding_state}")
print(f"Funding Score: {funding_score}/100")

print("\nNotas:")
for n in notes:
    print(f"- {n}")

print("\nArchivo generado:")
print("reports/funding_report.csv")