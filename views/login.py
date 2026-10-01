import streamlit as st

from auth import login_doctor, login_patient, login_sensor


def show() -> None:
    st.title("Login portal")
    if st.button("Back to landing"):
        st.session_state.page = "landing"
        st.rerun()
    patient_tab, doctor_tab, sensor_tab = st.tabs(["Patient", "Doctor", "Sensor"])
    with patient_tab:
        with st.form("patient_login"):
            email = st.text_input("Email", key="patient_login_email")
            password = st.text_input("Password", type="password", key="patient_login_password")
            submit = st.form_submit_button("Login", type="primary")
        if submit:
            user = login_patient(email, password)
            if user:
                st.session_state.update(role="patient", user_id=user["patient_id"], page="patient")
                st.rerun()
            st.error("Invalid credentials.")
    with doctor_tab:
        with st.form("doctor_login"):
            email = st.text_input("Email", key="doctor_login_email")
            password = st.text_input("Password", type="password", key="doctor_login_password")
            submit = st.form_submit_button("Login", type="primary")
        if submit:
            user = login_doctor(email, password)
            if user:
                st.session_state.update(role="doctor", user_id=user["doctor_id"], page="doctor")
                st.rerun()
            st.error("Invalid credentials.")
    with sensor_tab:
        with st.form("sensor_login"):
            mac = st.text_input("Sensor MAC", placeholder="AA:BB:CC:DD:EE:FF")
            passcode = st.text_input("Device passcode", type="password")
            submit = st.form_submit_button("Connect sensor", type="primary")
        if submit:
            user = login_sensor(mac, passcode)
            if user:
                st.session_state.update(role="sensor", user_id=user["patient_id"], sensor_mac=mac.upper(), page="sensor")
                st.rerun()
            st.error("Invalid credentials.")
