from __future__ import annotations

import random
from datetime import datetime, timedelta

from db import get_conn


def add_reading(patient_id: int, hr: int, spo2: int, sys_bp: int, dia_bp: int, temp_c: float) -> int:
    if not (0 <= hr <= 255 and 0 <= spo2 <= 100 and 0 <= sys_bp <= 400 and 0 <= dia_bp <= 400 and 0 <= temp_c <= 655.35):
        raise ValueError("One or more readings are outside the sensor range.")
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO vitals_log (patient_id, heart_rate, spo2, systolic_bp, diastolic_bp, temp_centi) VALUES (?, ?, ?, ?, ?, ?)",
            (patient_id, hr, spo2, sys_bp, dia_bp, round(temp_c * 100)),
        )
        return int(cur.lastrowid)


def get_readings(patient_id: int, since: datetime | None = None) -> list[dict]:
    query = "SELECT * FROM vitals_log WHERE patient_id = ?"
    params: list = [patient_id]
    if since:
        query += " AND recorded_at >= ?"
        params.append(since.isoformat(sep=" "))
    query += " ORDER BY recorded_at DESC"
    with get_conn() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def random_reading() -> tuple[int, int, int, int, float]:
    return random.randint(62, 120), random.randint(90, 99), random.randint(105, 155), random.randint(62, 98), round(random.uniform(36.1, 38.5), 1)
