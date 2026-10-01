# OHMS – Online Health Monitoring System
### Build Instructions (Python · Streamlit · SQLite3)

Build a complete, runnable web app named **OHMS** from the ER diagram, database tables, GUI workflow and Level-1 DFD below. Treat this document as the specification.

---

## 1. Tech Stack & Constraints

| Item | Choice |
|---|---|
| Language | Python 3.10+ |
| UI | Streamlit (`st.session_state` routing) |
| Database | `sqlite3` (standard library, no ORM) |
| Passwords | salted hash (`hashlib`/`bcrypt`) stored in `password_hash` |
| Extras | `pandas`, `plotly` or `st.line_chart` for vitals trends |

Rules:
- Run `PRAGMA foreign_keys = ON;` on every connection.
- Use parameterised queries only (`?`). Never build SQL with f-strings.
- Never store plain-text passwords.
- Wrap every write in a transaction (`with conn:`).
- Keep DB code separate from UI code.

## 2. Project Structure

```
ohms/
├── app.py            # entry point, router, session handling
├── db.py             # connection, schema, seed data
├── auth.py           # hashing, register/login (patient, doctor, sensor)
├── services/
│   ├── patient_service.py
│   ├── doctor_service.py
│   ├── vitals_service.py
│   ├── consult_service.py
│   └── alerts.py
├── views/
│   ├── landing.py
│   ├── registration.py
│   ├── login.py
│   ├── patient_dashboard.py
│   ├── doctor_dashboard.py
│   └── sensor_dashboard.py
├── requirements.txt
└── README.md
```
Run with `streamlit run app.py`. `ohms.db` is auto-created on first run.

## 3. ER Diagram → Entities & Relationships

Entities: `PATIENT`, `VITALS_LOG`, `CONSULTATIONS`, `DOCTOR`

| Relationship | Between | Cardinality |
|---|---|---|
| GENERATES | PATIENT → VITALS_LOG | 1 : N |
| HOLDS | PATIENT → CONSULTATIONS | 1 : N |
| ATTENDS | DOCTOR → CONSULTATIONS | 1 : N |

## 4. Database Schema (SQLite)

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS patients (
    patient_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name      TEXT NOT NULL,
    dob            DATE NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    sensor_mac     TEXT UNIQUE,                       -- allocated sensor (nullable)
    balance        NUMERIC NOT NULL DEFAULT 0 CHECK (balance >= 0),
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doctors (
    doctor_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name      TEXT NOT NULL,
    license_no     TEXT NOT NULL UNIQUE,              -- Medical Reg. No.
    speciality     TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    consult_fee    NUMERIC NOT NULL DEFAULT 0 CHECK (consult_fee >= 0),
    is_verified    BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vitals_log (
    log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id    INTEGER NOT NULL,
    heart_rate    INTEGER NOT NULL CHECK (heart_rate BETWEEN 0 AND 255),
    spo2          INTEGER NOT NULL CHECK (spo2 BETWEEN 0 AND 100),
    systolic_bp   INTEGER NOT NULL CHECK (systolic_bp BETWEEN 0 AND 400),
    diastolic_bp  INTEGER NOT NULL CHECK (diastolic_bp BETWEEN 0 AND 400),
    temp_centi    INTEGER NOT NULL CHECK (temp_centi BETWEEN 0 AND 65535), -- °C×100 (3650 = 36.50)
    recorded_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_vitals_patient_time ON vitals_log(patient_id, recorded_at DESC);

CREATE TABLE IF NOT EXISTS consultations (
    consult_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL,
    doctor_id       INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING','ACCEPTED','REJECTED','COMPLETED','SUGGESTED')),
    scheduled_at    TIMESTAMP NOT NULL,
    payment_status  TEXT NOT NULL DEFAULT 'UNPAID'
                    CHECK (payment_status IN ('UNPAID','PAID','REFUNDED')),
    fee_charged     NUMERIC NOT NULL DEFAULT 0,       -- snapshot of doctor's fee at booking
    prescription    TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id)  REFERENCES doctors(doctor_id)   ON DELETE RESTRICT
);
```

Notes:
- `consultations` columns come from the ER diagram (`consult_id, status, scheduled_at, payment_status, prescription`) plus the two foreign keys implied by HOLDS and ATTENDS. `fee_charged` and `created_at` are small additions for billing consistency.
- `SUGGESTED` status is used when a doctor suggests a consultation to a patient.
- Include a "Load demo data" option (2 verified doctors, 2 patients, a few vitals rows).

## 5. Roles & Authentication

| Role | Login identity | Lands on |
|---|---|---|
| Patient | email + password | Patient Dashboard |
| Doctor | email + password (only if `is_verified = 1`) | Doctor Dashboard |
| Sensor | sensor MAC + device passcode | Sensor Dashboard |

- Store `role`, `user_id`, `page` in `st.session_state`; guard every view by role.
- **Doctor sign-up** creates `is_verified = 0`. Provide an admin expander (passcode from env `OHMS_ADMIN_PASS`) that lists unverified doctors with `license_no` and a **Verify** button. This implements the DFD process "Manage Doctor (Auth & Profile)".
- **Sensor login:** the MAC must exist in `patients.sensor_mac` and the passcode must equal env `OHMS_SENSOR_PASS` (demo default `sensor123`). Validate MAC format `AA:BB:CC:DD:EE:FF`.
- **Log Out** clears the session and returns to the Landing Page.
- Login errors must not reveal which field was wrong.

## 6. GUI Workflow (Screens & Navigation)

```
Landing Page
├── Registration Portal
│   ├── Patient Sign Up ──(on success)──► Patient Dashboard
│   └── Doctor Sign Up
└── Login Portal
    ├── Patient Login ─► Patient Dashboard
    ├── Doctor Login  ─► Doctor Dashboard
    └── Sensor Login  ─► Sensor Dashboard

Patient Dashboard: Vitals Log | Book Consult ─► Payment ─► Prescription | Balance & Payment | Log Out
Doctor Dashboard:  Patient Vitals Log | Sensor Allocation | Consult Response ─► Prescription | Consultation Suggestion | Log Out
Sensor Dashboard:  Data Entry | Log Out
```

### 6.1 Landing Page
App title, short description, **Register** and **Login** buttons.

### 6.2 Registration Portal
Tabs: **Patient Sign Up** and **Doctor Sign Up**.
- Patient: full name, DOB, email, password, confirm password. Initial balance is 0. The sensor MAC is allocated later by a doctor.
- Doctor: full name, license no, speciality, email, password, consult fee.
- Validate email format, unique email/license, password ≥ 8 chars, DOB not in the future.
- Patient success → auto-login → Patient Dashboard. Doctor success → "Pending verification" message.

### 6.3 Login Portal
Tabs: **Patient**, **Doctor**, **Sensor**.

### 6.4 Patient Dashboard
1. **Vitals Log** – table (newest first), date filter, charts for heart rate, SpO₂, BP and temperature (`temp_centi/100` in °C). Highlight abnormal values (Section 8).
2. **Book Consult** – list verified doctors (name, speciality, fee). Pick a doctor and a future date/time. Insert a `PENDING`/`UNPAID` consultation with `fee_charged` = doctor's fee, then go to Payment.
3. **Payment** – show fee and balance. In one transaction, check `balance >= fee`, deduct the balance and set `payment_status='PAID'`. If the balance is insufficient, show an error and link to Balance & Payment. Unpaid bookings can be paid later.
4. **Balance & Payment** – show balance, simulated top-up (positive amounts only), and the consultation list with statuses.
5. **Prescription** – show the doctor's prescription with a text download button.
6. **Consult Suggestions** – list `SUGGESTED` consultations with **Accept & Pay** or **Dismiss**.
7. **Log Out**.

### 6.5 Doctor Dashboard
1. **Patient Vitals Log** – select a patient (at minimum those with a consultation with this doctor) and view the vitals table, charts and alerts.
2. **Sensor Allocation** – list patients with their `sensor_mac`. The doctor can assign, change or clear it, with MAC format and uniqueness validation. (DFD: sensor–patient mapping.)
3. **Consult Response** – list this doctor's pending consultations. **Accept** or **Reject**. Rejecting a paid consultation refunds the fee to the patient balance and sets `REFUNDED` (single transaction). After accepting, the doctor writes a **Prescription** and the status becomes `COMPLETED`.
4. **Consultation Suggestion** – based on vitals, create a `SUGGESTED` consultation with an advice note.
5. **Log Out**.

### 6.6 Sensor Dashboard
1. **Data Entry** – push readings for the patient mapped to the logged-in MAC: heart rate, SpO₂, systolic, diastolic, temperature (°C → `temp_centi = round(t*100)`). Add a "Generate random reading" button. Validate ranges before inserting into `vitals_log`.
2. **Log Out**.

## 7. Level-1 DFD → Modules

External entities: Patient, Doctor, Sensors. Six processes and four data stores (`patients`, `vitals_log`, `consultations`, `doctors`).

| # | Process | Input | Output / Store | Module |
|---|---|---|---|---|
| 1 | Manage Patient (Auth & Profile) | Patient details & credentials | `patients`; secure sensor mapping | `auth.py`, `patient_service.py` |
| 2 | Authenticate Sensor & Ingest Vitals | Raw continuous signals from sensors | `vitals_log` | `auth.py`, `vitals_service.py` |
| 3 | Generate Alerts & Medical Reports | `vitals_log` | Alerts/vitals summary → Doctor; report summary → Patient | `alerts.py` |
| 4 | Manage Doctor (Auth & Profile) | Doctor details/credentials | `doctors`; verify record; assigned mapping check | `doctor_service.py` |
| 5 | Process Payment & Book Consult | Payment details & consult request | `consultations`, `patients.balance` | `consult_service.py` |
| 6 | Manage Consult & Advice | Accept/Reject request; suggest consult / provide advice | `consultations` (prescription, status); suggestion → Patient | `consult_service.py` |

## 8. Alerts & Reports (Process 3)

`alerts.evaluate(reading) -> list[str]` with constant thresholds:

| Vital | Warn when |
|---|---|
| Heart rate | < 50 or > 110 bpm |
| SpO₂ | < 94 % (critical < 90 %) |
| Systolic BP | > 140 or < 90 |
| Diastolic BP | > 90 or < 60 |
| Temperature | > 38.0 °C or < 35.0 °C |

- Show alerts with `st.warning`/`st.error` and colour-coded rows.
- **Doctor view:** an Alerts panel of the latest abnormal readings.
- **Patient view:** a report summary (7-day averages, min/max, abnormal count) and a **Download CSV** button.

## 9. Business Rules Checklist

- [ ] Email and `license_no` are unique.
- [ ] Only verified doctors can log in or appear in booking.
- [ ] `sensor_mac` is unique; only doctors allocate it.
- [ ] A sensor writes only for the patient linked to its MAC.
- [ ] Payment is atomic and the balance never goes negative.
- [ ] No consultations in the past.
- [ ] Rejecting a paid consultation refunds the patient.
- [ ] Patients see only their own data; doctors see only permitted patients.
- [ ] All forms give `st.success`/`st.error` feedback.

## 10. Suggested Function Signatures

```python
# db.py
def get_conn() -> sqlite3.Connection      # row_factory=sqlite3.Row, foreign_keys ON
def init_db() -> None
def seed_demo_data() -> None

# auth.py
def hash_password(pw) -> str
def verify_password(pw, stored) -> bool
def register_patient(full_name, dob, email, password) -> int
def register_doctor(full_name, license_no, speciality, email, password, consult_fee) -> int
def login_patient(email, password) -> dict | None
def login_doctor(email, password) -> dict | None   # None if not verified
def login_sensor(mac, passcode) -> dict | None

# vitals_service.py
def add_reading(patient_id, hr, spo2, sys_bp, dia_bp, temp_c) -> int
def get_readings(patient_id, since=None) -> list

# consult_service.py
def book_consult(patient_id, doctor_id, scheduled_at) -> int
def pay_consult(consult_id) -> None                # atomic
def respond(consult_id, accept: bool) -> None      # refund if rejected & paid
def write_prescription(consult_id, text) -> None   # sets COMPLETED
def suggest_consult(doctor_id, patient_id, note, scheduled_at) -> int
def topup(patient_id, amount) -> None

# doctor_service.py
def list_unverified() -> list
def verify_doctor(doctor_id) -> None
def assign_sensor(patient_id, mac_or_none) -> None
```

## 11. Deliverables

1. Full source code in the structure from Section 2.
2. `requirements.txt` (`streamlit`, `pandas`, optionally `plotly`).
3. `README.md` with install steps, run command, env vars (`OHMS_ADMIN_PASS`, `OHMS_SENSOR_PASS`) and demo credentials.
4. Auto-created `ohms.db` with optional demo data.
5. The app starts with one command (`streamlit run app.py`) and needs no manual DB setup.

## 12. Acceptance Test

1. Register a doctor → can't log in → verify via admin panel → log in.
2. Register a patient → Patient Dashboard → top up balance.
3. As doctor, **Sensor Allocation**: assign `AA:BB:CC:DD:EE:01` to the patient.
4. Log in as Sensor with that MAC → **Data Entry**: submit readings, including one abnormal.
5. Patient **Vitals Log** shows the readings with alert highlighting.
6. Patient books a consult and pays (balance deducted, `PAID`).
7. Doctor accepts, writes a prescription → `COMPLETED`.
8. Patient sees the prescription.
9. Doctor suggests a consultation → patient sees and accepts it.
10. Doctor rejects a paid consultation → patient is refunded.
11. Logout works for all roles and protected pages are then inaccessible.