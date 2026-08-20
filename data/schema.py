"""
ElderCare - SQLite database schema + initialization.

The DB stores everything that changes per elder (profiles, plans, executions,
measurements). The knowledge banks (diseases, medications, conditions,
activities) are kept in Excel and mirrored into read-only tables on each
launch — so an admin can edit the .xlsx and re-launch to refresh.
"""

from pathlib import Path
import sqlite3
import pandas as pd

DB_PATH = Path(__file__).parent / "eldercare.db"
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge_banks"


# --- schema ---
DDL = [
    """
    CREATE TABLE IF NOT EXISTS organizations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        kind        TEXT NOT NULL,  -- nursing_home / sheltered / day_center / homecare / community
        country     TEXT,
        language    TEXT DEFAULT 'he',
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER REFERENCES organizations(id),
        username        TEXT UNIQUE NOT NULL,
        full_name       TEXT,
        role            TEXT NOT NULL,  -- admin / manager / caregiver / elder / family
        language        TEXT DEFAULT 'he',
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS elders (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER REFERENCES organizations(id),
        full_name       TEXT NOT NULL,
        birth_date      TEXT,
        gender          TEXT,
        room_number     TEXT,
        primary_language TEXT DEFAULT 'he',
        notes           TEXT,
        active          INTEGER DEFAULT 1,
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # 9-dimension profile -- one row per elder, all dimensions in one place.
    """
    CREATE TABLE IF NOT EXISTS elder_profile (
        elder_id        INTEGER PRIMARY KEY REFERENCES elders(id) ON DELETE CASCADE,

        -- medical: list of disease codes (CSV)
        medical_codes   TEXT,
        medical_notes   TEXT,

        -- medication: list of medication codes (CSV)
        medication_codes TEXT,
        medication_notes TEXT,

        -- nursing / cognitive / mental / social / family / cultural:
        -- list of condition codes (CSV). 'demographic' is no longer
        -- a code list — it's the structured living-environment columns below.
        nursing_codes      TEXT,
        cognitive_codes    TEXT,
        mental_codes       TEXT,
        social_codes       TEXT,
        family_codes       TEXT,
        demographic_codes  TEXT,  -- legacy, kept for backward compat (unused)
        cultural_codes     TEXT,  -- CON codes for cultural/identity (Holocaust survivor, Arabic speaker, religious, immigrant)

        -- demographic dimension = LIVING ENVIRONMENT (structured)
        living_arrangement     TEXT,      -- home_alone / home_family / assisted_living / nursing_home / day_center
        residence_floor        INTEGER DEFAULT 0,   -- 0 = ground floor
        has_elevator           INTEGER DEFAULT 1,   -- 0/1
        outdoor_accessibility  TEXT,      -- full / limited / none

        -- religion + observance level (each combo derives limitations + needs in the optimizer)
        religion               TEXT,      -- jewish / muslim / christian / hindu / none
        religiosity_level      TEXT,      -- very_observant / observant / secular

        -- meal times — fixed 1-hour blocks the optimizer leaves alone.
        -- lunch at 12:00 so it ends before the 13:00-16:00 rest window.
        breakfast_time         TEXT DEFAULT '08:00',
        breakfast_duration     INTEGER DEFAULT 60,
        lunch_time             TEXT DEFAULT '12:00',
        lunch_duration         INTEGER DEFAULT 60,
        dinner_time            TEXT DEFAULT '18:00',
        dinner_duration        INTEGER DEFAULT 60,

        -- elder preferences: which activity categories they like (CSV of category names),
        -- preferred time slots ("morning","noon","afternoon","evening"),
        -- and explicit WANT activity codes (these get an extra scoring bonus).
        preferences_categories    TEXT,
        preferences_time_slots    TEXT,
        preferred_activity_codes  TEXT,

        -- ranking weights (1..10) for each dimension - drives optimizer.
        weight_medical      REAL DEFAULT 5,
        weight_medication   REAL DEFAULT 5,
        weight_nursing      REAL DEFAULT 5,
        weight_cognitive    REAL DEFAULT 5,
        weight_mental       REAL DEFAULT 5,
        weight_social       REAL DEFAULT 5,
        weight_family       REAL DEFAULT 5,
        weight_demographic  REAL DEFAULT 5,
        weight_cultural     REAL DEFAULT 5,
        weight_preference   REAL DEFAULT 6,

        -- capability level (1..5) - filters activities by min_capability_level
        capability_level    INTEGER DEFAULT 3,

        updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # Daily plan = a set of activity assignments to time slots for one date.
    """
    CREATE TABLE IF NOT EXISTS daily_plans (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        elder_id        INTEGER REFERENCES elders(id) ON DELETE CASCADE,
        plan_date       TEXT NOT NULL,
        generated_at    TEXT DEFAULT CURRENT_TIMESTAMP,
        optimizer_version TEXT,
        objective_score REAL,
        UNIQUE(elder_id, plan_date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plan_items (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id         INTEGER REFERENCES daily_plans(id) ON DELETE CASCADE,
        time_slot       TEXT NOT NULL,  -- morning / noon / afternoon / evening
        start_time      TEXT,           -- HH:MM
        activity_code   TEXT NOT NULL,
        duration_min    INTEGER,
        rationale       TEXT,           -- why optimizer picked this
        executed        INTEGER DEFAULT 0,
        execution_notes TEXT,
        executed_at     TEXT,
        skipped_reason  TEXT,
        instructor_rating INTEGER,      -- 1..5 instructor's review of the resident
        instructor_review TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS measurements (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        elder_id        INTEGER REFERENCES elders(id) ON DELETE CASCADE,
        measurement_date TEXT NOT NULL,
        test_code       TEXT NOT NULL,  -- e.g. MMSE / TUG / BARTHEL / MOOD / PAIN
        score           REAL,
        max_score       REAL,
        notes           TEXT,
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # care-plan goals per elder (auto-generated by optimizer, manually editable)
    """
    CREATE TABLE IF NOT EXISTS care_goals (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        elder_id    INTEGER NOT NULL REFERENCES elders(id) ON DELETE CASCADE,
        goal_text   TEXT NOT NULL,
        target_tags TEXT,                 -- CSV of need tags this goal advances
        priority    INTEGER DEFAULT 3,    -- 1..5 (5 = highest)
        source      TEXT DEFAULT 'auto',  -- auto / manual
        active      INTEGER DEFAULT 1,
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # family members + main contacts per elder
    """
    CREATE TABLE IF NOT EXISTS family_contacts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        elder_id        INTEGER REFERENCES elders(id) ON DELETE CASCADE,
        relation        TEXT,
        name            TEXT NOT NULL,
        phone           TEXT,
        email           TEXT,
        is_primary      INTEGER DEFAULT 0,
        lives_with_elder INTEGER DEFAULT 0,
        notes           TEXT,
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # local nearby programs the elder can be referred to (day centers,
    # assisted living facilities, city programs).
    """
    CREATE TABLE IF NOT EXISTS external_programs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER REFERENCES organizations(id),
        name            TEXT NOT NULL,
        organization    TEXT,
        category        TEXT,
        address         TEXT,
        city            TEXT,
        accessibility   TEXT,
        contact         TEXT,
        url             TEXT,
        languages       TEXT,
        cost            TEXT,
        notes           TEXT,
        recurring_days  TEXT,
        start_time      TEXT,
        duration_min    INTEGER,
        strengthens     TEXT,
        min_capability_level INTEGER DEFAULT 1,
        source_kind     TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS elder_program_enrollment (
        elder_id        INTEGER NOT NULL REFERENCES elders(id) ON DELETE CASCADE,
        program_id      INTEGER NOT NULL REFERENCES external_programs(id) ON DELETE CASCADE,
        notes           TEXT,
        enrolled_at     TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (elder_id, program_id)
    )
    """,
    # online knowledge sources the institution links to (medical registries,
    # research databases, guideline portals). Managed from the Knowledge view.
    """
    CREATE TABLE IF NOT EXISTS kb_online_sources (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        url         TEXT NOT NULL,
        category    TEXT,
        description TEXT,
        active      INTEGER DEFAULT 1,
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


# A few real, well-known reference sources, inserted once when the table is
# empty so the feature ships with examples. The institution can add/remove more.
DEFAULT_ONLINE_SOURCES = [
    ("מאגר התרופות – משרד הבריאות", "https://israeldrugs.health.gov.il/",
     "medications", "מאגר התרופות הרשומות בישראל - עלונים, מינונים והתוויות."),
    ("ICD-11 – ארגון הבריאות העולמי", "https://icd.who.int/",
     "diseases", "הסיווג הבינלאומי של מחלות (WHO) - אבחנות וקודים."),
    ("MedlinePlus", "https://medlineplus.gov/",
     "conditions", "מידע רפואי מהימן לציבור על מחלות, מצבים ותרופות (NIH)."),
    ("PubMed", "https://pubmed.ncbi.nlm.nih.gov/",
     "research", "מאגר מאמרים ומחקרים רפואיים (NIH/NLM)."),
    ("משרד הרווחה – שירותים לאזרח הוותיק", "https://www.gov.il/he/departments/molsa",
     "activities", "תוכניות, זכויות ושירותים לזקנים ולמטפלים."),
    ("data.gov.il – נתוני בריאות", "https://data.gov.il/",
     "general", "נתונים ממשלתיים פתוחים, כולל מאגרי בריאות ורווחה."),
]

# kb_* tables are mirrored from Excel on every launch — drop and recreate so
# schema changes (e.g., added columns) always apply cleanly.
KB_DDL = [
    "DROP TABLE IF EXISTS kb_diseases",
    "CREATE TABLE kb_diseases (code TEXT PRIMARY KEY, name_he TEXT, name_en TEXT, category TEXT, limitations TEXT, needs_strengthening TEXT, description_he TEXT)",
    "DROP TABLE IF EXISTS kb_medications",
    "CREATE TABLE kb_medications (code TEXT PRIMARY KEY, name_he TEXT, name_en TEXT, drug_class TEXT, side_effects TEXT, activity_contraindications TEXT, needs_strengthening TEXT, description_he TEXT)",
    "DROP TABLE IF EXISTS kb_conditions",
    "CREATE TABLE kb_conditions (code TEXT PRIMARY KEY, name_he TEXT, name_en TEXT, dimension TEXT, severity TEXT, limitations TEXT, needs_strengthening TEXT, description_he TEXT)",
    "DROP TABLE IF EXISTS kb_activities",
    "CREATE TABLE kb_activities (code TEXT PRIMARY KEY, name_he TEXT, name_en TEXT, category TEXT, subcategory TEXT, strengthens TEXT, contraindications TEXT, min_capability_level INTEGER, duration_min INTEGER, group_size_min INTEGER, group_size_max INTEGER, location TEXT, description_he TEXT)",
    "DROP TABLE IF EXISTS kb_exercises",
    "CREATE TABLE kb_exercises (code TEXT PRIMARY KEY, name_he TEXT, name_en TEXT, name_ru TEXT, type TEXT, target_muscles TEXT, target_systems TEXT, strengthens TEXT, contraindications TEXT, intensity INTEGER, min_capability_level INTEGER, duration_min INTEGER, reps_sets TEXT, position TEXT, equipment TEXT, description_he TEXT)",
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    """Create tables, then mirror the Excel knowledge banks into kb_* tables."""
    conn = get_connection()
    cur = conn.cursor()
    for ddl in DDL:
        cur.execute(ddl)
    # rebuild kb_* tables fresh so schema additions take effect
    for ddl in KB_DDL:
        cur.execute(ddl)

    # seed example online sources once (kept if the table already has rows)
    if cur.execute("SELECT COUNT(*) FROM kb_online_sources").fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO kb_online_sources (name, url, category, description) "
            "VALUES (?, ?, ?, ?)",
            DEFAULT_ONLINE_SOURCES,
        )

    # migration: rename old avoid_activity_codes column to preferred_activity_codes
    cur.execute("PRAGMA table_info(elder_profile)")
    cols = {r[1] for r in cur.fetchall()}
    if "avoid_activity_codes" in cols and "preferred_activity_codes" not in cols:
        cur.execute(
            "ALTER TABLE elder_profile "
            "RENAME COLUMN avoid_activity_codes TO preferred_activity_codes"
        )
        # also clear since semantics flipped
        cur.execute("UPDATE elder_profile SET preferred_activity_codes = ''")
    elif "preferred_activity_codes" not in cols:
        cur.execute("ALTER TABLE elder_profile ADD COLUMN preferred_activity_codes TEXT")

    # migration: new elder_profile columns for living environment + cultural
    new_profile_cols = [
        ("cultural_codes",        "TEXT"),
        ("living_arrangement",    "TEXT"),
        ("residence_floor",       "INTEGER DEFAULT 0"),
        ("has_elevator",          "INTEGER DEFAULT 1"),
        ("outdoor_accessibility", "TEXT"),
        ("weight_cultural",       "REAL DEFAULT 5"),
        ("religion",              "TEXT"),
        ("religiosity_level",     "TEXT"),
        ("breakfast_time",        "TEXT DEFAULT '08:00'"),
        ("breakfast_duration",    "INTEGER DEFAULT 60"),
        ("lunch_time",            "TEXT DEFAULT '12:00'"),
        ("lunch_duration",        "INTEGER DEFAULT 60"),
        ("dinner_time",           "TEXT DEFAULT '18:00'"),
        ("dinner_duration",       "INTEGER DEFAULT 60"),
    ]
    cur.execute("PRAGMA table_info(elder_profile)")
    cols = {r[1] for r in cur.fetchall()}
    for col_name, col_type in new_profile_cols:
        if col_name not in cols:
            cur.execute(f"ALTER TABLE elder_profile ADD COLUMN {col_name} {col_type}")

    # migration: organizations - extra contact + branding fields
    cur.execute("PRAGMA table_info(organizations)")
    org_cols = {r[1] for r in cur.fetchall()}
    for col, ddl in [
        ("address",        "TEXT"),
        ("city",           "TEXT"),
        ("phone",          "TEXT"),
        ("email",          "TEXT"),
        ("contact_person", "TEXT"),
        ("manager_name",   "TEXT"),
        ("description",    "TEXT"),
        ("website",        "TEXT"),
        ("logo_emoji",     "TEXT"),
        ("institution_rules", "TEXT"),   # free-text rules, one per line
    ]:
        if col not in org_cols:
            cur.execute(f"ALTER TABLE organizations ADD COLUMN {col} {ddl}")

    # migration: external_programs - add any missing new columns
    cur.execute("PRAGMA table_info(external_programs)")
    ep_cols = {r[1] for r in cur.fetchall()}
    new_ep_cols = [
        ("organization_id",      "INTEGER"),
        ("recurring_days",       "TEXT"),
        ("start_time",           "TEXT"),
        ("duration_min",         "INTEGER"),
        ("strengthens",          "TEXT"),
        ("min_capability_level", "INTEGER DEFAULT 1"),
        ("source_kind",          "TEXT"),
    ]
    for col_name, col_type in new_ep_cols:
        if col_name not in ep_cols:
            cur.execute(f"ALTER TABLE external_programs ADD COLUMN {col_name} {col_type}")

    # migration: plan_items — instructor review of the resident per activity
    cur.execute("PRAGMA table_info(plan_items)")
    pi_cols = {r[1] for r in cur.fetchall()}
    for col_name, col_type in [
        ("instructor_rating", "INTEGER"),   # 1..5 (5 = excellent fit/engagement)
        ("instructor_review", "TEXT"),
    ]:
        if col_name not in pi_cols:
            cur.execute(f"ALTER TABLE plan_items ADD COLUMN {col_name} {col_type}")

    conn.commit()

    # mirror knowledge banks
    refresh_knowledge_banks(conn)

    # default org if empty
    if cur.execute("SELECT COUNT(*) FROM organizations").fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO organizations (name, kind, country, language) VALUES (?, ?, ?, ?)",
            ("Demo Care Center", "nursing_home", "IL", "he"),
        )
        conn.commit()
    conn.close()


def refresh_knowledge_banks(conn: sqlite3.Connection | None = None) -> dict:
    """Re-load the kb_* tables from Excel. Returns counts per table."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    counts = {}
    mapping = {
        "kb_diseases": "diseases.xlsx",
        "kb_medications": "medications.xlsx",
        "kb_conditions": "conditions.xlsx",
        "kb_activities": "activities.xlsx",
        "kb_exercises": "exercises.xlsx",
    }
    for table, filename in mapping.items():
        path = KNOWLEDGE_DIR / filename
        if not path.exists():
            counts[table] = 0
            continue
        df = pd.read_excel(path)
        df = df.fillna("")
        conn.execute(f"DELETE FROM {table}")
        df.to_sql(table, conn, if_exists="append", index=False)
        counts[table] = len(df)
    conn.commit()
    if own_conn:
        conn.close()
    return counts


if __name__ == "__main__":
    init_database()
    print(f"Database initialized at {DB_PATH}")
