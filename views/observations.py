from app_context import (
    date,
    display_date,
    has_db_id,
    now_iso,
    open_company_section,
    q,
    run,
    severity_index,
    st,
)


def render():
    st.subheader("Observationer")
    today_iso = date.today().isoformat()
    st.caption("Tværgående overblik over observationer, indsigter, LinkedIn-noter og forhold der bør verificeres.")

    companies = q("SELECT id, name FROM companies ORDER BY name")
    company_names = companies["name"].tolist() if len(companies) else []
    company_lookup = {row["name"]: int(row["id"]) for _, row in companies.iterrows()} if len(companies) else {}

    with st.expander("Opret observation", expanded=False):
        if not len(companies):
            st.info("Opret først en aktør under Virksomheder.")
        else:
            with st.form(f"observations_add_{st.session_state.get('observations_form_version',0)}", clear_on_submit=True):
                a, b, c = st.columns([1.3, 1, 1])
                selected_company = a.selectbox("Aktør", company_names)
                observation_date = b.text_input("Dato", today_iso)
                observation_type = c.selectbox("Type", ["Observation", "OSINT-signal", "Mødeindsigt", "Relation", "Risiko", "Mulighed"], index=0)
                title = st.text_input("Titel", "")
                source_type = st.selectbox("Kilde", ["Manuel", "LinkedIn", "Møde", "OSINT", "Kunde", "Andet"], index=0)
                d, e = st.columns(2)
                confidence = d.selectbox("Tillid", ["Lav", "Middel", "Høj"], index=1)
                verification_status = e.selectbox("Verifikation", ["Ikke verificeret", "Bør verificeres", "Delvist verificeret", "Verificeret"], index=1)
                content = st.text_area("Indhold", "", height=120)
                implication = st.text_area("Mulig betydning", "", height=90)
                follow_up = st.text_area("Opfølgning", "", height=90)
                if st.form_submit_button("Gem observation"):
                    run(
                        """INSERT INTO observations
                           (company_id, observation_date, title, observation_type, source_type, confidence, verification_status, content, implication, follow_up, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            company_lookup[selected_company],
                            observation_date,
                            title,
                            observation_type,
                            source_type,
                            confidence,
                            verification_status,
                            content,
                            implication,
                            follow_up,
                            now_iso(),
                            now_iso(),
                        ),
                    )
                    st.session_state["observations_form_version"] = st.session_state.get("observations_form_version",0) + 1
                    st.success("Observation gemt.")
                    st.rerun()

    df = q("""SELECT o.id, o.company_id, o.observation_date AS dato, c.name AS virksomhed, o.title AS titel, o.observation_type AS type,
                     o.source_type AS kilde, o.confidence AS tillid, o.verification_status AS verifikation,
                     o.content AS indhold, o.implication AS betydning, o.follow_up AS opfølgning
              FROM observations o LEFT JOIN companies c ON c.id=o.company_id
              ORDER BY o.observation_date DESC, o.created_at DESC""")
    if len(df):
        verify_count = int((df["verifikation"].fillna("") == "Bør verificeres").sum())
        unverified_count = int((df["verifikation"].fillna("") == "Ikke verificeret").sum())
        high_confidence_count = int((df["tillid"].fillna("") == "Høj").sum())
        followup_count = int((df["opfølgning"].fillna("") != "").sum())
        metric_cols = st.columns(4)
        metric_cols[0].metric("Observationer", len(df))
        metric_cols[1].metric("Bør verificeres", verify_count)
        metric_cols[2].metric("Ikke verificeret", unverified_count)
        metric_cols[3].metric("Med opfølgning", followup_count)

        f1, f2, f3, f4 = st.columns([1, 1, 1, 1.3])
        actor_filter = f1.selectbox("Aktør", ["Alle"] + company_names)
        verification_filter = f2.multiselect(
            "Verifikation",
            ["Ikke verificeret", "Bør verificeres", "Delvist verificeret", "Verificeret"],
            default=["Ikke verificeret", "Bør verificeres", "Delvist verificeret", "Verificeret"],
        )
        confidence_filter = f3.multiselect("Tillid", ["Lav", "Middel", "Høj"], default=["Middel", "Høj"])
        search_text = f4.text_input("Søg", "")

        shown = df.copy()
        if actor_filter != "Alle":
            shown = shown[shown["virksomhed"].fillna("") == actor_filter]
        if verification_filter:
            shown = shown[shown["verifikation"].isin(verification_filter)]
        if confidence_filter:
            shown = shown[shown["tillid"].isin(confidence_filter)]
        if search_text.strip():
            needle = search_text.strip().lower()
            searchable = (
                shown["titel"].fillna("")
                + " "
                + shown["indhold"].fillna("")
                + " "
                + shown["betydning"].fillna("")
                + " "
                + shown["opfølgning"].fillna("")
            ).str.lower()
            shown = shown[searchable.str.contains(needle, regex=False)]

        st.caption(f"Høj tillid: {high_confidence_count}")
        st.markdown(f"### Viste observationer ({len(shown)})")
        if len(shown):
            table_df = shown.drop(columns=["id", "company_id", "indhold"])
            st.dataframe(table_df, use_container_width=True, hide_index=True)

            with st.expander("Åbn / redigér observation", expanded=False):
                options = []
                for _, row in shown.iterrows():
                    label = f"{display_date(row['dato'])} - {row['virksomhed']} - {row['titel']}"
                    options.append((label, int(row["id"])))
                selected_label = st.selectbox("Vælg observation", [label for label, _ in options])
                selected_id = dict(options)[selected_label]
                selected = shown[shown["id"] == selected_id].iloc[0]
                a, b = st.columns(2)
                if a.button("Åbn profil", key=f"obs_detail_profile_{selected_id}", disabled=not has_db_id(selected["company_id"])):
                    open_company_section(int(selected["company_id"]), "Observationer")
                    st.rerun()
                if b.button("Opret opgave", key=f"obs_detail_followup_{selected_id}", disabled=not has_db_id(selected["company_id"])):
                    run(
                        """INSERT INTO followups
                           (company_id, title, followup_type, description, next_action, person, due_date, priority, status, source_type, source_id, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            int(selected["company_id"]),
                            f"Opfølgning på observation: {selected['titel']}",
                            "Opfølgning",
                            selected["indhold"] or selected["betydning"] or "",
                            selected["opfølgning"] or "Afklar observation og vurder næste skridt",
                            "",
                            "",
                            "Middel",
                            "Ny",
                            "Observation",
                            selected_id,
                            now_iso(),
                            now_iso(),
                        ),
                    )
                    st.success("Opgave oprettet fra observation.")
                    st.rerun()

                with st.form(f"observations_edit_{selected_id}"):
                    ea, eb, ec = st.columns([1.4, 1, 1])
                    edit_title = ea.text_input("Titel", selected["titel"] or "")
                    edit_date = eb.text_input("Dato", selected["dato"] or "")
                    edit_type = ec.selectbox("Type", ["Observation", "OSINT-signal", "Mødeindsigt", "Relation", "Risiko", "Mulighed"], index=severity_index(selected["type"], ["Observation", "OSINT-signal", "Mødeindsigt", "Relation", "Risiko", "Mulighed"]))
                    ed, ee, ef = st.columns(3)
                    edit_source = ed.selectbox("Kilde", ["Manuel", "LinkedIn", "Møde", "OSINT", "Kunde", "Andet"], index=severity_index(selected["kilde"], ["Manuel", "LinkedIn", "Møde", "OSINT", "Kunde", "Andet"]))
                    edit_confidence = ee.selectbox("Tillid", ["Lav", "Middel", "Høj"], index=severity_index(selected["tillid"], ["Lav", "Middel", "Høj"]))
                    edit_verification = ef.selectbox("Verifikation", ["Ikke verificeret", "Bør verificeres", "Delvist verificeret", "Verificeret"], index=severity_index(selected["verifikation"], ["Ikke verificeret", "Bør verificeres", "Delvist verificeret", "Verificeret"]))
                    edit_content = st.text_area("Indhold", selected["indhold"] or "", height=130)
                    edit_implication = st.text_area("Mulig betydning", selected["betydning"] or "", height=90)
                    edit_follow_up = st.text_area("Opfølgning", selected["opfølgning"] or "", height=90)
                    save_obs = st.form_submit_button("Gem ændringer")
                    delete_obs = st.form_submit_button("Slet observation")
                    if save_obs:
                        run(
                            """UPDATE observations
                               SET observation_date=?, title=?, observation_type=?, source_type=?, confidence=?, verification_status=?, content=?, implication=?, follow_up=?, updated_at=?
                               WHERE id=?""",
                            (edit_date, edit_title, edit_type, edit_source, edit_confidence, edit_verification, edit_content, edit_implication, edit_follow_up, now_iso(), selected_id),
                        )
                        st.success("Observation opdateret.")
                        st.rerun()
                    if delete_obs:
                        run("DELETE FROM observations WHERE id=?", (selected_id,))
                        st.success("Observation slettet.")
                        st.rerun()
        else:
            st.info("Ingen observationer matcher filtrene.")
    else:
        st.info("Ingen observationer endnu.")
