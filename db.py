
import sqlite3
from pathlib import Path
import csv
from datetime import datetime
import os
import shutil

DATA_DIR = Path(os.environ.get("FRANK_MONITOR_DATA_DIR", Path.home() / "FrankAdvisoryMonitorData"))
DB_PATH = DATA_DIR / "monitor.db"
UPLOAD_DIR = DATA_DIR / "UploadedDocuments"

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    actor_type TEXT DEFAULT 'Life science-virksomhed',
    category TEXT DEFAULT '',
    country TEXT DEFAULT 'Danmark',
    priority TEXT DEFAULT 'Middel',
    website TEXT DEFAULT '',
    linkedin TEXT DEFAULT '',
    status TEXT DEFAULT 'Aktiv',
    aliases TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'rss',
    url TEXT NOT NULL,
    keywords TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    status TEXT DEFAULT 'Aktiv',
    priority TEXT DEFAULT 'Middel',
    last_checked TEXT DEFAULT '',
    last_error TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trigger_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    pattern TEXT NOT NULL,
    default_score TEXT DEFAULT 'Lav',
    weight INTEGER DEFAULT 10,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    source_id INTEGER,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TEXT DEFAULT '',
    collected_at TEXT NOT NULL,
    raw_summary TEXT DEFAULT '',
    trigger_type TEXT DEFAULT '',
    score TEXT DEFAULT 'Lav',
    numeric_score INTEGER DEFAULT 0,
    ai_summary TEXT DEFAULT '',
    suggested_reaction TEXT DEFAULT '',
    contact_strategy TEXT DEFAULT '',
    status TEXT DEFAULT 'Ny',
    unique_key TEXT UNIQUE,
    source_excerpt TEXT DEFAULT '',
    matched_terms TEXT DEFAULT '',
    review_status TEXT DEFAULT 'Ny',
    review_note TEXT DEFAULT '',
    FOREIGN KEY(company_id) REFERENCES companies(id),
    FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    name TEXT NOT NULL,
    role TEXT DEFAULT '',
    email TEXT DEFAULT '',
    linkedin TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    title TEXT DEFAULT '',
    note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS company_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    case_type TEXT DEFAULT '',
    period_start TEXT DEFAULT '',
    period_end TEXT DEFAULT '',
    severity TEXT DEFAULT 'Middel',
    relevance TEXT DEFAULT 'Middel',
    status TEXT DEFAULT 'Åben',
    primary_source TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    significance TEXT DEFAULT '',
    current_relevance TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS case_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    source_name TEXT DEFAULT '',
    url TEXT NOT NULL,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(case_id) REFERENCES company_cases(id)
);

CREATE TABLE IF NOT EXISTS intelligence_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    memory_type TEXT DEFAULT 'Observation',
    title TEXT DEFAULT '',
    content TEXT NOT NULL,
    confidence TEXT DEFAULT 'Middel',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    meeting_date TEXT DEFAULT '',
    meeting_time TEXT DEFAULT '',
    location TEXT DEFAULT '',
    title TEXT NOT NULL,
    meeting_type TEXT DEFAULT 'Kaffemøde',
    participants TEXT DEFAULT '',
    relation_strength TEXT DEFAULT 'Middel',
    mood TEXT DEFAULT '',
    confidentiality TEXT DEFAULT 'Intern',
    shareability TEXT DEFAULT 'Del ikke eksternt',
    summary TEXT DEFAULT '',
    key_takeaways TEXT DEFAULT '',
    next_steps TEXT DEFAULT '',
    raw_text TEXT DEFAULT '',
    uploaded_filename TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    observation_date TEXT DEFAULT '',
    title TEXT NOT NULL,
    observation_type TEXT DEFAULT 'Observation',
    source_type TEXT DEFAULT 'OSINT',
    confidence TEXT DEFAULT 'Middel',
    confidentiality TEXT DEFAULT 'Intern',
    verification_status TEXT DEFAULT 'Ikke verificeret',
    content TEXT NOT NULL,
    implication TEXT DEFAULT '',
    follow_up TEXT DEFAULT '',
    related_meeting_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    FOREIGN KEY(company_id) REFERENCES companies(id),
    FOREIGN KEY(related_meeting_id) REFERENCES meetings(id)
);

CREATE TABLE IF NOT EXISTS uploaded_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    meeting_id INTEGER,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    extracted_text TEXT DEFAULT '',
    document_type TEXT DEFAULT 'Referat',
    confidentiality TEXT DEFAULT 'Intern',
    created_at TEXT NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(id),
    FOREIGN KEY(meeting_id) REFERENCES meetings(id)
);

CREATE TABLE IF NOT EXISTS briefings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    meeting_id INTEGER,
    title TEXT NOT NULL,
    briefing_text TEXT NOT NULL,
    user_notes TEXT DEFAULT '',
    source_context TEXT DEFAULT '',
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'Aktiv',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    FOREIGN KEY(company_id) REFERENCES companies(id),
    FOREIGN KEY(meeting_id) REFERENCES meetings(id)
);

CREATE TABLE IF NOT EXISTS followups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    person TEXT DEFAULT '',
    due_date TEXT DEFAULT '',
    priority TEXT DEFAULT 'Middel',
    status TEXT DEFAULT 'Ny',
    source_type TEXT DEFAULT 'Manuel',
    source_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    FOREIGN KEY(company_id) REFERENCES companies(id)
);
"""

def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "Backups").mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    old_local = Path("data/monitor.db")
    if not DB_PATH.exists() and old_local.exists():
        shutil.copy2(old_local, DB_PATH)

def backup_db_if_needed():
    if not DB_PATH.exists():
        return
    stamp = datetime.now().strftime("%Y-%m-%d")
    backup_path = DATA_DIR / "Backups" / f"monitor_{stamp}.db"
    if not backup_path.exists():
        shutil.copy2(DB_PATH, backup_path)

def connect():
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def add_column_if_missing(conn, table, column, definition):
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init_db():
    conn = connect()
    conn.executescript(SCHEMA)
    migrate_db(conn)
    conn.commit()
    seed_if_empty(conn)
    conn.close()
    backup_db_if_needed()

def migrate_db(conn):
    add_column_if_missing(conn, "companies", "actor_type", "TEXT DEFAULT 'Life science-virksomhed'")
    add_column_if_missing(conn, "companies", "aliases", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "companies", "status", "TEXT DEFAULT 'Aktiv'")
    conn.execute("UPDATE companies SET actor_type='Life science-virksomhed' WHERE actor_type IS NULL OR actor_type=''")
    conn.execute("UPDATE companies SET status='Aktiv' WHERE status IS NULL OR status='' OR status='Monitoreres'")

    add_column_if_missing(conn, "sources", "status", "TEXT DEFAULT 'Aktiv'")
    add_column_if_missing(conn, "sources", "priority", "TEXT DEFAULT 'Middel'")
    add_column_if_missing(conn, "sources", "last_checked", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "sources", "last_error", "TEXT DEFAULT ''")
    conn.execute("UPDATE sources SET status='Aktiv' WHERE status IS NULL OR status=''")
    conn.execute("UPDATE sources SET active=1 WHERE status='Aktiv'")
    conn.execute("UPDATE sources SET active=0 WHERE status!='Aktiv'")

    add_column_if_missing(conn, "signals", "source_excerpt", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "signals", "matched_terms", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "signals", "review_status", "TEXT DEFAULT 'Ny'")
    add_column_if_missing(conn, "signals", "review_note", "TEXT DEFAULT ''")
    conn.execute("UPDATE signals SET review_status='Ny' WHERE review_status IS NULL OR review_status=''")

    add_column_if_missing(conn, "notes", "title", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "notes", "updated_at", "TEXT DEFAULT ''")

    add_column_if_missing(conn, "meetings", "meeting_time", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "meetings", "location", "TEXT DEFAULT ''")

    add_column_if_missing(conn, "briefings", "meeting_id", "INTEGER")
    add_column_if_missing(conn, "briefings", "user_notes", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "briefings", "source_context", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "briefings", "version", "INTEGER DEFAULT 1")
    add_column_if_missing(conn, "briefings", "status", "TEXT DEFAULT 'Aktiv'")
    add_column_if_missing(conn, "briefings", "updated_at", "TEXT DEFAULT ''")

    add_column_if_missing(conn, "followups", "company_id", "INTEGER")
    add_column_if_missing(conn, "followups", "description", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "followups", "person", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "followups", "due_date", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "followups", "priority", "TEXT DEFAULT 'Middel'")
    add_column_if_missing(conn, "followups", "status", "TEXT DEFAULT 'Ny'")
    add_column_if_missing(conn, "followups", "source_type", "TEXT DEFAULT 'Manuel'")
    add_column_if_missing(conn, "followups", "source_id", "INTEGER")
    add_column_if_missing(conn, "followups", "updated_at", "TEXT DEFAULT ''")

def seed_if_empty(conn):
    cur = conn.execute("SELECT COUNT(*) AS n FROM companies")
    if cur.fetchone()["n"] == 0 and Path("seed_data/companies.csv").exists():
        with open("seed_data/companies.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                conn.execute(
                    "INSERT OR IGNORE INTO companies (name, category, country, priority, status, created_at) VALUES (?, ?, ?, ?, 'Aktiv', ?)",
                    (row["name"], row["category"], row["country"], row["priority"], datetime.utcnow().isoformat())
                )
    cur = conn.execute("SELECT COUNT(*) AS n FROM sources")
    if cur.fetchone()["n"] == 0 and Path("seed_data/sources.csv").exists():
        with open("seed_data/sources.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                conn.execute(
                    "INSERT INTO sources (name, source_type, url, keywords, active, status, priority, created_at) VALUES (?, ?, ?, ?, ?, 'Aktiv', 'Middel', ?)",
                    (row["name"], row["source_type"], row["url"], row["keywords"], int(row["active"]), datetime.utcnow().isoformat())
                )
    cur = conn.execute("SELECT COUNT(*) AS n FROM trigger_rules")
    if cur.fetchone()["n"] == 0 and Path("seed_data/trigger_rules.csv").exists():
        with open("seed_data/trigger_rules.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                conn.execute(
                    "INSERT INTO trigger_rules (name, pattern, default_score, weight, active) VALUES (?, ?, ?, ?, 1)",
                    (row["name"], row["pattern"], row["default_score"], int(row["weight"]))
                )
    conn.commit()

def fetch_df(query, params=()):
    import pandas as pd
    with connect() as conn:
        return pd.read_sql_query(query, conn, params=params)

def execute(query, params=()):
    with connect() as conn:
        conn.execute(query, params)
        conn.commit()

def insert_signal(signal):
    with connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO signals
            (company_id, source_id, title, url, published_at, collected_at, raw_summary,
             trigger_type, score, numeric_score, ai_summary, suggested_reaction,
             contact_strategy, status, unique_key, source_excerpt, matched_terms, review_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal.get("company_id"), signal.get("source_id"), signal["title"], signal["url"],
            signal.get("published_at",""), signal["collected_at"], signal.get("raw_summary",""),
            signal.get("trigger_type",""), signal.get("score","Lav"), signal.get("numeric_score",0),
            signal.get("ai_summary",""), signal.get("suggested_reaction",""),
            signal.get("contact_strategy",""), signal.get("status","Ny"), signal["unique_key"],
            signal.get("source_excerpt",""), signal.get("matched_terms",""), signal.get("review_status","Ny")
        ))
        conn.commit()
