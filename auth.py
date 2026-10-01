from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3

from db import get_conn

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAC_RE = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$", re.IGNORECASE)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
        return secrets.compare_digest(actual, expected)
    except ValueError:
        return False


def _validate_common(name: str, email: str, password: str) -> None:
    if not name.strip() or not EMAIL_RE.fullmatch(email.strip()):
        raise ValueError("Enter a valid name and email address.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")


def register_patient(full_name: str, dob: str, email: str, password: str) -> int:
    _validate_common(full_name, email, password)
    if dob > __import__("datetime").date.today().isoformat():
        raise ValueError("Date of birth cannot be in the future.")
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO patients (full_name, dob, email, password_hash) VALUES (?, ?, ?, ?)",
                (full_name.strip(), dob, email.strip().lower(), hash_password(password)),
            )
            return int(cur.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ValueError("That email is already registered.") from exc


def register_doctor(full_name: str, license_no: str, speciality: str, email: str, password: str, consult_fee: float) -> int:
    _validate_common(full_name, email, password)
    if not license_no.strip() or not speciality.strip() or consult_fee < 0:
        raise ValueError("Complete every field with valid values.")
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO doctors (full_name, license_no, speciality, email, password_hash, consult_fee) VALUES (?, ?, ?, ?, ?, ?)",
                (full_name.strip(), license_no.strip(), speciality.strip(), email.strip().lower(), hash_password(password), consult_fee),
            )
            return int(cur.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ValueError("That email or license number is already registered.") from exc


def login_patient(email: str, password: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM patients WHERE email = ?", (email.strip().lower(),)).fetchone()
    return dict(row) if row and verify_password(password, row["password_hash"]) else None


def login_doctor(email: str, password: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM doctors WHERE email = ? AND is_verified = 1", (email.strip().lower(),)).fetchone()
    return dict(row) if row and verify_password(password, row["password_hash"]) else None


def login_sensor(mac: str, passcode: str) -> dict | None:
    if not MAC_RE.fullmatch(mac.strip()):
        return None
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM patients WHERE sensor_mac = ?", (mac.strip().upper(),)).fetchone()
    expected = __import__("os").getenv("OHMS_SENSOR_PASS", "sensor123")
    return dict(row) if row and secrets.compare_digest(passcode, expected) else None
