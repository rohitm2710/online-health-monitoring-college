import streamlit as st


def show() -> None:
    st.markdown("# OHMS")
    st.markdown("### Online Health Monitoring System")
    st.divider()
    left, right = st.columns(2)
    with left:
        if st.button("Register", use_container_width=True, type="primary"):
            st.session_state.page = "register"
            st.rerun()
    with right:
        if st.button("Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()
