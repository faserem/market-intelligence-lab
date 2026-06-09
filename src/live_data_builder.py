import yfinance as yf
import pandas as pd

SYMBOL = "BTC-USD"

df = yf.download(
    SYMBOL,
    interval="5m",
    period="60d",
    auto_adjust=True,
    progress=False
)

print("Tipo columnas:", type(df.columns))
print("Columnas:", df.columns)

# Si Yahoo devuelve MultiIndex
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df = df.reset_index()

df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]

if "datetime" in df.columns:
    df.rename(columns={"datetime": "open_time"}, inplace=True)

if "date" in df.columns:
    df.rename(columns={"date": "open_time"}, inplace=True)

df["number_of_trades"] = 1
df["taker_buy_ratio"] = 0.50

print("\nFilas descargadas:", len(df))
print(df.head())

df.to_csv(
    "data/live_btc_5m.csv",
    index=False
)

print("\nArchivo generado:")
print("data/live_btc_5m.csv")