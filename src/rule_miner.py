import pandas as pd

df = pd.read_csv("data/intraday/BTCUSDT_5m.csv")

df["future_high"] = (
    df["high"]
    .shift(-1)
    .rolling(12)
    .max()
    .shift(-11)
)

df["future_low"] = (
    df["low"]
    .shift(-1)
    .rolling(12)
    .min()
    .shift(-11)
)

df["future_up_pct"] = (
    (df["future_high"] - df["close"])
    / df["close"]
) * 100

df["future_down_pct"] = (
    (df["future_low"] - df["close"])
    / df["close"]
) * 100

rules = []

for vol in [2, 3, 4]:

    for trades in [2, 3, 4]:

        for buy_ratio in [0.45, 0.48, 0.50]:

            subset = df[
                (df["volume_ratio_20"] >= vol)
                &
                (df["trades_ratio_20"] >= trades)
                &
                (df["taker_buy_ratio"] <= buy_ratio)
            ]

            if len(subset) < 20:
                continue

            down2 = (
                subset["future_down_pct"] <= -2
            ).mean() * 100

            down3 = (
                subset["future_down_pct"] <= -3
            ).mean() * 100

            rules.append({
                "volume": vol,
                "trades": trades,
                "buy_ratio": buy_ratio,
                "samples": len(subset),
                "down2_rate": down2,
                "down3_rate": down3
            })

rules = pd.DataFrame(rules)

rules = rules.sort_values(
    ["down2_rate", "samples"],
    ascending=False
)

rules.to_csv(
    "reports/rule_miner.csv",
    index=False
)

print(rules.head(30).to_string(index=False))