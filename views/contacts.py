from app_context import (
    has_db_id,
    now_iso,
    open_company_section,
    q,
    run,
    st,
)


def render():
    st.subheader("Kontakter / relationer")
    st.caption("Samlet relationsregister på tværs af aktører.")

    companies = q("SELECT id, name FROM companies ORDER BY name")
    company_names = companies["name"].tolist() if len(companies) else []
    company_lookup = {row["name"]: int(row["id"]) for _, row in companies.iterrows()} if len(companies) else {}

    with st.expander("Opret kontakt", expanded=False):
        if not len(companies):
            st.info("Opret først en aktør under Virksomheder.")
        else:
            with st.form(f"contacts_add_{st.session_state.get('contacts_form_version',0)}", clear_on_submit=True):
                a, b = st.columns([1.2, 1])
                selected_company = a.selectbox("Aktør", company_names)
                name = b.text_input("Navn", "")
                c, d, e = st.columns(3)
                role = c.text_input("Rolle", "")
                phone = d.text_input("Telefon", "")
                email = e.text_input("Email", "")
                linkedin = st.text_input("LinkedIn", "")
                notes = st.text_area("Noter", "", height=100)
                if st.form_submit_button("Gem kontakt"):
                    run(
                        "INSERT INTO contacts (company_id, name, role, phone, email, linkedin, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (company_lookup[selected_company], name, role, phone, email, linkedin, notes, now_iso()),
                    )
                    st.session_state["contacts_form_version"] = st.session_state.get("contacts_form_version",0) + 1
                    st.success("Kontakt gemt.")
                    st.rerun()

    contacts = q("""SELECT ct.id, ct.company_id, c.name AS actor, ct.name, ct.role, ct.phone, ct.email, ct.linkedin, ct.notes, ct.created_at
                    FROM contacts ct LEFT JOIN companies c ON c.id=ct.company_id
                    ORDER BY c.name, ct.name""")

    if len(contacts):
        contacts["actor"] = contacts["actor"].fillna("Ingen aktør")
        with_phone = int((contacts["phone"].fillna("") != "").sum())
        with_email = int((contacts["email"].fillna("") != "").sum())
        with_linkedin = int((contacts["linkedin"].fillna("") != "").sum())
        actor_count = int(contacts["actor"].nunique())
        metric_cols = st.columns(4)
        metric_cols[0].metric("Kontakter", len(contacts))
        metric_cols[1].metric("Aktører", actor_count)
        metric_cols[2].metric("Med telefon", with_phone)
        metric_cols[3].metric("Med LinkedIn", with_linkedin)
        st.caption(f"Med email: {with_email}")

        f1, f2, f3 = st.columns([1, 1, 1.4])
        actor_filter = f1.selectbox("Aktør", ["Alle"] + company_names)
        channel_filter = f2.selectbox("Kontaktinfo", ["Alle", "Mangler telefon", "Mangler email", "Har LinkedIn"], index=0)
        search_text = f3.text_input("Søg i navn, rolle, noter eller kontaktinfo", "")

        shown = contacts.copy()
        if actor_filter != "Alle":
            shown = shown[shown["actor"] == actor_filter]
        if channel_filter == "Mangler telefon":
            shown = shown[shown["phone"].fillna("") == ""]
        elif channel_filter == "Mangler email":
            shown = shown[shown["email"].fillna("") == ""]
        elif channel_filter == "Har LinkedIn":
            shown = shown[shown["linkedin"].fillna("") != ""]
        if search_text.strip():
            needle = search_text.strip().lower()
            searchable = (
                shown["name"].fillna("")
                + " "
                + shown["role"].fillna("")
                + " "
                + shown["notes"].fillna("")
                + " "
                + shown["phone"].fillna("")
                + " "
                + shown["email"].fillna("")
            ).str.lower()
            shown = shown[searchable.str.contains(needle, regex=False)]

        st.markdown(f"### Viste kontakter ({len(shown)})")
        if len(shown):
            table_df = shown.drop(columns=["id", "company_id", "created_at"])
            st.dataframe(table_df, use_container_width=True, hide_index=True)
            with st.expander("Åbn / redigér kontakt", expanded=False):
                options = []
                for _, row in shown.iterrows():
                    role_text = f" · {row['role']}" if row["role"] else ""
                    options.append((f"{row['name']} · {row['actor']}{role_text}", int(row["id"])))
                selected_label = st.selectbox("Vælg kontakt", [label for label, _ in options])
                selected_id = dict(options)[selected_label]
                selected = shown[shown["id"] == selected_id].iloc[0]
                a, b = st.columns(2)
                if a.button("Åbn aktørprofil", key=f"contact_open_profile_{selected_id}", disabled=not has_db_id(selected["company_id"])):
                    open_company_section(int(selected["company_id"]), "Kontakter")
                    st.rerun()
                if selected["linkedin"]:
                    b.link_button("Åbn LinkedIn", selected["linkedin"])

                with st.form(f"contacts_edit_{selected_id}"):
                    ea, eb = st.columns([1.2, 1])
                    edit_actor = ea.selectbox(
                        "Aktør",
                        company_names,
                        index=company_names.index(selected["actor"]) if selected["actor"] in company_names else 0,
                    )
                    edit_name = eb.text_input("Navn", selected["name"] or "")
                    ec, ed, ee = st.columns(3)
                    edit_role = ec.text_input("Rolle", selected["role"] or "")
                    edit_phone = ed.text_input("Telefon", selected["phone"] or "")
                    edit_email = ee.text_input("Email", selected["email"] or "")
                    edit_linkedin = st.text_input("LinkedIn", selected["linkedin"] or "")
                    edit_notes = st.text_area("Noter", selected["notes"] or "", height=100)
                    save_contact = st.form_submit_button("Gem ændringer")
                    delete_contact = st.form_submit_button("Slet kontakt")
                    if save_contact:
                        run(
                            "UPDATE contacts SET company_id=?, name=?, role=?, phone=?, email=?, linkedin=?, notes=? WHERE id=?",
                            (company_lookup[edit_actor], edit_name, edit_role, edit_phone, edit_email, edit_linkedin, edit_notes, selected_id),
                        )
                        st.success("Kontakt opdateret.")
                        st.rerun()
                    if delete_contact:
                        run("DELETE FROM contacts WHERE id=?", (selected_id,))
                        st.success("Kontakt slettet.")
                        st.rerun()
        else:
            st.info("Ingen kontakter matcher filtrene.")
    else:
        st.info("Ingen kontakter endnu.")
