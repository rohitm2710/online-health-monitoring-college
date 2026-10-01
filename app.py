from __future__ import annotations

import os

import streamlit as st

from db import init_db, seed_demo_data
from services.doctor_service import list_unverified, verify_doctor
from views import doctor_dashboard, landing, login, patient_dashboard, registration, sensor_dashboard

st.set_page_config(page_title="OHMS", page_icon="+", layout="wide")
st.markdown(
    """
    <style>
    :root { --ohms-ink: #e7f0f4; --ohms-teal: #43c6b7; --ohms-panel: #17242c; --ohms-muted: #a9bbc2; }
    [data-testid="stAppViewContainer"] { background: radial-gradient(circle at 12% 0%, #1e3b43 0%, #10191f 42%, #0b1115 100%); color: var(--ohms-ink); }
    [data-testid="stHeader"] { background: rgba(11, 17, 21, .86); }
    .block-container { max-width: 1180px; padding-top: 3rem; }
    h1, h2, h3 { color: var(--ohms-ink); letter-spacing: 0; }
    p, label, [data-testid="stCaptionContainer"] { color: var(--ohms-muted); }
    [data-testid="stMetric"], [data-testid="stForm"] { background: rgba(23, 36, 44, .86); border: 1px solid #2b4851; border-radius: 12px; padding: 1rem; }
    .stButton > button[kind="primary"] { background: var(--ohms-teal); border-color: var(--ohms-teal); }
    .stButton > button { border-radius: 8px; border-color: #39616a; color: var(--ohms-ink); background: #1a2c34; }
    input, textarea, [data-baseweb="select"] > div { background-color: #142229 !important; color: var(--ohms-ink) !important; border-color: #39616a !important; }
    [data-testid="stTabs"] button { color: var(--ohms-muted); }
    [data-testid="stTabs"] button[aria-selected="true"] { color: var(--ohms-teal); }
    [data-testid="stExpander"] { background: rgba(23, 36, 44, .72); border: 1px solid #2b4851; }
    </style>
    """,
    unsafe_allow_html=True,
)
init_db()
if os.getenv("OHMS_SEED_DEMO", "0") == "1":
    seed_demo_data()

if "page" not in st.session_state:
    st.session_state.page = "landing"


def admin_panel() -> None:
    with st.expander("Admin: verify doctors"):
        if not st.session_state.get("admin_unlocked", False):
            with st.form("admin_unlock"):
                supplied = st.text_input("Admin passcode", type="password")
                unlock = st.form_submit_button("Unlock admin panel", type="primary")
            if unlock:
                if supplied == os.getenv("OHMS_ADMIN_PASS", "admin123"):
                    st.session_state.admin_unlocked = True
                    st.rerun()
                st.error("Incorrect admin passcode.")
            return
        st.success("Admin panel unlocked.")
        if st.button("Lock admin panel"):
            st.session_state.admin_unlocked = False
            st.rerun()
        if st.button("Load demo data"):
            seed_demo_data()
            st.success("Demo data is ready.")
        pending = list_unverified()
        if not pending:
            st.success("No doctors are waiting for verification.")
        for doctor in pending:
            left, right = st.columns([4, 1])
            with left:
                st.write(f"{doctor['full_name']} · {doctor['license_no']} · {doctor['speciality']}")
            with right:
                if st.button("Verify", key=f"verify_{doctor['doctor_id']}"):
                    verify_doctor(doctor["doctor_id"])
                    st.success("Doctor verified.")
                    st.rerun()


page = st.session_state.page
if page == "landing":
    landing.show()
    admin_panel()
elif page == "register":
    registration.show()
elif page == "login":
    login.show()
elif page == "patient" and st.session_state.get("role") == "patient":
    patient_dashboard.show(st.session_state.user_id)
elif page == "doctor" and st.session_state.get("role") == "doctor":
    doctor_dashboard.show(st.session_state.user_id)
elif page == "sensor" and st.session_state.get("role") == "sensor":
    sensor_dashboard.show(st.session_state.user_id, st.session_state.get("sensor_mac", ""))
else:
    st.session_state.clear()
    st.session_state.page = "landing"
    st.rerun()
