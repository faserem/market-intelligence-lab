import pandas as pd
import subprocess
import shutil
import os
import time

# =====================================
# CONFIG
# =====================================

ANALYSIS_DATE = "2026-06-01"

# Precio real de entrada del trade a auditar.
# Usar None si querés analizar sólo el cierre del día.
MANUAL_PRICE = 68696.0

ORIGINAL_DATA = "data/btc_daily.csv"
BACKUP_DATA = "data/btc_daily_live_backup.csv"

BACKTEST_REPORT_DIR = f"reports/backtest_{ANALYSIS_DATE}"

modules = [
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
]

# =====================================
# INICIO
# =====================================

print("\n" + "=" * 70)
print("BACKTEST SNAPSHOT RUNNER")
print("=" * 70)

print(f"Fecha de análisis: {ANALYSIS_DATE}")
print(f"Precio manual auditado: {MANUAL_PRICE}")
print("Modo: usa solamente datos disponibles hasta esa fecha.")
print("Nota: para una entrada intradiaria, con datos diarios analizamos hasta el día anterior.")

start_time = time.time()

# =====================================
# BACKUP DATA ACTUAL
# =====================================

if not os.path.exists(ORIGINAL_DATA):
    raise FileNotFoundError("No existe data/btc_daily.csv")

shutil.copy(ORIGINAL_DATA, BACKUP_DATA)

# =====================================
# CREAR SNAPSHOT
# =====================================

df = pd.read_csv(ORIGINAL_DATA)
df["Date"] = pd.to_datetime(df["Date"])

snapshot = df[df["Date"] <= ANALYSIS_DATE].copy()

snapshot.to_csv(ORIGINAL_DATA, index=False)

print(f"\nFilas originales: {len(df)}")
print(f"Filas snapshot: {len(snapshot)}")
print(f"Última fecha usada: {snapshot['Date'].iloc[-1]}")

# =====================================
# CREAR CONFIG DE BACKTEST
# =====================================

config = pd.DataFrame([{
    "analysis_date": ANALYSIS_DATE,
    "manual_price": MANUAL_PRICE
}])

config.to_csv("reports/backtest_config.csv", index=False)

# =====================================
# CORRER MÓDULOS
# =====================================

try:
    for module in modules:

        print("\n" + "-" * 70)
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

    # =====================================
    # GUARDAR REPORTES BACKTEST
    # =====================================

    os.makedirs(BACKTEST_REPORT_DIR, exist_ok=True)

    for file in os.listdir("reports"):
        if file.endswith(".csv"):
            src = os.path.join("reports", file)
            dst = os.path.join(BACKTEST_REPORT_DIR, file)
            shutil.copy(src, dst)

    print("\nReportes históricos guardados en:")
    print(BACKTEST_REPORT_DIR)

finally:
    # =====================================
    # RESTAURAR DATA ORIGINAL
    # =====================================

    shutil.copy(BACKUP_DATA, ORIGINAL_DATA)

    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("BACKTEST FINALIZADO")
    print("=" * 70)

    print("Data original restaurada.")
    print(f"Tiempo total: {elapsed:.2f} segundos")