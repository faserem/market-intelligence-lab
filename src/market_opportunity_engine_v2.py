import glob
import os
import pandas as pd
import numpy as np

# ============================================================
# MARKET OPPORTUNITY ENGINE v2
# Objetivo:
# - Leer derivative_ticker de Tardis
# - Buscar setups OI/Precio
# - Optimizar parámetros
# - Backtestear con target/stop real secuencial
# - Exportar señales, ranking y señal actual
# ============================================================

SYMBOL = "BTCUSDT"

FILES = sorted(glob.glob("data/tardis/binance-futures_derivative_ticker_*_BTCUSDT.csv"))

REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)

OUT_SIGNALS = f"{REPORT_DIR}/moe_v2_signals.csv"
OUT_BACKTEST = f"{REPORT_DIR}/moe_v2_backtest.csv"
OUT_CURRENT = f"{REPORT_DIR}/moe_v2_current_signal.csv"

LOOKAHEAD_MINUTES = 60

TARGETS = [0.5, 0.8, 1.0, 1.2]
STOPS = [0.3, 0.5, 0.8]
COOLDOWNS = [10, 15, 20, 30]

# Parámetros a optimizar
PRICE_15_THRESHOLDS = [0.08, 0.10, 0.15, 0.20, 0.30]
OI_15_THRESHOLDS = [-0.02, -0.03, -0.05, -0.08, -0.10]

PRICE_5_THRESHOLDS = [0.03, 0.05, 0.08, 0.10]
OI_5_THRESHOLDS = [-0.01, -0.02, -0.03, -0.05]

PRICE_30_THRESHOLDS = [0.10, 0.15, 0.20, 0.30]
OI_30_THRESHOLDS = [-0.03, -0.05, -0.08, -0.10]

if not FILES:
    raise FileNotFoundError("No encontré archivos derivative_ticker en data/tardis/")

# ============================================================
# LOAD DATA
# ============================================================

dfs = []

for file in FILES:
    temp = pd.read_csv(file)
    temp["source_file"] = file
    dfs.append(temp)

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
)

df = df.dropna()

# ============================================================
# FEATURES
# ============================================================

for w in [5, 15, 30, 60]:
    df[f"price_change_{w}m"] = df["mark_price"].pct_change(w) * 100
    df[f"oi_change_{w}m"] = df["open_interest"].pct_change(w) * 100

df = df.dropna()

# ============================================================
# FUTURE PRICE PATH
# ============================================================

def simulate_trade(data, entry_time, direction, target, stop, lookahead_minutes):
    entry_price = data.loc[entry_time, "mark_price"]

    future = data.loc[
        (data.index > entry_time) &
        (data.index <= entry_time + pd.Timedelta(minutes=lookahead_minutes))
    ]

    if future.empty:
        return None

    for exit_time, row in future.iterrows():
        px = row["mark_price"]

        if direction == "SHORT":
            pnl = ((entry_price - px) / entry_price) * 100
            if pnl >= target:
                return {
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "entry_price": entry_price,
                    "exit_price": px,
                    "pnl_pct": target,
                    "exit_reason": "TARGET"
                }
            if pnl <= -stop:
                return {
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "entry_price": entry_price,
                    "exit_price": px,
                    "pnl_pct": -stop,
                    "exit_reason": "STOP"
                }

        if direction == "LONG":
            pnl = ((px - entry_price) / entry_price) * 100
            if pnl >= target:
                return {
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "entry_price": entry_price,
                    "exit_price": px,
                    "pnl_pct": target,
                    "exit_reason": "TARGET"
                }
            if pnl <= -stop:
                return {
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "entry_price": entry_price,
                    "exit_price": px,
                    "pnl_pct": -stop,
                    "exit_reason": "STOP"
                }

    exit_time = future.index[-1]
    exit_price = future["mark_price"].iloc[-1]

    if direction == "SHORT":
        pnl = ((entry_price - exit_price) / entry_price) * 100
    else:
        pnl = ((exit_price - entry_price) / entry_price) * 100

    return {
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl_pct": pnl,
        "exit_reason": "TIME_EXIT"
    }

# ============================================================
# SIGNAL GENERATION
# ============================================================

def generate_signals(
    data,
    price15_th,
    oi15_th,
    price5_th,
    oi5_th,
    price30_th,
    oi30_th,
    cooldown_minutes
):
    signals = []
    last_signal_time = None

    for ts, row in data.iterrows():

        if last_signal_time is not None:
            diff = (ts - last_signal_time).total_seconds() / 60
            if diff < cooldown_minutes:
                continue

        bear_score = 0
        bull_score = 0
        reasons = []

        pc5 = row["price_change_5m"]
        oi5 = row["oi_change_5m"]

        pc15 = row["price_change_15m"]
        oi15 = row["oi_change_15m"]

        pc30 = row["price_change_30m"]
        oi30 = row["oi_change_30m"]

        # SETUP PRINCIPAL VALIDADO:
        # Precio sube + OI baja = short covering fade
        if pc15 >= price15_th and oi15 <= oi15_th:
            bear_score += 45
            reasons.append("15m_PRICE_UP_OI_DOWN")

        if pc5 >= price5_th and oi5 <= oi5_th:
            bear_score += 15
            reasons.append("5m_CONFIRMATION")

        if pc30 >= price30_th and oi30 <= oi30_th:
            bear_score += 20
            reasons.append("30m_CONFIRMATION")

        # SETUP LONG PRELIMINAR:
        # Precio baja + OI baja = posible agotamiento de longs / rebote
        if pc15 <= -0.15 and oi15 <= -0.05:
            bull_score += 35
            reasons.append("15m_PRICE_DOWN_OI_DOWN_REBOUND")

        if pc5 <= -0.08 and oi5 <= -0.03:
            bull_score += 15
            reasons.append("5m_REBOUND_CONFIRMATION")

        if bear_score >= 60 and bear_score >= bull_score + 25:
            decision = "SHORT"
            confidence = min(100, bear_score)
            setup = "OI_SHORT_COVERING_FADE"

        elif bull_score >= 65 and bull_score >= bear_score + 25:
            decision = "LONG"
            confidence = min(100, bull_score)
            setup = "OI_REBOUND_PRELIMINARY"

        else:
            continue

        signals.append({
            "timestamp": ts,
            "price": row["mark_price"],
            "decision": decision,
            "setup": setup,
            "confidence": confidence,
            "bull_score": bull_score,
            "bear_score": bear_score,
            "price_change_5m": pc5,
            "oi_change_5m": oi5,
            "price_change_15m": pc15,
            "oi_change_15m": oi15,
            "price_change_30m": pc30,
            "oi_change_30m": oi30,
            "reasons": " | ".join(reasons)
        })

        last_signal_time = ts

    return pd.DataFrame(signals)

# ============================================================
# OPTIMIZATION LOOP
# ============================================================

backtest_rows = []
all_signal_sets = []

for price15_th in PRICE_15_THRESHOLDS:
    for oi15_th in OI_15_THRESHOLDS:
        for price5_th in PRICE_5_THRESHOLDS:
            for oi5_th in OI_5_THRESHOLDS:
                for price30_th in PRICE_30_THRESHOLDS:
                    for oi30_th in OI_30_THRESHOLDS:
                        for cooldown in COOLDOWNS:

                            signals = generate_signals(
                                df,
                                price15_th,
                                oi15_th,
                                price5_th,
                                oi5_th,
                                price30_th,
                                oi30_th,
                                cooldown
                            )

                            if signals.empty or len(signals) < 20:
                                continue

                            for target in TARGETS:
                                for stop in STOPS:

                                    trades = []

                                    for _, sig in signals.iterrows():
                                        trade = simulate_trade(
                                            df,
                                            sig["timestamp"],
                                            sig["decision"],
                                            target,
                                            stop,
                                            LOOKAHEAD_MINUTES
                                        )

                                        if trade is None:
                                            continue

                                        trade.update({
                                            "decision": sig["decision"],
                                            "setup": sig["setup"],
                                            "confidence": sig["confidence"],
                                            "target": target,
                                            "stop": stop,
                                            "price15_th": price15_th,
                                            "oi15_th": oi15_th,
                                            "price5_th": price5_th,
                                            "oi5_th": oi5_th,
                                            "price30_th": price30_th,
                                            "oi30_th": oi30_th,
                                            "cooldown": cooldown,
                                            "reasons": sig["reasons"]
                                        })

                                        trades.append(trade)

                                    if len(trades) < 20:
                                        continue

                                    trades_df = pd.DataFrame(trades)

                                    wins = trades_df[trades_df["pnl_pct"] > 0]["pnl_pct"]
                                    losses = trades_df[trades_df["pnl_pct"] <= 0]["pnl_pct"]

                                    gross_profit = wins.sum() if len(wins) else 0
                                    gross_loss = abs(losses.sum()) if len(losses) else 0

                                    if gross_loss == 0:
                                        continue

                                    pf = gross_profit / gross_loss
                                    win_rate = len(wins) / len(trades_df) * 100
                                    avg_pnl = trades_df["pnl_pct"].mean()
                                    total_pnl = trades_df["pnl_pct"].sum()

                                    backtest_rows.append({
                                        "trades": len(trades_df),
                                        "win_rate_pct": win_rate,
                                        "profit_factor": pf,
                                        "avg_pnl_pct": avg_pnl,
                                        "total_pnl_units": total_pnl,
                                        "target": target,
                                        "stop": stop,
                                        "price15_th": price15_th,
                                        "oi15_th": oi15_th,
                                        "price5_th": price5_th,
                                        "oi5_th": oi5_th,
                                        "price30_th": price30_th,
                                        "oi30_th": oi30_th,
                                        "cooldown": cooldown,
                                        "short_trades": (trades_df["decision"] == "SHORT").sum(),
                                        "long_trades": (trades_df["decision"] == "LONG").sum(),
                                        "best_trade": trades_df["pnl_pct"].max(),
                                        "worst_trade": trades_df["pnl_pct"].min()
                                    })

backtest = pd.DataFrame(backtest_rows)

if backtest.empty:
    print("No se encontraron configuraciones suficientes.")
    raise SystemExit

# Filtro de robustez mínimo
robust = backtest[
    (backtest["trades"] >= 40) &
    (backtest["profit_factor"] >= 1.3) &
    (backtest["avg_pnl_pct"] > 0)
].copy()

if robust.empty:
    robust = backtest.copy()

robust = robust.sort_values(
    ["profit_factor", "avg_pnl_pct", "trades"],
    ascending=[False, False, False]
)

best = robust.iloc[0]

# ============================================================
# REGENERATE BEST SIGNALS
# ============================================================

best_signals = generate_signals(
    df,
    best["price15_th"],
    best["oi15_th"],
    best["price5_th"],
    best["oi5_th"],
    best["price30_th"],
    best["oi30_th"],
    int(best["cooldown"])
)

best_signals.to_csv(OUT_SIGNALS, index=False)
robust.to_csv(OUT_BACKTEST, index=False)

# ============================================================
# CURRENT SIGNAL
# ============================================================

current = best_signals.tail(1).copy()

if current.empty:
    current_report = pd.DataFrame([{
        "timestamp": df.index[-1],
        "symbol": SYMBOL,
        "decision": "NO_TRADE",
        "setup": "NONE",
        "confidence": 0,
        "price": df["mark_price"].iloc[-1],
        "entry": np.nan,
        "stop": np.nan,
        "target_1": np.nan,
        "target_2": np.nan,
        "reasons": "No signal"
    }])
else:
    sig = current.iloc[-1]
    entry = sig["price"]

    if sig["decision"] == "SHORT":
        stop_price = entry * (1 + best["stop"] / 100)
        target_1 = entry * (1 - 0.5 / 100)
        target_2 = entry * (1 - best["target"] / 100)

    else:
        stop_price = entry * (1 - best["stop"] / 100)
        target_1 = entry * (1 + 0.5 / 100)
        target_2 = entry * (1 + best["target"] / 100)

    current_report = pd.DataFrame([{
        "timestamp": sig["timestamp"],
        "symbol": SYMBOL,
        "decision": sig["decision"],
        "setup": sig["setup"],
        "confidence": sig["confidence"],
        "price": entry,
        "entry": entry,
        "stop": stop_price,
        "target_1": target_1,
        "target_2": target_2,
        "best_pf": best["profit_factor"],
        "best_win_rate": best["win_rate_pct"],
        "best_trades": best["trades"],
        "reasons": sig["reasons"]
    }])

current_report.to_csv(OUT_CURRENT, index=False)

# ============================================================
# OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("MARKET OPPORTUNITY ENGINE v2")
print("=" * 70)

print(f"Archivos leídos: {len(FILES)}")
print(f"Filas 1m: {len(df)}")

print("\nMEJOR CONFIGURACIÓN")
print(best.to_string())

print("\nTOP 20 CONFIGURACIONES")
print(robust.head(20).to_string(index=False))

print("\nÚLTIMAS 20 SEÑALES DE LA MEJOR CONFIG")
print(best_signals.tail(20).to_string(index=False))

print("\nSEÑAL ACTUAL / ÚLTIMA SEÑAL")
print(current_report.to_string(index=False))

print("\nArchivos generados:")
print(OUT_BACKTEST)
print(OUT_SIGNALS)
print(OUT_CURRENT)