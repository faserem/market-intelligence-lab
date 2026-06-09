import os
import requests
import gzip
import shutil

EXCHANGE = "binance-futures"
SYMBOL = "BTCUSDT"

DATA_TYPES = [
    "derivative_ticker",
]

DATES = [
    "2026/01/01",
    "2026/02/01",
    "2026/03/01",
    "2026/04/01",
    "2026/05/01",
]
BASE_URL = "https://datasets.tardis.dev/v1"

RAW_DIR = "data/tardis/raw"
OUT_DIR = "data/tardis"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

print("\n" + "=" * 70)
print("TARDIS SAMPLE DOWNLOADER v0.2")
print("=" * 70)

for date in DATES:
    for data_type in DATA_TYPES:

        safe_date = date.replace("/", "-")

        filename_gz = f"{EXCHANGE}_{data_type}_{safe_date}_{SYMBOL}.csv.gz"
        filename_csv = f"{EXCHANGE}_{data_type}_{safe_date}_{SYMBOL}.csv"

        url = f"{BASE_URL}/{EXCHANGE}/{data_type}/{date}/{SYMBOL}.csv.gz"

        gz_path = os.path.join(RAW_DIR, filename_gz)
        csv_path = os.path.join(OUT_DIR, filename_csv)

        print(f"\nIntentando: {url}")

        if os.path.exists(csv_path):
            print(f"Ya existe CSV: {csv_path}")
            continue

        try:
            r = requests.get(url, timeout=120)

            if r.status_code != 200:
                print(f"No disponible: {r.status_code}")
                continue

            with open(gz_path, "wb") as f:
                f.write(r.content)

            with gzip.open(gz_path, "rb") as f_in:
                with open(csv_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            print(f"OK: {csv_path}")

        except Exception as e:
            print(f"Error: {e}")

print("\nListo. Revisá carpeta data/tardis/")