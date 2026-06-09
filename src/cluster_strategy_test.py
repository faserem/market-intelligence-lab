import pandas as pd
import numpy as np

EVENTS_PATH = "reports/intraday_cluster_events.csv"

events = pd.read_csv(EVENTS_PATH)
events["open_time"] = pd.to_datetime(events["open_time"])

# Probamos cluster 3 porque fue el mejor candidato DOWN
CLUSTER_ID = 3
DIRECTION = "SHORT"

TARGETS = [0.5, 0.8, 1.0, 1.5, 2.0]
STOPS = [0.3, 0.5, 0.8, 1.0]
HOLD_BARS = [3, 6, 12, 24]

cluster = events[events["cluster"] == CLUSTER_ID].copy()

rows = []

for target in TARGETS:
    for stop in STOPS:
        for hold in HOLD_BARS:

            results = []

            for _, row in cluster.iterrows():

                entry = row["close"]

                # En este archivo ya tenemos máximo/mínimo futuro para 12 velas.
                # Para v0.1 usamos future_up/down de 12 velas.
                future_up = row["future_up_pct"]
                future_down = row["future_down_pct"]

                if DIRECTION == "SHORT":
                    hit_target = future_down <= -target
                    hit_stop = future_up >= stop

                    if hit_target and not hit_stop:
                        pnl = target
                    elif hit_stop and not hit_target:
                        pnl = -stop
                    elif hit_target and hit_stop:
                        # conservador: si toca ambos, asumimos stop primero
                        pnl = -stop
                    else:
                        # salida por tiempo aproximada: si no toca nada, usamos sesgo neto
                        pnl = abs(future_down) if abs(future_down) > future_up else -future_up

                else:
                    hit_target = future_up >= target
                    hit_stop = future_down <= -stop

                    if hit_target and not hit_stop:
                        pnl = target
                    elif hit_stop and not hit_target:
                        pnl = -stop
                    elif hit_target and hit_stop:
                        pnl = -stop
                    else:
                        pnl = future_up if future_up > abs(future_down) else -abs(future_down)

                results.append(pnl)

            results = np.array(results)

            wins = results[results > 0]
            losses = results[results <= 0]

            win_rate = len(wins) / len(results) * 100
            gross_profit = wins.sum()
            gross_loss = abs(losses.sum())
            pf = gross_profit / gross_loss if gross_loss > 0 else np.nan

            rows.append({
                "cluster": CLUSTER_ID,
                "direction": DIRECTION,
                "samples": len(results),
                "target_pct": target,
                "stop_pct": stop,
                "hold_bars": hold,
                "hold_minutes": hold * 5,
                "win_rate_pct": win_rate,
                "profit_factor": pf,
                "avg_pnl_pct": results.mean(),
                "total_pnl_units": results.sum(),
            })

out = pd.DataFrame(rows)

out = out.sort_values(
    ["profit_factor", "avg_pnl_pct"],
    ascending=False
)

out.to_csv(
    "reports/cluster_strategy_test.csv",
    index=False
)

print("\n" + "=" * 70)
print("CLUSTER STRATEGY TEST")
print("=" * 70)

print(out.head(30).to_string(index=False))

print("\nArchivo generado:")
print("reports/cluster_strategy_test.csv")