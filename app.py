import streamlit as st

from app_config import APP_CAPTION, APP_TITLE, PAGE_OPTIONS
from db import DATA_DIR, init_db
from monitor import run_monitor
from views import render_page


st.set_page_config(page_title=APP_TITLE, layout="wide")
init_db()

st.markdown("""
<style>
div.stButton > button { min-height: 2.35rem; font-size: 0.95rem; }
[data-testid="stDataFrame"] { font-size: 0.88rem; }
.small-muted { color: #777; font-size: 0.85rem; }
.company-row { border-bottom: 1px solid #eee; padding: 0.15rem 0; }
</style>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state["page"] = "Dashboard"
if st.session_state["page"] not in PAGE_OPTIONS:
    st.session_state["page"] = "Dashboard"

st.title(APP_TITLE)
st.caption(APP_CAPTION)

with st.sidebar:
    st.caption(f"Data: {DATA_DIR}")
    chosen = st.radio("Vælg visning", PAGE_OPTIONS, index=PAGE_OPTIONS.index(st.session_state["page"]))
    if chosen != st.session_state["page"]:
        st.session_state["page"] = chosen
        st.rerun()
    if st.button("Kør overvågning nu", type="primary"):
        with st.spinner("Overvåger kilder..."):
            result = run_monitor()
        st.success(f"Færdig. Fund indsamlet: {result['collected']}. Relevante signaler: {result['relevant']}.")

page = st.session_state["page"]

render_page(page)
