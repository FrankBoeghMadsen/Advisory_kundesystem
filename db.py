
import sqlite3
from pathlib import Path
import csv
from datetime import datetime, timezone
import os
import shutil
import tempfile
from contextlib import closing

DATA_DIR = Path(os.environ.get("FRANK_MONITOR_DATA_DIR", Path.home() / "FrankAdvisoryMonitorData"))
DB_PATH = DATA_DIR / "monitor.db"
UPLOAD_DIR = DATA_DIR / "UploadedDocuments"


def utc_now_iso():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

MIGRATION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
)
"""

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
    phone TEXT DEFAULT '',
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
    followup_type TEXT DEFAULT 'Opfølgning',
    description TEXT DEFAULT '',
    next_action TEXT DEFAULT '',
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

def connect(db_path=None):
    path = Path(db_path) if db_path else DB_PATH
    if db_path is None:
        ensure_data_dir()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def verify_database(db_path):
    """Return integrity details without modifying the database."""
    path = Path(db_path).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    uri = f"{path.as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
        counts = {}
        for table in tables:
            if table.startswith("sqlite_"):
                continue
            escaped = table.replace('"', '""')
            counts[table] = conn.execute(f'SELECT COUNT(*) FROM "{escaped}"').fetchone()[0]
        return {
            "path": str(path),
            "integrity": integrity,
            "foreign_key_violations": len(foreign_key_violations),
            "tables": tables,
            "row_counts": counts,
        }
    finally:
        conn.close()


def create_backup(label="manual", source_path=None):
    """Create and verify a consistent SQLite backup."""
    ensure_data_dir()
    source = Path(source_path) if source_path else DB_PATH
    if not source.exists():
        raise FileNotFoundError(source)

    backup_dir = DATA_DIR / "Backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    safe_label = "".join(ch for ch in label if ch.isalnum() or ch in ("-", "_")) or "backup"
    if safe_label == "daily":
        filename = f"monitor_{datetime.now():%Y-%m-%d}.db"
    else:
        filename = f"monitor_{safe_label}_{datetime.now():%Y%m%d_%H%M%S_%f}.db"
    backup_path = backup_dir / filename

    if safe_label == "daily" and backup_path.exists():
        return backup_path

    temporary_path = backup_path.with_suffix(".tmp")
    source_uri = f"{source.resolve().as_uri()}?mode=ro"
    source_conn = sqlite3.connect(source_uri, uri=True)
    destination_conn = sqlite3.connect(temporary_path)
    try:
        source_conn.backup(destination_conn)
    finally:
        destination_conn.close()
        source_conn.close()

    result = verify_database(temporary_path)
    if result["integrity"] != "ok" or result["foreign_key_violations"]:
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError("Backup fejlede integritetskontrollen")
    os.replace(temporary_path, backup_path)
    return backup_path


def backup_db_if_needed():
    if not DB_PATH.exists():
        return None
    return create_backup("daily")


def restore_test(backup_path):
    """Prove that a backup can be restored and opened, without touching live data."""
    backup = Path(backup_path)
    restore_root = DATA_DIR / "RestoreTests"
    restore_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="frank-monitor-restore-", dir=restore_root
    ) as temp_dir:
        restored = Path(temp_dir) / "monitor.db"
        source_conn = sqlite3.connect(f"{backup.resolve().as_uri()}?mode=ro", uri=True)
        destination_conn = sqlite3.connect(restored)
        try:
            source_conn.backup(destination_conn)
        finally:
            destination_conn.close()
            source_conn.close()
        return verify_database(restored)

def add_column_if_missing(conn, table, column, definition):
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def migration_001_core_schema(conn):
    for statement in SCHEMA.split(";"):
        if statement.strip():
            conn.execute(statement)
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

    add_column_if_missing(conn, "contacts", "phone", "TEXT DEFAULT ''")

    add_column_if_missing(conn, "notes", "title", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "notes", "updated_at", "TEXT DEFAULT ''")

    add_column_if_missing(conn, "meetings", "meeting_time", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "meetings", "location", "TEXT DEFAULT ''")


def migration_002_briefings(conn):
    add_column_if_missing(conn, "briefings", "meeting_id", "INTEGER")
    add_column_if_missing(conn, "briefings", "user_notes", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "briefings", "source_context", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "briefings", "version", "INTEGER DEFAULT 1")
    add_column_if_missing(conn, "briefings", "status", "TEXT DEFAULT 'Aktiv'")
    add_column_if_missing(conn, "briefings", "updated_at", "TEXT DEFAULT ''")


def migration_003_followups(conn):
    add_column_if_missing(conn, "followups", "company_id", "INTEGER")
    add_column_if_missing(conn, "followups", "followup_type", "TEXT DEFAULT 'Opfølgning'")
    add_column_if_missing(conn, "followups", "description", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "followups", "next_action", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "followups", "person", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "followups", "due_date", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "followups", "priority", "TEXT DEFAULT 'Middel'")
    add_column_if_missing(conn, "followups", "status", "TEXT DEFAULT 'Ny'")
    add_column_if_missing(conn, "followups", "source_type", "TEXT DEFAULT 'Manuel'")
    add_column_if_missing(conn, "followups", "source_id", "INTEGER")
    add_column_if_missing(conn, "followups", "updated_at", "TEXT DEFAULT ''")
    conn.execute("UPDATE followups SET followup_type='Opfølgning' WHERE followup_type IS NULL OR followup_type=''")


MIGRATIONS = (
    (1, "core_schema", migration_001_core_schema),
    (2, "briefings", migration_002_briefings),
    (3, "followups", migration_003_followups),
)


def applied_migration_versions(db_path):
    path = Path(db_path)
    if not path.exists():
        return set()
    uri = f"{path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        if not exists:
            return set()
        return {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    finally:
        conn.close()


def pending_migrations(db_path=None):
    path = Path(db_path) if db_path else DB_PATH
    applied = applied_migration_versions(path)
    return [migration for migration in MIGRATIONS if migration[0] not in applied]


def migrate_db(conn):
    conn.execute(MIGRATION_TABLE_SQL)
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    for version, name, migration in MIGRATIONS:
        if version in applied:
            continue
        try:
            conn.execute("BEGIN")
            migration(conn)
            conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (version, name, utc_now_iso()),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def init_db():
    ensure_data_dir()
    existing_database = DB_PATH.exists()
    migrations = pending_migrations(DB_PATH)
    if existing_database and migrations:
        create_backup("pre_migration")

    conn = connect()
    try:
        migrate_db(conn)
        seed_if_empty(conn)
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_key_violations:
            raise RuntimeError(
                f"Databasekontrol fejlede: integrity={integrity}, "
                f"foreign_key_violations={len(foreign_key_violations)}"
            )
    finally:
        conn.close()
    backup_db_if_needed()

def seed_if_empty(conn):
    cur = conn.execute("SELECT COUNT(*) AS n FROM companies")
    if cur.fetchone()["n"] == 0 and Path("seed_data/companies.csv").exists():
        with open("seed_data/companies.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                conn.execute(
                    "INSERT OR IGNORE INTO companies (name, category, country, priority, status, created_at) VALUES (?, ?, ?, ?, 'Aktiv', ?)",
                    (row["name"], row["category"], row["country"], row["priority"], utc_now_iso())
                )
    cur = conn.execute("SELECT COUNT(*) AS n FROM sources")
    if cur.fetchone()["n"] == 0 and Path("seed_data/sources.csv").exists():
        with open("seed_data/sources.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                conn.execute(
                    "INSERT INTO sources (name, source_type, url, keywords, active, status, priority, created_at) VALUES (?, ?, ?, ?, ?, 'Aktiv', 'Middel', ?)",
                    (row["name"], row["source_type"], row["url"], row["keywords"], int(row["active"]), utc_now_iso())
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
    with closing(connect()) as conn:
        return pd.read_sql_query(query, conn, params=params)

def execute(query, params=()):
    with closing(connect()) as conn:
        conn.execute(query, params)
        conn.commit()

def insert_signal(signal):
    with closing(connect()) as conn:
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
