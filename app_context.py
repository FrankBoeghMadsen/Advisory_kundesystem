import streamlit as st
from datetime import date, datetime
from pathlib import Path

from app_config import ACTOR_TYPES, FOLLOWUP_STATUSES, FOLLOWUP_TYPES
from repositories import count_for, latest_meeting_id, q, run
from services.advisory_service import (
    briefing_context,
    company_timeline,
    meeting_focus_context,
    meeting_options,
    sync_actor_sources,
)
from services.ai_service import ai_briefing_text, ai_meeting_followup_text
from services.file_service import save_uploaded_file
from ui.formatting import (
    clean_text_value,
    display_date,
    followup_due_label,
    followup_group,
    has_db_id,
    merge_text_values,
    now_iso,
    severity_index,
    short,
)
from ui.navigation import open_company_section, open_followup, set_company, set_page

try:
    from document_utils import extract_text_from_file, simple_meeting_summary
except Exception:
    extract_text_from_file = None
    simple_meeting_summary = None
