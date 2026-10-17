from app_context import (
    ACTOR_TYPES,
    FOLLOWUP_TYPES,
    Path,
    ai_meeting_followup_text,
    briefing_context,
    company_timeline,
    count_for,
    datetime,
    display_date,
    extract_text_from_file,
    followup_due_label,
    meeting_options,
    now_iso,
    q,
    run,
    save_uploaded_file,
    set_company,
    severity_index,
    short,
    simple_meeting_summary,
    st,
    sync_actor_sources,
)


def render():
    st.subheader("Virksomheder")
    companies = q("SELECT * FROM companies ORDER BY name")
    if st.session_state.pop("force_profile_view", False):
        st.session_state["company_view_mode"] = "Profil"
    if st.session_state.get("company_view_mode") not in ["Oversigt", "Profil"]:
        st.session_state["company_view_mode"] = "Oversigt"
    mode = st.radio("Visning", ["Oversigt", "Profil"], horizontal=True, key="company_view_mode")

    if mode == "Oversigt":
        with st.expander("Opret ny aktør", expanded=False):
            with st.form(f"add_actor_form_{st.session_state.get('add_actor_form_version',0)}", clear_on_submit=True):
                a1, a2, a3 = st.columns([2, 1.4, 1])
                name = a1.text_input("Navn")
                actor_type = a2.selectbox("Aktørtype", ACTOR_TYPES, index=0)
                priority = a3.selectbox("Prioritet", ["Lav","Middel","Høj"], index=1)
                category = st.text_area("Kategori / kort beskrivelse", height=80)
                b1, b2 = st.columns(2)
                country = b1.text_input("Land", value="Danmark")
                status = b2.selectbox("Status", ["Aktiv","Pauset","Arkiveret"], index=0)
                c1, c2 = st.columns(2)
                website = c1.text_input("Website", value="")
                linkedin = c2.text_input("LinkedIn", value="")
                aliases = st.text_input("Aliaser / søgeord", value="")
                if st.form_submit_button("Opret aktør"):
                    clean_name = name.strip()
                    if not clean_name:
                        st.warning("Navn skal udfyldes.")
                    else:
                        try:
                            run(
                                """INSERT INTO companies
                                   (name, actor_type, category, country, priority, website, linkedin, status, aliases, created_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (clean_name, actor_type, category, country, priority, website, linkedin, status, aliases, now_iso()),
                            )
                            sync_actor_sources(clean_name, website, linkedin, aliases, status)
                            created = q("SELECT id FROM companies WHERE name=?", (clean_name,))
                            if len(created):
                                st.session_state["selected_company_id"] = int(created["id"].iloc[0])
                                st.session_state["force_profile_view"] = True
                            st.session_state["add_actor_form_version"] = st.session_state.get("add_actor_form_version",0) + 1
                            st.success("Aktør oprettet.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Aktøren kunne ikke oprettes. Tjek om navnet allerede findes. Fejl: {e}")

        f1, f2, f3, f4 = st.columns([1,1,1.4,2])
        status_filter = f1.multiselect("Status", ["Aktiv","Pauset","Arkiveret"], default=["Aktiv","Pauset"])
        priority_filter = f2.multiselect("Prioritet", ["Lav","Middel","Høj"], default=["Lav","Middel","Høj"])
        type_filter = f3.multiselect("Aktørtype", ACTOR_TYPES, default=ACTOR_TYPES)
        search = f4.text_input("Søg i virksomheder")
        shown = companies.copy()
        if len(shown):
            shown = shown[shown["status"].isin(status_filter)]
            shown = shown[shown["priority"].isin(priority_filter)]
            shown = shown[shown["actor_type"].fillna("Life science-virksomhed").isin(type_filter)]
            if search:
                shown = shown[shown["name"].fillna("").str.contains(search, case=False, na=False) |
                              shown["actor_type"].fillna("").str.contains(search, case=False, na=False) |
                              shown["category"].fillna("").str.contains(search, case=False, na=False) |
                              shown["aliases"].fillna("").str.contains(search, case=False, na=False)]
        if len(shown):
            for _, r in shown.iterrows():
                cols = st.columns([0.8,2.5,1.7,2,1,1])
                if cols[0].button("Åbn", key=f"open_company_{int(r['id'])}"):
                    set_company(int(r["id"]))
                    st.rerun()
                cols[1].markdown(f"**{r['name']}**")
                cols[2].caption(r["actor_type"] or "Life science-virksomhed")
                cols[3].caption(r["category"] or "")
                cols[4].caption(r["priority"] or "")
                cols[5].caption(r["status"] or "")
        else:
            st.info("Ingen virksomheder matcher filteret.")

    else:
        if len(companies) == 0:
            st.info("Ingen virksomheder.")
        else:
            ids = companies["id"].tolist()
            default_id = st.session_state.get("selected_company_id", ids[0])
            idx = ids.index(default_id) if default_id in ids else 0
            selected_name = st.selectbox("Vælg virksomhed", companies["name"].tolist(), index=idx)
            company_id = int(companies[companies["name"] == selected_name]["id"].iloc[0])
            st.session_state["selected_company_id"] = company_id
            row = q("SELECT * FROM companies WHERE id=?", (company_id,)).iloc[0]

            st.markdown(f"## {row['name']}")
            meta = st.columns([1.4, 2.2, 1, 1])
            meta[0].caption("Aktørtype")
            meta[0].markdown(f"**{row['actor_type'] or 'Life science-virksomhed'}**")
            meta[1].caption("Kategori")
            meta[1].markdown(f"**{row['category'] or '—'}**")
            meta[2].caption("Prioritet")
            meta[2].markdown(f"**{row['priority'] or '—'}**")
            meta[3].caption("Status")
            meta[3].markdown(f"**{row['status'] or '—'}**")
            links = []
            if row["website"]: links.append(f"[Website]({row['website']})")
            if row["linkedin"]: links.append(f"[LinkedIn]({row['linkedin']})")
            if links: st.markdown(" · ".join(links))

            sig_n = count_for("signals", company_id)
            meet_n = count_for("meetings", company_id)
            obs_n = count_for("observations", company_id)
            case_n = count_for("company_cases", company_id)
            contact_n = count_for("contacts", company_id)
            note_n = count_for("notes", company_id)
            mem_n = count_for("intelligence_memory", company_id)
            brief_n = count_for("briefings", company_id)
            follow_n = count_for("followups", company_id)
            business_n = count_for("commercial_tracks", company_id)
            timeline_n = sig_n + meet_n + obs_n + case_n + note_n + mem_n + brief_n + follow_n

            section_counts = {
                "Tidslinje": timeline_n,
                "Forretning": business_n,
                "Opfølgning": follow_n,
                "Signaler": sig_n,
                "Møder": meet_n,
                "Observationer": obs_n,
                "Historik / Sager": case_n,
                "Kontakter": contact_n,
                "Noter": note_n,
                "Videnbank": mem_n,
                "Briefing": brief_n,
            }
            sections = ["Tidslinje", "Forretning", "Opfølgning", "Signaler", "Møder", "Observationer", "Historik / Sager", "Kontakter", "Noter", "Videnbank", "Briefing"]
            section_key = f"profile_section_{company_id}"
            if st.session_state.get(section_key) not in sections:
                st.session_state[section_key] = "Tidslinje"
            section_base = st.radio(
                "Profilsektion",
                sections,
                horizontal=True,
                key=section_key,
                format_func=lambda name: f"{name} ({section_counts[name]})" if name in section_counts else name,
            )

            with st.expander("Redigér virksomhedsdata"):
                with st.form("edit_company_form"):
                    name = st.text_input("Navn", row["name"])
                    actor_type = st.selectbox(
                        "Aktørtype",
                        ACTOR_TYPES,
                        index=severity_index(row["actor_type"] or "Life science-virksomhed", ACTOR_TYPES),
                    )
                    category = st.text_area("Kategori", row["category"] or "", height=80)
                    country = st.text_input("Land", row["country"] or "Danmark")
                    priority = st.selectbox("Prioritet", ["Lav","Middel","Høj"], index=severity_index(row["priority"], ["Lav","Middel","Høj"]))
                    status = st.selectbox("Status", ["Aktiv","Pauset","Arkiveret"], index=severity_index(row["status"], ["Aktiv","Pauset","Arkiveret"]))
                    aliases = st.text_input("Aliaser", row["aliases"] or "")
                    website = st.text_input("Website", row["website"] or "")
                    linkedin = st.text_input("LinkedIn", row["linkedin"] or "")
                    if st.form_submit_button("Gem virksomhed"):
                        run("UPDATE companies SET name=?, actor_type=?, category=?, country=?, priority=?, status=?, aliases=?, website=?, linkedin=? WHERE id=?",
                            (name, actor_type, category, country, priority, status, aliases, website, linkedin, company_id))
                        sync_actor_sources(name, website, linkedin, aliases, status)
                        st.rerun()

            if section_base == "Tidslinje":
                st.markdown("### Samlet virksomhedstidslinje")
                timeline = company_timeline(company_id)
                if timeline:
                    for item in timeline:
                        with st.container(border=True):
                            date_text = display_date(item["date"]) or "Ukendt dato"
                            st.markdown(f"**{date_text} · {item['type']} · {item['title']}**")
                            if item["meta"]:
                                st.caption(item["meta"])
                            if item["body"]:
                                st.write(short(item["body"], 900))
                                if len(item["body"]) > 900:
                                    with st.expander("Vis hele indholdet"):
                                        for label, value in item["details"]:
                                            st.markdown(f"**{label}**")
                                            st.text_area(
                                                label,
                                                value,
                                                height=260,
                                                key=f"timeline_detail_{company_id}_{item['type']}_{item['sort_date']}_{label}_{abs(hash(value))}",
                                                disabled=True,
                                            )
                else:
                    st.info("Ingen tidslinjeelementer endnu.")

            elif section_base == "Forretning":
                st.markdown("### Forretningsforløb")
                business_tracks = q(
                    """SELECT t.*,
                              (SELECT COUNT(*) FROM proposals p WHERE p.track_id=t.id) AS proposal_count,
                              (SELECT COUNT(*) FROM engagements e WHERE e.track_id=t.id) AS engagement_count
                       FROM commercial_tracks t WHERE t.company_id=?
                       ORDER BY CASE t.status WHEN 'Åben' THEN 1 WHEN 'Afventer' THEN 2
                                WHEN 'Pauset' THEN 3 ELSE 4 END,
                                t.expected_decision_date, t.created_at DESC""",
                    (company_id,),
                )
                if len(business_tracks):
                    for _, track in business_tracks.iterrows():
                        st.markdown(f"**{track['title']}**")
                        st.caption(
                            f"{track['status']} · {int(track['proposal_count'])} tilbud · "
                            f"{int(track['engagement_count'])} kundeopgaver"
                            + (f" · Beslutning: {track['expected_decision_date']}" if track['expected_decision_date'] else "")
                        )
                        if track["need_description"]:
                            st.write(short(track["need_description"], 240))
                        st.divider()
                else:
                    st.info("Aktøren har ingen forretningsforløb. Relationer og møder er ikke automatisk salgsmuligheder.")
                if st.button("Åbn i Forretning", type="primary", key=f"open_business_{company_id}"):
                    st.session_state["business_company_id"] = company_id
                    st.session_state["page"] = "Forretning"
                    st.rerun()

            elif section_base == "Opfølgning":
                st.markdown("### Opfølgninger / leads / opgaver")
                highlighted_followup_id = st.session_state.pop("highlight_followup_id", None)
                followups = q("SELECT * FROM followups WHERE company_id=? ORDER BY due_date ASC, created_at DESC", (company_id,))
                if len(followups):
                    if highlighted_followup_id and highlighted_followup_id in followups["id"].tolist():
                        followups["_highlight_sort"] = followups["id"].apply(lambda value: 0 if int(value) == int(highlighted_followup_id) else 1)
                        followups = followups.sort_values(["_highlight_sort", "due_date", "created_at"], ascending=[True, True, False])
                    for _, f in followups.iterrows():
                        with st.container(border=True):
                            due = followup_due_label(f["due_date"])
                            if highlighted_followup_id and int(f["id"]) == int(highlighted_followup_id):
                                st.info("Valgt fra dashboard")
                            st.markdown(f"**{f['title']}**")
                            meta = [due, f["followup_type"], f["priority"], f["status"], f["source_type"]]
                            if f["person"]:
                                meta.insert(1, f["person"])
                            st.caption(" · ".join([m for m in meta if m]))
                            if f["next_action"]:
                                st.write(f"**Næste handling:** {f['next_action']}")
                            if f["description"]:
                                st.write(f["description"])
                            with st.expander("Redigér / slet opfølgning"):
                                with st.form(f"edit_followup_{int(f['id'])}"):
                                    title = st.text_input("Titel", f["title"])
                                    followup_type = st.selectbox("Type", FOLLOWUP_TYPES, index=severity_index(f["followup_type"] or "Opfølgning", FOLLOWUP_TYPES))
                                    next_action = st.text_input("Næste handling", f["next_action"] or "")
                                    description = st.text_area("Opgavebeskrivelse / baggrund", f["description"] or "", height=120)
                                    person = st.text_input("Person", f["person"] or "")
                                    due_date = st.text_input("Dato/timing", f["due_date"] or "")
                                    priority = st.selectbox("Prioritet", ["Lav", "Middel", "Høj"], index=severity_index(f["priority"], ["Lav", "Middel", "Høj"]))
                                    status = st.selectbox("Status", ["Ny", "Planlagt", "I gang", "Afventer", "Lukket", "Arkiveret"], index=severity_index(f["status"], ["Ny", "Planlagt", "I gang", "Afventer", "Lukket", "Arkiveret"]))
                                    a, b = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run(
                                            "UPDATE followups SET title=?, followup_type=?, description=?, next_action=?, person=?, due_date=?, priority=?, status=?, updated_at=? WHERE id=?",
                                            (title, followup_type, description, next_action, person, due_date, priority, status, now_iso(), int(f["id"])),
                                        )
                                        st.rerun()
                                    if b.form_submit_button("Slet opfølgning"):
                                        run("DELETE FROM followups WHERE id=?", (int(f["id"]),))
                                        st.rerun()
                else:
                    st.info("Ingen opfølgninger endnu.")
                with st.expander("Tilføj opfølgning / lead"):
                    with st.form(f"add_followup_{company_id}_{st.session_state.get('followup_form_version',0)}", clear_on_submit=True):
                        title = st.text_input("Titel", value="")
                        followup_type = st.selectbox("Type", FOLLOWUP_TYPES, index=0)
                        next_action = st.text_input("Næste handling", value="")
                        description = st.text_area("Opgavebeskrivelse / baggrund", value="", height=120)
                        person = st.text_input("Person", value="")
                        due_date = st.text_input("Dato/timing", value="")
                        priority = st.selectbox("Prioritet", ["Lav", "Middel", "Høj"], index=1)
                        status = st.selectbox("Status", ["Ny", "Planlagt", "I gang", "Afventer"], index=0)
                        if st.form_submit_button("Gem opfølgning"):
                            run(
                                """INSERT INTO followups
                                   (company_id, title, followup_type, description, next_action, person, due_date, priority, status, source_type, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (company_id, title, followup_type, description, next_action, person, due_date, priority, status, "Manuel", now_iso(), now_iso()),
                            )
                            st.session_state["followup_form_version"] = st.session_state.get("followup_form_version",0) + 1
                            st.rerun()

            elif section_base == "Signaler":
                sigs = q("SELECT id, collected_at, trigger_type, score, review_status, title FROM signals WHERE company_id=? ORDER BY collected_at DESC", (company_id,))
                if len(sigs):
                    for _, s in sigs.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{s['title']}**")
                            st.caption(f"Dato: {display_date(s['collected_at'])} · {s['trigger_type']} · {s['score']} · {s['review_status']}")
                            c = st.columns([1,1])
                            if c[0].button("Arkivér", key=f"prof_sig_arch_{int(s['id'])}"):
                                run("UPDATE signals SET review_status='Arkiveret' WHERE id=?", (int(s["id"]),)); st.rerun()
                            if c[1].button("Slet", key=f"prof_sig_del_{int(s['id'])}"):
                                run("DELETE FROM signals WHERE id=?", (int(s["id"]),)); st.rerun()
                else:
                    st.info("Ingen signaler.")

            elif section_base == "Møder":
                meetings = q("SELECT * FROM meetings WHERE company_id=? ORDER BY meeting_date DESC, meeting_time DESC, created_at DESC", (company_id,))
                if len(meetings):
                    for _, m in meetings.iterrows():
                        with st.container(border=True):
                            when = display_date(m["meeting_date"])
                            if "meeting_time" in meetings.columns and m["meeting_time"]:
                                when += f" kl. {m['meeting_time']}"
                            st.markdown(f"**{when} — {m['title']}**")
                            extra = []
                            if "location" in meetings.columns and m["location"]: extra.append(m["location"])
                            if m["meeting_type"]: extra.append(m["meeting_type"])
                            if m["relation_strength"]: extra.append(f"Relation: {m['relation_strength']}")
                            st.caption(" · ".join(extra))
                            if m["participants"]: st.write(f"**Deltagere:** {m['participants']}")
                            if m["summary"]: st.write(m["summary"])
                            if m["key_takeaways"]: st.write(f"**Hvad lærte vi:** {m['key_takeaways']}")
                            if m["next_steps"]: st.write(f"**Næste skridt / frister:** {m['next_steps']}")
                            if "uploaded_filename" in meetings.columns and m["uploaded_filename"]:
                                st.caption(f"Uploadet referat: {m['uploaded_filename']}")
                            if "raw_text" in meetings.columns and m["raw_text"]:
                                with st.expander("Vis referattekst"):
                                    st.text_area(
                                        "Referattekst",
                                        m["raw_text"],
                                        height=260,
                                        key=f"meeting_raw_text_{int(m['id'])}",
                                    )
                                followup_key = f"meeting_ai_followup_{int(m['id'])}"
                                allow_external_followup = st.checkbox(
                                    "Tillad, at dette referat og den tilknyttede kontekst sendes til OpenAI",
                                    value=False,
                                    key=f"allow_external_followup_{int(m['id'])}",
                                )
                                if st.button("Lav AI-opfølgning på referat", key=f"generate_followup_{int(m['id'])}"):
                                    st.session_state[followup_key] = ai_meeting_followup_text(
                                        row["name"],
                                        m["title"],
                                        m["raw_text"],
                                        briefing_context(company_id),
                                        allow_external=allow_external_followup,
                                    )
                                if followup_key in st.session_state:
                                    st.markdown("**AI-opfølgning**")
                                    st.markdown(st.session_state[followup_key])
                                    with st.form(f"save_followup_note_{int(m['id'])}"):
                                        note_title = st.text_input(
                                            "Notetitel",
                                            f"AI-opfølgning - {m['title']} - {m['meeting_date'] or datetime.now().strftime('%Y-%m-%d')}",
                                        )
                                        note_text = st.text_area(
                                            "Opfølgningstekst",
                                            st.session_state[followup_key],
                                            height=240,
                                        )
                                        if st.form_submit_button("Gem som note på virksomheden"):
                                            run(
                                                "INSERT INTO notes (company_id, title, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                                                (company_id, note_title, note_text, now_iso(), now_iso()),
                                            )
                                            st.success("AI-opfølgning gemt som note.")
                                    with st.form(f"save_followup_lead_{int(m['id'])}"):
                                        lead_title = st.text_input(
                                            "Lead/opfølgningstitel",
                                            f"Opfølgning - {m['title']}",
                                        )
                                        lead_type = st.selectbox("Type", FOLLOWUP_TYPES, index=severity_index("Mødeopfølgning", FOLLOWUP_TYPES))
                                        lead_next_action = st.text_input("Næste handling", value="")
                                        lead_description = st.text_area(
                                            "Opgavebeskrivelse / baggrund",
                                            st.session_state[followup_key],
                                            height=180,
                                        )
                                        lead_person = st.text_input("Person", value="")
                                        lead_due_date = st.text_input("Dato/timing", value="")
                                        lead_priority = st.selectbox("Prioritet", ["Lav", "Middel", "Høj"], index=1)
                                        lead_status = st.selectbox("Status", ["Ny", "Planlagt", "I gang", "Afventer"], index=0)
                                        if st.form_submit_button("Gem som opfølgning / lead"):
                                            run(
                                                """INSERT INTO followups
                                                   (company_id, title, followup_type, description, next_action, person, due_date, priority, status, source_type, source_id, created_at, updated_at)
                                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                                (
                                                    company_id,
                                                    lead_title,
                                                    lead_type,
                                                    lead_description,
                                                    lead_next_action,
                                                    lead_person,
                                                    lead_due_date,
                                                    lead_priority,
                                                    lead_status,
                                                    "AI-opfølgning",
                                                    int(m["id"]),
                                                    now_iso(),
                                                    now_iso(),
                                                ),
                                            )
                                            st.success("AI-opfølgning gemt som opfølgning/lead på dashboardet.")
                            with st.expander("Redigér / slet møde"):
                                with st.form(f"edit_meeting_{int(m['id'])}"):
                                    title = st.text_input("Titel", m["title"])
                                    meeting_date = st.text_input("Dato", m["meeting_date"] or "")
                                    meeting_time = st.text_input("Tidspunkt", m["meeting_time"] if "meeting_time" in meetings.columns else "")
                                    location = st.text_input("Adresse/sted", m["location"] if "location" in meetings.columns else "")
                                    participants = st.text_input("Deltagere", m["participants"] or "")
                                    summary = st.text_area("Resume", m["summary"] or "")
                                    key_takeaways = st.text_area("Hvad lærte vi?", m["key_takeaways"] or "")
                                    next_steps = st.text_area("Næste skridt / frister", m["next_steps"] or "")
                                    a,b = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run("UPDATE meetings SET title=?, meeting_date=?, meeting_time=?, location=?, participants=?, summary=?, key_takeaways=?, next_steps=?, updated_at=? WHERE id=?",
                                            (title, meeting_date, meeting_time, location, participants, summary, key_takeaways, next_steps, now_iso(), int(m["id"]))); st.rerun()
                                    if b.form_submit_button("Slet møde"):
                                        run("DELETE FROM meetings WHERE id=?", (int(m["id"]),)); st.rerun()
                with st.expander("Tilføj møde", expanded=False):
                    form_key = f"add_meeting_{company_id}_{st.session_state.get('meeting_form_version',0)}"
                    with st.form(form_key, clear_on_submit=True):
                        title = st.text_input("Titel", value="")
                        meeting_date = st.text_input("Dato", datetime.now().strftime("%Y-%m-%d"))
                        meeting_time = st.text_input("Tidspunkt", value="")
                        location = st.text_input("Adresse/sted", value="")
                        meeting_type = st.selectbox("Type", ["Kaffemøde","Kundemøde","Netværk","Konference","Telefon","Regulatorisk","Uformelt"])
                        participants = st.text_input("Deltagere", value="")
                        relation_strength = st.selectbox("Relationstyrke", ["Svag","Middel","Stærk","Meget stærk"], index=1)
                        confidentiality = st.selectbox("Fortrolighed", ["Offentlig/OSINT","Intern","Fortrolig","Del ikke eksternt"], index=1)
                        summary = st.text_area("Resume", value="")
                        key_takeaways = st.text_area("Hvad lærte vi?", value="")
                        next_steps = st.text_area("Næste skridt / frister", value="")
                        if st.form_submit_button("Gem møde"):
                            run("""INSERT INTO meetings (company_id, meeting_date, meeting_time, location, title, meeting_type, participants, relation_strength, confidentiality, summary, key_takeaways, next_steps, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (company_id, meeting_date, meeting_time, location, title, meeting_type, participants, relation_strength, confidentiality, summary, key_takeaways, next_steps, now_iso(), now_iso()))
                            st.session_state["meeting_form_version"] = st.session_state.get("meeting_form_version",0) + 1
                            st.rerun()
                with st.expander("Upload referat", expanded=False):
                    upload_key = f"upload_{company_id}_{st.session_state.get('upload_version',0)}"
                    uploaded = st.file_uploader("Upload Word, PDF eller TXT", type=["docx","pdf","txt"], key=upload_key)
                    if uploaded and extract_text_from_file:
                        meeting_title = st.text_input("Mødetitel", Path(uploaded.name).stem, key=f"upload_title_{upload_key}")
                        meeting_date = st.text_input("Dato for møde", datetime.now().strftime("%Y-%m-%d"), key=f"upload_date_{upload_key}")
                        meeting_time = st.text_input("Tidspunkt", value="", key=f"upload_time_{upload_key}")
                        location = st.text_input("Adresse/sted", value="", key=f"upload_location_{upload_key}")
                        if st.button("Gem og udtræk tekst", key=f"upload_btn_{upload_key}"):
                            path = save_uploaded_file(company_id, uploaded)
                            extracted = extract_text_from_file(str(path))
                            summary = simple_meeting_summary(extracted) if simple_meeting_summary else {"summary": extracted[:1000], "key_takeaways": "", "next_steps": ""}
                            run("""INSERT INTO meetings (company_id, meeting_date, meeting_time, location, title, meeting_type, confidentiality, shareability, summary, key_takeaways, next_steps, raw_text, uploaded_filename, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (company_id, meeting_date, meeting_time, location, meeting_title, "Referat", "Intern", "Kun internt", summary["summary"], summary["key_takeaways"], summary["next_steps"], extracted, uploaded.name, now_iso(), now_iso()))
                            st.session_state["upload_version"] = st.session_state.get("upload_version",0) + 1
                            st.rerun()

            elif section_base == "Observationer":
                observations = q("SELECT * FROM observations WHERE company_id=? ORDER BY observation_date DESC, created_at DESC", (company_id,))
                if len(observations):
                    for _, o in observations.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{o['title']}**")
                            st.caption(f"{display_date(o['observation_date'])} · {o['observation_type']} · {o['source_type']} · {o['confidence']} · {o['verification_status']}")
                            st.write(o["content"])
                            if o["implication"]: st.write(f"**Mulig betydning:** {o['implication']}")
                            if o["follow_up"]: st.write(f"**Opfølgning:** {o['follow_up']}")
                            with st.expander("Redigér / slet observation"):
                                with st.form(f"edit_obs_{int(o['id'])}"):
                                    title = st.text_input("Titel", o["title"])
                                    content = st.text_area("Indhold", o["content"])
                                    implication = st.text_area("Mulig betydning", o["implication"] or "")
                                    follow_up = st.text_area("Opfølgning", o["follow_up"] or "")
                                    a,b = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run("UPDATE observations SET title=?, content=?, implication=?, follow_up=?, updated_at=? WHERE id=?",
                                            (title, content, implication, follow_up, now_iso(), int(o["id"]))); st.rerun()
                                    if b.form_submit_button("Slet observation"):
                                        run("DELETE FROM observations WHERE id=?", (int(o["id"]),)); st.rerun()
                with st.expander("Tilføj observation / rygte / signal"):
                    with st.form(f"add_observation_{company_id}_{st.session_state.get('obs_form_version',0)}", clear_on_submit=True):
                        title = st.text_input("Titel", value="")
                        observation_date = st.text_input("Dato", datetime.now().strftime("%Y-%m-%d"))
                        observation_type = st.selectbox("Type", ["Observation","Rygte","Mødesignal","OSINT-signal","Relation","Risiko","Mulighed"])
                        source_type = st.selectbox("Kilde", ["OSINT","Kaffemøde","Konkurrent","Relation","Tidligere erfaring","Andet"])
                        confidence = st.selectbox("Tillid", ["Lav","Middel","Høj"], index=1)
                        verification_status = st.selectbox("Verifikation", ["Ikke verificeret","Bør verificeres","Delvist verificeret","Verificeret"], index=0)
                        content = st.text_area("Indhold", value="")
                        implication = st.text_area("Mulig betydning", value="")
                        follow_up = st.text_area("Opfølgning", value="")
                        if st.form_submit_button("Gem observation"):
                            run("""INSERT INTO observations (company_id, observation_date, title, observation_type, source_type, confidence, verification_status, content, implication, follow_up, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (company_id, observation_date, title, observation_type, source_type, confidence, verification_status, content, implication, follow_up, now_iso(), now_iso()))
                            st.session_state["obs_form_version"] = st.session_state.get("obs_form_version",0) + 1
                            st.rerun()

            elif section_base == "Historik / Sager":
                cases = q("SELECT * FROM company_cases WHERE company_id=? ORDER BY period_start DESC, created_at DESC", (company_id,))
                if len(cases):
                    for _, c in cases.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{c['title']}**")
                            st.caption(f"{c['case_type']} · {c['severity']} · relevans {c['relevance']} · {c['status']}")
                            if c["summary"]: st.write(c["summary"])
                            with st.expander("Redigér / slet sag"):
                                with st.form(f"edit_case_{int(c['id'])}"):
                                    title = st.text_input("Titel", c["title"])
                                    summary = st.text_area("Resume", c["summary"] or "")
                                    significance = st.text_area("Betydning", c["significance"] or "")
                                    current_relevance = st.text_area("Nuværende relevans", c["current_relevance"] or "")
                                    a,b = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run("UPDATE company_cases SET title=?, summary=?, significance=?, current_relevance=?, updated_at=? WHERE id=?",
                                            (title, summary, significance, current_relevance, now_iso(), int(c["id"]))); st.rerun()
                                    if b.form_submit_button("Slet sag"):
                                        run("DELETE FROM company_cases WHERE id=?", (int(c["id"]),)); st.rerun()
                with st.expander("Tilføj sag/historik"):
                    with st.form(f"add_case_{company_id}_{st.session_state.get('case_form_version',0)}", clear_on_submit=True):
                        title = st.text_input("Titel", value="")
                        case_type = st.text_input("Sagstype", value="Myndighedsreaktion / GMP")
                        period_start = st.text_input("Periode start", value="")
                        period_end = st.text_input("Periode slut", value="")
                        severity = st.selectbox("Alvor", ["Lav","Middel","Høj","Kritisk"], index=2)
                        relevance = st.selectbox("Relevans", ["Lav","Middel","Høj","Kritisk"], index=1)
                        status = st.selectbox("Status", ["Åben","Afsluttet","Monitoreres","Arkiveret"], index=1)
                        summary = st.text_area("Kort resume", value="")
                        significance = st.text_area("Betydning", value="")
                        current_relevance = st.text_area("Nuværende relevans", value="")
                        if st.form_submit_button("Gem sag"):
                            run("""INSERT INTO company_cases (company_id, title, case_type, period_start, period_end, severity, relevance, status, summary, significance, current_relevance, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (company_id, title, case_type, period_start, period_end, severity, relevance, status, summary, significance, current_relevance, now_iso(), now_iso()))
                            st.session_state["case_form_version"] = st.session_state.get("case_form_version",0) + 1
                            st.rerun()

            elif section_base == "Kontakter":
                contacts = q("SELECT * FROM contacts WHERE company_id=? ORDER BY name", (company_id,))
                if len(contacts):
                    for _, c in contacts.iterrows():
                        with st.container(border=True):
                            col1, col2 = st.columns([1.4, 1])
                            col1.markdown(f"**{c['name']}**")
                            col2.caption(c["role"] or "")
                            if c["email"]:
                                col1.caption(c["email"])
                            if c["phone"]:
                                col1.caption(c["phone"])
                            if c["linkedin"]:
                                col2.markdown(f"[LinkedIn]({c['linkedin']})")
                            if c["notes"]:
                                st.caption(c["notes"])
                            with st.expander("Redigér / slet kontakt"):
                                with st.form(f"edit_contact_{int(c['id'])}"):
                                    r1, r2 = st.columns(2)
                                    name = r1.text_input("Navn", c["name"])
                                    role = r2.text_input("Rolle", c["role"] or "")
                                    r3, r4 = st.columns(2)
                                    phone = r3.text_input("Telefon", c["phone"] or "")
                                    email = r4.text_input("Email", c["email"] or "")
                                    linkedin = st.text_input("LinkedIn", c["linkedin"] or "")
                                    notes = st.text_area("Noter", c["notes"] or "", height=90)
                                    if st.form_submit_button("Gem"):
                                        run("UPDATE contacts SET name=?, role=?, phone=?, email=?, linkedin=?, notes=? WHERE id=?",
                                            (name, role, phone, email, linkedin, notes, int(c["id"]))); st.rerun()
                                    if st.form_submit_button("Slet"):
                                        run("DELETE FROM contacts WHERE id=?", (int(c["id"]),)); st.rerun()
                else:
                    st.info("Ingen kontakter.")
                with st.expander("Tilføj kontakt"):
                    with st.form(f"add_contact_{company_id}_{st.session_state.get('contact_form_version',0)}", clear_on_submit=True):
                        name = st.text_input("Navn", value="")
                        role = st.text_input("Rolle", value="")
                        phone = st.text_input("Telefon", value="")
                        email = st.text_input("Email", value="")
                        linkedin = st.text_input("LinkedIn", value="")
                        notes = st.text_area("Noter", value="", height=90)
                        if st.form_submit_button("Gem kontakt"):
                            run("INSERT INTO contacts (company_id, name, role, phone, email, linkedin, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (company_id, name, role, phone, email, linkedin, notes, now_iso()))
                            st.session_state["contact_form_version"] = st.session_state.get("contact_form_version",0) + 1
                            st.rerun()

            elif section_base == "Noter":
                notes = q("SELECT * FROM notes WHERE company_id=? ORDER BY created_at DESC", (company_id,))
                if len(notes):
                    for _, n in notes.iterrows():
                        with st.container(border=True):
                            title = n["title"] if "title" in notes.columns and n["title"] else "Note"
                            st.markdown(f"**{title}**")
                            st.caption(f"Dato: {display_date(n['created_at'])}")
                            st.write(n["note"])
                            with st.expander("Redigér / slet note"):
                                with st.form(f"edit_note_{int(n['id'])}"):
                                    title2 = st.text_input("Overskrift", title if title != "Note" else "")
                                    note2 = st.text_area("Note", n["note"], height=160)
                                    a,b = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run("UPDATE notes SET title=?, note=?, updated_at=? WHERE id=?", (title2, note2, now_iso(), int(n["id"]))); st.rerun()
                                    if b.form_submit_button("Slet note"):
                                        run("DELETE FROM notes WHERE id=?", (int(n["id"]),)); st.rerun()
                with st.expander("Tilføj note"):
                    with st.form(f"add_note_{company_id}_{st.session_state.get('note_form_version',0)}", clear_on_submit=True):
                        title = st.text_input("Overskrift", value="")
                        note = st.text_area("Note", value="", height=160)
                        if st.form_submit_button("Gem note"):
                            run("INSERT INTO notes (company_id, title, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                                (company_id, title, note, now_iso(), now_iso()))
                            st.session_state["note_form_version"] = st.session_state.get("note_form_version",0) + 1
                            st.rerun()

            elif section_base == "Videnbank":
                memories = q("SELECT * FROM intelligence_memory WHERE company_id=? ORDER BY created_at DESC", (company_id,))
                if len(memories):
                    for _, m in memories.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{m['title'] or m['memory_type']}**")
                            st.caption(f"Dato: {display_date(m['created_at'])} · {m['memory_type']} · sikkerhed: {m['confidence']}")
                            st.write(m["content"])
                            with st.expander("Redigér / slet viden"):
                                with st.form(f"edit_mem_{int(m['id'])}"):
                                    title = st.text_input("Titel", m["title"] or "")
                                    content = st.text_area("Indhold", m["content"], height=180)
                                    confidence = st.selectbox("Sikkerhed", ["Lav","Middel","Høj"], index=severity_index(m["confidence"], ["Lav","Middel","Høj"]))
                                    a,b = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run("UPDATE intelligence_memory SET title=?, content=?, confidence=?, updated_at=? WHERE id=?",
                                            (title, content, confidence, now_iso(), int(m["id"]))); st.rerun()
                                    if b.form_submit_button("Slet viden"):
                                        run("DELETE FROM intelligence_memory WHERE id=?", (int(m["id"]),)); st.rerun()
                with st.expander("Tilføj viden"):
                    with st.form(f"add_memory_{company_id}_{st.session_state.get('mem_form_version',0)}", clear_on_submit=True):
                        memory_type = st.selectbox("Type", ["Observation","Relation","Kultur","Regulatorisk modenhed","Historisk erfaring","Strategisk mulighed"])
                        title = st.text_input("Titel", value="")
                        content = st.text_area("Indhold", value="", height=180)
                        confidence = st.selectbox("Sikkerhed", ["Lav","Middel","Høj"], index=1)
                        if st.form_submit_button("Gem viden"):
                            run("INSERT INTO intelligence_memory (company_id, memory_type, title, content, confidence, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (company_id, memory_type, title, content, confidence, now_iso(), now_iso()))
                            st.session_state["mem_form_version"] = st.session_state.get("mem_form_version",0) + 1
                            st.rerun()

            elif section_base == "Briefing":
                st.markdown("### Briefing til kommende møde")
                st.markdown(f"**Virksomhed:** {row['name']}")
                saved_briefings = q(
                    """SELECT b.*, m.title AS meeting_title, m.meeting_date, m.meeting_time
                       FROM briefings b
                       LEFT JOIN meetings m ON m.id=b.meeting_id
                       WHERE b.company_id=?
                       ORDER BY b.created_at DESC, b.id DESC""",
                    (company_id,),
                )
                if len(saved_briefings):
                    st.markdown("### Gemte briefings")
                    for _, b in saved_briefings.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{b['title']}**")
                            st.caption(f"Oprettet: {display_date(b['created_at'])} · version {int(b['version'] or 1)} · {b['status']}")
                            if b["meeting_id"]:
                                meeting_label = display_date(b["meeting_date"]) or "Ukendt dato"
                                if b["meeting_time"]:
                                    meeting_label += f" kl. {b['meeting_time']}"
                                st.caption(f"Knyttet til møde: {meeting_label} - {b['meeting_title'] or 'Møde'}")
                            st.markdown(b["briefing_text"])
                            if b["user_notes"]:
                                st.markdown("**Egne noter**")
                                st.write(b["user_notes"])
                            with st.expander("Redigér / slet briefing"):
                                with st.form(f"edit_briefing_{int(b['id'])}"):
                                    title = st.text_input("Titel", b["title"])
                                    labels, values, selected_index = meeting_options(company_id, b["meeting_id"])
                                    selected_meeting = st.selectbox("Knyttet til møde", labels, index=selected_index)
                                    briefing_text = st.text_area("Briefing", b["briefing_text"], height=260)
                                    user_notes = st.text_area("Egne noter", b["user_notes"] or "", height=120)
                                    status = st.selectbox("Status", ["Aktiv", "Arkiveret"], index=severity_index(b["status"], ["Aktiv", "Arkiveret"]))
                                    a, c = st.columns(2)
                                    if a.form_submit_button("Gem ændringer"):
                                        run(
                                            "UPDATE briefings SET title=?, meeting_id=?, briefing_text=?, user_notes=?, status=?, updated_at=? WHERE id=?",
                                            (title, values[selected_meeting], briefing_text, user_notes, status, now_iso(), int(b["id"])),
                                        )
                                        st.rerun()
                                    if c.form_submit_button("Slet briefing"):
                                        run("DELETE FROM briefings WHERE id=?", (int(b["id"]),))
                                        st.rerun()
                else:
                    st.info("Ingen gemte briefings endnu. Brug Briefing-generatoren og gem et udkast.")

                recent_meetings = q("SELECT meeting_date, meeting_time, location, title, key_takeaways, next_steps FROM meetings WHERE company_id=? ORDER BY meeting_date DESC, meeting_time DESC, created_at DESC LIMIT 5", (company_id,))
                recent_obs = q("SELECT observation_date, title, observation_type, confidence, verification_status FROM observations WHERE company_id=? ORDER BY observation_date DESC, created_at DESC LIMIT 8", (company_id,))
                if len(recent_meetings):
                    st.markdown("**Seneste møder:**")
                    for _, m in recent_meetings.iterrows():
                        when = display_date(m["meeting_date"])
                        if m["meeting_time"]: when += f" kl. {m['meeting_time']}"
                        loc = f" ({m['location']})" if m["location"] else ""
                        st.markdown(f"- {when}: {m['title']}{loc} — {m['key_takeaways'] or ''} {m['next_steps'] or ''}")
                if len(recent_obs):
                    st.markdown("**Observationer:**")
                    for _, o in recent_obs.iterrows():
                        st.markdown(f"- {display_date(o['observation_date'])}: {o['title']} ({o['observation_type']}, {o['confidence']}, {o['verification_status']})")
                st.markdown("**Mulige dagsordenpunkter:**")
                st.markdown("- Opfølgning på tidligere aftaler og åbne punkter")
                st.markdown("- Nye observationer, der bør verificeres")
                st.markdown("- Relevante regulatoriske/kvalitetsmæssige temaer")
                st.markdown("- Eventuelle frister, næste skridt og mulige rådgivningsbehov")
