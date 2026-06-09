import pandas as pd
import glob
import os
import re

# =====================================
# CONFIG
# =====================================

TRADE_FILES_PATTERN = "data/Binance-Futures-Trade-History*.csv"

# =====================================
# HELPERS
# =====================================

def parse_fee(value):
    if pd.isna(value):
        return 0.0
    match = re.search(r"-?\d+\.?\d*", str(value))
    return float(match.group()) if match else 0.0

def parse_time(value):
    return pd.to_datetime(value, format="%y-%m-%d %H:%M:%S", errors="coerce")

# =====================================
# CARGA ARCHIVOS
# =====================================

files = glob.glob(TRADE_FILES_PATTERN)

if not files:
    raise FileNotFoundError(
        "No encontré archivos Trade History en data/. "
        "Subí los CSV con nombre Binance-Futures-Trade-History..."
    )

dfs = []

for file in files:
    df = pd.read_csv(file)
    df["source_file"] = os.path.basename(file)
    dfs.append(df)

raw = pd.concat(dfs, ignore_index=True)

# =====================================
# LIMPIEZA
# =====================================

raw["Time"] = raw["Time"].apply(parse_time)
raw["Price"] = pd.to_numeric(raw["Price"], errors="coerce")
raw["Quantity"] = pd.to_numeric(raw["Quantity"], errors="coerce")
raw["Amount"] = pd.to_numeric(raw["Amount"], errors="coerce")
raw["Realized Profit"] = pd.to_numeric(raw["Realized Profit"], errors="coerce").fillna(0)
raw["fee_value"] = raw["Fee"].apply(parse_fee)

raw = raw.dropna(subset=["Time", "Symbol", "Side", "Price", "Quantity"])
raw = raw.sort_values("Time").reset_index(drop=True)

raw.to_csv("reports/raw_trade_history_clean.csv", index=False)

# =====================================
# RECONSTRUCCIÓN APROXIMADA DE TRADES
# =====================================

closed_trades = []

for symbol, df in raw.groupby("Symbol"):

    df = df.sort_values("Time").reset_index(drop=True)

    position_qty = 0.0
    entry_value = 0.0
    entry_time = None
    entry_price = None
    direction = None

    trade_realized = 0.0
    trade_fees = 0.0
    trade_rows = 0

    for _, row in df.iterrows():

        side = row["Side"]
        qty = float(row["Quantity"])
        price = float(row["Price"])
        realized = float(row["Realized Profit"])
        fee = float(row["fee_value"])
        time = row["Time"]

        signed_qty = qty if side == "BUY" else -qty

        # Si no hay posición abierta
        if position_qty == 0:
            position_qty = signed_qty
            entry_value = abs(qty * price)
            entry_time = time
            entry_price = price
            direction = "LONG" if position_qty > 0 else "SHORT"
            trade_realized = realized
            trade_fees = fee
            trade_rows = 1
            continue

        # Misma dirección: aumentamos posición
        if (position_qty > 0 and signed_qty > 0) or (position_qty < 0 and signed_qty < 0):
            old_abs_qty = abs(position_qty)
            new_abs_qty = old_abs_qty + qty

            entry_price = (
                (entry_price * old_abs_qty) + (price * qty)
            ) / new_abs_qty

            position_qty += signed_qty
            entry_value += abs(qty * price)
            trade_realized += realized
            trade_fees += fee
            trade_rows += 1
            continue

        # Dirección contraria: cerramos parcial o total
        closing_qty = min(abs(position_qty), qty)

        trade_realized += realized
        trade_fees += fee
        trade_rows += 1

        remaining_position_abs = abs(position_qty) - closing_qty

        # Cierre total o flip
        if qty >= abs(position_qty):

            exit_time = time
            exit_price = price

            duration_minutes = (exit_time - entry_time).total_seconds() / 60

            net_pnl = trade_realized - trade_fees

            closed_trades.append({
                "symbol": symbol,
                "direction": direction,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "duration_minutes": duration_minutes,
                "gross_pnl": trade_realized,
                "fees": trade_fees,
                "net_pnl": net_pnl,
                "rows_used": trade_rows,
            })

            leftover_qty = qty - abs(position_qty)

            # Si hubo flip, abrimos nueva posición con sobrante
            if leftover_qty > 0:
                position_qty = leftover_qty if side == "BUY" else -leftover_qty
                entry_value = abs(leftover_qty * price)
                entry_time = time
                entry_price = price
                direction = "LONG" if position_qty > 0 else "SHORT"
                trade_realized = 0.0
                trade_fees = 0.0
                trade_rows = 0
            else:
                position_qty = 0.0
                entry_value = 0.0
                entry_time = None
                entry_price = None
                direction = None
                trade_realized = 0.0
                trade_fees = 0.0
                trade_rows = 0

        else:
            # Cierre parcial
            position_qty += signed_qty

# =====================================
# DATAFRAME FINAL
# =====================================

trades = pd.DataFrame(closed_trades)

if trades.empty:
    raise ValueError("No pude reconstruir trades cerrados con estos archivos.")

trades["result"] = trades["net_pnl"].apply(lambda x: "WIN" if x > 0 else "LOSS")
trades["duration_hours"] = trades["duration_minutes"] / 60

trades.to_csv("reports/trade_audit.csv", index=False)

# =====================================
# RESÚMENES
# =====================================

summary = pd.DataFrame([{
    "total_trades": len(trades),
    "wins": (trades["net_pnl"] > 0).sum(),
    "losses": (trades["net_pnl"] <= 0).sum(),
    "win_rate_pct": (trades["net_pnl"] > 0).mean() * 100,
    "total_net_pnl": trades["net_pnl"].sum(),
    "avg_win": trades.loc[trades["net_pnl"] > 0, "net_pnl"].mean(),
    "avg_loss": trades.loc[trades["net_pnl"] <= 0, "net_pnl"].mean(),
    "best_trade": trades["net_pnl"].max(),
    "worst_trade": trades["net_pnl"].min(),
    "avg_duration_hours": trades["duration_hours"].mean(),
}])

summary.to_csv("reports/trade_audit_summary.csv", index=False)

by_symbol = trades.groupby("symbol").agg(
    trades=("net_pnl", "count"),
    win_rate_pct=("net_pnl", lambda x: (x > 0).mean() * 100),
    total_net_pnl=("net_pnl", "sum"),
    avg_pnl=("net_pnl", "mean"),
    best_trade=("net_pnl", "max"),
    worst_trade=("net_pnl", "min"),
    avg_duration_hours=("duration_hours", "mean"),
).reset_index().sort_values("total_net_pnl", ascending=False)

by_symbol.to_csv("reports/trade_audit_by_symbol.csv", index=False)

by_direction = trades.groupby("direction").agg(
    trades=("net_pnl", "count"),
    win_rate_pct=("net_pnl", lambda x: (x > 0).mean() * 100),
    total_net_pnl=("net_pnl", "sum"),
    avg_pnl=("net_pnl", "mean"),
    best_trade=("net_pnl", "max"),
    worst_trade=("net_pnl", "min"),
).reset_index().sort_values("total_net_pnl", ascending=False)

by_direction.to_csv("reports/trade_audit_by_direction.csv", index=False)

# =====================================
# OUTPUT
# =====================================

print("\n" + "=" * 70)
print("TRADE AUDIT ENGINE v0.1")
print("=" * 70)

print(f"Archivos leídos: {len(files)}")
print(f"Filas raw: {len(raw)}")
print(f"Trades reconstruidos: {len(trades)}")

print("\nRESUMEN GENERAL")
print(summary.to_string(index=False))

print("\nPOR SÍMBOLO")
print(by_symbol.to_string(index=False))

print("\nPOR DIRECCIÓN")
print(by_direction.to_string(index=False))

print("\nTOP 10 MEJORES TRADES")
print(
    trades.sort_values("net_pnl", ascending=False)
    .head(10)[["symbol", "direction", "entry_time", "exit_time", "entry_price", "exit_price", "net_pnl", "duration_hours"]]
    .to_string(index=False)
)

print("\nTOP 10 PEORES TRADES")
print(
    trades.sort_values("net_pnl", ascending=True)
    .head(10)[["symbol", "direction", "entry_time", "exit_time", "entry_price", "exit_price", "net_pnl", "duration_hours"]]
    .to_string(index=False)
)

print("\nArchivos generados:")
print("reports/trade_audit.csv")
print("reports/trade_audit_summary.csv")
print("reports/trade_audit_by_symbol.csv")
print("reports/trade_audit_by_direction.csv")