import pandas as pd

events = pd.read_csv(
    "reports/intraday_cluster_events.csv"
)

cluster3 = events[
    events["cluster"] == 3
].copy()

cluster3 = cluster3.sort_values(
    "open_time"
)

cluster3.to_csv(
    "reports/cluster3_events.csv",
    index=False
)

print("\nEventos Cluster 3:")
print(len(cluster3))

print("\nPrimeros 20:")
print(
    cluster3[
        [
            "open_time",
            "close",
            "future_up_pct",
            "future_down_pct",
            "volume_ratio_20",
            "trades_ratio_20",
            "taker_buy_ratio"
        ]
    ].head(20).to_string(index=False)
)

print("\nArchivo generado:")
print("reports/cluster3_events.csv")
