import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

DATA_PATH = "data/intraday/BTCUSDT_5m.csv"

df = pd.read_csv(DATA_PATH)
df["open_time"] = pd.to_datetime(df["open_time"])

for col in df.columns:
    if col not in ["open_time", "close_time"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna().reset_index(drop=True)

FORWARD = 12

df["future_high"] = (
    df["high"]
    .shift(-1)
    .rolling(FORWARD)
    .max()
    .shift(-(FORWARD - 1))
)

df["future_low"] = (
    df["low"]
    .shift(-1)
    .rolling(FORWARD)
    .min()
    .shift(-(FORWARD - 1))
)

df["future_up_pct"] = ((df["future_high"] - df["close"]) / df["close"]) * 100
df["future_down_pct"] = ((df["future_low"] - df["close"]) / df["close"]) * 100

events = df[
    (df["future_up_pct"] >= 2)
    |
    (df["future_down_pct"] <= -2)
].copy()

features = [
    "volume_ratio_20",
    "trades_ratio_20",
    "taker_buy_ratio",
    "body_pct",
    "range_pct"
]

X = events[features].fillna(0)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

kmeans = KMeans(
    n_clusters=5,
    random_state=42,
    n_init=10
)

events["cluster"] = kmeans.fit_predict(X_scaled)

# Exportar eventos completos con cluster
events.to_csv(
    "reports/intraday_cluster_events.csv",
    index=False
)

summary = []

for cluster in sorted(events["cluster"].unique()):

    subset = events[events["cluster"] == cluster]

    up2 = (subset["future_up_pct"] >= 2).mean() * 100
    down2 = (subset["future_down_pct"] <= -2).mean() * 100

    up3 = (subset["future_up_pct"] >= 3).mean() * 100
    down3 = (subset["future_down_pct"] <= -3).mean() * 100

    summary.append({
        "cluster": cluster,
        "samples": len(subset),

        "up_2_rate_pct": up2,
        "down_2_rate_pct": down2,
        "up_3_rate_pct": up3,
        "down_3_rate_pct": down3,

        "edge_up_2": up2 - down2,
        "edge_down_2": down2 - up2,

        "avg_future_up_pct": subset["future_up_pct"].mean(),
        "avg_future_down_pct": subset["future_down_pct"].mean(),

        "avg_volume_ratio": subset["volume_ratio_20"].mean(),
        "avg_trades_ratio": subset["trades_ratio_20"].mean(),
        "avg_taker_buy_ratio": subset["taker_buy_ratio"].mean(),
        "avg_body_pct": subset["body_pct"].mean(),
        "avg_range_pct": subset["range_pct"].mean()
    })

summary = pd.DataFrame(summary)

summary.to_csv(
    "reports/intraday_clusters.csv",
    index=False
)

print("\n" + "="*70)
print("INTRADAY CLUSTER MINER v0.2")
print("="*70)

print(summary.to_string(index=False))

print("\nArchivos generados:")
print("reports/intraday_clusters.csv")
print("reports/intraday_cluster_events.csv")