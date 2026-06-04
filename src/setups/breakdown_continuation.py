import pandas as pd

# =====================================
# CARGA REPORTES
# =====================================

pressure = pd.read_csv(
    "reports/market_pressure_report.csv"
).iloc[0]

transition = pd.read_csv(
    "reports/transition_report.csv"
).iloc[0]

breakout = pd.read_csv(
    "reports/breakout_report.csv"
).iloc[0]

zone = pd.read_csv(
    "reports/zone_position_report.csv"
).iloc[0]

# =====================================
# SCORE
# =====================================

score = 0
notes = []

# -------------------------------------
# PRESSURE
# -------------------------------------

if pressure["pressure_state"] == "BEARISH":
    score += 25
    notes.append("Presión bajista confirmada.")

# -------------------------------------
# TRANSITION
# -------------------------------------

transition_score = float(
    transition["transition_score"]
)

if transition_score >= 60:
    score += 20
    notes.append(
        f"Transition fuerte ({transition_score})"
    )

elif transition_score >= 40:
    score += 10
    notes.append(
        f"Transition moderada ({transition_score})"
    )

# -------------------------------------
# BREAKOUT
# -------------------------------------

breakout_score = float(
    breakout["breakout_score"]
)

if breakout_score >= 80:
    score += 30
    notes.append(
        f"Breakout muy fuerte ({breakout_score})"
    )

elif breakout_score >= 60:
    score += 15
    notes.append(
        f"Breakout fuerte ({breakout_score})"
    )

# -------------------------------------
# MOMENTUM
# -------------------------------------

momentum_20 = float(
    breakout["momentum_20"]
)

if momentum_20 <= -10:
    score += 15
    notes.append(
        f"Momentum bajista fuerte ({momentum_20:.2f}%)"
    )

elif momentum_20 <= -5:
    score += 8
    notes.append(
        f"Momentum bajista moderado ({momentum_20:.2f}%)"
    )

# -------------------------------------
# ZONA
# -------------------------------------

zone_state = str(
    zone["zone_state"]
)

if zone_state == "LOWER_ZONE":
    score += 10
    notes.append(
        "Precio en LOWER_ZONE."
    )

elif zone_state == "MIDDLE_ZONE":
    score += 5
    notes.append(
        "Precio en MIDDLE_ZONE."
    )

# =====================================
# RESULTADO
# =====================================

score = min(100, score)

if score >= 80:
    setup_state = "SETUP ACTIVO"

elif score >= 60:
    setup_state = "SETUP INTERESANTE"

elif score >= 40:
    setup_state = "VIGILAR"

else:
    setup_state = "NO SETUP"

# =====================================
# EXPORT
# =====================================

report = pd.DataFrame([{
    "setup_name": "BREAKDOWN_CONTINUATION",
    "setup_score": score,
    "setup_state": setup_state,
    "transition_score": transition_score,
    "breakout_score": breakout_score,
    "momentum_20": momentum_20,
    "zone_state": zone_state,
    "notes": " | ".join(notes)
}])

report.to_csv(
    "reports/breakdown_continuation_report.csv",
    index=False
)

# =====================================
# OUTPUT
# =====================================

print("\n")
print("=" * 70)
print("BREAKDOWN CONTINUATION SETUP")
print("=" * 70)

print(f"Score: {score}/100")
print(f"Estado: {setup_state}")

print("\nComponentes:")

print(
    f"Transition: {transition_score}"
)

print(
    f"Breakout: {breakout_score}"
)

print(
    f"Momentum20: {momentum_20:.2f}%"
)

print(
    f"Zone: {zone_state}"
)

print("\nNotas:")

for n in notes:
    print(f"- {n}")

print("\nArchivo generado:")
print(
    "reports/breakdown_continuation_report.csv"
)