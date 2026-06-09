import pandas as pd
import glob
import numpy as np

FILES = glob.glob("data/tardis/binance-futures_derivative_ticker_*_BTCUSDT.csv")

dfs = []

for file in FILES:
    df = pd.read_csv(file)
    dfs.append(df)

df = pd.concat(dfs, ignore_index=True)

df["timestamp"] = pd.to_datetime(df["timestamp"], unit="us")

df = df.dropna(subset=["open_interest", "mark_price"])

df = (
    df
    .set_index("timestamp")
    .sort_index()
    .resample("1min")
    .agg({
        "open_interest": "last",
        "mark_price": "last",
        "funding_rate": "last"
    })
)

df = df.dropna()

# =========================
# CONFIG
# =========================

WINDOW = 15
LOOKAHEAD = 60

# =========================
# FEATURES
# =========================

df["price_change"] = df["mark_price"].pct_change(WINDOW) * 100
df["oi_change"] = df["open_interest"].pct_change(WINDOW) * 100

df["future_high"] = (
    df["mark_price"]
    .shift(-1)
    .rolling(LOOKAHEAD)
    .max()
    .shift(-(LOOKAHEAD - 1))
)

df["future_low"] = (
    df["mark_price"]
    .shift(-1)
    .rolling(LOOKAHEAD)
    .min()
    .shift(-(LOOKAHEAD - 1))
)

df["future_close"] = df["mark_price"].shift(-LOOKAHEAD)

df["future_up_pct"] = ((df["future_high"] - df["mark_price"]) / df["mark_price"]) * 100
df["future_down_pct"] = ((df["future_low"] - df["mark_price"]) / df["mark_price"]) * 100
df["future_close_return_pct"] = ((df["mark_price"] - df["future_close"]) / df["mark_price"]) * 100

df = df.dropna(subset=[
    "price_change",
    "oi_change",
    "future_high",
    "future_low",
    "future_close",
    "future_up_pct",
    "future_down_pct",
    "future_close_return_pct"
])

# =========================
# SEÑAL
# =========================
# Precio sube pero OI baja:
# suba posiblemente por cierre de shorts, no por nuevos longs.

signals = df[
    (df["price_change"] > 0) &
    (df["oi_change"] < 0)
].copy()

TARGETS = [0.3, 0.5, 0.8, 1.0]
STOPS = [0.2, 0.3, 0.5, 0.8]

rows = []

for target in TARGETS:
    for stop in STOPS:

        results = []

        for _, row in signals.iterrows():

            hit_target = row["future_down_pct"] <= -target
            hit_stop = row["future_up_pct"] >= stop

            if hit_target and not hit_stop:
                pnl = target

            elif hit_stop and not hit_target:
                pnl = -stop

            elif hit_target and hit_stop:
                # Conservador: si toca target y stop en la misma ventana,
                # asumimos que primero tocó stop.
                pnl = -stop

            else:
                # Si no toca ni target ni stop,
                # salimos a los 60 minutos por retorno real.
                pnl = row["future_close_return_pct"]

            if pd.notna(pnl):
                results.append(pnl)

        results = np.array(results)

        if len(results) == 0:
            continue

        wins = results[results > 0]
        losses = results[results <= 0]

        gross_profit = wins.sum() if len(wins) else 0
        gross_loss = abs(losses.sum()) if len(losses) else 0

        pf = gross_profit / gross_loss if gross_loss > 0 else np.nan
        win_rate = len(wins) / len(results) * 100

        rows.append({
            "signals": len(results),
            "target_pct": target,
            "stop_pct": stop,
            "win_rate_pct": win_rate,
            "profit_factor": pf,
            "avg_pnl_pct": results.mean(),
            "total_pnl_units": results.sum(),
            "best_pnl_pct": results.max(),
            "worst_pnl_pct": results.min()
        })

out = pd.DataFrame(rows)

out = out.sort_values(
    ["profit_factor", "avg_pnl_pct"],
    ascending=False
)

out.to_csv("reports/oi_short_strategy_test.csv", index=False)

print("\n" + "=" * 70)
print("OI SHORT STRATEGY TEST v0.2")
print("=" * 70)

print(f"Archivos leídos: {len(FILES)}")
print(f"Filas 1m: {len(df)}")
print(f"Señales detectadas: {len(signals)}")

print("\nRESULTADOS")
print(out.to_string(index=False))

print("\nArchivo generado:")
print("reports/oi_short_strategy_test.csv")