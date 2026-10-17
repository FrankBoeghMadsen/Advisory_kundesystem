from app_context import (
    FOLLOWUP_STATUSES,
    FOLLOWUP_TYPES,
    date,
    followup_due_label,
    followup_group,
    has_db_id,
    now_iso,
    open_followup,
    q,
    run,
    severity_index,
    short,
    st,
)


def render():
    today_iso = date.today().isoformat()
    st.subheader("Opgaver / leads")
    st.caption("Samlet arbejdsbord for åbne opgaver, leads, kundeforløb og mødeopfølgninger.")

    companies = q("SELECT id, name FROM companies ORDER BY name")
    company_names = companies["name"].tolist() if len(companies) else []
    company_lookup = {row["name"]: int(row["id"]) for _, row in companies.iterrows()} if len(companies) else {}

    with st.expander("Opret ny opgave / lead", expanded=False):
        with st.form(f"tasks_add_followup_{st.session_state.get('tasks_followup_form_version',0)}", clear_on_submit=True):
            company_labels = ["Ingen aktør"] + company_names
            selected_company = st.selectbox("Aktør", company_labels)
            a, b, c = st.columns(3)
            title = a.text_input("Titel", value="")
            followup_type = b.selectbox("Type", FOLLOWUP_TYPES, index=0)
            priority = c.selectbox("Prioritet", ["Lav", "Middel", "Høj"], index=1)
            d, e, f = st.columns(3)
            due_date = d.text_input("Dato/timing", value="")
            status = e.selectbox("Status", ["Ny", "Planlagt", "I gang", "Afventer"], index=0)
            person = f.text_input("Person", value="")
            next_action = st.text_input("Næste handling", value="")
            description = st.text_area("Opgavebeskrivelse / baggrund", value="", height=120)
            if st.form_submit_button("Gem opgave"):
                selected_company_id = company_lookup.get(selected_company) if selected_company != "Ingen aktør" else None
                run(
                    """INSERT INTO followups
                       (company_id, title, followup_type, description, next_action, person, due_date, priority, status, source_type, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (selected_company_id, title, followup_type, description, next_action, person, due_date, priority, status, "Opgaver", now_iso(), now_iso()),
                )
                st.session_state["tasks_followup_form_version"] = st.session_state.get("tasks_followup_form_version",0) + 1
                st.success("Opgave gemt.")
                st.rerun()

    followups = q("""SELECT f.*, c.name AS company, t.title AS commercial_track,
                            d.title AS deliverable
                     FROM followups f
                     LEFT JOIN companies c ON c.id=f.company_id
                     LEFT JOIN commercial_tracks t ON t.id=f.commercial_track_id
                     LEFT JOIN deliverables d ON d.id=f.deliverable_id
                     ORDER BY
                        CASE COALESCE(f.status,'Ny') WHEN 'Lukket' THEN 2 WHEN 'Arkiveret' THEN 3 ELSE 1 END,
                        CASE f.priority WHEN 'Høj' THEN 1 WHEN 'Middel' THEN 2 ELSE 3 END,
                        CASE WHEN f.due_date='' OR f.due_date IS NULL THEN 1 ELSE 0 END,
                        f.due_date ASC,
                        f.created_at DESC""")

    if len(followups):
        followups["status"] = followups["status"].fillna("Ny")
        followups["priority"] = followups["priority"].fillna("Middel")
        followups["followup_type"] = followups["followup_type"].fillna("Opfølgning")
        followups["dashboard_group"] = followups.apply(lambda row: followup_group(row, today_iso), axis=1)

        open_df = followups[~followups["status"].isin(["Lukket", "Arkiveret"])]
        overdue_count = int((open_df["dashboard_group"] == "Forfaldne").sum()) if len(open_df) else 0
        next30_count = int((open_df["dashboard_group"] == "Næste 30 dage").sum()) if len(open_df) else 0
        undated_count = int((open_df["dashboard_group"] == "Uden dato").sum()) if len(open_df) else 0
        metric_cols = st.columns(5)
        metric_cols[0].metric("Åbne", len(open_df))
        metric_cols[1].metric("Forfaldne", overdue_count)
        metric_cols[2].metric("Næste 30 dage", next30_count)
        metric_cols[3].metric("Uden dato", undated_count)
        metric_cols[4].metric("Lukkede", int((followups["status"] == "Lukket").sum()))

        f1, f2, f3, f4 = st.columns([1.3, 1, 1, 1.2])
        status_filter = f1.multiselect(
            "Status",
            FOLLOWUP_STATUSES,
            default=["Ny", "Planlagt", "I gang", "Afventer"],
        )
        priority_filter = f2.multiselect("Prioritet", ["Lav", "Middel", "Høj"], default=["Høj", "Middel"])
        type_filter = f3.multiselect("Type", FOLLOWUP_TYPES, default=FOLLOWUP_TYPES)
        actor_filter = f4.selectbox("Aktør", ["Alle"] + company_names)
        search_text = st.text_input("Søg i titel, handling, beskrivelse eller person", value="")

        shown = followups.copy()
        if status_filter:
            shown = shown[shown["status"].isin(status_filter)]
        if priority_filter:
            shown = shown[shown["priority"].isin(priority_filter)]
        if type_filter:
            shown = shown[shown["followup_type"].isin(type_filter)]
        if actor_filter != "Alle":
            shown = shown[shown["company"].fillna("") == actor_filter]
        if search_text.strip():
            needle = search_text.strip().lower()
            searchable = (
                shown["title"].fillna("")
                + " "
                + shown["next_action"].fillna("")
                + " "
                + shown["description"].fillna("")
                + " "
                + shown["person"].fillna("")
            ).str.lower()
            shown = shown[searchable.str.contains(needle, regex=False)]

        st.markdown(f"### Viste opgaver ({len(shown)})")
        if len(shown):
            for _, task in shown.iterrows():
                task_id = int(task["id"])
                due = followup_due_label(task["due_date"], today_iso)
                title = task["title"] or "(uden titel)"
                company = task["company"] or "Ingen aktør"
                with st.container(border=True):
                    top_a, top_b = st.columns([4, 1])
                    top_a.markdown(f"**{title}**")
                    top_a.caption(f"{company} · {due} · {task['followup_type']} · {task['priority']} · {task['status']}")
                    if task["commercial_track"]:
                        context = f"Forløb: {task['commercial_track']}"
                        if task["deliverable"]:
                            context += f" · Leverance: {task['deliverable']}"
                        top_a.caption(context)
                    if top_b.button("Åbn profil", key=f"tasks_open_profile_{task_id}", disabled=not has_db_id(task["company_id"])):
                        open_followup(int(task["company_id"]), task_id)
                        st.rerun()
                    if task["next_action"]:
                        st.write(f"**Næste handling:** {task['next_action']}")
                    if task["description"]:
                        st.write(short(task["description"], 260))
                    with st.expander("Redigér"):
                        with st.form(f"tasks_edit_followup_{task_id}"):
                            ea, eb, ec = st.columns(3)
                            edit_title = ea.text_input("Titel", task["title"] or "")
                            edit_type = eb.selectbox("Type", FOLLOWUP_TYPES, index=severity_index(task["followup_type"] or "Opfølgning", FOLLOWUP_TYPES))
                            edit_priority = ec.selectbox("Prioritet", ["Lav", "Middel", "Høj"], index=severity_index(task["priority"] or "Middel", ["Lav", "Middel", "Høj"]))
                            ed, ee, ef = st.columns(3)
                            edit_due = ed.text_input("Dato/timing", task["due_date"] or "")
                            edit_status = ee.selectbox("Status", FOLLOWUP_STATUSES, index=severity_index(task["status"] or "Ny", FOLLOWUP_STATUSES))
                            edit_person = ef.text_input("Person", task["person"] or "")
                            edit_next_action = st.text_input("Næste handling", task["next_action"] or "")
                            edit_description = st.text_area("Beskrivelse", task["description"] or "", height=120)
                            save_task = st.form_submit_button("Gem ændringer")
                            delete_task = st.form_submit_button("Slet opgave")
                            if save_task:
                                run(
                                    """UPDATE followups
                                       SET title=?, followup_type=?, description=?, next_action=?, person=?, due_date=?, priority=?, status=?, updated_at=?
                                       WHERE id=?""",
                                    (edit_title, edit_type, edit_description, edit_next_action, edit_person, edit_due, edit_priority, edit_status, now_iso(), task_id),
                                )
                                st.success("Opgave opdateret.")
                                st.rerun()
                            if delete_task:
                                run("DELETE FROM followups WHERE id=?", (task_id,))
                                st.success("Opgave slettet.")
                                st.rerun()
        else:
            st.info("Ingen opgaver matcher filtrene.")
    else:
        st.info("Der er endnu ikke oprettet opgaver eller leads.")
