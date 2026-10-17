import streamlit as st


def set_page(name):
    st.session_state["page"] = name


def set_company(company_id):
    st.session_state["selected_company_id"] = int(company_id)
    st.session_state["force_profile_view"] = True


def open_company_section(company_id, section):
    st.session_state["selected_company_id"] = int(company_id)
    st.session_state[f"profile_section_{int(company_id)}"] = section
    st.session_state["force_profile_view"] = True
    st.session_state["page"] = "Virksomheder"


def open_followup(company_id, followup_id):
    st.session_state["highlight_followup_id"] = int(followup_id)
    open_company_section(company_id, "Opfølgning")
