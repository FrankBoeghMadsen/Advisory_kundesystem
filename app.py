import streamlit as st

from app_config import APP_CAPTION, APP_TITLE, APP_VERSION, PAGE_OPTIONS
from db import DATA_DIR, init_db
from monitor import run_monitor
from runtime_config import APP_MODE, RuntimeConfigurationError, mode_label
from views import render_page
from ui.navigation import render_navigation


st.set_page_config(page_title=APP_TITLE, layout="wide")
try:
    init_db()
except RuntimeConfigurationError as exc:
    st.error(f"Sikkerhedsstop: {exc}")
    st.info("Start programmet via den almindelige startfil eller den særskilte udviklingsstart.")
    st.stop()

st.markdown("""
<style>
div.stButton > button { min-height: 2.35rem; font-size: 0.95rem; }
[data-testid="stDataFrame"] { font-size: 0.88rem; }
.small-muted { color: #777; font-size: 0.85rem; }
.company-row { border-bottom: 1px solid #eee; padding: 0.15rem 0; }
h1 { font-size: 2rem !important; letter-spacing: 0 !important; }
h2, h3 { letter-spacing: 0 !important; }
[data-testid="stRadio"] label:has(input:checked) { background: #d3ebe4; border-bottom: 3px solid #24776b; font-weight: 700; }
.st-key-business_navigation label:has(input[type="radio"]) { padding: 8px 12px; border: 1px solid #aab6b2; border-radius: 4px; }
.st-key-business_status_filters [data-baseweb="tag"], .st-key-project_module [data-baseweb="tag"] { background-color: #e9efec; color: #243b35; border: 1px solid #b6c7c0; }
.st-key-business_status_filters [data-baseweb="tag"] svg, .st-key-project_module [data-baseweb="tag"] svg { color: #243b35; }
</style>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state["page"] = "Dashboard"
if st.session_state["page"] not in PAGE_OPTIONS:
    st.session_state["page"] = "Dashboard"

st.title(APP_TITLE)
st.caption(APP_VERSION)
st.caption(APP_CAPTION)

with st.sidebar:
    if APP_MODE == "development":
        st.warning("UDVIKLINGSDATABASE")
    st.caption(f"Tilstand: {mode_label()}")
    st.caption(f"Data: {DATA_DIR}")
    render_navigation()
    if st.session_state['page'] in ['Signalindbakke','Kilder','Triggerregler','Briefing'] and st.button("Kør overvågning nu"):
        with st.spinner("Overvåger kilder..."):
            result = run_monitor()
        st.success(f"Færdig. Fund indsamlet: {result['collected']}. Relevante signaler: {result['relevant']}.")

page = st.session_state["page"]

render_page(page)
