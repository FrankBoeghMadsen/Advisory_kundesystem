from app_context import (
    now_iso,
    q,
    run,
    st,
)


def render():
    st.subheader("Kildeadministration")
    df = q("SELECT id, name AS navn, source_type AS type, url, keywords AS nøgleord, status, priority AS prioritet, last_checked AS sidst_tjekket, last_error AS seneste_fejl FROM sources ORDER BY status, priority DESC, name")
    if len(df):
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Ingen kilder.")
    with st.expander("Tilføj kilde"):
        with st.form("add_source_form", clear_on_submit=True):
            name = st.text_input("Navn")
            source_type = st.text_input("Type")
            url = st.text_input("URL")
            keywords = st.text_input("Nøgleord")
            status = st.selectbox("Status", ["Aktiv","Pauset"], index=0)
            priority = st.selectbox("Prioritet", ["Lav","Middel","Høj"], index=1)
            if st.form_submit_button("Gem kilde"):
                run("INSERT INTO sources (name, source_type, url, keywords, active, status, priority, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (name, source_type, url, keywords, 1 if status == "Aktiv" else 0, status, priority, now_iso()))
                st.rerun()

    if len(df):
        st.markdown("### Redigér / slet kilder")
        for _, r in df.iterrows():
            with st.expander(f"{r['navn']}"):
                with st.form(f"edit_source_{int(r['id'])}"):
                    name = st.text_input("Navn", r["navn"])
                    source_type = st.text_input("Type", r["type"] or "")
                    url = st.text_input("URL", r["url"] or "")
                    keywords = st.text_input("Nøgleord", r["nøgleord"] or "")
                    status = st.selectbox("Status", ["Aktiv","Pauset"], index=0 if r["status"]=="Aktiv" else 1)
                    priority = st.selectbox("Prioritet", ["Lav","Middel","Høj"], index=["Lav","Middel","Høj"].index(r["prioritet"]) if r["prioritet"] in ["Lav","Middel","Høj"] else 1)
                    if st.form_submit_button("Gem ændringer"):
                        run("UPDATE sources SET name=?, source_type=?, url=?, keywords=?, active=?, status=?, priority=? WHERE id=?",
                            (name, source_type, url, keywords, 1 if status == "Aktiv" else 0, status, priority, int(r["id"])))
                        st.rerun()
                    if st.form_submit_button("Slet kilde"):
                        run("DELETE FROM sources WHERE id=?", (int(r["id"]),))
                        st.rerun()
