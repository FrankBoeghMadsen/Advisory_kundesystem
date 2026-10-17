from app_context import (
    ai_briefing_text,
    briefing_context,
    datetime,
    display_date,
    latest_meeting_id,
    meeting_focus_context,
    meeting_options,
    now_iso,
    open_company_section,
    q,
    run,
    short,
    st,
)


def render():
    st.subheader("Briefing-generator")
    companies = q("SELECT id, name FROM companies ORDER BY name")
    if len(companies):
        company_ids = companies["id"].tolist()
        default_id = st.session_state.get("selected_company_id", company_ids[0])
        default_index = company_ids.index(default_id) if default_id in company_ids else 0
        top_left, top_right = st.columns([1.2, 1.8])
        selected = top_left.selectbox("Aktør", companies["name"].tolist(), index=default_index)
        cid = int(companies[companies["name"] == selected]["id"].iloc[0])
        st.session_state["selected_company_id"] = cid

        latest_id = latest_meeting_id(cid)
        preferred_meeting_id = st.session_state.get("selected_briefing_meeting_id", latest_id)
        if preferred_meeting_id and not len(q("SELECT id FROM meetings WHERE company_id=? AND id=?", (cid, int(preferred_meeting_id)))):
            preferred_meeting_id = latest_id
        labels, values, selected_index = meeting_options(cid, preferred_meeting_id)
        selected_meeting = top_right.selectbox("Møde der forberedes", labels, index=selected_index)
        selected_meeting_id = values[selected_meeting]
        st.session_state["selected_briefing_meeting_id"] = selected_meeting_id

        context = briefing_context(cid) + meeting_focus_context(cid, selected_meeting_id)

        st.markdown(f"## Mødeforberedelse: {selected}")
        if selected_meeting_id:
            st.caption(f"Fokus: {selected_meeting}")
        else:
            st.caption("Fokus: generel briefing uden mødekobling")

        tab_draft, tab_data, tab_saved, tab_context = st.tabs(["AI-udkast", "Datagrundlag", "Gemte briefings", "Rå kontekst"])

        with tab_draft:
            st.markdown("### AI-udkast til mødeforberedelse")
            generated_key = f"generated_briefing_{cid}_{selected_meeting_id or 'none'}"
            allow_external_briefing = st.checkbox(
                "Tillad, at datagrundlaget sendes til OpenAI for denne briefing",
                value=False,
                key=f"allow_external_briefing_{cid}_{selected_meeting_id or 'none'}",
            )
            a, b = st.columns([1, 1])
            if a.button("Generér briefing", type="primary"):
                st.session_state[generated_key] = ai_briefing_text(
                    selected, context, allow_external=allow_external_briefing
                )
            if b.button("Åbn profil"):
                open_company_section(cid, "Briefing")
                st.rerun()
            if generated_key in st.session_state:
                briefing_text = st.session_state[generated_key]
                st.markdown(briefing_text)
                with st.form(f"save_briefing_{cid}_{selected_meeting_id or 'none'}"):
                    default_title = f"Briefing - {selected} - {datetime.now().strftime('%Y-%m-%d')}"
                    title = st.text_input("Titel", default_title)
                    user_notes = st.text_area("Egne noter", value="", height=120)
                    if st.form_submit_button("Gem briefing på profilen"):
                        existing = q("SELECT MAX(version) AS max_version FROM briefings WHERE company_id=?", (cid,))
                        max_version = int(existing["max_version"].iloc[0] or 0) if len(existing) else 0
                        run(
                            """INSERT INTO briefings
                               (company_id, meeting_id, title, briefing_text, user_notes, source_context, version, status, created_at, updated_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                cid,
                                selected_meeting_id,
                                title,
                                briefing_text,
                                user_notes,
                                context,
                                max_version + 1,
                                "Aktiv",
                                now_iso(),
                                now_iso(),
                            ),
                        )
                        st.success("Briefing gemt på profilen.")
            else:
                st.info("Vælg aktør og møde øverst, og generér derefter et mødebrief. Hvis OpenAI API-nøgle ikke er sat, laves en lokal struktureret briefing.")

        with tab_data:
            st.markdown("### Datagrundlag")
            for heading, sql in [
                ("Seneste møder", "SELECT meeting_date AS dato, meeting_time AS tid, location AS sted, title AS titel, key_takeaways AS læring, next_steps AS næste_skridt FROM meetings WHERE company_id=? ORDER BY meeting_date DESC, meeting_time DESC LIMIT 5"),
                ("Åbne opfølgninger / leads", "SELECT due_date AS dato, title AS titel, followup_type AS type, next_action AS næste_handling, person AS person, priority AS prioritet, status AS status, description AS beskrivelse FROM followups WHERE company_id=? AND COALESCE(status,'Ny') NOT IN ('Lukket','Arkiveret') ORDER BY due_date ASC, created_at DESC LIMIT 8"),
                ("Observationer", "SELECT observation_date AS dato, title AS titel, observation_type AS type, confidence AS tillid, verification_status AS verifikation FROM observations WHERE company_id=? ORDER BY observation_date DESC LIMIT 8"),
                ("Historik / sager", "SELECT title AS titel, case_type AS type, severity AS alvor, relevance AS relevans, summary AS resume FROM company_cases WHERE company_id=? ORDER BY period_start DESC LIMIT 5"),
                ("Signaler", "SELECT collected_at AS dato, title AS titel, trigger_type AS trigger, score AS score FROM signals WHERE company_id=? ORDER BY collected_at DESC LIMIT 8")
            ]:
                df = q(sql, (cid,))
                if len(df):
                    st.markdown(f"**{heading}**")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.caption(f"Ingen data: {heading}")

        with tab_saved:
            st.markdown("### Gemte briefings")
            saved_briefings = q(
                """SELECT b.*, m.title AS meeting_title, m.meeting_date, m.meeting_time
                   FROM briefings b
                   LEFT JOIN meetings m ON m.id=b.meeting_id
                   WHERE b.company_id=?
                   ORDER BY b.created_at DESC, b.id DESC
                   LIMIT 10""",
                (cid,),
            )
            if len(saved_briefings):
                for _, b_row in saved_briefings.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**{b_row['title']}**")
                        meta = [f"Oprettet: {display_date(b_row['created_at'])}", f"version {int(b_row['version'] or 1)}", b_row["status"]]
                        st.caption(" · ".join([m for m in meta if m]))
                        if b_row["meeting_id"]:
                            meeting_label = display_date(b_row["meeting_date"]) or "Ukendt dato"
                            if b_row["meeting_time"]:
                                meeting_label += f" kl. {b_row['meeting_time']}"
                            st.caption(f"Knyttet til møde: {meeting_label} - {b_row['meeting_title'] or 'Møde'}")
                        st.write(short(b_row["briefing_text"], 700))
                        with st.expander("Læs hele briefingen"):
                            st.markdown(b_row["briefing_text"])
                            if b_row["user_notes"]:
                                st.markdown("**Egne noter**")
                                st.write(b_row["user_notes"])
            else:
                st.info("Ingen gemte briefings for denne aktør endnu.")

        with tab_context:
            st.markdown("### Rå kontekst brugt til briefing")
            st.text_area("Kontekst", context, height=300)
