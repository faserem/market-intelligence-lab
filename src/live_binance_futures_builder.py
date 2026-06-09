import requests
import pandas as pd
import time
from datetime import datetime, timezone

SYMBOL = "BTCUSDT"
INTERVAL = "5m"
LIMIT = 500

BASE = "https://fapi.binance.com"

OUT_FILE = "data/live_binance_futures_5m.csv"
OI_FILE = "data/live_binance_open_interest.csv"

# =========================
# KLINES FUTURES
# =========================

def get_klines():
    url = f"{BASE}/fapi/v1/klines"

    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "limit": LIMIT
    }

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()

    data = r.json()

    df = pd.DataFrame(data, columns=[
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
    ])

    numeric_cols = [
        "open", "high", "low", "close", "volume",
        "quote_asset_volume", "number_of_trades",
        "taker_buy_base_volume", "taker_buy_quote_volume"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

    df["return_pct"] = (df["close"] - df["open"]) / df["open"] * 100
    df["range_pct"] = (df["high"] - df["low"]) / df["open"] * 100
    df["body_pct"] = abs(df["close"] - df["open"]) / df["open"] * 100

    df["taker_buy_ratio"] = df["taker_buy_base_volume"] / df["volume"]
    df["taker_sell_ratio"] = 1 - df["taker_buy_ratio"]

    df["volume_ma_20"] = df["volume"].rolling(20).mean()
    df["volume_ratio_20"] = df["volume"] / df["volume_ma_20"]

    df["trades_ma_20"] = df["number_of_trades"].rolling(20).mean()
    df["trades_ratio_20"] = df["number_of_trades"] / df["trades_ma_20"]

    return df

# =========================
# OPEN INTEREST ACTUAL
# =========================

def get_open_interest():
    url = f"{BASE}/fapi/v1/openInterest"

    params = {
        "symbol": SYMBOL
    }

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()

    data = r.json()

    df = pd.DataFrame([{
        "timestamp": datetime.now(timezone.utc),
        "symbol": data.get("symbol"),
        "open_interest": float(data.get("openInterest"))
    }])

    return df

# =========================
# RUN
# =========================

print("\n" + "=" * 70)
print("LIVE BINANCE FUTURES BUILDER")
print("=" * 70)

try:
    klines = get_klines()
    klines.to_csv(OUT_FILE, index=False)

    print(f"Klines OK: {len(klines)} filas")
    print(f"Archivo: {OUT_FILE}")
    print(f"Último precio: {klines['close'].iloc[-1]:,.2f}")

except Exception as e:
    print("\nERROR descargando klines:")
    print(e)

try:
    oi = get_open_interest()
    oi.to_csv(OI_FILE, index=False)

    print("\nOpen Interest OK")
    print(oi.to_string(index=False))
    print(f"Archivo: {OI_FILE}")

except Exception as e:
    print("\nERROR descargando Open Interest:")
    print(e)

print("\nFin.")