import pandas as pd
import numpy as np

DATA_PATH = "data/btc_daily.csv"

SWING_LOOKBACK = 5

df = pd.read_csv(DATA_PATH)

df["Date"] = pd.to_datetime(df["Date"])

for col in ["Open", "High", "Low", "Close", "Volume"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna().sort_values("Date").reset_index(drop=True)

current_price = df["Close"].iloc[-1]
current_date = df["Date"].iloc[-1]

# ======================================
# DETECCIÓN DE SWING HIGHS / LOWS
# ======================================

df["swing_high"] = False
df["swing_low"] = False

for i in range(SWING_LOOKBACK, len(df) - SWING_LOOKBACK):

    current_high = df.loc[i, "High"]
    current_low = df.loc[i, "Low"]

    left_highs = df.loc[i-SWING_LOOKBACK:i-1, "High"]
    right_highs = df.loc[i+1:i+SWING_LOOKBACK, "High"]

    left_lows = df.loc[i-SWING_LOOKBACK:i-1, "Low"]
    right_lows = df.loc[i+1:i+SWING_LOOKBACK, "Low"]

    if current_high > left_highs.max() and current_high > right_highs.max():
        df.loc[i, "swing_high"] = True

    if current_low < left_lows.min() and current_low < right_lows.min():
        df.loc[i, "swing_low"] = True

# ======================================
# EXTRAER SWINGS
# ======================================

highs = df[df["swing_high"]][["Date", "High"]].copy().sort_values("Date")
lows = df[df["swing_low"]][["Date", "Low"]].copy().sort_values("Date")

highs["structure"] = ""

for i in range(1, len(highs)):
    prev_high = highs.iloc[i-1]["High"]
    current_high = highs.iloc[i]["High"]

    if current_high > prev_high:
        highs.iloc[i, highs.columns.get_loc("structure")] = "HH"
    else:
        highs.iloc[i, highs.columns.get_loc("structure")] = "LH"

lows["structure"] = ""

for i in range(1, len(lows)):
    prev_low = lows.iloc[i-1]["Low"]
    current_low = lows.iloc[i]["Low"]

    if current_low > prev_low:
        lows.iloc[i, lows.columns.get_loc("structure")] = "HL"
    else:
        lows.iloc[i, lows.columns.get_loc("structure")] = "LL"

# ======================================
# MERGE EVENTOS
# ======================================

events = []

for _, row in highs.iterrows():
    events.append({
        "Date": row["Date"],
        "Type": row["structure"],
        "Price": row["High"],
        "SwingKind": "HIGH"
    })

for _, row in lows.iterrows():
    events.append({
        "Date": row["Date"],
        "Type": row["structure"],
        "Price": row["Low"],
        "SwingKind": "LOW"
    })

events = pd.DataFrame(events).sort_values("Date").reset_index(drop=True)

# ======================================
# BOS / CHOCH SIMPLE
# ======================================

events["event"] = ""

trend = "UNKNOWN"

for i in range(1, len(events)):

    current = events.iloc[i]["Type"]

    if current in ["HH", "HL"]:

        if trend == "BEARISH":
            events.iloc[i, events.columns.get_loc("event")] = "CHOCH_BULLISH"

        trend = "BULLISH"

    elif current in ["LH", "LL"]:

        if trend == "BULLISH":
            events.iloc[i, events.columns.get_loc("event")] = "CHOCH_BEARISH"

        trend = "BEARISH"

# ======================================
# ÚLTIMOS SWINGS CONFIRMADOS
# ======================================

last_swing_high = highs.tail(1).iloc[0] if len(highs) > 0 else None
last_swing_low = lows.tail(1).iloc[0] if len(lows) > 0 else None

last_high_price = last_swing_high["High"] if last_swing_high is not None else None
last_high_date = last_swing_high["Date"] if last_swing_high is not None else None

last_low_price = last_swing_low["Low"] if last_swing_low is not None else None
last_low_date = last_swing_low["Date"] if last_swing_low is not None else None

# ======================================
# LIVE STRUCTURE SIGNAL
# ======================================

if last_low_price is not None and current_price < last_low_price:
    live_structure_signal = "LIVE_BREAKDOWN"

elif last_high_price is not None and current_price > last_high_price:
    live_structure_signal = "LIVE_BREAKOUT"

else:
    live_structure_signal = "NO_LIVE_BREAK"

# Distancias
if last_low_price is not None:
    dist_to_last_low_pct = ((current_price - last_low_price) / current_price) * 100
else:
    dist_to_last_low_pct = None

if last_high_price is not None:
    dist_to_last_high_pct = ((last_high_price - current_price) / current_price) * 100
else:
    dist_to_last_high_pct = None

# ======================================
# ESTADO RECIENTE
# ======================================

last_events = events.tail(12)

bullish_count = (
    (last_events["Type"] == "HH").sum()
    +
    (last_events["Type"] == "HL").sum()
)

bearish_count = (
    (last_events["Type"] == "LH").sum()
    +
    (last_events["Type"] == "LL").sum()
)

if live_structure_signal == "LIVE_BREAKDOWN":
    structure_state = "LIVE_BEARISH_BREAKDOWN"

elif live_structure_signal == "LIVE_BREAKOUT":
    structure_state = "LIVE_BULLISH_BREAKOUT"

elif bullish_count > bearish_count:
    structure_state = "BULLISH_STRUCTURE"

elif bearish_count > bullish_count:
    structure_state = "BEARISH_STRUCTURE"

else:
    structure_state = "NEUTRAL_STRUCTURE"

# ======================================
# EXPORT
# ======================================

events.to_csv(
    "reports/market_structure_events.csv",
    index=False
)

summary = pd.DataFrame([{
    "current_date": current_date,
    "current_price": current_price,
    "last_swing_high_date": last_high_date,
    "last_swing_high_price": last_high_price,
    "last_swing_low_date": last_low_date,
    "last_swing_low_price": last_low_price,
    "dist_to_last_high_pct": dist_to_last_high_pct,
    "dist_to_last_low_pct": dist_to_last_low_pct,
    "live_structure_signal": live_structure_signal,
    "bullish_events_last_12": bullish_count,
    "bearish_events_last_12": bearish_count,
    "structure_state": structure_state
}])

summary.to_csv(
    "reports/market_structure_report.csv",
    index=False
)

# ======================================
# OUTPUT
# ======================================

print("\n" + "="*70)
print("MARKET STRUCTURE ENGINE v0.2")
print("="*70)

print(f"Fecha actual: {current_date}")
print(f"Precio actual: {current_price:,.2f}")

print("\nÚltimo swing high confirmado:")
print(f"{last_high_date} | {last_high_price:,.2f}")

print("\nÚltimo swing low confirmado:")
print(f"{last_low_date} | {last_low_price:,.2f}")

print("\nLive signal:")
print(live_structure_signal)

print("\nEstructura detectada:")
print(structure_state)

print("\nÚltimos 12 eventos:")
print(last_events.to_string(index=False))

print("\nArchivos generados:")
print("reports/market_structure_events.csv")
print("reports/market_structure_report.csv")