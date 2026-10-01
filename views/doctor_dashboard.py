from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from auth import MAC_RE
from db import get_conn
from services.alerts import evaluate
from services.consult_service import doctor_consultations, respond, suggest_consult, write_prescription
from services.doctor_service import assign_sensor, doctor_patients, list_patients
from services.vitals_service import get_readings


def _logout() -> None:
    st.session_state.clear()
    st.session_state.page = "landing"
    st.rerun()


def _patient_vitals(doctor_id: int) -> None:
    patients = doctor_patients(doctor_id)
    st.subheader("Patient vitals log")
    if not patients:
        st.info("Patients appear here after a consultation is booked.")
        return
    selected = st.selectbox("Patient", patients, format_func=lambda p: f"{p['full_name']} · {p['email']}")
    rows = get_readings(selected["patient_id"], datetime.now() - timedelta(days=30))
    if rows:
        frame = pd.DataFrame(rows)
        frame["temperature_c"] = frame["temp_centi"] / 100
        frame["alerts"] = frame.apply(lambda row: "; ".join(evaluate(row.to_dict())), axis=1)
        st.dataframe(frame[["recorded_at", "heart_rate", "spo2", "systolic_bp", "diastolic_bp", "temperature_c", "alerts"]], use_container_width=True, hide_index=True)
        for _, row in frame[frame["alerts"] != ""].iterrows():
            st.error(f"Alert {row['recorded_at']}: {row['alerts']}")
    else:
        st.info("No readings for this patient.")


def _allocation() -> None:
    st.subheader("Sensor allocation")
    for patient in list_patients():
        with st.form(f"sensor_{patient['patient_id']}"):
            st.write(f"**{patient['full_name']}** · {patient['email']}")
            mac = st.text_input("Sensor MAC", value=patient["sensor_mac"] or "", key=f"mac_{patient['patient_id']}")
            if st.form_submit_button("Save mapping"):
                try:
                    assign_sensor(patient["patient_id"], mac or None)
                    st.success("Sensor mapping saved.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))


def _consultations(doctor_id: int) -> None:
    st.subheader("Consult response")
    pending = doctor_consultations(doctor_id, "PENDING")
    for consult in pending:
        with st.container(border=True):
            st.write(f"**{consult['patient_name']}** · {consult['scheduled_at']} · {consult['payment_status']}")
            accept, reject = st.columns(2)
            with accept:
                if st.button("Accept", key=f"accept_{consult['consult_id']}"):
                    respond(consult["consult_id"], doctor_id, True)
                    st.rerun()
            with reject:
                if st.button("Reject", key=f"reject_{consult['consult_id']}"):
                    respond(consult["consult_id"], doctor_id, False)
                    st.rerun()
    st.markdown("#### Accepted consultations")
    for consult in doctor_consultations(doctor_id, "ACCEPTED"):
        with st.form(f"prescription_{consult['consult_id']}"):
            st.write(f"**{consult['patient_name']}** · {consult['scheduled_at']}")
            prescription = st.text_area("Prescription")
            if st.form_submit_button("Complete with prescription"):
                try:
                    write_prescription(consult["consult_id"], doctor_id, prescription)
                    st.success("Prescription saved.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))


def _suggest(doctor_id: int) -> None:
    st.subheader("Consultation suggestion")
    patients = list_patients()
    if not patients:
        return
    with st.form("suggestion"):
        patient = st.selectbox("Patient", patients, format_func=lambda p: p["full_name"])
        note = st.text_area("Advice note")
        when = st.datetime_input("Suggested appointment", value=datetime.now() + timedelta(days=2))
        if st.form_submit_button("Send suggestion"):
            try:
                suggest_consult(doctor_id, patient["patient_id"], note, when.isoformat(sep=" "))
                st.success("Suggestion sent.")
            except ValueError as exc:
                st.error(str(exc))


def show(doctor_id: int) -> None:
    with get_conn() as conn:
        doctor = dict(conn.execute("SELECT * FROM doctors WHERE doctor_id = ?", (doctor_id,)).fetchone())
    st.title(f"Dr. {doctor['full_name']}")
    if st.button("Log out"):
        _logout()
    vitals, allocation, consults, suggestion = st.tabs(["Patient vitals", "Sensor allocation", "Consult response", "Suggest consult"])
    with vitals:
        _patient_vitals(doctor_id)
    with allocation:
        _allocation()
    with consults:
        _consultations(doctor_id)
    with suggestion:
        _suggest(doctor_id)
