import math
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def clean(value, fallback=None):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return fallback
    return value


def parse_danish_number(text):
    text = str(text or '').strip().replace('\u00a0', '').replace(' ', '')
    if not text:
        return None
    if not re.fullmatch(r'(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d{1,2})?', text):
        raise ValueError('Brug et positivt dansk tal, fx 12.500,00, eller lad feltet stå tomt.')
    try:
        return float(Decimal(text.replace('.', '').replace(',', '.')))
    except InvalidOperation as exc:
        raise ValueError('Tallet kunne ikke læses.') from exc


def number_text(value):
    value = clean(value)
    if value is None:
        return ''
    return f'{float(value):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def fee_text(value, model='Fast pris'):
    value = clean(value)
    if value is None:
        return 'Honorar ikke registreret'
    unit = ' kr./time ekskl. moms' if model == 'Timepris' else ' kr. ekskl. moms'
    return number_text(value) + unit


def parse_date(value):
    value = clean(value)
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def date_text(value):
    parsed = parse_date(value)
    return parsed.strftime('%d-%m-%Y') if parsed else (str(clean(value) or 'Ingen dato'))


def iso_date(value):
    if isinstance(value, str):
        return value
    return value.isoformat() if value else ''
