import yfinance as yf
import pandas as pd

ticker = "BTC-USD"

print("Descargando datos...")

df = yf.download(
    ticker,
    start="2017-01-01",
    interval="1d",
    auto_adjust=True,
    progress=False
)

# Si viene con MultiIndex
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df = df.reset_index()

df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]

df.to_csv("data/btc_daily.csv", index=False)

print(f"Filas descargadas: {len(df)}")
print(df.head())