import pandas as pd

DATA_PATH = "data/btc_daily.csv"

df = pd.read_csv(DATA_PATH)
df["Date"] = pd.to_datetime(df["Date"])

for col in ["Open", "High", "Low", "Close", "Volume"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna().sort_values("Date").reset_index(drop=True)

df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
df["EMA100"] = df["Close"].ewm(span=100, adjust=False).mean()
df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

df["EMA200_slope_20d"] = df["EMA200"].pct_change(20) * 100
df["price_vs_ema200_pct"] = ((df["Close"] - df["EMA200"]) / df["EMA200"]) * 100

latest = df.iloc[-1]

close = latest["Close"]
ema50 = latest["EMA50"]
ema100 = latest["EMA100"]
ema200 = latest["EMA200"]
slope = latest["EMA200_slope_20d"]
price_vs_ema200 = latest["price_vs_ema200_pct"]

if close > ema50 > ema100 > ema200 and slope > 1:
    regime = "STRONG_BULL"
elif close > ema200 and slope >= 0:
    regime = "BULL"
elif close < ema50 < ema100 < ema200 and slope < -1:
    regime = "STRONG_BEAR"
elif close < ema200 and slope <= 0:
    regime = "BEAR"
else:
    regime = "RANGE"

report = pd.DataFrame([{
    "date": latest["Date"],
    "close": close,
    "ema50": ema50,
    "ema100": ema100,
    "ema200": ema200,
    "ema200_slope_20d": slope,
    "price_vs_ema200_pct": price_vs_ema200,
    "regime": regime
}])

report.to_csv("reports/regime_report.csv", index=False)

print("\n" + "=" * 70)
print("REGIME ENGINE v0.1")
print("=" * 70)

print(f"Fecha: {latest['Date']}")
print(f"Close: {close:,.2f}")
print(f"EMA50: {ema50:,.2f}")
print(f"EMA100: {ema100:,.2f}")
print(f"EMA200: {ema200:,.2f}")
print(f"EMA200 slope 20d: {slope:.2f}%")
print(f"Precio vs EMA200: {price_vs_ema200:.2f}%")
print(f"Régimen: {regime}")

print("\nArchivo generado:")
print("reports/regime_report.csv")