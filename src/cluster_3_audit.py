import pandas as pd

df = pd.read_csv("data/intraday/BTCUSDT_5m.csv")

clusters = pd.read_csv("reports/intraday_clusters.csv")

print(clusters)