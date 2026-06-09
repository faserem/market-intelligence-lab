import pandas as pd

FILE = "data/tardis/binance-futures_derivative_ticker_2026-01-01_BTCUSDT.csv"

df = pd.read_csv(FILE)

print("\nColumnas:")
print(df.columns.tolist())

print("\nPrimeras filas:")
print(df.head(10).to_string())

print("\nShape:")
print(df.shape)