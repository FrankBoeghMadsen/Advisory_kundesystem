import streamlit as st
from pathlib import Path

from app_config import APP_CAPTION, APP_TITLE, APP_VERSION, PAGE_OPTIONS
from db import DATA_DIR, init_db
from monitor import run_monitor
from runtime_config import APP_MODE, RuntimeConfigurationError, mode_label
from views import render_page
from ui.navigation import render_navigation


LOGO_PATH=Path(__file__).resolve().parent/'assets'/'advisory-compass.png'
st.set_page_config(page_title=APP_TITLE, page_icon=str(LOGO_PATH), layout="wide")
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
.company-row { border-bottom: 1px solid #E5E7EB; padding: 0.15rem 0; }
h1 { font-size: 2rem !important; letter-spacing: 0 !important; }
h2, h3 { letter-spacing: 0 !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #000080 !important; }
[data-testid="stMainBlockContainer"] { padding-top: 1.5rem; padding-bottom: 2rem; }
.st-key-project_module [data-testid="stVerticalBlock"] { gap: 0.65rem; }
.st-key-project_module h4 { margin-top: 0.8rem; }
.st-key-project_form_actions { max-width: 26rem; }
@media (max-width: 768px) {
    .st-key-project_form_actions [data-testid="stHorizontalBlock"] { flex-wrap: nowrap; }
    .st-key-project_form_actions [data-testid="stColumn"] { min-width: 0; width: auto; flex: 1 1 auto; }
}
[data-testid="stRadio"] label:has(input:checked) { background: #CDEFF8; border-bottom: 3px solid #000080; font-weight: 700; }
.st-key-business_navigation label:has(input[type="radio"]) { padding: 8px 12px; border: 1px solid #E5E7EB; border-radius: 4px; }
.st-key-business_status_filters [data-baseweb="tag"], .st-key-project_module [data-baseweb="tag"] { background-color: #E5E7EB; color: #1F2933; border: 1px solid #E5E7EB; }
.st-key-business_status_filters [data-baseweb="tag"] svg, .st-key-project_module [data-baseweb="tag"] svg { color: #1F2933; }
</style>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state["page"] = "Dashboard"
if st.session_state["page"] not in PAGE_OPTIONS:
    st.session_state["page"] = "Dashboard"

with st.sidebar:
    logo, name=st.columns([1,3],vertical_alignment='center')
    logo.image(str(LOGO_PATH),width=56)
    name.markdown('**'+APP_TITLE+'**')
    if APP_MODE == "development":
        st.warning("UDVIKLINGSDATABASE")
    elif APP_MODE == "test":
        st.warning("TESTDATABASE")
    with st.expander('Om og tekniske oplysninger'):
        st.caption(APP_VERSION)
        st.caption(APP_CAPTION)
        st.caption(f"Tilstand: {mode_label()}")
        st.caption(f"Data: {DATA_DIR}")
    render_navigation()
    if st.session_state['page'] in ['Signalindbakke','Kilder','Triggerregler','Briefing'] and st.button("Kør overvågning nu"):
        with st.spinner("Overvåger kilder..."):
            result = run_monitor()
        st.success(f"Færdig. Fund indsamlet: {result['collected']}. Relevante signaler: {result['relevant']}.")

page = st.session_state["page"]

if APP_MODE in ('development','test'):
    with st.container(key='runtime_notice'):
        st.caption('**UDVIKLINGSDATABASE**' if APP_MODE=='development' else '**TESTDATABASE**')

render_page(page)
