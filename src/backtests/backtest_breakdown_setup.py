import pandas as pd
import numpy as np

# =====================================
# CONFIG
# =====================================

START_DATE = "2020-01-01"

DATA_PATH = "data/btc_daily.csv"
OUTPUT_PATH = "reports/backtest_breakdown_setup.csv"
SUMMARY_PATH = "reports/backtest_breakdown_summary.csv"

# Umbrales del setup
MIN_SCORE = 70

# =====================================
# CARGA DATA
# =====================================

df = pd.read_csv(DATA_PATH)

df["Date"] = pd.to_datetime(df["Date"])

for col in ["Open", "High", "Low", "Close", "Volume"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna().sort_values("Date").reset_index(drop=True)

# =====================================
# INDICADORES BASE
# =====================================

df["ret_1d"] = df["Close"].pct_change() * 100
df["momentum_5d"] = df["Close"].pct_change(5) * 100
df["momentum_20d"] = df["Close"].pct_change(20) * 100

df["prev_close"] = df["Close"].shift(1)
df["tr1"] = df["High"] - df["Low"]
df["tr2"] = abs(df["High"] - df["prev_close"])
df["tr3"] = abs(df["Low"] - df["prev_close"])
df["TR"] = df[["tr1", "tr2", "tr3"]].max(axis=1)

df["ATR14"] = df["TR"].rolling(14).mean()
df["ATR50"] = df["TR"].rolling(50).mean()
df["ATR_RATIO"] = df["ATR14"] / df["ATR50"]

# Futuro
df["future_close_1d"] = df["Close"].shift(-1)
df["future_close_2d"] = df["Close"].shift(-2)
df["future_close_3d"] = df["Close"].shift(-3)

df["future_return_1d"] = ((df["future_close_1d"] - df["Close"]) / df["Close"]) * 100
df["future_return_2d"] = ((df["future_close_2d"] - df["Close"]) / df["Close"]) * 100
df["future_return_3d"] = ((df["future_close_3d"] - df["Close"]) / df["Close"]) * 100

# Para short: gana si el retorno futuro es negativo
df["short_win_1d"] = df["future_return_1d"] < 0
df["short_win_2d"] = df["future_return_2d"] < 0
df["short_win_3d"] = df["future_return_3d"] < 0

# =====================================
# ZONAS SIMPLES DINÁMICAS
# =====================================

# Soporte/resistencia rolling usando últimos 20/50 días
df["rolling_low_20"] = df["Low"].rolling(20).min()
df["rolling_low_50"] = df["Low"].rolling(50).min()
df["rolling_high_20"] = df["High"].rolling(20).max()
df["rolling_high_50"] = df["High"].rolling(50).max()

df["dist_to_low_20_pct"] = ((df["Close"] - df["rolling_low_20"]) / df["Close"]) * 100
df["dist_to_low_50_pct"] = ((df["Close"] - df["rolling_low_50"]) / df["Close"]) * 100

df["dist_to_high_20_pct"] = ((df["rolling_high_20"] - df["Close"]) / df["Close"]) * 100
df["dist_to_high_50_pct"] = ((df["rolling_high_50"] - df["Close"]) / df["Close"]) * 100

# =====================================
# BREAKDOWN SETUP SCORE
# =====================================

scores = []
notes_list = []

for _, row in df.iterrows():

    score = 0
    notes = []

    # Momentum bajista
    if row["momentum_5d"] <= -5:
        score += 20
        notes.append("momentum_5d_bearish")

    elif row["momentum_5d"] <= -2:
        score += 10
        notes.append("momentum_5d_moderate")

    if row["momentum_20d"] <= -10:
        score += 25
        notes.append("momentum_20d_bearish")

    elif row["momentum_20d"] <= -5:
        score += 12
        notes.append("momentum_20d_moderate")

    # Volatilidad no agotada
    if pd.notna(row["ATR_RATIO"]):
        if row["ATR_RATIO"] <= 1.20:
            score += 15
            notes.append("volatility_not_exhausted")
        else:
            score += 5
            notes.append("volatility_already_expanded")

    # Cerca de soporte rolling
    if pd.notna(row["dist_to_low_20_pct"]):
        if row["dist_to_low_20_pct"] <= 3:
            score += 25
            notes.append("near_20d_low")
        elif row["dist_to_low_20_pct"] <= 7:
            score += 12
            notes.append("near_20d_low_moderate")

    if pd.notna(row["dist_to_low_50_pct"]):
        if row["dist_to_low_50_pct"] <= 5:
            score += 15
            notes.append("near_50d_low")
        elif row["dist_to_low_50_pct"] <= 10:
            score += 8
            notes.append("near_50d_low_moderate")

    # Rechazo desde resistencia cercana / lejos del high
    if pd.notna(row["dist_to_high_20_pct"]):
        if row["dist_to_high_20_pct"] >= 8:
            score += 10
            notes.append("far_from_20d_high")

    # Movimiento diario fuerte bajista
    if row["ret_1d"] <= -3:
        score += 15
        notes.append("strong_daily_drop")
    elif row["ret_1d"] <= -1.5:
        score += 8
        notes.append("moderate_daily_drop")

    score = min(100, score)

    scores.append(score)
    notes_list.append("|".join(notes))

df["breakdown_score"] = scores
df["setup_notes"] = notes_list
df["setup_active"] = df["breakdown_score"] >= MIN_SCORE

# =====================================
# FILTRO PERÍODO
# =====================================

bt = df[df["Date"] >= START_DATE].copy()
bt = bt.dropna(subset=["future_return_1d", "future_return_2d", "future_return_3d"])

signals = bt[bt["setup_active"]].copy()

# =====================================
# RESUMEN
# =====================================

summary_rows = []

for threshold in [50, 60, 70, 80, 90]:
    subset = bt[bt["breakdown_score"] >= threshold].copy()

    if len(subset) == 0:
        continue

    summary_rows.append({
        "threshold": threshold,
        "signals": len(subset),
        "win_rate_1d_pct": subset["short_win_1d"].mean() * 100,
        "win_rate_2d_pct": subset["short_win_2d"].mean() * 100,
        "win_rate_3d_pct": subset["short_win_3d"].mean() * 100,
        "avg_return_1d_pct": subset["future_return_1d"].mean(),
        "avg_return_2d_pct": subset["future_return_2d"].mean(),
        "avg_return_3d_pct": subset["future_return_3d"].mean(),
        "median_return_3d_pct": subset["future_return_3d"].median(),
        "best_short_3d_pct": subset["future_return_3d"].min(),
        "worst_short_3d_pct": subset["future_return_3d"].max(),
    })

summary = pd.DataFrame(summary_rows)

# =====================================
# EXPORT
# =====================================

bt.to_csv(OUTPUT_PATH, index=False)
summary.to_csv(SUMMARY_PATH, index=False)

# =====================================
# OUTPUT
# =====================================

print("\n" + "=" * 70)
print("BACKTEST BREAKDOWN SETUP v0.1")
print("=" * 70)

print(f"Período desde: {START_DATE}")
print(f"Filas analizadas: {len(bt)}")
print(f"Señales score >= {MIN_SCORE}: {len(signals)}")

print("\nRESUMEN POR UMBRAL")
print(summary.to_string(index=False))

print("\nÚLTIMAS 15 SEÑALES")
cols = [
    "Date",
    "Close",
    "breakdown_score",
    "momentum_5d",
    "momentum_20d",
    "ATR_RATIO",
    "future_return_1d",
    "future_return_2d",
    "future_return_3d",
    "setup_notes"
]

print(
    signals.tail(15)[cols].to_string(index=False)
)

print("\nArchivos generados:")
print(OUTPUT_PATH)
print(SUMMARY_PATH)