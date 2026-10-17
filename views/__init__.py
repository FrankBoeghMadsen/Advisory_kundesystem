from views.briefing import render as render_briefing
from views.companies import render as render_companies
from views.contacts import render as render_contacts
from views.dashboard import render as render_dashboard
from views.knowledge import render as render_knowledge
from views.meetings import render as render_meetings
from views.observations import render as render_observations
from views.signals import render as render_signals
from views.sources import render as render_sources
from views.tasks import render as render_tasks
from views.trigger_rules import render as render_trigger_rules


VIEW_RENDERERS = {
    "Dashboard": render_dashboard,
    "Opgaver": render_tasks,
    "Signalindbakke": render_signals,
    "Virksomheder": render_companies,
    "Møder": render_meetings,
    "Observationer": render_observations,
    "Kontakter": render_contacts,
    "Viden": render_knowledge,
    "Briefing": render_briefing,
    "Kilder": render_sources,
    "Triggerregler": render_trigger_rules,
}


def render_page(page):
    renderer = VIEW_RENDERERS.get(page)
    if renderer:
        renderer()
