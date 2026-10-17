import math

import streamlit as st

from app_config import (
    DELIVERABLE_STATUSES,
    ENGAGEMENT_STATUSES,
    FEE_MODELS,
    PROPOSAL_STATUSES,
    TRACK_CLOSE_REASONS,
    TRACK_STATUSES,
)
from repositories import q, run
from services.business_service import (
    create_engagement_from_proposal,
    next_proposal_version,
    set_deliverable_followups,
    set_track_followups,
    set_track_meetings,
)
from ui.formatting import now_iso, severity_index


def _clean_value(value, fallback=""):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return fallback
    return value


def _money(value):
    value = _clean_value(value, None)
    if value is None:
        return "Ikke angivet"
    return f"{float(value):,.2f} kr. ekskl. moms".replace(",", "X").replace(".", ",").replace("X", ".")


def _tracks():
    return q(
        """SELECT t.*, c.name AS company, ct.name AS primary_contact
           FROM commercial_tracks t
           JOIN companies c ON c.id=t.company_id
           LEFT JOIN contacts ct ON ct.id=t.primary_contact_id
           ORDER BY CASE t.status WHEN 'Åben' THEN 1 WHEN 'Afventer' THEN 2
                    WHEN 'Pauset' THEN 3 ELSE 4 END,
                    t.expected_decision_date, t.created_at DESC"""
    )


def _track_label(row):
    return f"{row['company']} · {row['title']}"


def _render_pipeline(companies, tracks):
    open_tracks = tracks[tracks["status"] != "Lukket"] if len(tracks) else tracks
    preferred = st.session_state.pop("business_company_id", None)
    preferred_name = None
    if preferred is not None and len(companies) and preferred in companies["id"].tolist():
        preferred_name = companies.loc[companies["id"] == preferred, "name"].iloc[0]
    cols = st.columns(4)
    cols[0].metric("Åbne forløb", len(open_tracks))
    cols[1].metric("Afventer", int((tracks["status"] == "Afventer").sum()) if len(tracks) else 0)
    cols[2].metric("Pauset", int((tracks["status"] == "Pauset").sum()) if len(tracks) else 0)
    cols[3].metric("Lukkede", int((tracks["status"] == "Lukket").sum()) if len(tracks) else 0)

    with st.expander("Opret forretningsforløb", expanded=False):
        if not len(companies):
            st.info("Opret først en aktør.")
        else:
            company_ids = [int(value) for value in companies["id"].tolist()]
            default_index = company_ids.index(preferred) if preferred in company_ids else 0
            with st.form("business_add_track", clear_on_submit=True):
                company_id = st.selectbox(
                    "Aktør",
                    company_ids,
                    index=default_index,
                    format_func=lambda value: companies.loc[companies["id"] == value, "name"].iloc[0],
                )
                title = st.text_input("Titel på forretningsforløb")
                need = st.text_area("Konkret behov / mulighed", height=110)
                a, b = st.columns(2)
                service_area = a.text_input("Rådgivningsområde")
                expected_date = b.text_input("Forventet beslutningsdato", placeholder="ÅÅÅÅ-MM-DD")
                if st.form_submit_button("Opret forretningsforløb", type="primary"):
                    if not title.strip():
                        st.warning("Titel skal udfyldes.")
                    else:
                        run(
                            """INSERT INTO commercial_tracks
                               (company_id, title, need_description, service_area, status,
                                expected_decision_date, created_at, updated_at)
                               VALUES (?, ?, ?, ?, 'Åben', ?, ?, ?)""",
                            (company_id, title.strip(), need, service_area, expected_date, now_iso(), now_iso()),
                        )
                        st.success("Forretningsforløb oprettet.")
                        st.rerun()

    if not len(tracks):
        st.info("Der er endnu ingen forretningsforløb. Relationer og møder forbliver uændrede.")
        return

    filter_cols = st.columns([1.2, 1.5, 2])
    status_filter = filter_cols[0].multiselect(
        "Status", TRACK_STATUSES, default=["Åben", "Afventer", "Pauset"]
    )
    actor_options = ["Alle"] + sorted(tracks["company"].dropna().unique().tolist())
    actor_filter = filter_cols[1].selectbox(
        "Aktør",
        actor_options,
        index=actor_options.index(preferred_name) if preferred_name in actor_options else 0,
    )
    search = filter_cols[2].text_input("Søg i forretningsforløb")
    shown = tracks.copy()
    if status_filter:
        shown = shown[shown["status"].isin(status_filter)]
    if actor_filter != "Alle":
        shown = shown[shown["company"] == actor_filter]
    if search.strip():
        needle = search.strip().lower()
        searchable = (
            shown["title"].fillna("") + " " + shown["need_description"].fillna("")
            + " " + shown["service_area"].fillna("")
        ).str.lower()
        shown = shown[searchable.str.contains(needle, regex=False)]

    st.markdown(f"### Forløb ({len(shown)})")
    for _, track in shown.iterrows():
        track_id = int(track["id"])
        label = f"{_track_label(track)} · {track['status']}"
        with st.expander(label):
            if track["need_description"]:
                st.write(track["need_description"])
            meta = []
            if track["service_area"]:
                meta.append(track["service_area"])
            if track["primary_contact"]:
                meta.append(f"Kontakt: {track['primary_contact']}")
            if track["expected_decision_date"]:
                meta.append(f"Beslutning: {track['expected_decision_date']}")
            if track["close_reason"]:
                meta.append(f"Resultat: {track['close_reason']}")
            if meta:
                st.caption(" · ".join(meta))

            contacts = q(
                "SELECT id, name, role FROM contacts WHERE company_id=? ORDER BY name",
                (int(track["company_id"]),),
            )
            contact_ids = [None] + [int(value) for value in contacts["id"].tolist()]
            current_contact = int(track["primary_contact_id"]) if _clean_value(track["primary_contact_id"], None) is not None else None
            with st.form(f"business_edit_track_{track_id}"):
                edit_title = st.text_input("Titel", track["title"] or "")
                edit_need = st.text_area("Behov / mulighed", track["need_description"] or "", height=100)
                a, b = st.columns(2)
                edit_area = a.text_input("Rådgivningsområde", track["service_area"] or "")
                edit_date = b.text_input("Forventet beslutningsdato", track["expected_decision_date"] or "")
                c, d, e = st.columns(3)
                edit_status = c.selectbox(
                    "Status", TRACK_STATUSES,
                    index=severity_index(track["status"] or "Åben", TRACK_STATUSES),
                )
                edit_reason = d.selectbox(
                    "Afslutningsårsag", TRACK_CLOSE_REASONS,
                    index=severity_index(track["close_reason"] or "", TRACK_CLOSE_REASONS),
                )
                edit_contact = e.selectbox(
                    "Primær kontakt",
                    contact_ids,
                    index=contact_ids.index(current_contact) if current_contact in contact_ids else 0,
                    format_func=lambda value: "Ingen valgt" if value is None else contacts.loc[contacts["id"] == value, "name"].iloc[0],
                )
                if st.form_submit_button("Gem forløb"):
                    closed_at = now_iso() if edit_status == "Lukket" and not track["closed_at"] else (track["closed_at"] or "")
                    if edit_status != "Lukket":
                        edit_reason, closed_at = "", ""
                    run(
                        """UPDATE commercial_tracks SET title=?, need_description=?, service_area=?,
                           status=?, expected_decision_date=?, close_reason=?, closed_at=?,
                           primary_contact_id=?, updated_at=? WHERE id=?""",
                        (edit_title, edit_need, edit_area, edit_status, edit_date, edit_reason,
                         closed_at, edit_contact, now_iso(), track_id),
                    )
                    st.success("Forløb opdateret.")
                    st.rerun()

            meetings = q(
                "SELECT id, meeting_date, title FROM meetings WHERE company_id=? ORDER BY meeting_date DESC, created_at DESC",
                (int(track["company_id"]),),
            )
            linked_meetings = q("SELECT meeting_id FROM meeting_tracks WHERE track_id=?", (track_id,))
            linked_ids = [int(value) for value in linked_meetings["meeting_id"].tolist()] if len(linked_meetings) else []
            meeting_ids = [int(value) for value in meetings["id"].tolist()] if len(meetings) else []
            with st.form(f"business_track_meetings_{track_id}"):
                selected_meetings = st.multiselect(
                    "Tilknyttede møder",
                    meeting_ids,
                    default=[value for value in linked_ids if value in meeting_ids],
                    format_func=lambda value: f"{meetings.loc[meetings['id'] == value, 'meeting_date'].iloc[0]} · {meetings.loc[meetings['id'] == value, 'title'].iloc[0]}",
                )
                if st.form_submit_button("Gem mødekoblinger"):
                    set_track_meetings(track_id, selected_meetings)
                    st.success("Mødekoblinger opdateret.")

            followups = q(
                "SELECT id, title, due_date FROM followups WHERE company_id=? ORDER BY due_date, created_at DESC",
                (int(track["company_id"]),),
            )
            linked_followups = q("SELECT id FROM followups WHERE commercial_track_id=?", (track_id,))
            linked_followup_ids = [int(value) for value in linked_followups["id"].tolist()] if len(linked_followups) else []
            followup_ids = [int(value) for value in followups["id"].tolist()] if len(followups) else []
            with st.form(f"business_track_followups_{track_id}"):
                selected_followups = st.multiselect(
                    "Tilknyttede opfølgninger",
                    followup_ids,
                    default=[value for value in linked_followup_ids if value in followup_ids],
                    format_func=lambda value: f"{followups.loc[followups['id'] == value, 'due_date'].iloc[0] or 'Uden dato'} · {followups.loc[followups['id'] == value, 'title'].iloc[0]}",
                )
                if st.form_submit_button("Gem opfølgningskoblinger"):
                    set_track_followups(track_id, selected_followups)
                    st.success("Opfølgninger opdateret.")


def _render_proposals(tracks):
    if not len(tracks):
        st.info("Opret et forretningsforløb, før der registreres tilbud.")
        return
    track_ids = [int(value) for value in tracks["id"].tolist()]
    selected_track_id = st.selectbox(
        "Forløb til nyt tilbud",
        track_ids,
        format_func=lambda value: _track_label(tracks.loc[tracks["id"] == value].iloc[0]),
        key="proposal_track_selector",
    )
    version = next_proposal_version(selected_track_id)
    with st.expander("Opret tilbud", expanded=False):
        with st.form("business_add_proposal", clear_on_submit=True):
            title = st.text_input("Tilbudstitel")
            st.caption(f"Version {version}")
            scope = st.text_area("Omfang", height=100)
            deliverables = st.text_area("Forventede leverancer", height=90)
            assumptions = st.text_area("Forudsætninger", height=80)
            a, b = st.columns(2)
            fee_model = a.selectbox("Honorarmodel", FEE_MODELS, index=3)
            has_offer = b.checkbox("Tilbudt honorar er angivet")
            offered_fee = b.number_input("Tilbudt honorar ekskl. moms", min_value=0.0, step=1000.0, disabled=not has_offer)
            fee_note = st.text_area("Honorarnote", height=70)
            c, d = st.columns(2)
            sent_date = c.text_input("Afsendelsesdato", placeholder="ÅÅÅÅ-MM-DD")
            valid_until = d.text_input("Gyldigt til", placeholder="ÅÅÅÅ-MM-DD")
            document_reference = st.text_input("Reference til tilbudsdokument")
            status = st.selectbox("Status", PROPOSAL_STATUSES, index=0)
            if st.form_submit_button("Gem tilbud", type="primary"):
                if not title.strip():
                    st.warning("Tilbudstitel skal udfyldes.")
                else:
                    run(
                        """INSERT INTO proposals
                           (track_id, title, version, scope, deliverables_summary, assumptions,
                            fee_model, offered_fee_ex_vat, fee_note, status, sent_date,
                            valid_until, document_reference, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (selected_track_id, title.strip(), version, scope, deliverables, assumptions,
                         fee_model, offered_fee if has_offer else None, fee_note, status, sent_date,
                         valid_until, document_reference, now_iso(), now_iso()),
                    )
                    st.success("Tilbud gemt.")
                    st.rerun()

    proposals = q(
        """SELECT p.*, t.title AS track_title, c.name AS company,
                  e.id AS engagement_id
           FROM proposals p
           JOIN commercial_tracks t ON t.id=p.track_id
           JOIN companies c ON c.id=t.company_id
           LEFT JOIN engagements e ON e.accepted_proposal_id=p.id
           ORDER BY p.created_at DESC"""
    )
    if not len(proposals):
        st.info("Der er endnu ingen tilbud.")
        return
    for _, proposal in proposals.iterrows():
        proposal_id = int(proposal["id"])
        with st.expander(
            f"{proposal['company']} · {proposal['title']} · v{int(proposal['version'])} · {proposal['status']}"
        ):
            st.caption(f"Forløb: {proposal['track_title']} · {_money(proposal['offered_fee_ex_vat'])} · {proposal['fee_model']}")
            if proposal["scope"]:
                st.write(proposal["scope"])
            if proposal["document_reference"]:
                st.write(f"**Dokumentreference:** {proposal['document_reference']}")
            with st.form(f"business_edit_proposal_{proposal_id}"):
                edit_title = st.text_input("Tilbudstitel", proposal["title"] or "")
                edit_scope = st.text_area("Omfang", proposal["scope"] or "", height=90)
                edit_deliverables = st.text_area(
                    "Forventede leverancer", proposal["deliverables_summary"] or "", height=80
                )
                edit_assumptions = st.text_area(
                    "Forudsætninger", proposal["assumptions"] or "", height=70
                )
                fee_a, fee_b = st.columns(2)
                edit_fee_model = fee_a.selectbox(
                    "Honorarmodel", FEE_MODELS,
                    index=severity_index(proposal["fee_model"] or "Endnu ikke aftalt", FEE_MODELS),
                )
                edit_has_offer = fee_b.checkbox(
                    "Tilbudt honorar er angivet",
                    value=_clean_value(proposal["offered_fee_ex_vat"], None) is not None,
                    key=f"edit_proposal_has_fee_{proposal_id}",
                )
                edit_offered_fee = fee_b.number_input(
                    "Tilbudt honorar ekskl. moms",
                    min_value=0.0,
                    value=float(_clean_value(proposal["offered_fee_ex_vat"], 0.0)),
                    step=1000.0,
                    disabled=not edit_has_offer,
                    key=f"edit_proposal_fee_{proposal_id}",
                )
                edit_status = st.selectbox(
                    "Status", PROPOSAL_STATUSES,
                    index=severity_index(proposal["status"] or "Kladde", PROPOSAL_STATUSES),
                )
                edit_sent = st.text_input("Afsendelsesdato", proposal["sent_date"] or "")
                edit_valid = st.text_input("Gyldigt til", proposal["valid_until"] or "")
                edit_doc = st.text_input("Dokumentreference", proposal["document_reference"] or "")
                edit_note = st.text_area("Honorarnote", proposal["fee_note"] or "", height=70)
                if st.form_submit_button("Gem tilbud"):
                    run(
                        """UPDATE proposals SET title=?, scope=?, deliverables_summary=?,
                           assumptions=?, fee_model=?, offered_fee_ex_vat=?, status=?,
                           sent_date=?, valid_until=?, document_reference=?, fee_note=?,
                           updated_at=? WHERE id=?""",
                        (edit_title, edit_scope, edit_deliverables, edit_assumptions,
                         edit_fee_model, edit_offered_fee if edit_has_offer else None,
                         edit_status, edit_sent, edit_valid, edit_doc, edit_note,
                         now_iso(), proposal_id),
                    )
                    st.rerun()

            if _clean_value(proposal["engagement_id"], None) is None:
                st.markdown("#### Opret kundeopgave fra tilbud")
                with st.form(f"business_convert_proposal_{proposal_id}"):
                    engagement_title = st.text_input("Opgavetitel", proposal["title"] or "")
                    engagement_description = st.text_area("Opgavebeskrivelse", proposal["scope"] or "", height=90)
                    a, b, c = st.columns(3)
                    engagement_status = a.selectbox("Opgavestatus", ENGAGEMENT_STATUSES, index=0)
                    start_date = b.text_input("Startdato", key=f"proposal_start_{proposal_id}")
                    target_end_date = c.text_input("Forventet slutdato", key=f"proposal_end_{proposal_id}")
                    d, e = st.columns(2)
                    agreed_model = d.selectbox(
                        "Aftalt honorarmodel", FEE_MODELS,
                        index=severity_index(proposal["fee_model"] or "Endnu ikke aftalt", FEE_MODELS),
                    )
                    has_agreed_fee = e.checkbox(
                        "Aftalt honorar er angivet",
                        value=_clean_value(proposal["offered_fee_ex_vat"], None) is not None,
                    )
                    default_fee = float(_clean_value(proposal["offered_fee_ex_vat"], 0.0))
                    agreed_fee = e.number_input(
                        "Aftalt honorar ekskl. moms", min_value=0.0,
                        value=default_fee, step=1000.0, disabled=not has_agreed_fee,
                    )
                    agreed_note = st.text_area("Aftalt honorarnote", proposal["fee_note"] or "", height=70)
                    if st.form_submit_button("Accepter tilbud og opret kundeopgave", type="primary"):
                        create_engagement_from_proposal(
                            proposal_id, engagement_title, engagement_description,
                            engagement_status, start_date, target_end_date, agreed_model,
                            agreed_fee if has_agreed_fee else None, agreed_note,
                        )
                        st.success("Tilbud accepteret og kundeopgave oprettet.")
                        st.rerun()
            else:
                st.success("Tilbuddet er knyttet til en kundeopgave.")


def _render_engagements(tracks):
    if not len(tracks):
        st.info("Opret et forretningsforløb, før der registreres kundeopgaver.")
        return
    track_ids = [int(value) for value in tracks["id"].tolist()]
    selected_track_id = st.selectbox(
        "Forløb til direkte kundeopgave",
        track_ids,
        format_func=lambda value: _track_label(tracks.loc[tracks["id"] == value].iloc[0]),
        key="engagement_track_selector",
    )
    with st.expander("Opret kundeopgave uden tilbud", expanded=False):
        with st.form("business_add_direct_engagement", clear_on_submit=True):
            title = st.text_input("Opgavetitel")
            description = st.text_area("Opgavebeskrivelse", height=100)
            a, b, c = st.columns(3)
            status = a.selectbox("Status", ENGAGEMENT_STATUSES, index=0)
            start_date = b.text_input("Startdato", placeholder="ÅÅÅÅ-MM-DD")
            end_date = c.text_input("Forventet slutdato", placeholder="ÅÅÅÅ-MM-DD")
            d, e = st.columns(2)
            fee_model = d.selectbox("Aftalt honorarmodel", FEE_MODELS, index=3)
            has_fee = e.checkbox("Aftalt honorar er angivet")
            agreed_fee = e.number_input("Aftalt honorar ekskl. moms", min_value=0.0, step=1000.0, disabled=not has_fee)
            fee_note = st.text_area("Honorarnote", height=70)
            if st.form_submit_button("Opret kundeopgave", type="primary"):
                if not title.strip():
                    st.warning("Opgavetitel skal udfyldes.")
                else:
                    run(
                        """INSERT INTO engagements
                           (track_id, title, description, fee_model, agreed_fee_ex_vat,
                            fee_note, status, start_date, target_end_date, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (selected_track_id, title.strip(), description, fee_model,
                         agreed_fee if has_fee else None, fee_note, status, start_date,
                         end_date, now_iso(), now_iso()),
                    )
                    st.success("Kundeopgave oprettet.")
                    st.rerun()

    engagements = q(
        """SELECT e.*, t.title AS track_title, c.name AS company,
                  p.offered_fee_ex_vat, p.title AS proposal_title
           FROM engagements e
           JOIN commercial_tracks t ON t.id=e.track_id
           JOIN companies c ON c.id=t.company_id
           LEFT JOIN proposals p ON p.id=e.accepted_proposal_id
           ORDER BY CASE e.status WHEN 'I gang' THEN 1 WHEN 'Planlagt' THEN 2
                    WHEN 'Afventer' THEN 3 ELSE 4 END, e.target_end_date, e.created_at DESC"""
    )
    if not len(engagements):
        st.info("Der er endnu ingen kundeopgaver.")
        return
    for _, engagement in engagements.iterrows():
        engagement_id = int(engagement["id"])
        with st.expander(f"{engagement['company']} · {engagement['title']} · {engagement['status']}"):
            st.caption(
                f"Forløb: {engagement['track_title']} · Aftalt: {_money(engagement['agreed_fee_ex_vat'])} · {engagement['fee_model']}"
            )
            if _clean_value(engagement["offered_fee_ex_vat"], None) is not None:
                st.caption(f"Tilbudt: {_money(engagement['offered_fee_ex_vat'])}")
            if engagement["description"]:
                st.write(engagement["description"])
            with st.form(f"business_edit_engagement_{engagement_id}"):
                edit_title = st.text_input("Opgavetitel", engagement["title"] or "")
                edit_description = st.text_area("Opgavebeskrivelse", engagement["description"] or "", height=90)
                a, b, c = st.columns(3)
                edit_status = a.selectbox(
                    "Status", ENGAGEMENT_STATUSES,
                    index=severity_index(engagement["status"] or "Planlagt", ENGAGEMENT_STATUSES),
                )
                edit_start = b.text_input("Startdato", engagement["start_date"] or "")
                edit_end = c.text_input("Forventet slutdato", engagement["target_end_date"] or "")
                edit_completed = st.text_input("Afslutningsdato", engagement["completed_at"] or "")
                fee_a, fee_b = st.columns(2)
                edit_fee_model = fee_a.selectbox(
                    "Aftalt honorarmodel", FEE_MODELS,
                    index=severity_index(engagement["fee_model"] or "Endnu ikke aftalt", FEE_MODELS),
                )
                edit_has_fee = fee_b.checkbox(
                    "Aftalt honorar er angivet",
                    value=_clean_value(engagement["agreed_fee_ex_vat"], None) is not None,
                    key=f"edit_engagement_has_fee_{engagement_id}",
                )
                edit_fee = fee_b.number_input(
                    "Aftalt honorar ekskl. moms",
                    min_value=0.0,
                    value=float(_clean_value(engagement["agreed_fee_ex_vat"], 0.0)),
                    step=1000.0,
                    disabled=not edit_has_fee,
                    key=f"edit_engagement_fee_{engagement_id}",
                )
                edit_fee_note = st.text_area("Honorarnote", engagement["fee_note"] or "", height=70)
                edit_outcome = st.text_area("Resultat / læring", engagement["outcome_notes"] or "", height=80)
                edit_future = st.text_area("Muligt fremtidigt samarbejde", engagement["future_collaboration_note"] or "", height=80)
                if st.form_submit_button("Gem kundeopgave"):
                    completed = edit_completed
                    if edit_status == "Afsluttet" and not completed:
                        completed = now_iso()[:10]
                    run(
                        """UPDATE engagements SET title=?, description=?, status=?, start_date=?,
                           target_end_date=?, completed_at=?, fee_model=?, agreed_fee_ex_vat=?,
                           fee_note=?, outcome_notes=?, future_collaboration_note=?,
                           updated_at=? WHERE id=?""",
                        (edit_title, edit_description, edit_status, edit_start, edit_end, completed,
                         edit_fee_model, edit_fee if edit_has_fee else None, edit_fee_note,
                         edit_outcome, edit_future, now_iso(), engagement_id),
                    )
                    st.rerun()
            with st.form(f"business_add_deliverable_{engagement_id}", clear_on_submit=True):
                st.markdown("**Ny leverance**")
                deliverable_title = st.text_input("Leverancetitel")
                deliverable_description = st.text_area("Beskrivelse", height=70)
                a, b, c = st.columns(3)
                due_date = a.text_input("Deadline", placeholder="ÅÅÅÅ-MM-DD")
                priority = b.selectbox("Prioritet", ["Lav", "Middel", "Høj"], index=1)
                deliverable_status = c.selectbox("Status", DELIVERABLE_STATUSES, index=0)
                responsible = st.text_input("Ansvarlig / note")
                if st.form_submit_button("Opret leverance"):
                    if not deliverable_title.strip():
                        st.warning("Leverancetitel skal udfyldes.")
                    else:
                        run(
                            """INSERT INTO deliverables
                               (engagement_id, title, description, due_date, priority,
                                status, responsible_note, created_at, updated_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (engagement_id, deliverable_title.strip(), deliverable_description,
                             due_date, priority, deliverable_status, responsible, now_iso(), now_iso()),
                        )
                        st.success("Leverance oprettet.")
                        st.rerun()


def _render_deadlines():
    deliverables = q(
        """SELECT d.*, e.title AS engagement_title, t.id AS track_id,
                  t.company_id, t.title AS track_title, c.name AS company
           FROM deliverables d
           JOIN engagements e ON e.id=d.engagement_id
           JOIN commercial_tracks t ON t.id=e.track_id
           JOIN companies c ON c.id=t.company_id
           ORDER BY CASE WHEN d.due_date='' OR d.due_date IS NULL THEN 1 ELSE 0 END,
                    d.due_date, CASE d.priority WHEN 'Høj' THEN 1 WHEN 'Middel' THEN 2 ELSE 3 END"""
    )
    if not len(deliverables):
        st.info("Der er endnu ingen leverancer eller deadlines.")
        return
    for _, deliverable in deliverables.iterrows():
        deliverable_id = int(deliverable["id"])
        due = deliverable["due_date"] or "Uden deadline"
        with st.expander(
            f"{due} · {deliverable['company']} · {deliverable['title']} · {deliverable['status']}"
        ):
            st.caption(f"Kundeopgave: {deliverable['engagement_title']} · Prioritet: {deliverable['priority']}")
            if deliverable["description"]:
                st.write(deliverable["description"])
            with st.form(f"business_edit_deliverable_{deliverable_id}"):
                edit_title = st.text_input("Titel", deliverable["title"] or "")
                edit_description = st.text_area("Beskrivelse", deliverable["description"] or "", height=80)
                a, b, c = st.columns(3)
                edit_due = a.text_input("Deadline", deliverable["due_date"] or "")
                edit_priority = b.selectbox(
                    "Prioritet", ["Lav", "Middel", "Høj"],
                    index=severity_index(deliverable["priority"] or "Middel", ["Lav", "Middel", "Høj"]),
                )
                edit_status = c.selectbox(
                    "Status", DELIVERABLE_STATUSES,
                    index=severity_index(deliverable["status"] or "Ikke startet", DELIVERABLE_STATUSES),
                )
                edit_responsible = st.text_input("Ansvarlig / note", deliverable["responsible_note"] or "")
                if st.form_submit_button("Gem leverance"):
                    completed_at = deliverable["completed_at"] or ""
                    if edit_status == "Leveret" and not completed_at:
                        completed_at = now_iso()[:10]
                    if edit_status != "Leveret":
                        completed_at = ""
                    run(
                        """UPDATE deliverables SET title=?, description=?, due_date=?, priority=?,
                           status=?, completed_at=?, responsible_note=?, updated_at=? WHERE id=?""",
                        (edit_title, edit_description, edit_due, edit_priority, edit_status,
                         completed_at, edit_responsible, now_iso(), deliverable_id),
                    )
                    st.rerun()
            followups = q(
                "SELECT id, title, due_date FROM followups WHERE company_id=? ORDER BY due_date, created_at DESC",
                (int(deliverable["company_id"]),),
            )
            linked = q("SELECT id FROM followups WHERE deliverable_id=?", (deliverable_id,))
            linked_ids = [int(value) for value in linked["id"].tolist()] if len(linked) else []
            followup_ids = [int(value) for value in followups["id"].tolist()] if len(followups) else []
            with st.form(f"business_deliverable_followups_{deliverable_id}"):
                selected_followups = st.multiselect(
                    "Tilknyttede opfølgninger",
                    followup_ids,
                    default=[value for value in linked_ids if value in followup_ids],
                    format_func=lambda value: f"{followups.loc[followups['id'] == value, 'due_date'].iloc[0] or 'Uden dato'} · {followups.loc[followups['id'] == value, 'title'].iloc[0]}",
                )
                if st.form_submit_button("Gem leverancekoblinger"):
                    set_deliverable_followups(deliverable_id, selected_followups)
                    st.success("Opfølgninger er knyttet til leverancen.")


def _render_completed(tracks):
    closed_tracks = tracks[tracks["status"] == "Lukket"] if len(tracks) else tracks
    completed = q(
        """SELECT e.*, t.title AS track_title, c.name AS company
           FROM engagements e JOIN commercial_tracks t ON t.id=e.track_id
           JOIN companies c ON c.id=t.company_id
           WHERE e.status IN ('Afsluttet','Annulleret')
           ORDER BY e.completed_at DESC, e.updated_at DESC"""
    )
    st.markdown("### Afsluttede kundeopgaver")
    if len(completed):
        for _, row in completed.iterrows():
            st.markdown(f"**{row['company']} · {row['title']}**")
            st.caption(f"{row['status']} · {row['completed_at'] or 'Dato ikke angivet'} · {_money(row['agreed_fee_ex_vat'])}")
            if row["future_collaboration_note"]:
                st.write(f"Muligt fremtidigt samarbejde: {row['future_collaboration_note']}")
            st.divider()
    else:
        st.info("Ingen afsluttede kundeopgaver.")
    st.markdown("### Lukkede forretningsforløb")
    if len(closed_tracks):
        for _, row in closed_tracks.iterrows():
            st.write(f"**{_track_label(row)}** · {row['close_reason'] or 'Ingen årsag angivet'}")
    else:
        st.info("Ingen lukkede forretningsforløb.")


def render():
    st.subheader("Forretning")
    st.caption("Konkrete rådgivningsmuligheder, tilbud, kundeopgaver og leverancer.")
    companies = q("SELECT id, name FROM companies ORDER BY name")
    tracks = _tracks()
    pipeline_tab, proposal_tab, engagement_tab, deadline_tab, completed_tab = st.tabs(
        ["Pipeline", "Tilbud", "Kundeopgaver", "Deadlines", "Afsluttet"]
    )
    with pipeline_tab:
        _render_pipeline(companies, tracks)
    with proposal_tab:
        _render_proposals(tracks)
    with engagement_tab:
        _render_engagements(tracks)
    with deadline_tab:
        _render_deadlines()
    with completed_tab:
        _render_completed(tracks)
