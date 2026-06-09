import pandas as pd
import numpy as np
from itertools import product

# =====================================
# CONFIG
# =====================================

DATA_PATH = "data/intraday/BTCUSDT_5m.csv"

OUTPUT_EVENTS = "reports/intraday_big_move_events.csv"
OUTPUT_PATTERNS = "reports/intraday_pattern_rankings.csv"
OUTPUT_CONTEXT = "reports/intraday_feature_context.csv"

# movimientos futuros a estudiar
MOVE_THRESHOLDS = [0.5, 1.0, 1.5, 2.0, 3.0]

# ventanas futuras en velas de 5m
# 3 = 15m, 6 = 30m, 12 = 1h, 24 = 2h
FUTURE_WINDOWS = [3, 6, 12, 24]

# =====================================
# CARGA
# =====================================

df = pd.read_csv(DATA_PATH)

df["open_time"] = pd.to_datetime(df["open_time"])

for col in [
    "open", "high", "low", "close", "volume",
    "quote_asset_volume", "number_of_trades",
    "taker_buy_base_volume", "taker_buy_quote_volume",
    "return_pct", "range_pct", "body_pct",
    "taker_buy_ratio", "taker_sell_ratio",
    "volume_ratio_20", "trades_ratio_20"
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna().sort_values("open_time").reset_index(drop=True)

# =====================================
# FEATURES
# =====================================

df["ret_1"] = df["close"].pct_change(1) * 100
df["ret_3"] = df["close"].pct_change(3) * 100
df["ret_6"] = df["close"].pct_change(6) * 100
df["ret_12"] = df["close"].pct_change(12) * 100

df["vol_ratio_50"] = df["volume"] / df["volume"].rolling(50).mean()
df["trades_ratio_50"] = df["number_of_trades"] / df["number_of_trades"].rolling(50).mean()

df["range_ma_20"] = df["range_pct"].rolling(20).mean()
df["range_ratio_20"] = df["range_pct"] / df["range_ma_20"]

df["body_ma_20"] = df["body_pct"].rolling(20).mean()
df["body_ratio_20"] = df["body_pct"] / df["body_ma_20"]

df["taker_delta"] = df["taker_buy_ratio"] - 0.5

df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

df["dist_ema20_pct"] = ((df["close"] - df["ema20"]) / df["ema20"]) * 100
df["dist_ema50_pct"] = ((df["close"] - df["ema50"]) / df["ema50"]) * 100

df["rolling_high_12"] = df["high"].shift(1).rolling(12).max()
df["rolling_low_12"] = df["low"].shift(1).rolling(12).min()

df["rolling_high_48"] = df["high"].shift(1).rolling(48).max()
df["rolling_low_48"] = df["low"].shift(1).rolling(48).min()

df["break_high_12"] = df["close"] > df["rolling_high_12"]
df["break_low_12"] = df["close"] < df["rolling_low_12"]

df["break_high_48"] = df["close"] > df["rolling_high_48"]
df["break_low_48"] = df["close"] < df["rolling_low_48"]

# Compresión previa
df["compression_20"] = df["range_ma_20"] / df["range_pct"].rolling(100).mean()

# =====================================
# FUTUROS
# =====================================

for w in FUTURE_WINDOWS:
    df[f"future_high_{w}"] = df["high"].shift(-1).rolling(w).max().shift(-(w-1))
    df[f"future_low_{w}"] = df["low"].shift(-1).rolling(w).min().shift(-(w-1))

    df[f"future_up_{w}_pct"] = ((df[f"future_high_{w}"] - df["close"]) / df["close"]) * 100
    df[f"future_down_{w}_pct"] = ((df[f"future_low_{w}"] - df["close"]) / df["close"]) * 100

# =====================================
# EVENTOS DE MOVIMIENTOS GRANDES
# =====================================

events = []

for idx, row in df.iterrows():

    for w in FUTURE_WINDOWS:

        for th in MOVE_THRESHOLDS:

            if row[f"future_up_{w}_pct"] >= th:
                events.append({
                    "open_time": row["open_time"],
                    "direction": "UP",
                    "window_bars": w,
                    "threshold_pct": th,
                    "future_move_pct": row[f"future_up_{w}_pct"],
                    "close": row["close"],
                })

            if row[f"future_down_{w}_pct"] <= -th:
                events.append({
                    "open_time": row["open_time"],
                    "direction": "DOWN",
                    "window_bars": w,
                    "threshold_pct": th,
                    "future_move_pct": row[f"future_down_{w}_pct"],
                    "close": row["close"],
                })

events_df = pd.DataFrame(events)
events_df.to_csv(OUTPUT_EVENTS, index=False)

# =====================================
# PATRONES BINARIOS
# =====================================

# Convertimos features en condiciones simples.
df["high_volume"] = df["vol_ratio_50"] >= 1.5
df["very_high_volume"] = df["vol_ratio_50"] >= 2.0

df["high_trades"] = df["trades_ratio_50"] >= 1.5
df["large_range"] = df["range_ratio_20"] >= 1.5
df["large_body"] = df["body_ratio_20"] >= 1.5

df["buy_pressure"] = df["taker_buy_ratio"] >= 0.58
df["sell_pressure"] = df["taker_buy_ratio"] <= 0.42

df["above_ema20"] = df["close"] > df["ema20"]
df["below_ema20"] = df["close"] < df["ema20"]

df["above_ema50"] = df["close"] > df["ema50"]
df["below_ema50"] = df["close"] < df["ema50"]

df["compressed"] = df["compression_20"] <= 0.75

conditions = {
    "high_volume": "high_volume",
    "very_high_volume": "very_high_volume",
    "high_trades": "high_trades",
    "large_range": "large_range",
    "large_body": "large_body",
    "buy_pressure": "buy_pressure",
    "sell_pressure": "sell_pressure",
    "break_high_12": "break_high_12",
    "break_low_12": "break_low_12",
    "break_high_48": "break_high_48",
    "break_low_48": "break_low_48",
    "above_ema20": "above_ema20",
    "below_ema20": "below_ema20",
    "above_ema50": "above_ema50",
    "below_ema50": "below_ema50",
    "compressed": "compressed",
}

# =====================================
# RANKING DE PATRONES
# =====================================

pattern_rows = []

base = df.dropna().copy()

condition_names = list(conditions.keys())

# Probamos combinaciones de 1, 2 y 3 condiciones
combos = []

for c in condition_names:
    combos.append((c,))

for c1, c2 in product(condition_names, condition_names):
    if c1 < c2:
        combos.append((c1, c2))

for c1, c2, c3 in product(condition_names, condition_names, condition_names):
    if c1 < c2 < c3:
        combos.append((c1, c2, c3))

for combo in combos:

    mask = pd.Series(True, index=base.index)

    for c in combo:
        mask = mask & base[conditions[c]].astype(bool)

    subset = base[mask].copy()

    # Evitamos patrones demasiado escasos
    if len(subset) < 50:
        continue

    for w in FUTURE_WINDOWS:
        for th in MOVE_THRESHOLDS:

            up_hit = subset[f"future_up_{w}_pct"] >= th
            down_hit = subset[f"future_down_{w}_pct"] <= -th

            up_rate = up_hit.mean() * 100
            down_rate = down_hit.mean() * 100

            avg_up = subset[f"future_up_{w}_pct"].mean()
            avg_down = subset[f"future_down_{w}_pct"].mean()

            pattern_rows.append({
                "pattern": " + ".join(combo),
                "conditions_count": len(combo),
                "samples": len(subset),
                "window_bars": w,
                "window_minutes": w * 5,
                "threshold_pct": th,
                "up_hit_rate_pct": up_rate,
                "down_hit_rate_pct": down_rate,
                "avg_future_up_pct": avg_up,
                "avg_future_down_pct": avg_down,
                "edge_up_vs_down": up_rate - down_rate,
                "edge_down_vs_up": down_rate - up_rate,
            })

patterns = pd.DataFrame(pattern_rows)

patterns = patterns.sort_values(
    by=["threshold_pct", "window_minutes", "edge_up_vs_down"],
    ascending=[False, True, False]
)

patterns.to_csv(OUTPUT_PATTERNS, index=False)

# =====================================
# CONTEXTO FEATURE PROMEDIO PARA EVENTOS GRANDES
# =====================================

context_rows = []

for w in FUTURE_WINDOWS:
    for th in MOVE_THRESHOLDS:

        up_cases = df[df[f"future_up_{w}_pct"] >= th]
        down_cases = df[df[f"future_down_{w}_pct"] <= -th]

        for name, cases in [("UP", up_cases), ("DOWN", down_cases)]:

            if len(cases) == 0:
                continue

            context_rows.append({
                "direction": name,
                "window_bars": w,
                "window_minutes": w * 5,
                "threshold_pct": th,
                "cases": len(cases),
                "avg_volume_ratio_50": cases["vol_ratio_50"].mean(),
                "avg_trades_ratio_50": cases["trades_ratio_50"].mean(),
                "avg_range_ratio_20": cases["range_ratio_20"].mean(),
                "avg_body_ratio_20": cases["body_ratio_20"].mean(),
                "avg_taker_buy_ratio": cases["taker_buy_ratio"].mean(),
                "avg_compression_20": cases["compression_20"].mean(),
                "break_high_12_rate": cases["break_high_12"].mean() * 100,
                "break_low_12_rate": cases["break_low_12"].mean() * 100,
                "break_high_48_rate": cases["break_high_48"].mean() * 100,
                "break_low_48_rate": cases["break_low_48"].mean() * 100,
            })

context = pd.DataFrame(context_rows)
context.to_csv(OUTPUT_CONTEXT, index=False)

# =====================================
# OUTPUT
# =====================================

print("\n" + "=" * 70)
print("INTRADAY PATTERN MINER v0.1")
print("=" * 70)

print(f"Filas analizadas: {len(df)}")
print(f"Eventos detectados: {len(events_df)}")
print(f"Patrones evaluados: {len(patterns)}")

print("\nTOP 20 PATRONES UP por edge")
top_up = patterns[
    (patterns["threshold_pct"] >= 1.0) &
    (patterns["samples"] >= 100)
].sort_values("edge_up_vs_down", ascending=False).head(20)

print(top_up.to_string(index=False))

print("\nTOP 20 PATRONES DOWN por edge")
top_down = patterns[
    (patterns["threshold_pct"] >= 1.0) &
    (patterns["samples"] >= 100)
].sort_values("edge_down_vs_up", ascending=False).head(20)

print(top_down.to_string(index=False))

print("\nCONTEXTO PROMEDIO DE EVENTOS")
print(context.tail(20).to_string(index=False))

print("\nArchivos generados:")
print(OUTPUT_EVENTS)
print(OUTPUT_PATTERNS)
print(OUTPUT_CONTEXT)