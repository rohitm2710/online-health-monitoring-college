import streamlit as st

from services.vitals_service import add_reading, random_reading


def _logout() -> None:
    st.session_state.clear()
    st.session_state.page = "landing"
    st.rerun()


def show(patient_id: int, sensor_mac: str) -> None:
    st.title("Sensor dashboard")
    st.caption(f"Connected device: {sensor_mac} · patient ID {patient_id}")
    if st.button("Log out"):
        _logout()
    if st.button("Generate random reading"):
        values = random_reading()
        for key, value in zip(("hr", "spo2", "sys", "dia", "temp"), values):
            st.session_state[key] = value
    with st.form("sensor_reading"):
        hr = st.number_input("Heart rate (bpm)", min_value=0, max_value=255, value=st.session_state.get("hr", 72))
        spo2 = st.number_input("SpO2 (%)", min_value=0, max_value=100, value=st.session_state.get("spo2", 98))
        sys_bp = st.number_input("Systolic BP", min_value=0, max_value=400, value=st.session_state.get("sys", 120))
        dia_bp = st.number_input("Diastolic BP", min_value=0, max_value=400, value=st.session_state.get("dia", 78))
        temp = st.number_input("Temperature (C)", min_value=0.0, max_value=655.35, value=float(st.session_state.get("temp", 36.6)), step=0.1)
        if st.form_submit_button("Submit reading", type="primary"):
            try:
                add_reading(patient_id, hr, spo2, sys_bp, dia_bp, temp)
                st.success("Reading stored for the mapped patient.")
            except ValueError as exc:
                st.error(str(exc))
