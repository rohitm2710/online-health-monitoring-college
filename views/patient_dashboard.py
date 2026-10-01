from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from db import get_conn
from services.alerts import evaluate
from services.consult_service import book_consult, list_doctors, patient_consultations, pay_consult, suggest_consult, topup
from services.patient_service import get_patient, report_summary
from services.vitals_service import get_readings


def _logout() -> None:
    st.session_state.clear()
    st.session_state.page = "landing"
    st.rerun()


def _vitals(patient_id: int) -> None:
    st.subheader("Vitals log")
    days = st.slider("Show recent days", 1, 30, 7)
    rows = get_readings(patient_id, datetime.now() - timedelta(days=days))
    if not rows:
        st.info("No readings yet.")
        return
    frame = pd.DataFrame(rows)
    frame["temperature_c"] = frame["temp_centi"] / 100
    frame["alerts"] = frame.apply(lambda row: "; ".join(evaluate(row.to_dict())), axis=1)
    st.dataframe(frame[["recorded_at", "heart_rate", "spo2", "systolic_bp", "diastolic_bp", "temperature_c", "alerts"]], use_container_width=True, hide_index=True)
    abnormal = frame[frame["alerts"] != ""]
    for _, row in abnormal.iterrows():
        st.warning(f"{row['recorded_at']}: {row['alerts']}")


def _booking(patient_id: int) -> None:
    st.subheader("Book a consultation")
    doctors = list_doctors()
    if not doctors:
        st.info("No verified doctors are available.")
        return
    options = {f"{d['full_name']} · {d['speciality']} · ${d['consult_fee']:.2f}": d["doctor_id"] for d in doctors}
    with st.form("book_consult"):
        selected = st.selectbox("Doctor", list(options))
        when = st.datetime_input("Appointment time", value=datetime.now() + timedelta(days=1))
        submit = st.form_submit_button("Book consultation", type="primary")
    if submit:
        try:
            consult_id = book_consult(patient_id, options[selected], when.isoformat(sep=" "))
            st.session_state.payment_id = consult_id
            st.success("Consultation booked. Complete payment below.")
        except ValueError as exc:
            st.error(str(exc))


def _payment(patient_id: int) -> None:
    st.subheader("Payment")
    consults = [c for c in patient_consultations(patient_id) if c["payment_status"] == "UNPAID" and c["status"] in ("PENDING", "SUGGESTED")]
    if not consults:
        st.info("There are no unpaid consultations.")
        return
    for consult in consults:
        with st.container(border=True):
            st.write(f"**{consult['doctor_name']}** · {consult['scheduled_at']} · ${consult['fee_charged']:.2f}")
            if st.button("Pay", key=f"pay_{consult['consult_id']}"):
                try:
                    pay_consult(consult["consult_id"], patient_id)
                    st.success("Payment complete.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))


def _balance(patient_id: int) -> None:
    patient = get_patient(patient_id)
    st.subheader("Balance & payment")
    st.metric("Available balance", f"${patient['balance']:.2f}")
    with st.form("topup"):
        amount = st.number_input("Top-up amount", min_value=0.01, step=10.0)
        if st.form_submit_button("Add funds"):
            try:
                topup(patient_id, amount)
                st.success("Balance updated.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    st.dataframe(pd.DataFrame(patient_consultations(patient_id)), use_container_width=True, hide_index=True)


def _prescriptions(patient_id: int) -> None:
    st.subheader("Prescriptions")
    prescriptions = [c for c in patient_consultations(patient_id) if c["prescription"]]
    if not prescriptions:
        st.info("No prescriptions yet.")
    for consult in prescriptions:
        st.write(f"**{consult['doctor_name']}** · {consult['created_at']}")
        st.write(consult["prescription"])


def _suggestions(patient_id: int) -> None:
    st.subheader("Consult suggestions")
    suggestions = [c for c in patient_consultations(patient_id) if c["status"] == "SUGGESTED"]
    for consult in suggestions:
        st.info(f"{consult['doctor_name']}: {consult['advice_note'] or 'Follow-up recommended.'} · {consult['scheduled_at']}")
        accept, dismiss = st.columns(2)
        with accept:
            if st.button("Accept & pay", key=f"accept_{consult['consult_id']}"):
                st.session_state.payment_id = consult["consult_id"]
                st.rerun()
        with dismiss:
            if st.button("Dismiss", key=f"dismiss_{consult['consult_id']}"):
                with get_conn() as conn:
                    conn.execute("UPDATE consultations SET status = 'REJECTED' WHERE consult_id = ? AND patient_id = ?", (consult["consult_id"], patient_id))
                st.rerun()


def show(patient_id: int) -> None:
    patient = get_patient(patient_id)
    st.title(f"Welcome, {patient['full_name']}")
    top_left, top_right = st.columns([3, 1])
    with top_left:
        summary = report_summary(patient_id)
        st.caption(f"7-day report: {summary.get('count', 0)} readings · {summary.get('abnormal', 0)} abnormal")
    with top_right:
        if st.button("Log out"):
            _logout()
    vitals, booking, payment, balance, prescriptions, suggestions = st.tabs(["Vitals log", "Book consult", "Payment", "Balance", "Prescriptions", "Suggestions"])
    with vitals:
        _vitals(patient_id)
    with booking:
        _booking(patient_id)
    with payment:
        _payment(patient_id)
    with balance:
        _balance(patient_id)
    with prescriptions:
        _prescriptions(patient_id)
    with suggestions:
        _suggestions(patient_id)
