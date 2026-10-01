from __future__ import annotations

import re

from db import get_conn

MAC_RE = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$", re.IGNORECASE)


def list_unverified() -> list[dict]:
    with get_conn() as conn:
        return [dict(row) for row in conn.execute("SELECT doctor_id, full_name, license_no, speciality, email FROM doctors WHERE is_verified = 0 ORDER BY full_name").fetchall()]


def verify_doctor(doctor_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE doctors SET is_verified = 1 WHERE doctor_id = ?", (doctor_id,))


def list_patients() -> list[dict]:
    with get_conn() as conn:
        return [dict(row) for row in conn.execute("SELECT patient_id, full_name, email, sensor_mac FROM patients ORDER BY full_name").fetchall()]


def assign_sensor(patient_id: int, mac_or_none: str | None) -> None:
    mac = mac_or_none.strip().upper() if mac_or_none else None
    if mac and not MAC_RE.fullmatch(mac):
        raise ValueError("MAC must look like AA:BB:CC:DD:EE:FF.")
    with get_conn() as conn:
        try:
            conn.execute("UPDATE patients SET sensor_mac = ? WHERE patient_id = ?", (mac, patient_id))
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise ValueError("That sensor is already assigned.") from exc
            raise


def doctor_patients(doctor_id: int) -> list[dict]:
    with get_conn() as conn:
        return [dict(row) for row in conn.execute("""SELECT DISTINCT p.patient_id, p.full_name, p.email, p.sensor_mac
            FROM patients p JOIN consultations c ON c.patient_id = p.patient_id
            WHERE c.doctor_id = ? ORDER BY p.full_name""", (doctor_id,)).fetchall()]
