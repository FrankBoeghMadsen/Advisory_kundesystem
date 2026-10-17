from app_context import (
    display_date,
    q,
    run,
    short,
    st,
)


def render():
    st.subheader("Signalindbakke")
    df = q("""SELECT s.id, s.collected_at, c.name AS company, s.trigger_type, s.score,
                     s.title, s.raw_summary, s.source_excerpt, s.matched_terms, s.ai_summary,
                     s.suggested_reaction, COALESCE(s.review_status,'Ny') AS review_status,
                     s.review_note, s.url
              FROM signals s LEFT JOIN companies c ON c.id=s.company_id
              ORDER BY s.collected_at DESC""")
    f1, f2, f3 = st.columns(3)
    status_filter = f1.multiselect("Status", ["Ny","Til vurdering","Gemt på virksomhed","Irrelevant","Arkiveret"], default=["Ny","Til vurdering"])
    score_filter = f2.multiselect("Score", ["Lav","Middel","Høj","Kritisk"], default=["Lav","Middel","Høj","Kritisk"])
    search = f3.text_input("Søg")
    if len(df):
        df = df[df["review_status"].isin(status_filter)]
        df = df[df["score"].isin(score_filter)]
        if search:
            df = df[df["company"].fillna("").str.contains(search, case=False, na=False) | df["title"].fillna("").str.contains(search, case=False, na=False)]
    if len(df):
        for _, r in df.iterrows():
            with st.container(border=True):
                st.markdown(f"### {r['company'] or 'Ukendt'}")
                st.markdown(f"**{r['title']}**")
                st.caption(f"Dato: {display_date(r['collected_at'])} · Trigger: {r['trigger_type']} · Score: {r['score']} · Status: {r['review_status']}")
                if r["matched_terms"]:
                    st.write(f"**Match:** {r['matched_terms']}")
                preview = r["source_excerpt"] or r["ai_summary"] or r["raw_summary"] or ""
                if preview:
                    st.write(short(preview, 1400))
                if r["suggested_reaction"]:
                    st.write(f"**Foreløbig vurdering:** {r['suggested_reaction']}")
                if r["review_note"]:
                    st.info(f"Note: {r['review_note']}")
                btns = st.columns([1,1,1,1,1,2])
                if btns[0].button("Til vurdering", key=f"sig_review_{r['id']}"):
                    run("UPDATE signals SET review_status=? WHERE id=?", ("Til vurdering", int(r["id"]))); st.rerun()
                if btns[1].button("Gem", key=f"sig_save_{r['id']}"):
                    run("UPDATE signals SET review_status=? WHERE id=?", ("Gemt på virksomhed", int(r["id"]))); st.rerun()
                if btns[2].button("Irrelevant", key=f"sig_irr_{r['id']}"):
                    run("UPDATE signals SET review_status=? WHERE id=?", ("Irrelevant", int(r["id"]))); st.rerun()
                if btns[3].button("Arkivér", key=f"sig_arch_{r['id']}"):
                    run("UPDATE signals SET review_status=? WHERE id=?", ("Arkiveret", int(r["id"]))); st.rerun()
                if btns[4].button("Slet", key=f"sig_del_{r['id']}"):
                    run("DELETE FROM signals WHERE id=?", (int(r["id"]),)); st.rerun()
                if r["url"]:
                    btns[5].link_button("Åbn kilde", r["url"])
                with st.expander("Ret behandlingsnote"):
                    note = st.text_area("Note", value=r["review_note"] or "", key=f"sig_note_{r['id']}")
                    if st.button("Gem note", key=f"sig_note_save_{r['id']}"):
                        run("UPDATE signals SET review_note=? WHERE id=?", (note, int(r["id"]))); st.rerun()
    else:
        st.info("Ingen signaler matcher filteret.")
