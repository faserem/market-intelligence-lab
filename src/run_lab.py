import subprocess
import time

modules = [
    "src/btc_data_engine.py",
    "src/confluence_mapper.py",
    "src/reaction_detector.py",
    "src/confluence_score_engine.py",
    "src/zone_clustering_engine.py",
    "src/market_state_engine.py",
    "src/market_pressure_engine.py",
    "src/volatility_engine.py",
    "src/opportunity_engine.py",
    "src/transition_engine.py",
    "src/breakout_engine.py",
    "src/zone_position_engine.py",
    "src/funding_engine.py",
]

print("\n")
print("=" * 70)
print("MARKET INTELLIGENCE LAB")
print("=" * 70)

start_time = time.time()

for module in modules:

    print("\n")
    print("-" * 70)
    print(f"Ejecutando: {module}")
    print("-" * 70)

    result = subprocess.run(
        ["python", module],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.stderr:
        print("ERROR:")
        print(result.stderr)

elapsed = time.time() - start_time

print("\n")
print("=" * 70)
print("LAB FINALIZADO")
print("=" * 70)

print(f"Tiempo total: {elapsed:.2f} segundos")

print("\nReportes generados en:")
print("reports/")
