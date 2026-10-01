from datetime import date

import streamlit as st

from auth import register_doctor, register_patient


def show() -> None:
    st.title("Registration portal")
    if st.button("Back to landing"):
        st.session_state.page = "landing"
        st.rerun()
    patient_tab, doctor_tab = st.tabs(["Patient sign up", "Doctor sign up"])
    with patient_tab:
        with st.form("patient_registration"):
            name = st.text_input("Full name")
            dob_year, dob_month, dob_day = st.columns(3)
            with dob_year:
                year = st.number_input("Year", min_value=1900, max_value=date.today().year, value=1990, step=1)
            with dob_month:
                month = st.number_input("Month", min_value=1, max_value=12, value=1, step=1)
            with dob_day:
                day = st.number_input("Day", min_value=1, max_value=31, value=1, step=1)
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create patient account", type="primary")
        if submitted:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    dob = date(int(year), int(month), int(day))
                    patient_id = register_patient(name, dob.isoformat(), email, password)
                    st.session_state.update(role="patient", user_id=patient_id, page="patient")
                    st.success("Account created.")
                    st.rerun()
                except ValueError as exc:
                    st.error("Enter a valid date of birth." if "day is out of range" in str(exc) else str(exc))
    with doctor_tab:
        with st.form("doctor_registration"):
            name = st.text_input("Full name", key="doctor_name")
            license_no = st.text_input("Medical registration number")
            speciality = st.text_input("Speciality")
            email = st.text_input("Email", key="doctor_email")
            password = st.text_input("Password", type="password", key="doctor_password")
            fee = st.number_input("Consultation fee", min_value=0.0, step=5.0)
            submitted = st.form_submit_button("Submit for verification", type="primary")
        if submitted:
            try:
                register_doctor(name, license_no, speciality, email, password, fee)
                st.success("Registration submitted. An administrator must verify this account before login.")
            except ValueError as exc:
                st.error(str(exc))
