import pandas as pd
import numpy as np
from itertools import combinations

DATA_PATH = "data/intraday/BTCUSDT_5m.csv"

OUTPUT = "reports/intraday_strategy_miner.csv"

df = pd.read_csv(DATA_PATH)
df["open_time"] = pd.to_datetime(df["open_time"])

for col in df.columns:
    if col != "open_time" and col != "close_time":
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna().sort_values("open_time").reset_index(drop=True)

# =========================
# FEATURES
# =========================

df["ret_1"] = df["close"].pct_change(1) * 100
df["ret_3"] = df["close"].pct_change(3) * 100
df["ret_6"] = df["close"].pct_change(6) * 100
df["ret_12"] = df["close"].pct_change(12) * 100

df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
df["ema100"] = df["close"].ewm(span=100, adjust=False).mean()

df["above_ema20"] = df["close"] > df["ema20"]
df["below_ema20"] = df["close"] < df["ema20"]
df["above_ema50"] = df["close"] > df["ema50"]
df["below_ema50"] = df["close"] < df["ema50"]

df["vol_ratio_20"] = df["volume"] / df["volume"].rolling(20).mean()
df["vol_ratio_50"] = df["volume"] / df["volume"].rolling(50).mean()

df["trades_ratio_20"] = df["number_of_trades"] / df["number_of_trades"].rolling(20).mean()
df["trades_ratio_50"] = df["number_of_trades"] / df["number_of_trades"].rolling(50).mean()

df["taker_buy_ratio"] = df["taker_buy_base_volume"] / df["volume"]
df["taker_sell_ratio"] = 1 - df["taker_buy_ratio"]

df["range_pct"] = (df["high"] - df["low"]) / df["open"] * 100
df["body_pct"] = abs(df["close"] - df["open"]) / df["open"] * 100

df["range_ratio_20"] = df["range_pct"] / df["range_pct"].rolling(20).mean()
df["body_ratio_20"] = df["body_pct"] / df["body_pct"].rolling(20).mean()

df["high_12"] = df["high"].shift(1).rolling(12).max()
df["low_12"] = df["low"].shift(1).rolling(12).min()
df["high_48"] = df["high"].shift(1).rolling(48).max()
df["low_48"] = df["low"].shift(1).rolling(48).min()

df["break_high_12"] = df["close"] > df["high_12"]
df["break_low_12"] = df["close"] < df["low_12"]
df["break_high_48"] = df["close"] > df["high_48"]
df["break_low_48"] = df["close"] < df["low_48"]

df["range_ma_20"] = df["range_pct"].rolling(20).mean()
df["range_ma_100"] = df["range_pct"].rolling(100).mean()
df["compressed"] = df["range_ma_20"] < df["range_ma_100"] * 0.75

# =========================
# CONDICIONES
# =========================

conditions = {
    "above_ema20": df["above_ema20"],
    "below_ema20": df["below_ema20"],
    "above_ema50": df["above_ema50"],
    "below_ema50": df["below_ema50"],
    "high_volume": df["vol_ratio_50"] >= 1.5,
    "very_high_volume": df["vol_ratio_50"] >= 2.0,
    "high_trades": df["trades_ratio_50"] >= 1.5,
    "large_range": df["range_ratio_20"] >= 1.5,
    "large_body": df["body_ratio_20"] >= 1.5,
    "buy_pressure": df["taker_buy_ratio"] >= 0.58,
    "sell_pressure": df["taker_buy_ratio"] <= 0.42,
    "break_high_12": df["break_high_12"],
    "break_low_12": df["break_low_12"],
    "break_high_48": df["break_high_48"],
    "break_low_48": df["break_low_48"],
    "compressed": df["compressed"],
    "ret_3_up": df["ret_3"] > 0.3,
    "ret_3_down": df["ret_3"] < -0.3,
    "ret_6_up": df["ret_6"] > 0.5,
    "ret_6_down": df["ret_6"] < -0.5,
}

# =========================
# SIMULACIÓN
# =========================

HOLD_BARS_LIST = [3, 6, 12, 24]  # 15m, 30m, 1h, 2h
TARGETS = [0.5, 0.8, 1.0, 1.5, 2.0]
STOPS = [0.3, 0.5, 0.8, 1.0]

rows = []

condition_names = list(conditions.keys())

combos = []
for r in [1, 2, 3]:
    combos.extend(list(combinations(condition_names, r)))

for combo in combos:

    mask = pd.Series(True, index=df.index)

    for c in combo:
        mask &= conditions[c].fillna(False)

    signal_idx = df[mask].index.tolist()

    if len(signal_idx) < 80:
        continue

    for direction in ["LONG", "SHORT"]:
        for hold_bars in HOLD_BARS_LIST:
            for target in TARGETS:
                for stop in STOPS:

                    results = []

                    for i in signal_idx:

                        if i + hold_bars >= len(df):
                            continue

                        entry = df.loc[i, "close"]

                        future = df.iloc[i+1:i+hold_bars+1]

                        if direction == "LONG":
                            target_price = entry * (1 + target / 100)
                            stop_price = entry * (1 - stop / 100)

                            hit_target = future["high"] >= target_price
                            hit_stop = future["low"] <= stop_price

                        else:
                            target_price = entry * (1 - target / 100)
                            stop_price = entry * (1 + stop / 100)

                            hit_target = future["low"] <= target_price
                            hit_stop = future["high"] >= stop_price

                        target_hit_index = hit_target.idxmax() if hit_target.any() else None
                        stop_hit_index = hit_stop.idxmax() if hit_stop.any() else None

                        if target_hit_index is not None and stop_hit_index is not None:
                            if target_hit_index < stop_hit_index:
                                pnl = target
                            else:
                                pnl = -stop

                        elif target_hit_index is not None:
                            pnl = target

                        elif stop_hit_index is not None:
                            pnl = -stop

                        else:
                            exit_price = df.loc[i + hold_bars, "close"]

                            if direction == "LONG":
                                pnl = ((exit_price - entry) / entry) * 100
                            else:
                                pnl = ((entry - exit_price) / entry) * 100

                        results.append(pnl)

                    if len(results) < 50:
                        continue

                    results = np.array(results)

                    wins = results[results > 0]
                    losses = results[results <= 0]

                    win_rate = len(wins) / len(results) * 100
                    avg_win = wins.mean() if len(wins) else 0
                    avg_loss = losses.mean() if len(losses) else 0

                    gross_profit = wins.sum() if len(wins) else 0
                    gross_loss = abs(losses.sum()) if len(losses) else 0
                    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.nan

                    expectancy = results.mean()

                    rows.append({
                        "pattern": " + ".join(combo),
                        "direction": direction,
                        "samples": len(results),
                        "hold_bars": hold_bars,
                        "hold_minutes": hold_bars * 5,
                        "target_pct": target,
                        "stop_pct": stop,
                        "win_rate_pct": win_rate,
                        "avg_win_pct": avg_win,
                        "avg_loss_pct": avg_loss,
                        "profit_factor": profit_factor,
                        "expectancy_pct": expectancy,
                        "total_pnl_pct_units": results.sum(),
                    })

out = pd.DataFrame(rows)

out = out.replace([np.inf, -np.inf], np.nan).dropna(subset=["profit_factor"])

out = out[
    (out["samples"] >= 80) &
    (out["profit_factor"] > 1.1)
].copy()

out = out.sort_values(
    ["profit_factor", "expectancy_pct", "samples"],
    ascending=[False, False, False]
)

out.to_csv(OUTPUT, index=False)

print("\n" + "=" * 70)
print("INTRADAY STRATEGY MINER v0.1")
print("=" * 70)

print(f"Estrategias encontradas: {len(out)}")

print("\nTOP 30 ESTRATEGIAS")
print(out.head(30).to_string(index=False))

print("\nArchivo generado:")
print(OUTPUT)