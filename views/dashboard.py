from app_context import (
    FOLLOWUP_STATUSES,
    FOLLOWUP_TYPES,
    date,
    display_date,
    followup_due_label,
    followup_group,
    has_db_id,
    now_iso,
    open_company_section,
    open_followup,
    q,
    run,
    set_page,
    severity_index,
    short,
    st,
)


def render():
    today_iso = date.today().isoformat()
    signals = q("""SELECT s.id, s.collected_at, c.name AS company, s.trigger_type, s.score,
                          s.title, COALESCE(s.review_status,'Ny') AS review_status
                   FROM signals s LEFT JOIN companies c ON c.id=s.company_id
                   ORDER BY s.collected_at DESC""")
    companies = q("SELECT * FROM companies")
    meetings = q("SELECT m.*, c.name AS company FROM meetings m LEFT JOIN companies c ON c.id=m.company_id ORDER BY m.meeting_date ASC, m.meeting_time ASC")
    observations = q("SELECT * FROM observations")
    followups = q("""SELECT f.*, c.name AS company, t.title AS commercial_track
                     FROM followups f LEFT JOIN companies c ON c.id=f.company_id
                     LEFT JOIN commercial_tracks t ON t.id=f.commercial_track_id
                     WHERE COALESCE(f.status, 'Ny') NOT IN ('Lukket', 'Arkiveret')
                     ORDER BY
                        CASE f.priority WHEN 'Høj' THEN 1 WHEN 'Middel' THEN 2 ELSE 3 END,
                        CASE WHEN f.due_date='' OR f.due_date IS NULL THEN 1 ELSE 0 END,
                        f.due_date ASC,
                        f.created_at DESC""")
    if len(followups):
        followups["dashboard_group"] = followups.apply(lambda row: followup_group(row, today_iso), axis=1)
    upcoming = q("""SELECT m.id, m.company_id, m.meeting_date, m.meeting_time, m.location, m.title, c.name AS company
                    FROM meetings m LEFT JOIN companies c ON c.id=m.company_id
                    WHERE m.meeting_date >= ?
                    ORDER BY m.meeting_date ASC, m.meeting_time ASC
                    LIMIT 8""", (today_iso,))
    linkedin_refs = q("""SELECT s.id, s.name, s.url, s.keywords, c.id AS company_id, c.name AS company
                         FROM sources s
                         LEFT JOIN companies c ON s.url=c.linkedin
                         WHERE (LOWER(s.name) LIKE '%linkedin%' OR LOWER(s.url) LIKE '%linkedin%')
                           AND COALESCE(s.priority, 'Middel')='Høj'
                         ORDER BY s.name
                         LIMIT 12""")
    overdue_count = int((followups["dashboard_group"] == "Forfaldne").sum()) if len(followups) else 0
    next30_count = int((followups["dashboard_group"] == "Næste 30 dage").sum()) if len(followups) else 0
    undated_count = int((followups["dashboard_group"] == "Uden dato").sum()) if len(followups) else 0
    new_signal_count = int((signals["review_status"] == "Ny").sum()) if len(signals) else 0
    cols = st.columns(5)
    cols[0].metric("Forfaldne", overdue_count)
    cols[1].metric("Næste 30 dage", next30_count)
    cols[2].metric("Kommende møder", len(upcoming))
    cols[3].metric("Nye signaler", new_signal_count)
    cols[4].metric("Opgaver/leads", len(followups))

    business_counts = q(
        """SELECT
             (SELECT COUNT(*) FROM commercial_tracks WHERE status!='Lukket') AS open_tracks,
             (SELECT COUNT(*) FROM proposals WHERE status IN ('Sendt','Afventer')) AS pending_proposals,
             (SELECT COUNT(*) FROM engagements WHERE status IN ('Planlagt','I gang','Afventer')) AS active_engagements,
             (SELECT COUNT(*) FROM deliverables WHERE status NOT IN ('Leveret','Annulleret')) AS open_deliverables"""
    ).iloc[0]
    st.markdown("### Forretning")
    business_cols = st.columns(5)
    business_cols[0].metric("Åbne forløb", int(business_counts["open_tracks"]))
    business_cols[1].metric("Tilbud afventer", int(business_counts["pending_proposals"]))
    business_cols[2].metric("Aktive kundeopgaver", int(business_counts["active_engagements"]))
    business_cols[3].metric("Åbne leverancer", int(business_counts["open_deliverables"]))
    if business_cols[4].button("Åbn Forretning", type="primary", use_container_width=True):
        set_page("Forretning")
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"Dashboard · {display_date(date.today().isoformat())}")
        st.markdown("### Dagens fokus")
        if overdue_count:
            st.warning(f"{overdue_count} opfølgning(er) er forfaldne.")
        elif next30_count:
            st.info(f"{next30_count} opfølgning(er) ligger inden for de næste 30 dage.")
        else:
            st.success("Ingen daterede opfølgninger kræver akut handling.")
        if len(upcoming):
            next_meeting = upcoming.iloc[0]
            when = display_date(next_meeting["meeting_date"])
            if next_meeting["meeting_time"]:
                when += f" kl. {next_meeting['meeting_time']}"
            st.markdown(f"**Næste møde:** {when} — {next_meeting['company'] or 'Ukendt aktør'}")
            st.caption(next_meeting["title"] or "Møde")
        if new_signal_count:
            st.caption(f"{new_signal_count} nye signaler bør gennemgås i Signalindbakken.")
        if undated_count:
            st.caption(f"{undated_count} åbne opgaver/leads mangler dato.")

        with st.expander("Tilføj opfølgning / lead", expanded=False):
            with st.form(f"dashboard_add_followup_{st.session_state.get('dashboard_followup_form_version',0)}", clear_on_submit=True):
                company_labels = ["Ingen aktør"] + companies["name"].tolist() if len(companies) else ["Ingen aktør"]
                selected_company = st.selectbox("Aktør", company_labels)
                title = st.text_input("Titel", value="")
                followup_type = st.selectbox("Type", FOLLOWUP_TYPES, index=0)
                next_action = st.text_input("Næste handling", value="")
                person = st.text_input("Person", value="")
                due_date = st.text_input("Dato/timing", value="")
                priority = st.selectbox("Prioritet", ["Lav", "Middel", "Høj"], index=1)
                status = st.selectbox("Status", ["Ny", "Planlagt", "I gang", "Afventer"], index=0)
                description = st.text_area("Opgavebeskrivelse / baggrund", value="", height=120)
                if st.form_submit_button("Gem opfølgning"):
                    selected_company_id = None
                    if selected_company != "Ingen aktør" and len(companies):
                        selected_company_id = int(companies[companies["name"] == selected_company]["id"].iloc[0])
                    run(
                        """INSERT INTO followups
                           (company_id, title, followup_type, description, next_action, person, due_date, priority, status, source_type, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (selected_company_id, title, followup_type, description, next_action, person, due_date, priority, status, "Dashboard", now_iso(), now_iso()),
                    )
                    st.session_state["dashboard_followup_form_version"] = st.session_state.get("dashboard_followup_form_version",0) + 1
                    st.success("Opfølgning gemt.")
                    st.rerun()

        st.markdown("### Næste handlinger / leads")
        if len(followups):
            for group_name in ["Forfaldne", "Næste 30 dage", "Uden dato", "Planlagt senere"]:
                group_df = followups[followups["dashboard_group"] == group_name]
                if len(group_df):
                    st.markdown(f"**{group_name} ({len(group_df)})**")
                    for _, f in group_df.head(6).iterrows():
                        with st.container(border=True):
                            due = followup_due_label(f["due_date"], today_iso)
                            company = f["company"] or "Ingen virksomhed"
                            person = f" · {f['person']}" if f["person"] else ""
                            st.markdown(f"**{f['title']}**")
                            if f['commercial_track']:
                                st.caption(f"Forretningsforløb: {f['commercial_track']}")
                                if st.button('Åbn forløb', key=f"dash_business_{int(f['id'])}"):
                                    st.session_state['business_track_id'] = int(f['commercial_track_id'])
                                    set_page('Forretning')
                                    st.rerun()
                            st.caption(f"{company}{person} · {due} · {f['followup_type']} · {f['priority']} · {f['status']}")
                            if f["next_action"]:
                                st.write(f"**Næste handling:** {f['next_action']}")
                            if f["description"]:
                                st.write(short(f["description"], 220))
                            a, b, c = st.columns([1, 1.35, 1])
                            if a.button("Åbn profil", key=f"dash_follow_open_{int(f['id'])}", disabled=not has_db_id(f["company_id"])):
                                open_followup(int(f["company_id"]), int(f["id"]))
                                st.rerun()
                            selected_status = b.selectbox(
                                "Status",
                                FOLLOWUP_STATUSES,
                                index=severity_index(f["status"] or "Ny", FOLLOWUP_STATUSES),
                                key=f"dash_follow_status_{int(f['id'])}",
                            )
                            if c.button("Gem status", key=f"dash_follow_save_status_{int(f['id'])}"):
                                run("UPDATE followups SET status=?, updated_at=? WHERE id=?", (selected_status, now_iso(), int(f["id"])))
                                st.rerun()
        else:
            st.success("Ingen åbne opfølgninger.")

        if len(followups):
            st.markdown("### Pipeline / opgavestatus")
            status_cols = st.columns(4)
            for idx, status_name in enumerate(["Ny", "Planlagt", "I gang", "Afventer"]):
                status_df = followups[followups["status"].fillna("Ny") == status_name]
                with status_cols[idx]:
                    st.metric(status_name, len(status_df))
                    for _, f in status_df.head(3).iterrows():
                        due = followup_due_label(f["due_date"], today_iso)
                        st.caption(f"{f['followup_type']} · {due}")
                        st.write(short(f["title"], 80))
                        if st.button("Åbn", key=f"pipeline_open_{int(f['id'])}", disabled=not has_db_id(f["company_id"])):
                            open_followup(int(f["company_id"]), int(f["id"]))
                            st.rerun()

        st.markdown("### Signalpåmindelse")
        new_count = int((signals["review_status"] == "Ny").sum()) if len(signals) else 0
        review_count = int((signals["review_status"] == "Til vurdering").sum()) if len(signals) else 0
        if new_count or review_count:
            st.info(f"Der er {new_count} nye signaler og {review_count} signaler til vurdering.")
        else:
            st.success("Ingen nye signaler kræver behandling.")
        if st.button("Gå til Signalindbakke"):
            set_page("Signalindbakke")
            st.rerun()
    with c2:
        st.subheader("Kommende møder / husketing")
        if len(upcoming):
            for _, m in upcoming.iterrows():
                with st.container(border=True):
                    when = display_date(m["meeting_date"])
                    if m["meeting_time"]:
                        when += f" kl. {m['meeting_time']}"
                    st.markdown(f"**{when} — {m['company'] or 'Ukendt aktør'}**")
                    st.caption(f"{m['title'] or 'Møde'}" + (f" · {m['location']}" if m["location"] else ""))
                    a, b = st.columns(2)
                    if a.button("Åbn profil", key=f"dash_meeting_profile_{int(m['id'])}", disabled=not has_db_id(m["company_id"])):
                        open_company_section(int(m["company_id"]), "Møder")
                        st.rerun()
                    if b.button("Briefing", key=f"dash_meeting_briefing_{int(m['id'])}", disabled=not has_db_id(m["company_id"])):
                        st.session_state["selected_company_id"] = int(m["company_id"])
                        st.session_state["selected_briefing_meeting_id"] = int(m["id"])
                        set_page("Briefing")
                        st.rerun()
        else:
            st.caption("Ingen kommende møder registreret.")

        st.subheader("LinkedIn-referencekilder")
        st.caption("Kun referencekilder med prioritet Høj vises her. Skift prioritet under Kilder for at vælge til/fra.")
        if len(linkedin_refs):
            for _, src in linkedin_refs.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{src['company'] or src['name']}**")
                    st.caption("Manuel referencekilde")
                    if src["url"]:
                        st.link_button("Åbn LinkedIn", src["url"])
                    with st.expander("Gem LinkedIn-opslag som observation"):
                        if not has_db_id(src["company_id"]):
                            st.info("Kilden er ikke koblet direkte til en aktør. Gem observationen fra aktørprofilen i stedet.")
                        else:
                            with st.form(f"linkedin_obs_{int(src['id'])}", clear_on_submit=True):
                                title = st.text_input("Titel", value=f"LinkedIn-opslag - {src['company']}")
                                observation_date = st.text_input("Dato", value=today_iso)
                                post_url = st.text_input("Opslags-URL", value="")
                                content = st.text_area("Indhold / uddrag fra opslag", value="", height=120)
                                implication = st.text_area("Mulig betydning", value="", height=90)
                                follow_up = st.text_area("Opfølgning", value="", height=90)
                                if st.form_submit_button("Gem observation"):
                                    observation_content = content
                                    if post_url:
                                        observation_content = f"{content}\n\nLinkedIn-URL: {post_url}".strip()
                                    run(
                                        """INSERT INTO observations
                                           (company_id, observation_date, title, observation_type, source_type, confidence, verification_status, content, implication, follow_up, created_at, updated_at)
                                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                        (
                                            int(src["company_id"]),
                                            observation_date,
                                            title,
                                            "OSINT-signal",
                                            "LinkedIn",
                                            "Middel",
                                            "Bør verificeres",
                                            observation_content,
                                            implication,
                                            follow_up,
                                            now_iso(),
                                            now_iso(),
                                        ),
                                    )
                                    st.success("LinkedIn-observation gemt på aktørprofilen.")
        else:
            st.caption("Ingen LinkedIn-referencekilder endnu.")
