import os
import zipfile
import requests
import pandas as pd

# =====================================
# CONFIG
# =====================================

SYMBOL = "BTCUSDT"
INTERVAL = "5m"

START_YEAR = 2026
START_MONTH = 1

END_YEAR = 2026
END_MONTH = 6

BASE_URL = "https://data.binance.vision/data/futures/um/monthly/klines"

RAW_DIR = "data/intraday/raw"
OUTPUT_DIR = "data/intraday"
OUTPUT_FILE = f"{OUTPUT_DIR}/{SYMBOL}_{INTERVAL}.csv"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =====================================
# HELPERS
# =====================================

def month_range(start_year, start_month, end_year, end_month):
    months = []
    year = start_year
    month = start_month

    while (year < end_year) or (year == end_year and month <= end_month):
        months.append((year, month))

        month += 1
        if month == 13:
            month = 1
            year += 1

    return months

def download_file(url, filepath):
    if os.path.exists(filepath):
        print(f"Ya existe: {filepath}")
        return True

    print(f"Descargando: {url}")

    try:
        r = requests.get(url, timeout=30)

        if r.status_code != 200:
            print(f"No disponible ({r.status_code}): {url}")
            return False

        with open(filepath, "wb") as f:
            f.write(r.content)

        return True

    except Exception as e:
        print(f"Error descargando {url}: {e}")
        return False

# =====================================
# DESCARGA
# =====================================

all_dfs = []

for year, month in month_range(START_YEAR, START_MONTH, END_YEAR, END_MONTH):

    ym = f"{year}-{month:02d}"
    filename = f"{SYMBOL}-{INTERVAL}-{ym}.zip"

    url = f"{BASE_URL}/{SYMBOL}/{INTERVAL}/{filename}"
    zip_path = f"{RAW_DIR}/{filename}"

    ok = download_file(url, zip_path)

    if not ok:
        continue

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            csv_name = z.namelist()[0]
            print(f"Leyendo: {csv_name}")

            with z.open(csv_name) as f:
                df = pd.read_csv(f)

            expected_cols = [
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_asset_volume",
                "number_of_trades",
                "taker_buy_base_volume",
                "taker_buy_quote_volume",
                "ignore"
            ]

            # Si vino sin header y pandas tomó la primera fila como header raro
            if list(df.columns) != expected_cols:
                with z.open(csv_name) as f:
                    df = pd.read_csv(f, header=None)

                # Si la primera fila es header textual, eliminarla
                if str(df.iloc[0, 0]).lower() in ["open_time", "open time"]:
                    df = df.iloc[1:].copy()

                df.columns = expected_cols

            all_dfs.append(df)

    except Exception as e:
        print(f"Error leyendo ZIP {zip_path}: {e}")

if not all_dfs:
    raise RuntimeError("No se descargó ningún archivo intradiario.")

# =====================================
# FORMATO BINANCE KLINES
# =====================================

data = pd.concat(all_dfs, ignore_index=True)

expected_cols = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore"
]

data = data[expected_cols]

numeric_cols = expected_cols

for col in numeric_cols:
    data[col] = pd.to_numeric(data[col], errors="coerce")

data = data.dropna(subset=["open_time", "open", "high", "low", "close"])

data["open_time"] = pd.to_datetime(data["open_time"], unit="ms")
data["close_time"] = pd.to_datetime(data["close_time"], unit="ms")

data = data.sort_values("open_time").drop_duplicates("open_time").reset_index(drop=True)

# =====================================
# FEATURES BÁSICAS
# =====================================

data["return_pct"] = (data["close"] - data["open"]) / data["open"] * 100
data["range_pct"] = (data["high"] - data["low"]) / data["open"] * 100
data["body_pct"] = abs(data["close"] - data["open"]) / data["open"] * 100

data["taker_buy_ratio"] = data["taker_buy_base_volume"] / data["volume"]
data["taker_sell_ratio"] = 1 - data["taker_buy_ratio"]

data["volume_ma_20"] = data["volume"].rolling(20).mean()
data["volume_ratio_20"] = data["volume"] / data["volume_ma_20"]

data["trades_ma_20"] = data["number_of_trades"].rolling(20).mean()
data["trades_ratio_20"] = data["number_of_trades"] / data["trades_ma_20"]

# =====================================
# EXPORT
# =====================================

data.to_csv(OUTPUT_FILE, index=False)

print("\n" + "=" * 70)
print("INTRADAY DATA DOWNLOADER v0.2")
print("=" * 70)

print(f"Símbolo: {SYMBOL}")
print(f"Intervalo: {INTERVAL}")
print(f"Filas: {len(data)}")
print(f"Desde: {data['open_time'].min()}")
print(f"Hasta: {data['open_time'].max()}")

print("\nArchivo generado:")
print(OUTPUT_FILE)

print("\nColumnas:")
print(list(data.columns))