import pandas as pd

df = pd.read_csv("data/btc_daily.csv")

df["Date"] = pd.to_datetime(df["Date"])
df = df.set_index("Date")

# Aseguramos columnas numéricas
for col in ["Open", "High", "Low", "Close", "Volume"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Niveles anuales
yearly = df.resample("YE").agg({
    "Open": "first",
    "High": "max",
    "Low": "min",
    "Close": "last"
})

# Niveles mensuales
monthly = df.resample("ME").agg({
    "Open": "first",
    "High": "max",
    "Low": "min",
    "Close": "last"
})

# Niveles semanales
weekly = df.resample("W").agg({
    "Open": "first",
    "High": "max",
    "Low": "min",
    "Close": "last"
})

# Pivots diarios clásicos
df["PP"] = (df["High"].shift(1) + df["Low"].shift(1) + df["Close"].shift(1)) / 3
df["R1"] = (2 * df["PP"]) - df["Low"].shift(1)
df["S1"] = (2 * df["PP"]) - df["High"].shift(1)
df["R2"] = df["PP"] + (df["High"].shift(1) - df["Low"].shift(1))
df["S2"] = df["PP"] - (df["High"].shift(1) - df["Low"].shift(1))
df["R3"] = df["High"].shift(1) + 2 * (df["PP"] - df["Low"].shift(1))
df["S3"] = df["Low"].shift(1) - 2 * (df["High"].shift(1) - df["PP"])

# Guardamos reportes
yearly.to_csv("reports/yearly_levels.csv")
monthly.to_csv("reports/monthly_levels.csv")
weekly.to_csv("reports/weekly_levels.csv")
df.to_csv("reports/btc_daily_with_pivots.csv")

print("Confluence Mapper v0.1 ejecutado correctamente.")
print("Reportes generados:")
print("- reports/yearly_levels.csv")
print("- reports/monthly_levels.csv")
print("- reports/weekly_levels.csv")
print("- reports/btc_daily_with_pivots.csv")

print("\nÚltimos pivots diarios:")
print(df[["Close", "PP", "R1", "R2", "R3", "S1", "S2", "S3"]].tail(5))