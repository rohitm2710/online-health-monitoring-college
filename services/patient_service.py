from __future__ import annotations

from datetime import datetime, timedelta

from db import get_conn
from services.alerts import evaluate
from services.vitals_service import get_readings


def get_patient(patient_id: int) -> dict:
    with get_conn() as conn:
        return dict(conn.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone())


def report_summary(patient_id: int) -> dict:
    readings = get_readings(patient_id, datetime.now() - timedelta(days=7))
    if not readings:
        return {"count": 0, "abnormal": 0}
    return {
        "count": len(readings),
        "abnormal": sum(bool(evaluate(row)) for row in readings),
        "avg_hr": round(sum(r["heart_rate"] for r in readings) / len(readings), 1),
        "avg_spo2": round(sum(r["spo2"] for r in readings) / len(readings), 1),
        "avg_temp": round(sum(r["temp_centi"] for r in readings) / len(readings) / 100, 1),
    }
