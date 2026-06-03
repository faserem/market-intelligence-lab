import pandas as pd
import numpy as np

# =====================================
# CARGA DE DATOS
# =====================================

btc = pd.read_csv("data/btc_daily.csv")

for col in ["Open", "High", "Low", "Close", "Volume"]:
    btc[col] = pd.to_numeric(btc[col], errors="coerce")

btc = btc.dropna()

# =====================================
# ATR
# =====================================

btc["prev_close"] = btc["Close"].shift(1)

btc["tr1"] = btc["High"] - btc["Low"]
btc["tr2"] = abs(btc["High"] - btc["prev_close"])
btc["tr3"] = abs(btc["Low"] - btc["prev_close"])

btc["TR"] = btc[["tr1", "tr2", "tr3"]].max(axis=1)

btc["ATR14"] = btc["TR"].rolling(14).mean()
btc["ATR50"] = btc["TR"].rolling(50).mean()

# =====================================
# DATOS ACTUALES
# =====================================

current_price = btc["Close"].iloc[-1]
atr14 = btc["ATR14"].iloc[-1]
atr50 = btc["ATR50"].iloc[-1]

vol_ratio = atr14 / atr50

# =====================================
# ESTADO DE VOLATILIDAD
# =====================================

if vol_ratio < 0.80:
    volatility_state = "COMPRESSED"

elif vol_ratio > 1.20:
    volatility_state = "EXPANDING"

else:
    volatility_state = "NORMAL"

# =====================================
# SCORE
# =====================================

if volatility_state == "COMPRESSED":
    volatility_score = 85

elif volatility_state == "NORMAL":
    volatility_score = 50

else:
    volatility_score = 25

# =====================================
# OUTPUT
# =====================================

print("\n")
print("=" * 70)
print("VOLATILITY ENGINE v0.1")
print("=" * 70)

print(f"Precio BTC: {current_price:,.2f}")
print(f"ATR14: {atr14:,.2f}")
print(f"ATR50: {atr50:,.2f}")
print(f"ATR14 / ATR50: {vol_ratio:.2f}")

print("\nEstado de volatilidad:")
print(volatility_state)

print("\nVolatility Score:")
print(f"{volatility_score}/100")

# =====================================
# EXPORT
# =====================================

report = pd.DataFrame([{
    "current_price": current_price,
    "atr14": atr14,
    "atr50": atr50,
    "vol_ratio": vol_ratio,
    "volatility_state": volatility_state,
    "volatility_score": volatility_score
}])

report.to_csv(
    "reports/volatility_report.csv",
    index=False
)

print("\nArchivo generado:")
print("reports/volatility_report.csv")