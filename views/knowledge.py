from app_context import (
    display_date,
    has_db_id,
    now_iso,
    open_company_section,
    q,
    run,
    severity_index,
    short,
    st,
)


def render():
    st.subheader("Viden / noter")
    st.caption("Samlet overblik over frie noter og strukturerede videnbank-punkter på tværs af aktører.")

    companies = q("SELECT id, name FROM companies ORDER BY name")
    company_names = companies["name"].tolist() if len(companies) else []
    company_lookup = {row["name"]: int(row["id"]) for _, row in companies.iterrows()} if len(companies) else {}

    with st.expander("Opret note eller viden", expanded=False):
        if not len(companies):
            st.info("Opret først en aktør under Virksomheder.")
        else:
            with st.form(f"knowledge_add_{st.session_state.get('knowledge_form_version',0)}", clear_on_submit=True):
                a, b, c = st.columns([1.2, 1, 1])
                selected_company = a.selectbox("Aktør", company_names)
                entry_kind = b.selectbox("Indholdstype", ["Note", "Videnbank"], index=0)
                memory_type = c.selectbox("Videns-type", ["Observation", "Relation", "Kultur", "Regulatorisk modenhed", "Historisk erfaring", "Strategisk mulighed"], index=0)
                title = st.text_input("Titel", "")
                content = st.text_area("Indhold", "", height=170)
                confidence = st.selectbox("Sikkerhed", ["Lav", "Middel", "Høj"], index=1)
                if st.form_submit_button("Gem"):
                    if entry_kind == "Note":
                        run(
                            "INSERT INTO notes (company_id, title, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                            (company_lookup[selected_company], title, content, now_iso(), now_iso()),
                        )
                    else:
                        run(
                            "INSERT INTO intelligence_memory (company_id, memory_type, title, content, confidence, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (company_lookup[selected_company], memory_type, title, content, confidence, now_iso(), now_iso()),
                        )
                    st.session_state["knowledge_form_version"] = st.session_state.get("knowledge_form_version",0) + 1
                    st.success("Indhold gemt.")
                    st.rerun()

    notes_df = q("""SELECT n.id, n.company_id, c.name AS actor, 'Note' AS kind, '' AS memory_type,
                           n.title, n.note AS content, '' AS confidence, n.created_at, n.updated_at
                    FROM notes n LEFT JOIN companies c ON c.id=n.company_id""")
    memory_df = q("""SELECT m.id, m.company_id, c.name AS actor, 'Videnbank' AS kind, m.memory_type,
                            m.title, m.content, m.confidence, m.created_at, m.updated_at
                     FROM intelligence_memory m LEFT JOIN companies c ON c.id=m.company_id""")
    items = []
    if len(notes_df):
        items.append(notes_df)
    if len(memory_df):
        items.append(memory_df)

    if items:
        import pandas as pd
        knowledge = pd.concat(items, ignore_index=True)
        knowledge["actor"] = knowledge["actor"].fillna("Ingen aktør")
        knowledge["title"] = knowledge["title"].fillna("")
        knowledge["content"] = knowledge["content"].fillna("")
        knowledge["created_at"] = knowledge["created_at"].fillna("")
        knowledge = knowledge.sort_values(["created_at", "id"], ascending=[False, False])

        note_count = int((knowledge["kind"] == "Note").sum())
        memory_count = int((knowledge["kind"] == "Videnbank").sum())
        high_confidence_count = int((knowledge["confidence"].fillna("") == "Høj").sum())
        actor_count = int(knowledge["actor"].nunique())
        metric_cols = st.columns(4)
        metric_cols[0].metric("Viden/noter", len(knowledge))
        metric_cols[1].metric("Noter", note_count)
        metric_cols[2].metric("Videnbank", memory_count)
        metric_cols[3].metric("Aktører", actor_count)
        st.caption(f"Høj sikkerhed: {high_confidence_count}")

        f1, f2, f3, f4 = st.columns([1, 1, 1, 1.4])
        actor_filter = f1.selectbox("Aktør", ["Alle"] + company_names)
        kind_filter = f2.multiselect("Indholdstype", ["Note", "Videnbank"], default=["Note", "Videnbank"])
        confidence_filter = f3.multiselect("Sikkerhed", ["Lav", "Middel", "Høj"], default=["Lav", "Middel", "Høj"])
        search_text = f4.text_input("Søg i titel eller indhold", "")

        shown = knowledge.copy()
        if actor_filter != "Alle":
            shown = shown[shown["actor"] == actor_filter]
        if kind_filter:
            shown = shown[shown["kind"].isin(kind_filter)]
        if confidence_filter:
            shown = shown[(shown["kind"] == "Note") | (shown["confidence"].isin(confidence_filter))]
        if search_text.strip():
            needle = search_text.strip().lower()
            searchable = (shown["title"].fillna("") + " " + shown["content"].fillna("") + " " + shown["memory_type"].fillna("")).str.lower()
            shown = shown[searchable.str.contains(needle, regex=False)]

        st.markdown(f"### Vist viden ({len(shown)})")
        if len(shown):
            table_df = shown.copy()
            table_df["dato"] = table_df["created_at"].apply(display_date)
            table_df["visning"] = table_df["content"].apply(lambda value: short(value, 180))
            st.dataframe(
                table_df[["dato", "actor", "kind", "memory_type", "title", "confidence", "visning"]],
                use_container_width=True,
                hide_index=True,
            )

            with st.expander("Åbn / redigér viden eller note", expanded=False):
                options = []
                for _, row in shown.iterrows():
                    title = row["title"] or row["memory_type"] or row["kind"]
                    options.append((f"{display_date(row['created_at'])} · {row['actor']} · {row['kind']} · {title}", f"{row['kind']}:{int(row['id'])}"))
                selected_label = st.selectbox("Vælg indhold", [label for label, _ in options])
                selected_key = dict(options)[selected_label]
                selected_kind, selected_raw_id = selected_key.split(":", 1)
                selected_id = int(selected_raw_id)
                selected = shown[(shown["kind"] == selected_kind) & (shown["id"] == selected_id)].iloc[0]

                a, b = st.columns(2)
                if a.button("Åbn aktørprofil", key=f"knowledge_open_profile_{selected_kind}_{selected_id}", disabled=not has_db_id(selected["company_id"])):
                    open_company_section(int(selected["company_id"]), "Noter" if selected_kind == "Note" else "Videnbank")
                    st.rerun()
                if b.button("Opret opgave", key=f"knowledge_create_task_{selected_kind}_{selected_id}", disabled=not has_db_id(selected["company_id"])):
                    run(
                        """INSERT INTO followups
                           (company_id, title, followup_type, description, next_action, person, due_date, priority, status, source_type, source_id, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            int(selected["company_id"]),
                            f"Opfølgning på {selected_kind.lower()}: {selected['title'] or selected['memory_type'] or 'uden titel'}",
                            "Opfølgning",
                            selected["content"],
                            "Vurder om viden/noten kræver konkret handling",
                            "",
                            "",
                            "Middel",
                            "Ny",
                            selected_kind,
                            selected_id,
                            now_iso(),
                            now_iso(),
                        ),
                    )
                    st.success("Opgave oprettet.")
                    st.rerun()

                with st.form(f"knowledge_edit_{selected_kind}_{selected_id}"):
                    ea, eb = st.columns([1.2, 1])
                    edit_actor = ea.selectbox(
                        "Aktør",
                        company_names,
                        index=company_names.index(selected["actor"]) if selected["actor"] in company_names else 0,
                    )
                    edit_title = eb.text_input("Titel", selected["title"] or "")
                    edit_content = st.text_area("Indhold", selected["content"] or "", height=190)
                    if selected_kind == "Videnbank":
                        ec, ed = st.columns(2)
                        edit_memory_type = ec.selectbox(
                            "Videns-type",
                            ["Observation", "Relation", "Kultur", "Regulatorisk modenhed", "Historisk erfaring", "Strategisk mulighed"],
                            index=severity_index(selected["memory_type"], ["Observation", "Relation", "Kultur", "Regulatorisk modenhed", "Historisk erfaring", "Strategisk mulighed"]),
                        )
                        edit_confidence = ed.selectbox("Sikkerhed", ["Lav", "Middel", "Høj"], index=severity_index(selected["confidence"], ["Lav", "Middel", "Høj"]))
                    save_item = st.form_submit_button("Gem ændringer")
                    delete_item = st.form_submit_button("Slet")
                    if save_item:
                        if selected_kind == "Note":
                            run(
                                "UPDATE notes SET company_id=?, title=?, note=?, updated_at=? WHERE id=?",
                                (company_lookup[edit_actor], edit_title, edit_content, now_iso(), selected_id),
                            )
                        else:
                            run(
                                "UPDATE intelligence_memory SET company_id=?, memory_type=?, title=?, content=?, confidence=?, updated_at=? WHERE id=?",
                                (company_lookup[edit_actor], edit_memory_type, edit_title, edit_content, edit_confidence, now_iso(), selected_id),
                            )
                        st.success("Indhold opdateret.")
                        st.rerun()
                    if delete_item:
                        if selected_kind == "Note":
                            run("DELETE FROM notes WHERE id=?", (selected_id,))
                        else:
                            run("DELETE FROM intelligence_memory WHERE id=?", (selected_id,))
                        st.success("Indhold slettet.")
                        st.rerun()
        else:
            st.info("Ingen viden/noter matcher filtrene.")
    else:
        st.info("Der er endnu ingen noter eller videnbank-punkter.")
