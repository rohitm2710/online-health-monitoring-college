from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).with_name("ohms.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS patients (
                patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                dob DATE NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                sensor_mac TEXT UNIQUE,
                balance NUMERIC NOT NULL DEFAULT 0 CHECK (balance >= 0),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS doctors (
                doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                license_no TEXT NOT NULL UNIQUE,
                speciality TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                consult_fee NUMERIC NOT NULL DEFAULT 0 CHECK (consult_fee >= 0),
                is_verified BOOLEAN NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS vitals_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                heart_rate INTEGER NOT NULL CHECK (heart_rate BETWEEN 0 AND 255),
                spo2 INTEGER NOT NULL CHECK (spo2 BETWEEN 0 AND 100),
                systolic_bp INTEGER NOT NULL CHECK (systolic_bp BETWEEN 0 AND 400),
                diastolic_bp INTEGER NOT NULL CHECK (diastolic_bp BETWEEN 0 AND 400),
                temp_centi INTEGER NOT NULL CHECK (temp_centi BETWEEN 0 AND 65535),
                recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_vitals_patient_time ON vitals_log(patient_id, recorded_at DESC);
            CREATE TABLE IF NOT EXISTS consultations (
                consult_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                doctor_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','ACCEPTED','REJECTED','COMPLETED','SUGGESTED')),
                scheduled_at TIMESTAMP NOT NULL,
                payment_status TEXT NOT NULL DEFAULT 'UNPAID' CHECK (payment_status IN ('UNPAID','PAID','REFUNDED')),
                fee_charged NUMERIC NOT NULL DEFAULT 0,
                prescription TEXT,
                advice_note TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id) ON DELETE RESTRICT
            );
            """
        )


def seed_demo_data() -> None:
    from auth import hash_password

    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM patients LIMIT 1").fetchone():
            return
        doctor_password = hash_password("doctor123")
        patient_password = hash_password("patient123")
        conn.execute(
            "INSERT INTO doctors (full_name, license_no, speciality, email, password_hash, consult_fee, is_verified) VALUES (?, ?, ?, ?, ?, ?, 1)",
            ("Dr. Maya Rao", "MED-1001", "Cardiology", "maya@ohms.local", doctor_password, 45.0),
        )
        conn.execute(
            "INSERT INTO doctors (full_name, license_no, speciality, email, password_hash, consult_fee, is_verified) VALUES (?, ?, ?, ?, ?, ?, 1)",
            ("Dr. Liam Chen", "MED-1002", "Internal Medicine", "liam@ohms.local", doctor_password, 35.0),
        )
        conn.execute(
            "INSERT INTO patients (full_name, dob, email, password_hash, sensor_mac, balance) VALUES (?, ?, ?, ?, ?, ?)",
            ("Ava Morgan", "1994-06-12", "ava@ohms.local", patient_password, "AA:BB:CC:DD:EE:01", 100.0),
        )
        conn.execute(
            "INSERT INTO patients (full_name, dob, email, password_hash, sensor_mac, balance) VALUES (?, ?, ?, ?, ?, ?)",
            ("Noah Williams", "1988-11-03", "noah@ohms.local", patient_password, None, 25.0),
        )
        patient_id = conn.execute("SELECT patient_id FROM patients WHERE email = ?", ("ava@ohms.local",)).fetchone()[0]
        now = datetime.now()
        readings = [(72, 98, 120, 78, 36.6), (116, 91, 148, 96, 38.4), (68, 97, 118, 76, 36.7)]
        for offset, reading in enumerate(readings):
            conn.execute(
                "INSERT INTO vitals_log (patient_id, heart_rate, spo2, systolic_bp, diastolic_bp, temp_centi, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (patient_id, *reading[:4], round(reading[4] * 100), now - timedelta(days=2 - offset)),
            )


if __name__ == "__main__":
    init_db()
    if os.getenv("OHMS_SEED_DEMO", "0") == "1":
        seed_demo_data()
