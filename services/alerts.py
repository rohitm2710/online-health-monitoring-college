from __future__ import annotations


def evaluate(reading: dict) -> list[str]:
    alerts = []
    if reading["heart_rate"] < 50 or reading["heart_rate"] > 110:
        alerts.append("Heart rate outside 50-110 bpm")
    if reading["spo2"] < 90:
        alerts.append("Critical SpO2 below 90%")
    elif reading["spo2"] < 94:
        alerts.append("SpO2 below 94%")
    if reading["systolic_bp"] > 140 or reading["systolic_bp"] < 90:
        alerts.append("Systolic blood pressure outside 90-140 mmHg")
    if reading["diastolic_bp"] > 90 or reading["diastolic_bp"] < 60:
        alerts.append("Diastolic blood pressure outside 60-90 mmHg")
    temperature = reading["temp_centi"] / 100
    if temperature > 38 or temperature < 35:
        alerts.append("Temperature outside 35.0-38.0 C")
    return alerts
