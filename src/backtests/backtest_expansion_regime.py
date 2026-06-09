import pandas as pd
import numpy as np

START_DATE = "2020-01-01"

DATA_PATH = "data/btc_daily.csv"
OUTPUT_PATH = "reports/backtest_expansion_regime.csv"
SUMMARY_PATH = "reports/backtest_expansion_regime_summary.csv"

df = pd.read_csv(DATA_PATH)
df["Date"] = pd.to_datetime(df["Date"])

for col in ["Open", "High", "Low", "Close", "Volume"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna().sort_values("Date").reset_index(drop=True)

# ==========================
# REGIME
# ==========================

df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
df["EMA100"] = df["Close"].ewm(span=100, adjust=False).mean()
df["EMA200"] = df["Close"].ewm(span=200, adjust=False).mean()

df["EMA200_slope_20d"] = df["EMA200"].pct_change(20) * 100

def classify_regime(row):
    close = row["Close"]
    ema50 = row["EMA50"]
    ema100 = row["EMA100"]
    ema200 = row["EMA200"]
    slope = row["EMA200_slope_20d"]

    if close > ema50 > ema100 > ema200 and slope > 1:
        return "STRONG_BULL"
    elif close > ema200 and slope >= 0:
        return "BULL"
    elif close < ema50 < ema100 < ema200 and slope < -1:
        return "STRONG_BEAR"
    elif close < ema200 and slope <= 0:
        return "BEAR"
    else:
        return "RANGE"

df["regime"] = df.apply(classify_regime, axis=1)

# ==========================
# BASE
# ==========================

df["ret_1d"] = df["Close"].pct_change() * 100
df["momentum_5d"] = df["Close"].pct_change(5) * 100
df["momentum_20d"] = df["Close"].pct_change(20) * 100

df["vol_avg_20"] = df["Volume"].rolling(20).mean()
df["volume_ratio"] = df["Volume"] / df["vol_avg_20"]

df["prev_low_20"] = df["Low"].shift(1).rolling(20).min()
df["prev_high_20"] = df["High"].shift(1).rolling(20).max()

df["prev_low_50"] = df["Low"].shift(1).rolling(50).min()
df["prev_high_50"] = df["High"].shift(1).rolling(50).max()

df["prev_close"] = df["Close"].shift(1)
df["tr1"] = df["High"] - df["Low"]
df["tr2"] = abs(df["High"] - df["prev_close"])
df["tr3"] = abs(df["Low"] - df["prev_close"])
df["TR"] = df[["tr1", "tr2", "tr3"]].max(axis=1)

df["ATR14"] = df["TR"].rolling(14).mean()
df["ATR50"] = df["TR"].rolling(50).mean()
df["ATR_RATIO"] = df["ATR14"] / df["ATR50"]

# ==========================
# FUTURO
# ==========================

for days in [1, 2, 3, 5]:
    df[f"future_close_{days}d"] = df["Close"].shift(-days)
    df[f"future_return_{days}d"] = (
        (df[f"future_close_{days}d"] - df["Close"]) / df["Close"]
    ) * 100

# ==========================
# TRIGGERS
# ==========================

df["down_break_20"] = df["Close"] < df["prev_low_20"]
df["down_break_50"] = df["Close"] < df["prev_low_50"]

df["up_break_20"] = df["Close"] > df["prev_high_20"]
df["up_break_50"] = df["Close"] > df["prev_high_50"]

down_scores = []
up_scores = []
down_notes = []
up_notes = []

for _, row in df.iterrows():

    down_score = 0
    up_score = 0
    dn = []
    un = []

    # Rupturas
    if row["down_break_20"]:
        down_score += 35
        dn.append("down_break_20")

    if row["down_break_50"]:
        down_score += 25
        dn.append("down_break_50")

    if row["up_break_20"]:
        up_score += 35
        un.append("up_break_20")

    if row["up_break_50"]:
        up_score += 25
        un.append("up_break_50")

    # Momentum
    if row["momentum_5d"] <= -3:
        down_score += 15
        dn.append("bearish_momentum_5d")

    if row["momentum_20d"] <= -7:
        down_score += 15
        dn.append("bearish_momentum_20d")

    if row["momentum_5d"] >= 3:
        up_score += 15
        un.append("bullish_momentum_5d")

    if row["momentum_20d"] >= 7:
        up_score += 15
        un.append("bullish_momentum_20d")

    # Volumen
    if pd.notna(row["volume_ratio"]):
        if row["volume_ratio"] >= 1.5:
            down_score += 15
            up_score += 15
            dn.append("high_volume")
            un.append("high_volume")
        elif row["volume_ratio"] >= 1.2:
            down_score += 8
            up_score += 8
            dn.append("moderate_volume")
            un.append("moderate_volume")

    # Volatilidad
    if pd.notna(row["ATR_RATIO"]):
        if row["ATR_RATIO"] <= 1.2:
            down_score += 10
            up_score += 10
            dn.append("vol_not_exhausted")
            un.append("vol_not_exhausted")
        else:
            down_score += 3
            up_score += 3
            dn.append("vol_expanded")
            un.append("vol_expanded")

    # Vela fuerte
    if row["ret_1d"] <= -2:
        down_score += 10
        dn.append("strong_bearish_day")

    if row["ret_1d"] >= 2:
        up_score += 10
        un.append("strong_bullish_day")

    # Filtro de régimen como score extra
    if row["regime"] in ["BEAR", "STRONG_BEAR"]:
        down_score += 15
        dn.append("bear_regime")

    if row["regime"] in ["BULL", "STRONG_BULL"]:
        up_score += 15
        un.append("bull_regime")

    # Penalización si va contra régimen fuerte
    if row["regime"] == "STRONG_BULL":
        down_score -= 20
        dn.append("against_strong_bull")

    if row["regime"] == "STRONG_BEAR":
        up_score -= 20
        un.append("against_strong_bear")

    down_scores.append(max(0, min(100, down_score)))
    up_scores.append(max(0, min(100, up_score)))
    down_notes.append("|".join(dn))
    up_notes.append("|".join(un))

df["down_expansion_score"] = down_scores
df["up_expansion_score"] = up_scores
df["down_notes"] = down_notes
df["up_notes"] = up_notes

df["dominant_direction"] = np.where(
    df["down_expansion_score"] > df["up_expansion_score"] + 10,
    "DOWN",
    np.where(
        df["up_expansion_score"] > df["down_expansion_score"] + 10,
        "UP",
        "MIXED"
    )
)

df["dominant_score"] = df[["down_expansion_score", "up_expansion_score"]].max(axis=1)

# ==========================
# BACKTEST
# ==========================

bt = df[df["Date"] >= START_DATE].copy()
bt = bt.dropna(subset=[
    "future_return_1d",
    "future_return_2d",
    "future_return_3d",
    "future_return_5d"
])

summary_rows = []

for direction in ["DOWN", "UP"]:
    for threshold in [50, 60, 70, 80, 90]:

        if direction == "DOWN":
            subset = bt[
                (bt["down_expansion_score"] >= threshold) &
                (bt["dominant_direction"] == "DOWN")
            ].copy()

            win_1d = subset["future_return_1d"] < 0
            win_2d = subset["future_return_2d"] < 0
            win_3d = subset["future_return_3d"] < 0
            win_5d = subset["future_return_5d"] < 0

        else:
            subset = bt[
                (bt["up_expansion_score"] >= threshold) &
                (bt["dominant_direction"] == "UP")
            ].copy()

            win_1d = subset["future_return_1d"] > 0
            win_2d = subset["future_return_2d"] > 0
            win_3d = subset["future_return_3d"] > 0
            win_5d = subset["future_return_5d"] > 0

        if len(subset) == 0:
            continue

        summary_rows.append({
            "direction": direction,
            "threshold": threshold,
            "signals": len(subset),
            "win_rate_1d_pct": win_1d.mean() * 100,
            "win_rate_2d_pct": win_2d.mean() * 100,
            "win_rate_3d_pct": win_3d.mean() * 100,
            "win_rate_5d_pct": win_5d.mean() * 100,
            "avg_return_1d_pct": subset["future_return_1d"].mean(),
            "avg_return_3d_pct": subset["future_return_3d"].mean(),
            "avg_return_5d_pct": subset["future_return_5d"].mean(),
            "median_return_3d_pct": subset["future_return_3d"].median(),
            "best_down_move_3d_pct": subset["future_return_3d"].min(),
            "best_up_move_3d_pct": subset["future_return_3d"].max(),
        })

summary = pd.DataFrame(summary_rows)

# Por régimen
regime_summary = bt.groupby("regime").agg(
    rows=("Close", "count"),
    avg_forward_3d=("future_return_3d", "mean"),
    median_forward_3d=("future_return_3d", "median")
).reset_index()

bt.to_csv(OUTPUT_PATH, index=False)
summary.to_csv(SUMMARY_PATH, index=False)
regime_summary.to_csv("reports/backtest_regime_summary.csv", index=False)

print("\n" + "=" * 70)
print("BACKTEST EXPANSION + REGIME v0.1")
print("=" * 70)

print(f"Período desde: {START_DATE}")
print(f"Filas analizadas: {len(bt)}")

print("\nRESUMEN POR SEÑAL")
print(summary.to_string(index=False))

print("\nRESUMEN POR RÉGIMEN")
print(regime_summary.to_string(index=False))

print("\nÚLTIMAS 20 SEÑALES DOMINANTES")
signals = bt[bt["dominant_score"] >= 70].copy()

cols = [
    "Date",
    "Close",
    "regime",
    "dominant_direction",
    "dominant_score",
    "down_expansion_score",
    "up_expansion_score",
    "future_return_1d",
    "future_return_3d",
    "future_return_5d",
    "down_notes",
    "up_notes"
]

print(signals.tail(20)[cols].to_string(index=False))

print("\nArchivos generados:")
print(OUTPUT_PATH)
print(SUMMARY_PATH)
print("reports/backtest_regime_summary.csv")