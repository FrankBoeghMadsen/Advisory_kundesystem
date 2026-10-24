
import sqlite3
from pathlib import Path
import csv
from datetime import datetime, timezone
import os
import shutil
import tempfile
from contextlib import closing

from runtime_config import (
    APP_MODE,
    DATA_DIR,
    PRODUCTION_DATA_DIR,
    validate_data_configuration,
    validate_database_write_path,
)

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
    validate_data_configuration(APP_MODE, DATA_DIR, PRODUCTION_DATA_DIR)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "Backups").mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    old_local = Path("data/monitor.db")
    if APP_MODE == "production" and not DB_PATH.exists() and old_local.exists():
        shutil.copy2(old_local, DB_PATH)

def connect(db_path=None):
    path = Path(db_path) if db_path else DB_PATH
    if db_path is None:
        validate_data_configuration(APP_MODE, DATA_DIR, PRODUCTION_DATA_DIR)
        ensure_data_dir()
    validate_database_write_path(path, APP_MODE, PRODUCTION_DATA_DIR)
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
    validate_data_configuration(APP_MODE, DATA_DIR, PRODUCTION_DATA_DIR)
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


def migration_004_business_module(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS commercial_tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            primary_contact_id INTEGER,
            title TEXT NOT NULL,
            need_description TEXT DEFAULT '',
            service_area TEXT DEFAULT '',
            status TEXT DEFAULT 'Åben',
            expected_decision_date TEXT DEFAULT '',
            close_reason TEXT DEFAULT '',
            closed_at TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT DEFAULT '',
            FOREIGN KEY(company_id) REFERENCES companies(id),
            FOREIGN KEY(primary_contact_id) REFERENCES contacts(id)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            scope TEXT DEFAULT '',
            deliverables_summary TEXT DEFAULT '',
            assumptions TEXT DEFAULT '',
            fee_model TEXT DEFAULT 'Endnu ikke aftalt',
            offered_fee_ex_vat NUMERIC,
            fee_note TEXT DEFAULT '',
            status TEXT DEFAULT 'Kladde',
            sent_date TEXT DEFAULT '',
            valid_until TEXT DEFAULT '',
            document_reference TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT DEFAULT '',
            FOREIGN KEY(track_id) REFERENCES commercial_tracks(id),
            UNIQUE(track_id, version)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS engagements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL,
            accepted_proposal_id INTEGER,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            fee_model TEXT DEFAULT 'Endnu ikke aftalt',
            agreed_fee_ex_vat NUMERIC,
            fee_note TEXT DEFAULT '',
            status TEXT DEFAULT 'Planlagt',
            start_date TEXT DEFAULT '',
            target_end_date TEXT DEFAULT '',
            completed_at TEXT DEFAULT '',
            outcome_notes TEXT DEFAULT '',
            future_collaboration_note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT DEFAULT '',
            FOREIGN KEY(track_id) REFERENCES commercial_tracks(id),
            FOREIGN KEY(accepted_proposal_id) REFERENCES proposals(id)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS deliverables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            engagement_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            due_date TEXT DEFAULT '',
            priority TEXT DEFAULT 'Middel',
            status TEXT DEFAULT 'Ikke startet',
            completed_at TEXT DEFAULT '',
            responsible_note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT DEFAULT '',
            FOREIGN KEY(engagement_id) REFERENCES engagements(id)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS meeting_tracks (
            meeting_id INTEGER NOT NULL,
            track_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(meeting_id, track_id),
            FOREIGN KEY(meeting_id) REFERENCES meetings(id),
            FOREIGN KEY(track_id) REFERENCES commercial_tracks(id)
        )"""
    )
    add_column_if_missing(
        conn, "followups", "commercial_track_id", "INTEGER REFERENCES commercial_tracks(id)"
    )
    add_column_if_missing(
        conn, "followups", "deliverable_id", "INTEGER REFERENCES deliverables(id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_commercial_tracks_company ON commercial_tracks(company_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_proposals_track ON proposals(track_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_engagements_track ON engagements(track_id)"
    )
    conn.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS idx_engagements_accepted_proposal
           ON engagements(accepted_proposal_id)
           WHERE accepted_proposal_id IS NOT NULL"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_deliverables_engagement ON deliverables(engagement_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_followups_commercial_track ON followups(commercial_track_id)"
    )


def migration_005_agreement_details(conn):
    for table in ("proposals", "engagements"):
        add_column_if_missing(conn, table, "max_hours", "NUMERIC")
        add_column_if_missing(conn, table, "fee_cap_ex_vat", "NUMERIC")
        add_column_if_missing(conn, table, "included_hours", "NUMERIC")
    add_column_if_missing(conn, "engagements", "actual_hours", "NUMERIC")
    add_column_if_missing(conn, "engagements", "reuse_potential", "TEXT DEFAULT 'Ikke vurderet'")
    add_column_if_missing(conn, "engagements", "reuse_notes", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "engagements", "original_agreement", "TEXT DEFAULT ''")
    conn.execute("""CREATE TABLE proposal_changes (
        id INTEGER PRIMARY KEY, proposal_id INTEGER NOT NULL REFERENCES proposals(id),
        changed_at TEXT NOT NULL, reason TEXT NOT NULL,
        previous_values TEXT NOT NULL, new_values TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE engagement_amendments (
        id INTEGER PRIMARY KEY, engagement_id INTEGER NOT NULL REFERENCES engagements(id),
        amendment_date TEXT DEFAULT '', description TEXT NOT NULL,
        previous_fee NUMERIC, new_fee NUMERIC, acceptance_reference TEXT DEFAULT '',
        created_at TEXT NOT NULL)""")
    # Preserve the pre-upgrade agreement, including direct engagements without proposals.
    import json
    for row in conn.execute("SELECT * FROM engagements").fetchall():
        conn.execute("UPDATE engagements SET original_agreement=? WHERE id=?",
                     (json.dumps(dict(row), ensure_ascii=False), row["id"]))
    conn.execute("""CREATE TRIGGER protect_accepted_proposal
        BEFORE UPDATE ON proposals WHEN OLD.status='Accepteret'
        AND NOT EXISTS (
            SELECT 1 FROM proposal_changes h
            WHERE h.proposal_id=OLD.id AND h.changed_at=NEW.updated_at
              AND h.changed_at!=COALESCE(OLD.updated_at,''))
        BEGIN SELECT RAISE(ABORT, 'Accepteret tilbud kræver en logget korrektion'); END""")


def migration_006_agreement_acceptance(conn):
    import json
    add_column_if_missing(conn,'engagements','accepted_proposal_snapshot',"TEXT DEFAULT ''")
    add_column_if_missing(conn,'engagements','agreement_baseline',"TEXT DEFAULT ''")
    add_column_if_missing(conn,'engagements','agreement_revision','INTEGER DEFAULT 0')
    add_column_if_missing(conn,'engagement_amendments','status',"TEXT DEFAULT 'Historisk registreret'")
    add_column_if_missing(conn,'engagement_amendments','proposed_terms',"TEXT DEFAULT '{}'")
    add_column_if_missing(conn,'engagement_amendments','baseline_revision','INTEGER DEFAULT 0')
    add_column_if_missing(conn,'engagement_amendments','accepted_at',"TEXT DEFAULT ''")
    for row in conn.execute('SELECT * FROM engagements').fetchall():
        conn.execute('UPDATE engagements SET agreement_baseline=? WHERE id=?',
            (json.dumps(dict(row),ensure_ascii=False),row['id']))


def migration_007_followup_completion(conn):
    add_column_if_missing(conn, 'followups', 'completed_at', "TEXT DEFAULT ''")
    add_column_if_missing(conn, 'followups', 'completion_result', "TEXT DEFAULT ''")
    # Do not invent completion dates for already closed historical records.
    conn.execute('''CREATE TRIGGER followups_completed_update AFTER UPDATE OF status ON followups
        WHEN NEW.status='Lukket' AND COALESCE(OLD.status,'Ny')<>'Lukket'
        BEGIN UPDATE followups SET completed_at=strftime('%Y-%m-%dT%H:%M:%f','now')
        WHERE id=NEW.id; END''')
    conn.execute('''CREATE TRIGGER followups_completed_insert AFTER INSERT ON followups
        WHEN NEW.status='Lukket' AND COALESCE(NEW.completed_at,'')=''
        BEGIN UPDATE followups SET completed_at=strftime('%Y-%m-%dT%H:%M:%f','now')
        WHERE id=NEW.id; END''')


def migration_008_project_core(conn):
    conn.execute('''CREATE TABLE projects (
        id INTEGER PRIMARY KEY, title TEXT NOT NULL CHECK(length(trim(title))>0),
        purpose TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'Planlagt'
        CHECK(status IN ('Planlagt','Aktivt','Afventer','Afsluttet','Annulleret')),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE project_companies (
        project_id INTEGER NOT NULL REFERENCES projects(id),
        company_id INTEGER NOT NULL REFERENCES companies(id),
        coordinator INTEGER NOT NULL DEFAULT 0 CHECK(coordinator IN (0,1)),
        contracting_party INTEGER NOT NULL DEFAULT 0 CHECK(contracting_party IN (0,1)),
        payer INTEGER NOT NULL DEFAULT 0 CHECK(payer IN (0,1)),
        participant INTEGER NOT NULL DEFAULT 0 CHECK(participant IN (0,1)),
        beneficiary INTEGER NOT NULL DEFAULT 0 CHECK(beneficiary IN (0,1)),
        PRIMARY KEY(project_id,company_id))''')
    conn.execute('''CREATE TABLE project_workstreams (
        id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
        company_id INTEGER, title TEXT NOT NULL CHECK(length(trim(title))>0),
        status TEXT NOT NULL DEFAULT 'Planlagt'
        CHECK(status IN ('Planlagt','I gang','Afventer','Afsluttet','Annulleret')),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        FOREIGN KEY(project_id,company_id) REFERENCES project_companies(project_id,company_id))''')
    conn.execute('''CREATE TABLE project_tracks (
        project_id INTEGER NOT NULL REFERENCES projects(id),
        track_id INTEGER NOT NULL UNIQUE REFERENCES commercial_tracks(id),
        PRIMARY KEY(project_id,track_id))''')
    # Narrow guards also protect these new relations from legacy connections with FK off.
    conditions = {
        'project_companies': "NOT EXISTS(SELECT 1 FROM projects WHERE id=NEW.project_id) OR NOT EXISTS(SELECT 1 FROM companies WHERE id=NEW.company_id)",
        'project_workstreams': "NOT EXISTS(SELECT 1 FROM projects WHERE id=NEW.project_id) OR (NEW.company_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM project_companies WHERE project_id=NEW.project_id AND company_id=NEW.company_id))",
        'project_tracks': "NOT EXISTS(SELECT 1 FROM projects WHERE id=NEW.project_id) OR NOT EXISTS(SELECT 1 FROM commercial_tracks t JOIN project_companies p ON p.company_id=t.company_id WHERE t.id=NEW.track_id AND p.project_id=NEW.project_id)",
    }
    for table, condition in conditions.items():
        for operation in ('INSERT','UPDATE'):
            conn.execute(f'''CREATE TRIGGER validate_{table}_{operation.lower()} BEFORE {operation} ON {table}
                WHEN {condition} BEGIN SELECT RAISE(ABORT,'Ugyldig projektrelation'); END''')
    conn.execute('''CREATE TRIGGER protect_project_company_delete BEFORE DELETE ON project_companies
        WHEN EXISTS(SELECT 1 FROM project_workstreams WHERE project_id=OLD.project_id AND company_id=OLD.company_id)
        OR EXISTS(SELECT 1 FROM project_tracks p JOIN commercial_tracks t ON t.id=p.track_id WHERE p.project_id=OLD.project_id AND t.company_id=OLD.company_id)
        BEGIN SELECT RAISE(ABORT,'Deltageren har tilknyttede spor eller forløb'); END''')
    conn.execute('''CREATE TRIGGER protect_project_company_key BEFORE UPDATE OF project_id,company_id ON project_companies
        WHEN NEW.project_id<>OLD.project_id OR NEW.company_id<>OLD.company_id
        BEGIN SELECT RAISE(ABORT,'Projektdeltagerens nøgle kan ikke flyttes'); END''')
    conn.execute('''CREATE TRIGGER protect_project_delete BEFORE DELETE ON projects
        WHEN EXISTS(SELECT 1 FROM project_companies WHERE project_id=OLD.id)
        OR EXISTS(SELECT 1 FROM project_workstreams WHERE project_id=OLD.id)
        OR EXISTS(SELECT 1 FROM project_tracks WHERE project_id=OLD.id)
        BEGIN SELECT RAISE(ABORT,'Projektet har relationer'); END''')
    conn.execute('''CREATE TRIGGER protect_project_company_source BEFORE DELETE ON companies
        WHEN EXISTS(SELECT 1 FROM project_companies WHERE company_id=OLD.id)
        BEGIN SELECT RAISE(ABORT,'Virksomheden er projektdeltager'); END''')
    conn.execute('''CREATE TRIGGER protect_project_track_source BEFORE DELETE ON commercial_tracks
        WHEN EXISTS(SELECT 1 FROM project_tracks WHERE track_id=OLD.id)
        BEGIN SELECT RAISE(ABORT,'Forløbet er projekttilknyttet'); END''')
    conn.execute('''CREATE TRIGGER protect_project_track_company BEFORE UPDATE OF company_id ON commercial_tracks
        WHEN EXISTS(SELECT 1 FROM project_tracks p WHERE p.track_id=OLD.id AND NOT EXISTS(
        SELECT 1 FROM project_companies c WHERE c.project_id=p.project_id AND c.company_id=NEW.company_id))
        BEGIN SELECT RAISE(ABORT,'Forløbets virksomhed skal være projektdeltager'); END''')
    for parent, condition in (
        ('projects','EXISTS(SELECT 1 FROM project_companies WHERE project_id=OLD.id) OR EXISTS(SELECT 1 FROM project_workstreams WHERE project_id=OLD.id) OR EXISTS(SELECT 1 FROM project_tracks WHERE project_id=OLD.id)'),
        ('companies','EXISTS(SELECT 1 FROM project_companies WHERE company_id=OLD.id)'),
        ('commercial_tracks','EXISTS(SELECT 1 FROM project_tracks WHERE track_id=OLD.id)')):
        conn.execute(f'''CREATE TRIGGER protect_{parent}_project_id BEFORE UPDATE OF id ON {parent}
            WHEN NEW.id<>OLD.id AND ({condition})
            BEGIN SELECT RAISE(ABORT,'En refereret projektnøgle kan ikke ændres'); END''')
    conn.execute('CREATE INDEX idx_project_workstreams_project ON project_workstreams(project_id)')


def migration_009_planning_acceptance(conn):
    conn.execute('''CREATE TABLE proposal_acceptances (
        id INTEGER PRIMARY KEY, proposal_id INTEGER NOT NULL REFERENCES proposals(id),
        acceptance_date TEXT NOT NULL DEFAULT '', acceptance_method TEXT NOT NULL DEFAULT '',
        document_reference TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', recorded_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE work_blocks (
        id INTEGER PRIMARY KEY, work_date TEXT NOT NULL,
        engagement_id INTEGER NOT NULL REFERENCES engagements(id),
        deliverable_id INTEGER REFERENCES deliverables(id),
        description TEXT NOT NULL CHECK(length(trim(description))>0),
        planned_minutes INTEGER NOT NULL CHECK(planned_minutes>0), note TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE daily_capacity (
        work_date TEXT PRIMARY KEY, capacity_minutes INTEGER NOT NULL CHECK(capacity_minutes>=0))''')
    conn.execute('CREATE INDEX idx_work_blocks_date ON work_blocks(work_date)')
    # Targeted guards do not change legacy connections or global FK behaviour.
    for operation in ('INSERT','UPDATE'):
        conn.execute(f'''CREATE TRIGGER work_blocks_guard_{operation.lower()} BEFORE {operation} ON work_blocks
            WHEN NOT EXISTS(SELECT 1 FROM engagements WHERE id=NEW.engagement_id)
            OR (NEW.deliverable_id IS NOT NULL AND NOT EXISTS(
                SELECT 1 FROM deliverables WHERE id=NEW.deliverable_id AND engagement_id=NEW.engagement_id))
            BEGIN SELECT RAISE(ABORT,'Ugyldig planlægningsrelation'); END''')
    for table,column in (('engagements','engagement_id'),('deliverables','deliverable_id')):
        conn.execute(f'''CREATE TRIGGER protect_planned_{table} BEFORE DELETE ON {table}
            WHEN EXISTS(SELECT 1 FROM work_blocks WHERE {column}=OLD.id)
            BEGIN SELECT RAISE(ABORT,'Posten har arbejdsblokke'); END''')
        conn.execute(f'''CREATE TRIGGER protect_planned_key_{table} BEFORE UPDATE OF id ON {table}
            WHEN NEW.id<>OLD.id AND EXISTS(SELECT 1 FROM work_blocks WHERE {column}=OLD.id)
            BEGIN SELECT RAISE(ABORT,'Posten har arbejdsblokke'); END''')
    conn.execute('''CREATE TRIGGER protect_planned_delivery_parent BEFORE UPDATE OF engagement_id ON deliverables
        WHEN NEW.engagement_id<>OLD.engagement_id AND EXISTS(SELECT 1 FROM work_blocks WHERE deliverable_id=OLD.id)
        BEGIN SELECT RAISE(ABORT,'Leverancen har arbejdsblokke'); END''')
    conn.execute('''CREATE TRIGGER acceptance_guard BEFORE INSERT ON proposal_acceptances
        WHEN NOT EXISTS(SELECT 1 FROM proposals WHERE id=NEW.proposal_id AND status='Accepteret')
        BEGIN SELECT RAISE(ABORT,'Tilbuddet er ikke accepteret'); END''')
    for operation in ('UPDATE','DELETE'):
        conn.execute(f'''CREATE TRIGGER acceptance_history_{operation.lower()} BEFORE {operation} ON proposal_acceptances
            BEGIN SELECT RAISE(ABORT,'Acceptdokumentation bevares som historik'); END''')
    conn.execute('''CREATE TRIGGER protect_documented_proposal BEFORE DELETE ON proposals
        WHEN EXISTS(SELECT 1 FROM proposal_acceptances WHERE proposal_id=OLD.id)
        BEGIN SELECT RAISE(ABORT,'Tilbuddet har acceptdokumentation'); END''')
    conn.execute('''CREATE TRIGGER protect_documented_proposal_key BEFORE UPDATE OF id ON proposals
        WHEN NEW.id<>OLD.id AND EXISTS(SELECT 1 FROM proposal_acceptances WHERE proposal_id=OLD.id)
        BEGIN SELECT RAISE(ABORT,'Tilbuddet har acceptdokumentation'); END''')


MIGRATIONS = (
    (1, "core_schema", migration_001_core_schema),
    (2, "briefings", migration_002_briefings),
    (3, "followups", migration_003_followups),
    (4, "business_module", migration_004_business_module),
    (5, "agreement_details", migration_005_agreement_details),
    (6, "agreement_acceptance", migration_006_agreement_acceptance),
    (7, "followup_completion", migration_007_followup_completion),
    (8, "project_core", migration_008_project_core),
    (9, "planning_acceptance", migration_009_planning_acceptance),
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
    validate_data_configuration(APP_MODE, DATA_DIR, PRODUCTION_DATA_DIR)
    if APP_MODE == 'development' and any(m[0] == 8 for m in pending_migrations(DB_PATH)) and os.environ.get('FRANK_MONITOR_STAGE61_MIGRATION') != '1':
        from runtime_config import RuntimeConfigurationError
        raise RuntimeConfigurationError('Etape 6.1 kræver genstart med Start Monitor Development.bat. Automatisk genindlæsning må ikke migrere databasen.')
    if APP_MODE == 'development' and any(m[0] == 7 for m in pending_migrations(DB_PATH)) and os.environ.get('FRANK_MONITOR_STAGE52_MIGRATION') != '1':
        from runtime_config import RuntimeConfigurationError
        raise RuntimeConfigurationError('Etape 5.2 kræver genstart med Start Monitor Development.bat. Automatisk genindlæsning må ikke migrere databasen.')
    if APP_MODE == "production" and any(m[0] >= 5 for m in pending_migrations(DB_PATH)):
        from runtime_config import RuntimeConfigurationError
        raise RuntimeConfigurationError(
            "Udviklingsversionen afventer godkendelse til drift. Brug udviklingsstarten eller den tidligere driftversion."
        )
    if APP_MODE == 'development' and any(m[0] == 9 for m in pending_migrations(DB_PATH)) and os.environ.get('FRANK_MONITOR_PLANNING_MIGRATION') != '1':
        from runtime_config import RuntimeConfigurationError
        raise RuntimeConfigurationError('Ugeplanlægning kræver genstart med Start Monitor Development.bat. Automatisk genindlæsning må ikke migrere databasen.')
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
