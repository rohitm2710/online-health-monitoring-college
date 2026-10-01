# OHMS

OHMS is a Streamlit + SQLite online health monitoring system for patients, doctors, and mapped sensor devices.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The database is created automatically as `ohms.db` on first start. To seed the two demo doctors, two patients, and sample vitals, set `OHMS_SEED_DEMO=1` before the first run:

```powershell
$env:OHMS_SEED_DEMO="1"
streamlit run app.py
```

## Environment variables

- `OHMS_ADMIN_PASS`: passcode for the doctor verification panel. Default: `admin123`.
- `OHMS_SENSOR_PASS`: passcode for mapped sensors. Default: `sensor123`.
- `OHMS_SEED_DEMO`: set to `1` to load demo data when the database is empty.

## Demo credentials

- Patient: `ava@ohms.local` / `patient123`
- Patient: `noah@ohms.local` / `patient123`
- Doctor: `maya@ohms.local` / `doctor123`
- Doctor: `liam@ohms.local` / `doctor123`
- Sensor MAC: `AA:BB:CC:DD:EE:01` / `sensor123`

Doctors are verified demo accounts. New doctors remain pending until the admin panel on the landing page verifies them.
