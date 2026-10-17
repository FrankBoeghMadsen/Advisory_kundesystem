from app_context import (
    clean_text_value,
    date,
    display_date,
    has_db_id,
    merge_text_values,
    now_iso,
    open_company_section,
    q,
    run,
    set_page,
    st,
)


def render():
    st.subheader("Møder")
    today_iso = date.today().isoformat()
    st.caption("Samlet overblik over kommende og tidligere møder på tværs af aktører.")

    companies = q("SELECT id, name FROM companies ORDER BY name")
    company_names = companies["name"].tolist() if len(companies) else []
    company_lookup = {row["name"]: int(row["id"]) for _, row in companies.iterrows()} if len(companies) else {}

    with st.expander("Opret møde", expanded=False):
        if not len(companies):
            st.info("Opret først en aktør under Virksomheder.")
        else:
            with st.form(f"meetings_add_{st.session_state.get('meetings_form_version',0)}", clear_on_submit=True):
                a, b, c = st.columns([1.3, 1, 1])
                selected_company = a.selectbox("Aktør", company_names)
                meeting_date = b.text_input("Dato", today_iso)
                meeting_time = c.text_input("Tid", "")
                d, e = st.columns([1.5, 1])
                title = d.text_input("Titel", "Møde")
                meeting_type = e.selectbox("Type", ["Kaffemøde", "Kundemøde", "Opfølgning", "Statusmøde", "Referat", "Andet"], index=0)
                location = st.text_input("Sted", "")
                participants = st.text_input("Deltagere", "")
                summary = st.text_area("Resume", "", height=110)
                next_steps = st.text_area("Næste skridt / frister", "", height=90)
                if st.form_submit_button("Gem møde"):
                    run(
                        """INSERT INTO meetings
                           (company_id, meeting_date, meeting_time, location, title, meeting_type, participants, relation_strength, confidentiality, summary, next_steps, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            company_lookup[selected_company],
                            meeting_date,
                            meeting_time,
                            location,
                            title,
                            meeting_type,
                            participants,
                            "Middel",
                            "Intern",
                            summary,
                            next_steps,
                            now_iso(),
                            now_iso(),
                        ),
                    )
                    st.session_state["meetings_form_version"] = st.session_state.get("meetings_form_version",0) + 1
                    st.success("Møde gemt.")
                    st.rerun()

    df = q("""SELECT m.id, m.company_id, m.meeting_date AS dato, m.meeting_time AS tid, m.location AS sted, c.name AS virksomhed, m.title AS titel,
                     m.meeting_type AS type, m.participants AS deltagere, m.summary AS resume,
                     m.key_takeaways AS læring, m.next_steps AS næste_skridt,
                     m.uploaded_filename AS filnavn, m.raw_text AS referattekst
              FROM meetings m LEFT JOIN companies c ON c.id=m.company_id
              ORDER BY m.meeting_date DESC, m.meeting_time DESC, m.created_at DESC""")
    if len(df):
        upcoming_count = int((df["dato"].fillna("") >= today_iso).sum())
        minutes_count = int((df["referattekst"].fillna("") != "").sum())
        metric_cols = st.columns(4)
        metric_cols[0].metric("Møder", len(df))
        metric_cols[1].metric("Kommende", upcoming_count)
        metric_cols[2].metric("Med referat", minutes_count)
        metric_cols[3].metric("Aktører", int(df["virksomhed"].nunique()))

        duplicate_groups = []
        for (company_id_value, date_value), group in df.groupby(["company_id", "dato"], dropna=False):
            if has_db_id(company_id_value) and clean_text_value(date_value) and len(group) > 1:
                first_row = group.iloc[0]
                duplicate_groups.append(
                    (
                        f"{display_date(date_value)} - {first_row['virksomhed']} ({len(group)} mødeposter)",
                        int(company_id_value),
                        clean_text_value(date_value),
                    )
                )

        if duplicate_groups:
            with st.expander("Mulige møder der kan samles", expanded=False):
                st.caption("Viser mødeposter med samme aktør og dato. Brug funktionen til at samle forberedelsesnoter og referat i én mødepost.")
                duplicate_label = st.selectbox("Mulig dublet", [label for label, _, _ in duplicate_groups])
                _, duplicate_company_id, duplicate_date = next(item for item in duplicate_groups if item[0] == duplicate_label)
                duplicate_rows = df[
                    (df["company_id"] == duplicate_company_id)
                    & (df["dato"].fillna("").astype(str) == duplicate_date)
                ].copy()
                meeting_options_for_merge = []
                for _, row in duplicate_rows.iterrows():
                    markers = []
                    if clean_text_value(row["referattekst"]):
                        markers.append("referat")
                    if clean_text_value(row["resume"]):
                        markers.append("resume")
                    if clean_text_value(row["næste_skridt"]):
                        markers.append("næste skridt")
                    marker_text = f" · {', '.join(markers)}" if markers else ""
                    meeting_options_for_merge.append((f"#{int(row['id'])} · {row['titel'] or 'Møde'}{marker_text}", int(row["id"])))

                with st.form("merge_meetings_form"):
                    keep_label = st.selectbox("Behold som hovedmøde", [label for label, _ in meeting_options_for_merge])
                    merge_label = st.selectbox("Flyt indhold fra og slet", [label for label, _ in meeting_options_for_merge])
                    merge_submitted = st.form_submit_button("Saml mødeposter")
                    if merge_submitted:
                        keep_id = dict(meeting_options_for_merge)[keep_label]
                        merge_id = dict(meeting_options_for_merge)[merge_label]
                        if keep_id == merge_id:
                            st.warning("Vælg to forskellige mødeposter.")
                        else:
                            keep_row = duplicate_rows[duplicate_rows["id"] == keep_id].iloc[0]
                            merge_row = duplicate_rows[duplicate_rows["id"] == merge_id].iloc[0]
                            merge_note = f"Tilføjet fra mødepost #{merge_id}: {merge_row['titel'] or 'Møde'}"
                            merged_title = clean_text_value(keep_row["titel"]) or clean_text_value(merge_row["titel"]) or "Møde"
                            merged_type = clean_text_value(keep_row["type"]) or clean_text_value(merge_row["type"])
                            merged_participants = merge_text_values(keep_row["deltagere"], merge_row["deltagere"], merge_note)
                            merged_summary = merge_text_values(keep_row["resume"], merge_row["resume"], merge_note)
                            merged_takeaways = merge_text_values(keep_row["læring"], merge_row["læring"], merge_note)
                            merged_next_steps = merge_text_values(keep_row["næste_skridt"], merge_row["næste_skridt"], merge_note)
                            merged_raw_text = merge_text_values(keep_row["referattekst"], merge_row["referattekst"], merge_note)
                            merged_filename = clean_text_value(keep_row["filnavn"]) or clean_text_value(merge_row["filnavn"])
                            merged_location = clean_text_value(keep_row["sted"]) or clean_text_value(merge_row["sted"])
                            merged_time = clean_text_value(keep_row["tid"]) or clean_text_value(merge_row["tid"])

                            run(
                                """UPDATE meetings
                                   SET title=?, meeting_type=?, meeting_time=?, location=?, participants=?,
                                       summary=?, key_takeaways=?, next_steps=?, raw_text=?, uploaded_filename=?, updated_at=?
                                   WHERE id=?""",
                                (
                                    merged_title,
                                    merged_type,
                                    merged_time,
                                    merged_location,
                                    merged_participants,
                                    merged_summary,
                                    merged_takeaways,
                                    merged_next_steps,
                                    merged_raw_text,
                                    merged_filename,
                                    now_iso(),
                                    keep_id,
                                ),
                            )
                            run("UPDATE uploaded_documents SET meeting_id=? WHERE meeting_id=?", (keep_id, merge_id))
                            run("UPDATE briefings SET meeting_id=?, updated_at=? WHERE meeting_id=?", (keep_id, now_iso(), merge_id))
                            run("UPDATE observations SET related_meeting_id=?, updated_at=? WHERE related_meeting_id=?", (keep_id, now_iso(), merge_id))
                            run("DELETE FROM meetings WHERE id=?", (merge_id,))
                            st.success("Mødeposterne er samlet.")
                            st.rerun()

        f1, f2, f3 = st.columns([1.1, 1, 1.4])
        timing_filter = f1.selectbox("Periode", ["Alle", "Kommende", "Tidligere"], index=0)
        actor_filter = f2.selectbox("Aktør", ["Alle"] + company_names)
        search_text = f3.text_input("Søg i titel, resume, næste skridt eller deltagere", "")

        shown = df.copy()
        if timing_filter == "Kommende":
            shown = shown[shown["dato"].fillna("") >= today_iso]
            shown = shown.sort_values(["dato", "tid"], ascending=[True, True])
        elif timing_filter == "Tidligere":
            shown = shown[shown["dato"].fillna("") < today_iso]
        if actor_filter != "Alle":
            shown = shown[shown["virksomhed"].fillna("") == actor_filter]
        if search_text.strip():
            needle = search_text.strip().lower()
            searchable = (
                shown["titel"].fillna("")
                + " "
                + shown["resume"].fillna("")
                + " "
                + shown["næste_skridt"].fillna("")
                + " "
                + shown["deltagere"].fillna("")
            ).str.lower()
            shown = shown[searchable.str.contains(needle, regex=False)]

        table_df = shown.drop(columns=["id", "company_id", "referattekst"])
        st.markdown(f"### Viste møder ({len(shown)})")
        st.dataframe(table_df, use_container_width=True, hide_index=True)
        with st.expander("Åbn referat / mødedetaljer", expanded=False):
            options = []
            for _, row in shown.iterrows():
                label = f"{display_date(row['dato'])} - {row['virksomhed']} - {row['titel']}"
                options.append((label, int(row["id"])))
            if options:
                selected_label = st.selectbox("Vælg møde", [label for label, _ in options])
                selected_id = dict(options)[selected_label]
                selected = shown[shown["id"] == selected_id].iloc[0]
                a, b = st.columns(2)
                if a.button("Åbn profil", key=f"meetings_detail_profile_{selected_id}", disabled=not has_db_id(selected["company_id"])):
                    open_company_section(int(selected["company_id"]), "Møder")
                    st.rerun()
                if b.button("Lav briefing", key=f"meetings_detail_briefing_{selected_id}", disabled=not has_db_id(selected["company_id"])):
                    st.session_state["selected_company_id"] = int(selected["company_id"])
                    st.session_state["selected_briefing_meeting_id"] = selected_id
                    set_page("Briefing")
                    st.rerun()
                if selected["filnavn"]:
                    st.caption(f"Uploadet fil: {selected['filnavn']}")
                if selected["resume"]:
                    st.markdown("**Resume**")
                    st.write(selected["resume"])
                if selected["læring"]:
                    st.markdown("**Hvad lærte vi**")
                    st.write(selected["læring"])
                if selected["næste_skridt"]:
                    st.markdown("**Næste skridt / frister**")
                    st.write(selected["næste_skridt"])
                if selected["referattekst"]:
                    st.markdown("**Referattekst**")
                    st.text_area("Referattekst", selected["referattekst"], height=360, key=f"meeting_page_raw_text_{selected_id}")
                else:
                    st.info("Der er ikke gemt referattekst på dette møde.")
            else:
                st.info("Ingen møder matcher filtrene.")
    else:
        st.info("Ingen møder endnu.")
