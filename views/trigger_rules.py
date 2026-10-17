from app_context import (
    q,
    run,
    st,
)


def render():
    st.subheader("Triggerregler")
    df = q("SELECT id, name AS navn, pattern AS mønster, default_score AS score, weight AS vægt, active AS aktiv FROM trigger_rules ORDER BY weight DESC")
    if len(df):
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Ingen triggerregler.")
    with st.expander("Tilføj triggerregel"):
        with st.form("add_trigger_form", clear_on_submit=True):
            name = st.text_input("Navn")
            pattern = st.text_input("Mønster")
            score = st.selectbox("Score", ["Lav","Middel","Høj","Kritisk"], index=1)
            weight = st.number_input("Vægt", value=5)
            active = st.checkbox("Aktiv", value=True)
            if st.form_submit_button("Gem triggerregel"):
                run("INSERT INTO trigger_rules (name, pattern, default_score, weight, active) VALUES (?, ?, ?, ?, ?)",
                    (name, pattern, score, weight, 1 if active else 0))
                st.rerun()

    if len(df):
        st.markdown("### Redigér / slet triggerregler")
        for _, r in df.iterrows():
            with st.expander(f"{r['navn']}"):
                with st.form(f"edit_trigger_{int(r['id'])}"):
                    name = st.text_input("Navn", r["navn"])
                    pattern = st.text_input("Mønster", r["mønster"] or "")
                    score = st.selectbox("Score", ["Lav","Middel","Høj","Kritisk"], index=["Lav","Middel","Høj","Kritisk"].index(r["score"]) if r["score"] in ["Lav","Middel","Høj","Kritisk"] else 1)
                    weight = st.number_input("Vægt", value=int(r["vægt"]) if r["vægt"] else 5)
                    active = st.checkbox("Aktiv", value=bool(r["aktiv"]))
                    if st.form_submit_button("Gem ændringer"):
                        run("UPDATE trigger_rules SET name=?, pattern=?, default_score=?, weight=?, active=? WHERE id=?",
                            (name, pattern, score, weight, 1 if active else 0, int(r["id"])))
                        st.rerun()
                    if st.form_submit_button("Slet triggerregel"):
                        run("DELETE FROM trigger_rules WHERE id=?", (int(r["id"]),))
                        st.rerun()
