import glob
import os
import pandas as pd

FILES = sorted(glob.glob("data/tardis/binance-futures_derivative_ticker_*_BTCUSDT.csv"))

OUT_FILE = "data/moe_dataset_1m.csv"

os.makedirs("data", exist_ok=True)

if not FILES:
    raise FileNotFoundError("No encontré derivative_ticker en data/tardis/")

dfs = []

print("\nBUILD DATASET 1M")
print("=" * 70)

for file in FILES:
    print(f"Leyendo: {file}", flush=True)
    df = pd.read_csv(file)
    dfs.append(df)

raw = pd.concat(dfs, ignore_index=True)

raw["timestamp"] = pd.to_datetime(raw["timestamp"], unit="us")
raw = raw.dropna(subset=["open_interest", "mark_price"])

df = (
    raw
    .set_index("timestamp")
    .sort_index()
    .resample("1min")
    .agg({
        "open_interest": "last",
        "mark_price": "last",
        "funding_rate": "last"
    })
    .dropna()
)

for w in [5, 15, 30, 60]:
    df[f"price_change_{w}m"] = df["mark_price"].pct_change(w) * 100
    df[f"oi_change_{w}m"] = df["open_interest"].pct_change(w) * 100

df = df.dropna().reset_index()

df.to_csv(OUT_FILE, index=False)

print("\nDataset generado:")
print(OUT_FILE)
print(f"Archivos leídos: {len(FILES)}")
print(f"Filas: {len(df)}")
print(f"Desde: {df['timestamp'].min()}")
print(f"Hasta: {df['timestamp'].max()}")