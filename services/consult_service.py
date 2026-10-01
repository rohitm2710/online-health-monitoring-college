from __future__ import annotations

from datetime import datetime

from db import get_conn


def list_doctors() -> list[dict]:
    with get_conn() as conn:
        return [dict(row) for row in conn.execute("SELECT doctor_id, full_name, speciality, consult_fee FROM doctors WHERE is_verified = 1 ORDER BY full_name").fetchall()]


def book_consult(patient_id: int, doctor_id: int, scheduled_at: str) -> int:
    try:
        when = datetime.fromisoformat(scheduled_at)
    except ValueError as exc:
        raise ValueError("Choose a valid appointment time.") from exc
    if when <= datetime.now():
        raise ValueError("Appointments must be in the future.")
    with get_conn() as conn:
        doctor = conn.execute("SELECT consult_fee FROM doctors WHERE doctor_id = ? AND is_verified = 1", (doctor_id,)).fetchone()
        if not doctor:
            raise ValueError("That doctor is unavailable.")
        cur = conn.execute("INSERT INTO consultations (patient_id, doctor_id, scheduled_at, fee_charged) VALUES (?, ?, ?, ?)", (patient_id, doctor_id, scheduled_at, doctor[0]))
        return int(cur.lastrowid)


def pay_consult(consult_id: int, patient_id: int) -> None:
    with get_conn() as conn:
        consult = conn.execute("SELECT patient_id, fee_charged, payment_status FROM consultations WHERE consult_id = ?", (consult_id,)).fetchone()
        if not consult or consult[0] != patient_id:
            raise ValueError("Consultation not found.")
        if consult[2] == "PAID":
            return
        balance = conn.execute("SELECT balance FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()[0]
        if balance < consult[1]:
            raise ValueError("Insufficient balance. Top up before paying.")
        conn.execute("UPDATE patients SET balance = balance - ? WHERE patient_id = ?", (consult[1], patient_id))
        conn.execute("UPDATE consultations SET payment_status = 'PAID' WHERE consult_id = ?", (consult_id,))


def respond(consult_id: int, doctor_id: int, accept: bool) -> None:
    with get_conn() as conn:
        row = conn.execute("SELECT patient_id, payment_status FROM consultations WHERE consult_id = ? AND doctor_id = ?", (consult_id, doctor_id)).fetchone()
        if not row:
            raise ValueError("Consultation not found.")
        if accept:
            conn.execute("UPDATE consultations SET status = 'ACCEPTED' WHERE consult_id = ?", (consult_id,))
        else:
            conn.execute("UPDATE consultations SET status = 'REJECTED', payment_status = CASE WHEN payment_status = 'PAID' THEN 'REFUNDED' ELSE payment_status END WHERE consult_id = ?", (consult_id,))
            if row[1] == "PAID":
                fee = conn.execute("SELECT fee_charged FROM consultations WHERE consult_id = ?", (consult_id,)).fetchone()[0]
                conn.execute("UPDATE patients SET balance = balance + ? WHERE patient_id = ?", (fee, row[0]))


def write_prescription(consult_id: int, doctor_id: int, text: str) -> None:
    if not text.strip():
        raise ValueError("Prescription cannot be empty.")
    with get_conn() as conn:
        conn.execute("UPDATE consultations SET prescription = ?, status = 'COMPLETED' WHERE consult_id = ? AND doctor_id = ?", (text.strip(), consult_id, doctor_id))


def suggest_consult(doctor_id: int, patient_id: int, note: str, scheduled_at: str) -> int:
    when = datetime.fromisoformat(scheduled_at)
    if when <= datetime.now():
        raise ValueError("Suggested appointments must be in the future.")
    with get_conn() as conn:
        doctor = conn.execute("SELECT consult_fee FROM doctors WHERE doctor_id = ?", (doctor_id,)).fetchone()
        cur = conn.execute("INSERT INTO consultations (patient_id, doctor_id, status, scheduled_at, fee_charged, advice_note) VALUES (?, ?, 'SUGGESTED', ?, ?, ?)", (patient_id, doctor_id, scheduled_at, doctor[0], note.strip()))
        return int(cur.lastrowid)


def topup(patient_id: int, amount: float) -> None:
    if amount <= 0:
        raise ValueError("Top-up amount must be positive.")
    with get_conn() as conn:
        conn.execute("UPDATE patients SET balance = balance + ? WHERE patient_id = ?", (amount, patient_id))


def patient_consultations(patient_id: int) -> list[dict]:
    with get_conn() as conn:
        return [dict(row) for row in conn.execute("""SELECT c.*, d.full_name AS doctor_name, d.speciality
            FROM consultations c JOIN doctors d ON d.doctor_id = c.doctor_id
            WHERE c.patient_id = ? ORDER BY c.created_at DESC""", (patient_id,)).fetchall()]


def doctor_consultations(doctor_id: int, status: str | None = None) -> list[dict]:
    query = """SELECT c.*, p.full_name AS patient_name, p.patient_id FROM consultations c JOIN patients p ON p.patient_id = c.patient_id WHERE c.doctor_id = ?"""
    params: list = [doctor_id]
    if status:
        query += " AND c.status = ?"
        params.append(status)
    query += " ORDER BY c.scheduled_at"
    with get_conn() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]
