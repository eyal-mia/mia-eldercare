"""
ElderCare - Daily activity plan optimizer.

Multi-dimensional planner that assigns activities to time slots, maximizing
the match between the elder's needs (weighted per-dimension) and activities'
benefits, while respecting hard and soft constraints.

Pure-Python greedy by default (always works, no external solver). PuLP/CBC
is used opportunistically only if available; on any failure we fall back to
greedy so plan generation NEVER silently fails.

Runs OFFLINE. Reads the SQLite DB written by data/schema.py and the elder's
profile; writes back daily_plans + plan_items. Can be invoked from the UI
or via CLI:

    python -m models.optimizer --elder-id 1 --date 2026-06-08
    python -m models.optimizer --elder-id 1 --week 2026-06-07   # weekly
"""

from __future__ import annotations
from pathlib import Path
import sys
import argparse
import datetime as dt
from dataclasses import dataclass, field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.schema import get_connection  # noqa: E402
from models.holidays import holiday_for_date, is_relevant_for_elder  # noqa: E402


# ---- RELIGION + OBSERVANCE → tags --------------------------------------------
# Each (religion, level) pair produces a set of limitation tags (things the
# elder must NOT be exposed to) and need tags (things activities should
# strengthen / honor). These are merged into the elder's main tag set so the
# normal scoring + eligibility logic handles them transparently.
RELIGION_TAGS: dict[tuple[str, str], dict[str, list[str]]] = {
    # ===== Jewish =====
    ("jewish", "very_observant"): {
        "limitations": [
            "shabbat_violation", "mixed_gender_sensitive", "non_kosher_meals",
            "trigger_topics_christmas", "music_on_shabbat",
        ],
        "needs": [
            "religious_appropriate", "prayer_times_respected", "kosher_food",
            "synagogue_attendance", "torah_study", "reminiscence",
        ],
    },
    ("jewish", "observant"): {
        "limitations": ["shabbat_sensitive", "non_kosher_meals"],
        "needs": [
            "religious_appropriate", "prayer_times_respected",
            "kosher_food", "synagogue_attendance", "reminiscence",
        ],
    },
    ("jewish", "secular"): {
        "limitations": [],
        "needs": ["jewish_culture", "hebrew_content", "reminiscence"],
    },

    # ===== Muslim =====
    ("muslim", "very_observant"): {
        "limitations": [
            "ramadan_fasting_period", "non_halal_meals",
            "mixed_gender_strict", "alcohol_present",
            "loud_music_islamic", "mixed_gender_sensitive",
        ],
        "needs": [
            "prayer_5x_daily", "halal_food", "mosque_attendance",
            "islamic_appropriate", "ramadan_appropriate",
            "arabic_content", "quran_listening",
        ],
    },
    ("muslim", "observant"): {
        "limitations": ["non_halal_meals", "mixed_gender_sensitive"],
        "needs": [
            "halal_food", "islamic_appropriate", "mosque_attendance",
            "arabic_content", "prayer_5x_daily",
        ],
    },
    ("muslim", "secular"): {
        "limitations": [],
        "needs": ["arabic_content", "muslim_culture"],
    },

    # ===== Christian =====
    ("christian", "very_observant"): {
        "limitations": ["sunday_violation"],
        "needs": [
            "christian_appropriate", "sunday_service", "bible_study",
            "church_attendance", "rosary_prayer", "hymn_singing",
        ],
    },
    ("christian", "observant"): {
        "limitations": [],
        "needs": [
            "christian_appropriate", "sunday_service",
            "church_attendance", "bible_study",
        ],
    },
    ("christian", "secular"): {
        "limitations": [],
        "needs": ["christian_culture"],
    },

    # ===== Hindu =====
    ("hindu", "very_observant"): {
        "limitations": [
            "non_vegetarian", "non_sattvic_food", "beef_present",
            "leather_present", "non_pure_environment",
        ],
        "needs": [
            "vegetarian_food", "sattvic_diet", "puja_routine",
            "temple_attendance", "hindu_appropriate", "yoga",
            "meditation_mantra", "indian_culture",
        ],
    },
    ("hindu", "observant"): {
        "limitations": ["beef_present", "non_vegetarian"],
        "needs": [
            "vegetarian_food", "hindu_appropriate", "yoga",
            "indian_culture", "temple_attendance",
        ],
    },
    ("hindu", "secular"): {
        "limitations": [],
        "needs": ["indian_culture", "yoga"],
    },
}


def religion_tags(religion: str, level: str) -> dict[str, list[str]]:
    """Return {limitations: [...], needs: [...]} for the (religion, level) pair.
    Returns empty lists if either is missing or unknown."""
    if not religion or not level or religion == "none":
        return {"limitations": [], "needs": []}
    return RELIGION_TAGS.get((religion, level), {"limitations": [], "needs": []})


# ---- INSTITUTION RULES PARSING ----------------------------------------------
# Each rule is one free-text line written by the institution. The optimizer
# applies whatever it can parse and shows every rule (parsed or not) in the
# plan rationale so caregivers always see the context.
import re as _re_rules  # noqa: E402

_DAY_KEYS_HE = {
    "ראשון": "sun", "שני": "mon", "שלישי": "tue",
    "רביעי": "wed", "חמישי": "thu", "שישי": "fri", "שבת": "sat",
}


def parse_institution_rules(rules_text: str | None) -> dict:
    """Parse one-rule-per-line text into a constraints dict.

    Only TIME-based rules are auto-applied. Day-of-week phrases are too
    error-prone (e.g. "אין פעילות חיצונית ביום שבת" is about external
    activities only, not all activities) — so days are NOT auto-blocked.
    All raw lines are returned for display so caregivers see the context.

    Recognized patterns:
      • "אין / אסור / no" + "אחרי / after / מעבר ל" + HH:MM
            → no_activity_after_minutes
      • "אין / אסור / no" + "לפני / before / עד" + HH:MM
            → no_activity_before_minutes
    """
    out = {
        "no_activity_after_minutes":  None,
        "no_activity_before_minutes": None,
        "raw_lines": [],
    }
    if not rules_text:
        return out
    for line in str(rules_text).splitlines():
        line = line.strip()
        if not line:
            continue
        out["raw_lines"].append(line)

        m = _re_rules.search(r"(\d{1,2}):(\d{2})", line)
        if m is None:
            continue
        time_minutes = int(m.group(1)) * 60 + int(m.group(2))
        forbid = any(k in line for k in ("אין", "אסור", "no ", "not "))
        if not forbid:
            continue
        after = any(k in line for k in ("אחרי", "after", "מעבר ל"))
        before = any(k in line for k in ("לפני", "before", "עד "))
        if after:
            if (out["no_activity_after_minutes"] is None
                    or time_minutes < out["no_activity_after_minutes"]):
                out["no_activity_after_minutes"] = time_minutes
        elif before:
            if (out["no_activity_before_minutes"] is None
                    or time_minutes > out["no_activity_before_minutes"]):
                out["no_activity_before_minutes"] = time_minutes
    return out


def load_institution_rules(conn, elder_id: int) -> dict:
    """Read institution rules and return the parsed constraints dict.

    Source of truth is the Word file (knowledge_banks/rules_bank.docx), read
    fresh on EVERY optimizer run. Any per-org rules still stored in the DB
    are merged in for backward compatibility.
    """
    rule_lines: list[str] = []

    # 1) Word file — primary "rules bank", re-read every call
    try:
        from models.rules_doc import read_rules
        rule_lines.extend(read_rules())
    except Exception:
        pass

    # 2) legacy per-org DB rules (merged, de-duplicated)
    try:
        row = conn.execute("""
            SELECT o.institution_rules
            FROM organizations o
            JOIN elders e ON e.organization_id = o.id
            WHERE e.id = ?
        """, (elder_id,)).fetchone()
        if row is not None:
            db_text = row["institution_rules"]
            if db_text:
                for ln in str(db_text).splitlines():
                    ln = ln.strip()
                    if ln and ln not in rule_lines:
                        rule_lines.append(ln)
    except Exception:
        pass

    return parse_institution_rules("\n".join(rule_lines))


VERSION = "0.4.0-min-hour"

# Every scheduled activity (not meals) gets at least this many minutes in the
# plan. Meals keep their natural per-elder duration.
MIN_ACTIVITY_DURATION = 60


# Each slot has an explicit start AND end window. Activities are placed by a
# running clock and may NOT bleed past the slot's end. The 13:00-16:00 window
# is intentionally left with NO slot → it's a quiet rest period with no
# activities. Physical activity is concentrated in the morning slot only.
DEFAULT_SLOTS = [
    {"name": "morning",   "start": "08:00", "end": "12:00", "allow_physical": True},
    {"name": "noon",      "start": "12:00", "end": "13:00"},   # lunch window
    # --- rest 13:00-16:00 (no slot) ---
    # afternoon also allows physical activity → a second (gentler) movement
    # session in the day, so plans aren't limited to a single morning block.
    {"name": "afternoon", "start": "16:00", "end": "18:00", "allow_physical": True},
    {"name": "evening",   "start": "18:00", "end": "20:00"},
]
# Friday — half day (Shabbat begins at sunset, no afternoon/evening activities)
FRIDAY_SLOTS = [
    {"name": "morning", "start": "08:00", "end": "12:00", "allow_physical": True},
    {"name": "noon",    "start": "12:00", "end": "13:00"},
]
# Saturday — rest day (Shabbat). One quiet morning activity, no sport.
SATURDAY_SLOTS = [
    {"name": "morning", "start": "10:00", "end": "12:00",
     "rest_day": True, "no_sport": True, "allow_physical": True},
]


def get_slots_for_date(plan_date: dt.date | str | None) -> list[dict]:
    if plan_date is None:
        return DEFAULT_SLOTS
    if isinstance(plan_date, str):
        plan_date = dt.date.fromisoformat(plan_date)
    weekday = plan_date.weekday()  # Mon=0 ... Fri=4 Sat=5 Sun=6
    if weekday == 5:
        return SATURDAY_SLOTS
    if weekday == 4:
        return FRIDAY_SLOTS
    return DEFAULT_SLOTS

# Soft contraindication weights — used as a *penalty* instead of a hard block,
# so plans always generate even when the knowledge bank has overlapping tags.
SOFT_BLOCK_PENALTY = 15.0   # subtract this per overlapping safety tag
HARD_SAFETY_TAGS = {
    # tags that, if present in BOTH activity contras AND elder limitations,
    # are serious enough to hard-block. Everything else is soft-penalized.
    "long_no_bathroom_access",
    "trigger_topics",
    "high_pressure_competitive",
    "complex_instructions",   # if dementia is severe and activity needs instructions
}


@dataclass
class Activity:
    code: str
    name_he: str
    name_en: str
    category: str
    subcategory: str
    strengthens: set[str]
    contraindications: set[str]
    min_capability_level: int
    duration_min: int
    group_size_min: int
    group_size_max: int
    location: str
    description_he: str


@dataclass
class ElderContext:
    elder_id: int
    full_name: str
    capability_level: int
    limitations: set[str] = field(default_factory=set)
    needs: set[str] = field(default_factory=set)
    need_weights: dict[str, float] = field(default_factory=dict)
    preferences_categories: set[str] = field(default_factory=set)
    preferences_time_slots: set[str] = field(default_factory=set)
    preferred_activity_codes: set[str] = field(default_factory=set)
    weight_preference: float = 6.0
    # living environment (the new "demographic" dimension)
    living_arrangement: str = ""        # home_alone / home_family / assisted_living / nursing_home / day_center
    residence_floor: int = 0
    has_elevator: bool = True
    outdoor_accessibility: str = "full"  # full / limited / none
    can_go_outdoor: bool = True          # derived
    # meal times (HH:MM) + durations (minutes) — 1-hour meals by default
    breakfast_time: str = "08:00"
    breakfast_duration: int = 60
    lunch_time: str = "12:00"
    lunch_duration: int = 60
    dinner_time: str = "18:00"
    dinner_duration: int = 60
    # care-plan goals → tag: scoring bonus (activities advancing goals score higher)
    goal_bonus: dict[str, float] = field(default_factory=dict)
    # refusals → graduated penalty for activities the elder marked "not wanted"
    refusal_by_code: dict[str, int] = field(default_factory=dict)
    refusal_by_family: dict[str, int] = field(default_factory=dict)
    # instructor ratings → bonus/penalty from the instructor's review (avg 1-5)
    rating_by_code: dict[str, float] = field(default_factory=dict)
    rating_by_family: dict[str, float] = field(default_factory=dict)


# --- LOADERS ----------------------------------------------------------------
def _split_csv(value) -> set[str]:
    if value is None:
        return set()
    try:
        import math
        if isinstance(value, float) and math.isnan(value):
            return set()
    except Exception:
        pass
    if not value:
        return set()
    if isinstance(value, str):
        return {p.strip() for p in value.replace(",", ";").split(";") if p.strip()}
    return set()


def load_activities(conn) -> list[Activity]:
    rows = conn.execute("SELECT * FROM kb_activities").fetchall()
    out = []
    for r in rows:
        out.append(Activity(
            code=r["code"],
            name_he=r["name_he"] or r["code"],
            name_en=r["name_en"] or r["code"],
            category=r["category"] or "general",
            subcategory=r["subcategory"] or "",
            strengthens=_split_csv(r["strengthens"]),
            contraindications=_split_csv(r["contraindications"]),
            min_capability_level=int(r["min_capability_level"] or 1),
            duration_min=int(r["duration_min"] or 30),
            group_size_min=int(r["group_size_min"] or 1),
            group_size_max=int(r["group_size_max"] or 20),
            location=r["location"] or "indoor",
            description_he=r["description_he"] or "",
        ))
    return out


def load_enrolled_programs(conn, elder_id: int, plan_date: dt.date | str) -> list[dict]:
    """External programs the elder enrolled in that run on plan_date's weekday."""
    if isinstance(plan_date, str):
        plan_date = dt.date.fromisoformat(plan_date)
    weekday_keys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    target_day = weekday_keys[plan_date.weekday()]

    try:
        rows = conn.execute("""
            SELECT ep.*
            FROM external_programs ep
            JOIN elder_program_enrollment epe ON epe.program_id = ep.id
            WHERE epe.elder_id = ?
        """, (elder_id,)).fetchall()
    except Exception:
        return []

    matches = []
    for r in rows:
        days = (r["recurring_days"] or "").lower().replace(",", ";").split(";")
        days = [d.strip() for d in days if d.strip()]
        if target_day in days:
            matches.append(dict(r))
    return matches


def load_exercises(conn) -> list[Activity]:
    """Exercises live in their own table but slot into the Activity dataclass
    so the same scoring/eligibility logic applies. They're tagged with
    category='sport' so the optimizer can prefer them for the morning slot."""
    try:
        rows = conn.execute("SELECT * FROM kb_exercises").fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        out.append(Activity(
            code=r["code"],
            name_he=r["name_he"] or r["code"],
            name_en=r["name_en"] or r["code"],
            category="sport",
            subcategory=r["type"] or "",       # strength/aerobic/balance/flexibility/breathing
            strengthens=_split_csv(r["strengthens"]),
            contraindications=_split_csv(r["contraindications"]),
            min_capability_level=int(r["min_capability_level"] or 1),
            duration_min=int(r["duration_min"] or 15),
            group_size_min=1,
            group_size_max=10,
            location="indoor",
            description_he=(r["description_he"] or "") +
                           (f"  ({r['reps_sets']})" if r["reps_sets"] else ""),
        ))
    return out


def load_elder_context(conn, elder_id: int) -> ElderContext:
    elder = conn.execute("SELECT * FROM elders WHERE id = ?", (elder_id,)).fetchone()
    if not elder:
        raise ValueError(f"No elder with id={elder_id}")
    profile = conn.execute(
        "SELECT * FROM elder_profile WHERE elder_id = ?", (elder_id,)
    ).fetchone()
    if not profile:
        raise ValueError(
            f"No profile for elder_id={elder_id}. Fill the profile tab first."
        )

    # column might be the new name (preferred_activity_codes) or — for very
    # old databases pre-migration — the old name (avoid_activity_codes).
    profile_keys = set(profile.keys())
    if "preferred_activity_codes" in profile_keys:
        preferred = _split_csv(profile["preferred_activity_codes"])
    elif "avoid_activity_codes" in profile_keys:
        preferred = _split_csv(profile["avoid_activity_codes"])
    else:
        preferred = set()

    # living environment columns may not exist on very old DBs — guard each.
    def _pget(key, default=None):
        return profile[key] if key in profile_keys else default
    living = _pget("living_arrangement") or ""
    floor = int(_pget("residence_floor", 0) or 0)
    has_elev = bool(int(_pget("has_elevator", 1) or 0))
    outdoor = _pget("outdoor_accessibility") or "full"

    can_outdoor = True
    if outdoor == "none":
        can_outdoor = False
    elif outdoor == "limited":
        can_outdoor = True   # OK but penalize
    if floor > 2 and not has_elev:
        can_outdoor = False  # too hard to leave the apartment

    ctx = ElderContext(
        elder_id=elder_id,
        full_name=elder["full_name"],
        capability_level=int(profile["capability_level"] or 3),
        preferences_categories=_split_csv(profile["preferences_categories"]),
        preferences_time_slots=_split_csv(profile["preferences_time_slots"]),
        preferred_activity_codes=preferred,
        weight_preference=float(profile["weight_preference"] or 6),
        living_arrangement=living,
        residence_floor=floor,
        has_elevator=has_elev,
        outdoor_accessibility=outdoor,
        can_go_outdoor=can_outdoor,
        breakfast_time=str(_pget("breakfast_time") or "08:00"),
        breakfast_duration=int(_pget("breakfast_duration", 60) or 60),
        lunch_time=str(_pget("lunch_time") or "12:00"),
        lunch_duration=int(_pget("lunch_duration", 60) or 60),
        dinner_time=str(_pget("dinner_time") or "18:00"),
        dinner_duration=int(_pget("dinner_duration", 60) or 60),
    )

    # cultural codes column may be missing in old DBs — guard.
    cultural_codes = _pget("cultural_codes") or ""
    weight_cultural = float(_pget("weight_cultural", 5) or 5)
    weight_demographic = float(profile["weight_demographic"] or 5)  # used only for living env tags

    dim_sources = [
        ("medical",    profile["medical_codes"],    "kb_diseases",   float(profile["weight_medical"] or 5)),
        ("medication", profile["medication_codes"], "kb_medications", float(profile["weight_medication"] or 5)),
        ("nursing",    profile["nursing_codes"],    "kb_conditions", float(profile["weight_nursing"] or 5)),
        ("cognitive",  profile["cognitive_codes"],  "kb_conditions", float(profile["weight_cognitive"] or 5)),
        ("mental",     profile["mental_codes"],     "kb_conditions", float(profile["weight_mental"] or 5)),
        ("social",     profile["social_codes"],     "kb_conditions", float(profile["weight_social"] or 5)),
        ("family",     profile["family_codes"],     "kb_conditions", float(profile["weight_family"] or 5)),
        ("cultural",   cultural_codes,              "kb_conditions", weight_cultural),
    ]
    for dim, codes_csv, table, weight in dim_sources:
        for code in _split_csv(codes_csv):
            row = conn.execute(
                f"SELECT * FROM {table} WHERE code = ?", (code,)
            ).fetchone()
            if not row:
                continue
            # column names differ between tables — guard each lookup
            cols = set(row.keys())
            lim_col = "activity_contraindications" if table == "kb_medications" else "limitations"
            if lim_col in cols:
                for lim in _split_csv(row[lim_col]):
                    ctx.limitations.add(lim)
            if "needs_strengthening" in cols:
                for need in _split_csv(row["needs_strengthening"]):
                    ctx.needs.add(need)
                    ctx.need_weights[need] = ctx.need_weights.get(need, 0.0) + weight

    # derive limitation + need tags from LIVING ENVIRONMENT (demographic dim)
    if not ctx.can_go_outdoor:
        ctx.limitations.add("no_outdoor")
    if living == "home_alone":
        ctx.needs.add("home_based_options")
        ctx.need_weights["home_based_options"] = (
            ctx.need_weights.get("home_based_options", 0.0) + weight_demographic
        )
        ctx.needs.add("social")  # combats isolation
        ctx.need_weights["social"] = (
            ctx.need_weights.get("social", 0.0) + weight_demographic
        )
    if living in {"assisted_living", "nursing_home"}:
        ctx.needs.add("structured_routine")
        ctx.need_weights["structured_routine"] = (
            ctx.need_weights.get("structured_routine", 0.0) + weight_demographic
        )

    # derive tags from RELIGION + observance level
    religion = (_pget("religion") or "").lower()
    religiosity = (_pget("religiosity_level") or "").lower()
    rtags = religion_tags(religion, religiosity)
    for lim in rtags["limitations"]:
        ctx.limitations.add(lim)
    for need in rtags["needs"]:
        ctx.needs.add(need)
        ctx.need_weights[need] = (
            ctx.need_weights.get(need, 0.0) + weight_cultural
        )

    # MEASUREMENT-DRIVEN NEEDS — translate the resident's latest assessment
    # scores (Barthel, Fried frailty, PHQ-2, AD8, MMSE, TUG, STS5, gait, grip,
    # mood, pain) into weighted need tags. Runs BEFORE goals so both the care
    # goals and the plan reflect the test results.
    try:
        for tag, w in _fetch_measurement_needs(conn, elder_id).items():
            ctx.needs.add(tag)
            ctx.need_weights[tag] = ctx.need_weights.get(tag, 0.0) + w
    except Exception:
        pass

    # CARE-PLAN GOALS — auto-generate 5 if none exist, then apply their bonus
    # so the plan actively works toward the goals. Manual edits are preserved.
    try:
        from models.goals import ensure_goals, goal_bonus_map
        goals = ensure_goals(conn, elder_id, ctx.needs, ctx.need_weights)
        ctx.goal_bonus = goal_bonus_map(goals)
    except Exception:
        ctx.goal_bonus = {}

    # REFUSALS — activities the elder marked "not wanted" get a graduated
    # penalty (weighted into the optimizer, not a binary block).
    try:
        ctx.refusal_by_code, ctx.refusal_by_family = _fetch_refusals(conn, elder_id, 30)
    except Exception:
        ctx.refusal_by_code, ctx.refusal_by_family = {}, {}

    # INSTRUCTOR RATINGS — the instructor's review of how the resident engaged
    # with each activity feeds the next plan (positive → boost, negative → cut).
    try:
        ctx.rating_by_code, ctx.rating_by_family = _fetch_ratings(conn, elder_id, 30)
    except Exception:
        ctx.rating_by_code, ctx.rating_by_family = {}, {}
    return ctx


RATING_FACTOR = 4.0     # per (avg_rating - 3) point → activities the instructor
                        # rated highly score higher; low ratings score lower

MEASUREMENT_WEIGHT = 6.0  # base weight for need tags derived from test scores


def _fetch_measurement_needs(conn, elder_id: int) -> dict[str, float]:
    """Read the LATEST score per assessment test and translate abnormal results
    into weighted need tags. Returns {tag: weight}."""
    rows = conn.execute("""
        SELECT test_code, score
        FROM measurements m
        WHERE elder_id = ? AND measurement_date = (
            SELECT MAX(measurement_date) FROM measurements m2
            WHERE m2.elder_id = m.elder_id AND m2.test_code = m.test_code)
    """, (elder_id,)).fetchall()
    latest = {}
    for r in rows:
        try:
            latest[r["test_code"]] = float(r["score"])
        except (TypeError, ValueError):
            continue

    needs: dict[str, float] = {}
    W = MEASUREMENT_WEIGHT

    def add(tags, w=W):
        for tg in tags:
            needs[tg] = needs.get(tg, 0.0) + w

    b = latest.get("BARTHEL")
    if b is not None:
        if b < 60:
            add(["physiotherapy", "daily_movement", "quadriceps_strength",
                 "range_of_motion", "weight_bearing_low"], W * 1.5)
        elif b < 85:
            add(["daily_movement", "quadriceps_strength", "range_of_motion"])

    f = latest.get("FRAILTY")
    if f is not None:
        if f >= 3:
            add(["balance", "quadriceps_strength", "weight_bearing_low",
                 "aerobic_low", "balanced_diet"], W * 1.5)
        elif f >= 1:
            add(["balance", "aerobic_low", "weight_bearing_low"])

    if (latest.get("PHQ2") or 0) >= 3:
        add(["social", "light_exposure", "behavioral_activation",
             "creative", "mindfulness", "hope_focus"])
    if (latest.get("AD8") or 0) >= 2:
        add(["memory_games", "moderate_cognitive", "reminiscence", "sensory_stim"])
    if latest.get("MMSE") is not None and latest["MMSE"] < 24:
        add(["memory_games", "moderate_cognitive", "reminiscence"])
    if (latest.get("TUG") or 0) >= 12:
        add(["balance", "gait_training", "weight_bearing_low"])
    if (latest.get("STS5") or 0) >= 15:
        add(["quadriceps_strength", "weight_bearing_low"])
    if latest.get("GAIT4M") is not None and latest["GAIT4M"] < 0.8:
        add(["gait_training", "balance", "aerobic_low"])
    if latest.get("GRIP") is not None and latest["GRIP"] < 20:
        add(["upper_body_low", "quadriceps_strength"])
    if latest.get("MOOD") is not None and latest["MOOD"] <= 4:
        add(["social", "light_exposure", "creative", "music_therapy"])
    if (latest.get("PAIN") or 0) >= 6:
        add(["relaxation", "mindfulness", "range_of_motion"])

    return needs


def _fetch_ratings(conn, elder_id: int, days_back: int = 30):
    """Average instructor rating (1-5) per activity code and base family over
    the look-back window. Returns (by_code, by_family) of avg ratings."""
    cutoff = (dt.date.today() - dt.timedelta(days=days_back)).isoformat()
    rows = conn.execute("""
        SELECT pi.activity_code AS code, pi.instructor_rating AS rating,
               COALESCE(ka.name_he, ke.name_he, ep.name, pi.activity_code) AS nm
        FROM plan_items pi
        JOIN daily_plans dp ON dp.id = pi.plan_id
        LEFT JOIN kb_activities ka ON ka.code = pi.activity_code
        LEFT JOIN kb_exercises  ke ON ke.code = pi.activity_code
        LEFT JOIN external_programs ep ON ('EXT_' || ep.id) = pi.activity_code
        WHERE dp.elder_id = ? AND dp.plan_date >= ?
          AND pi.instructor_rating IS NOT NULL
    """, (elder_id, cutoff)).fetchall()
    code_sum: dict[str, list] = {}
    fam_sum: dict[str, list] = {}
    for r in rows:
        try:
            rating = float(r["rating"])
        except (TypeError, ValueError):
            continue
        code_sum.setdefault(r["code"], []).append(rating)
        fam = (r["nm"] or "").split(" - ")[0].strip()
        if fam:
            fam_sum.setdefault(fam, []).append(rating)
    by_code = {c: sum(v) / len(v) for c, v in code_sum.items() if v}
    by_family = {f: sum(v) / len(v) for f, v in fam_sum.items() if v}
    return by_code, by_family


REFUSAL_PENALTY = 8.0   # score deducted per past refusal (code + family)


def _fetch_refusals(conn, elder_id: int, days_back: int = 30):
    """Count how many times each activity (and its base family) was refused
    over the look-back window. Returns (by_code, by_family)."""
    cutoff = (dt.date.today() - dt.timedelta(days=days_back)).isoformat()
    rows = conn.execute("""
        SELECT pi.activity_code AS code,
               COALESCE(ka.name_he, ke.name_he, ep.name, pi.activity_code) AS nm
        FROM plan_items pi
        JOIN daily_plans dp ON dp.id = pi.plan_id
        LEFT JOIN kb_activities ka ON ka.code = pi.activity_code
        LEFT JOIN kb_exercises  ke ON ke.code = pi.activity_code
        LEFT JOIN external_programs ep ON ('EXT_' || ep.id) = pi.activity_code
        WHERE dp.elder_id = ? AND dp.plan_date >= ?
          AND pi.executed = 0 AND pi.skipped_reason = 'refused'
    """, (elder_id, cutoff)).fetchall()
    by_code: dict[str, int] = {}
    by_family: dict[str, int] = {}
    for r in rows:
        by_code[r["code"]] = by_code.get(r["code"], 0) + 1
        fam = (r["nm"] or "").split(" - ")[0].strip()
        if fam:
            by_family[fam] = by_family.get(fam, 0) + 1
    return by_code, by_family


# --- SCORING + ELIGIBILITY --------------------------------------------------
def _score_activity(act: Activity, ctx: ElderContext) -> tuple[float, list[str]]:
    """Return (raw score, list of human-readable rationale tags)."""
    matched = []
    score = 0.0
    for need in act.strengthens:
        if need in ctx.needs:
            w = ctx.need_weights.get(need, 0.0)
            score += w
            matched.append((need, w))
    rationale_parts = [f"{n}({w:.0f})" for n, w in
                       sorted(matched, key=lambda kv: -kv[1])[:3]]

    # care-plan goal bonus — activities that advance an active goal score higher
    goal_score = sum(ctx.goal_bonus.get(n, 0.0) for n in act.strengthens)
    if goal_score > 0:
        score += goal_score
        rationale_parts.insert(0, "🎯 יעד")

    # refusal penalty — down-weight activities the elder previously refused
    refusals = (ctx.refusal_by_code.get(act.code, 0)
                + ctx.refusal_by_family.get(_family_key(act), 0))
    if refusals > 0:
        score -= refusals * REFUSAL_PENALTY
        rationale_parts.append(f"סירוב×{refusals}")

    # instructor rating — the instructor's review shifts the score up or down.
    # Prefer the specific-code average; fall back to the family average.
    fam = _family_key(act)
    avg_rating = ctx.rating_by_code.get(act.code)
    if avg_rating is None:
        avg_rating = ctx.rating_by_family.get(fam)
    if avg_rating is not None:
        adj = (avg_rating - 3.0) * RATING_FACTOR
        score += adj
        if adj >= 0:
            rationale_parts.append(f"⭐מדריך {avg_rating:.1f}")
        else:
            rationale_parts.append(f"⭐מדריך {avg_rating:.1f}↓")

    if act.category in ctx.preferences_categories:
        score += ctx.weight_preference
        rationale_parts.append("העדפה")

    # explicit preferred activity bonus — strong signal from elder/family that
    # this specific activity should be chosen. Scales with weight_preference.
    if act.code in ctx.preferred_activity_codes:
        bonus = ctx.weight_preference * 3.0
        score += bonus
        rationale_parts.insert(0, "★ בחירת הדייר/ת")

    # soft contraindication penalty
    overlap = act.contraindications & ctx.limitations
    safe_overlap = overlap - HARD_SAFETY_TAGS
    if safe_overlap:
        # mild deduction; smaller than benefit so activity still picks if needed
        score -= SOFT_BLOCK_PENALTY * len(safe_overlap)
        rationale_parts.append(f"זהירות({','.join(sorted(safe_overlap))})")

    return score, rationale_parts


def _is_eligible(act: Activity, ctx: ElderContext) -> tuple[bool, str]:
    """Hard eligibility. Returns (eligible, reason_if_not).

    Hard filters:
    - capability level
    - safety contraindications
    - outdoor activities when the elder can't go outside (high floor + no
      elevator, or 'outdoor_accessibility=none')
    """
    if act.min_capability_level > ctx.capability_level:
        return False, f"min_capability={act.min_capability_level}>elder={ctx.capability_level}"
    hard_block = act.contraindications & ctx.limitations & HARD_SAFETY_TAGS
    if hard_block:
        return False, f"hard_safety:{','.join(sorted(hard_block))}"
    if act.location == "outdoor" and not ctx.can_go_outdoor:
        return False, "outdoor_inaccessible"
    return True, ""


def _slot_for_time(hhmm: str, slots: list[dict]) -> str | None:
    """Map an HH:MM string to one of the slots based on its start_time order."""
    if not hhmm:
        return slots[0]["name"] if slots else None
    try:
        h = int(hhmm.split(":")[0])
    except Exception:
        return slots[0]["name"] if slots else None
    if h < 12:
        target = "morning"
    elif h < 15:
        target = "noon"
    elif h < 18:
        target = "afternoon"
    else:
        target = "evening"
    by_name = {s["name"]: s for s in slots}
    if target in by_name:
        return target
    return slots[0]["name"] if slots else None


def _family_key(act: Activity) -> str:
    """A stable 'family' identifier so two variants of the same base activity
    ('הליכה - בוקר' and 'הליכה - ערב') count as the same thing and aren't both
    scheduled on one day. The base is the name before the first ' - '."""
    base = (act.name_he or act.code).split(" - ")[0].strip()
    return base or act.code


def _name_time_hint(name: str) -> str | None:
    """If the activity NAME states a time of day (e.g. 'הליכה - בוקר',
    'ערב שירה', 'Morning walk'), return the matching slot name so we don't
    place a 'morning' activity in the evening. Returns None when no hint.
    Order matters: check 'afternoon' before 'noon' because the Hebrew word
    for afternoon contains the word for noon."""
    if not name:
        return None
    n = name.lower()
    if "אחר הצהריים" in name or "אחה" in name or "afternoon" in n:
        return "afternoon"
    if "ערב" in name or "evening" in n:
        return "evening"
    if "בוקר" in name or "morning" in n:
        return "morning"
    if "צהריים" in name or "צהר" in name or "noon" in n:
        return "noon"
    return None


# --- GREEDY SOLVER ----------------------------------------------------------
def solve_greedy(
    ctx: ElderContext,
    activities: list[Activity],
    slots: list[dict],
    history_executed: set[str],
    history_skipped: set[str],
    exercises: list[Activity] | None = None,
    plan_date: dt.date | str | None = None,
    enrolled_programs: list[dict] | None = None,
    elder_demographic_codes: set[str] | None = None,
    institution_rules: dict | None = None,
) -> tuple[list[dict], float]:
    """Greedy with several guarantees:
      STEP 0: Holiday (if today is one) → inserted into its prescribed slot.
      STEP 0.5: Enrolled external programs (city / assisted living) for today's
                weekday → inserted into their fixed time slot.
      STEP 1: Morning sport (unless slots flag no_sport, e.g. Saturday).
      STEP 2: Greedy fill of remaining time with regular activities.
    """
    exercises = exercises or []
    enrolled_programs = enrolled_programs or []
    elder_demographic_codes = elder_demographic_codes or set()
    rules = institution_rules or {
        "no_activity_after_minutes": None,
        "no_activity_before_minutes": None,
        "raw_lines": [],
    }

    chosen: list[dict] = []
    used_codes: set[str] = set()
    used_families: set[str] = set()   # base activity names already used today
    used_categories_per_slot: dict[str, set[str]] = {s["name"]: set() for s in slots}
    total_score = 0.0
    slot_by_name = {s["name"]: s for s in slots}

    def _hhmm_to_min(hhmm: str, fallback: int = 0) -> int:
        try:
            h, m = map(int, str(hhmm).split(":"))
            return h * 60 + m
        except Exception:
            return fallback

    # explicit end-of-window per slot, so nothing bleeds past it
    slot_end = {s["name"]: _hhmm_to_min(s.get("end", "20:00"), 20 * 60)
                for s in slots}

    def _available(slot_name: str) -> int:
        """Minutes left in the slot from the current clock to the slot's end."""
        ch = _hhmm_to_min(slot_clock[slot_name])
        return max(0, slot_end[slot_name] - ch)

    def _violates_time_rule(start_hhmm: str, duration_min: int) -> bool:
        """Check institution time rules. True if this activity falls in a
        forbidden time window."""
        try:
            h, m = map(int, start_hhmm.split(":"))
            start_min = h * 60 + m
            end_min = start_min + duration_min
        except Exception:
            return False
        after = rules.get("no_activity_after_minutes")
        if after is not None and end_min > after:
            return True
        before = rules.get("no_activity_before_minutes")
        if before is not None and start_min < before:
            return True
        return False

    # Running clock per slot so activities never overlap in time. Each slot
    # starts at its configured start_time; we advance the clock by an
    # activity's duration_min once it's placed.
    slot_clock = {s["name"]: s["start"] for s in slots}

    def _advance_clock(slot_name: str, duration_min: int) -> str:
        """Return current clock value for `slot_name` and advance it by
        `duration_min` minutes. So consecutive activities in the same slot
        get back-to-back times instead of sharing one start_time."""
        t = slot_clock[slot_name]
        try:
            h, m = map(int, t.split(":"))
        except Exception:
            h, m = 9, 0
        start = f"{h:02d}:{m:02d}"
        total = h * 60 + m + max(0, int(duration_min))
        slot_clock[slot_name] = f"{(total // 60) % 24:02d}:{total % 60:02d}"
        return start

    def _peek_clock(slot_name: str) -> str:
        """Look at the current clock without advancing."""
        return slot_clock[slot_name]

    def _set_clock_to_at_least(slot_name: str, hhmm: str) -> str:
        """Bump the clock forward to hhmm if it's earlier; return the actual
        start time used (either hhmm or current clock if it's already later)."""
        try:
            h, m = map(int, hhmm.split(":"))
            new_minutes = h * 60 + m
            ch, cm = map(int, slot_clock[slot_name].split(":"))
            cur_minutes = ch * 60 + cm
            if new_minutes > cur_minutes:
                slot_clock[slot_name] = f"{h:02d}:{m:02d}"
                return f"{h:02d}:{m:02d}"
            return slot_clock[slot_name]
        except Exception:
            return slot_clock[slot_name]

    # ---- STEP -1: meals (fixed blocks, must appear in the plan) ---------
    meals = [
        ("MEAL_BREAKFAST", "🌅 ארוחת בוקר", ctx.breakfast_time,
         max(10, int(ctx.breakfast_duration))),
        ("MEAL_LUNCH",     "☀️ ארוחת צהריים", ctx.lunch_time,
         max(10, int(ctx.lunch_duration))),
        ("MEAL_DINNER",    "🌙 ארוחת ערב", ctx.dinner_time,
         max(10, int(ctx.dinner_duration))),
    ]
    def _bucket(mmin: int) -> str:
        if mmin < 12 * 60:
            return "morning"
        if mmin < 15 * 60:
            return "noon"
        if mmin < 18 * 60:
            return "afternoon"
        return "evening"

    for code, label, mtime, mdur in meals:
        mmin = _hhmm_to_min(mtime)
        # find the activity slot whose window actually CONTAINS the meal time
        host = None
        for s in slots:
            if _hhmm_to_min(s["start"]) <= mmin < slot_end[s["name"]]:
                host = s["name"]
                break
        if host is not None:
            # meal falls inside an activity window → bump clock + consume time
            start_t = _set_clock_to_at_least(host, mtime)
            avail = _available(host)
            actual_dur = min(mdur, avail) if avail > 0 else mdur
            if avail > 0:
                _advance_clock(host, actual_dur)
            used_categories_per_slot[host].add("meal")
            tag_slot = host
        else:
            # meal time is outside every activity window (e.g. Saturday lunch)
            # → still show it at its own time, but don't touch any slot clock
            start_t = mtime
            actual_dur = mdur
            tag_slot = _bucket(mmin)
        chosen.append({
            "time_slot": tag_slot,
            "start_time": start_t,
            "activity_code": code,
            "duration_min": actual_dur,
            "rationale": label,
        })
        used_codes.add(code)

    # ---- STEP 0: holiday -------------------------------------------------
    if plan_date is not None:
        hol = holiday_for_date(plan_date)
        if hol and is_relevant_for_elder(hol, elder_demographic_codes):
            slot_name = hol.get("time_slot", "morning")
            slot = slot_by_name.get(slot_name)
            if slot is None and slots:
                slot = slots[0]
                slot_name = slot["name"]
            dur = max(MIN_ACTIVITY_DURATION, int(hol.get("duration_min", 45)))
            if slot is not None and _available(slot_name) >= dur:
                start_t = _advance_clock(slot_name, dur)
                chosen.append({
                    "time_slot": slot_name,
                    "start_time": start_t,
                    "activity_code": hol["code"],
                    "duration_min": dur,
                    "rationale": "🎉 חג: " + hol.get("name_he", ""),
                })
                used_codes.add(hol["code"])
                used_categories_per_slot[slot_name].add("holiday")
                total_score += 20

    # ---- STEP 0.5: enrolled external programs ----------------------------
    # External programs prefer their fixed start_time; if that's later than the
    # current clock we honor it (and bump the clock there).
    for prog in enrolled_programs:
        slot_name = _slot_for_time(prog.get("start_time", ""), slots)
        if slot_name is None:
            continue
        slot = slot_by_name[slot_name]
        dur = max(MIN_ACTIVITY_DURATION, int(prog.get("duration_min") or 60))
        code = f"EXT_{prog['id']}"
        if code in used_codes:
            continue
        # honor program's fixed start if later than current clock; skip if it
        # wouldn't fit before the slot ends
        prog_time = prog.get("start_time") or slot["start"]
        start_min = max(_hhmm_to_min(slot_clock[slot_name]),
                        _hhmm_to_min(prog_time))
        if start_min + dur > slot_end[slot_name]:
            continue
        slot_clock[slot_name] = f"{start_min // 60:02d}:{start_min % 60:02d}"
        start_t = _advance_clock(slot_name, dur)
        chosen.append({
            "time_slot": slot_name,
            "start_time": start_t,
            "activity_code": code,
            "duration_min": dur,
            "rationale": f"🏛️ {prog.get('source_kind') or 'תוכנית חיצונית'}: {prog['name']}",
        })
        used_codes.add(code)
        used_categories_per_slot[slot_name].add("external")
        total_score += 15

    # ---- STEP 1: reserve morning sport ------------------------------------
    morning_slot = slot_by_name.get("morning")
    if morning_slot and exercises and not morning_slot.get("no_sport"):
        ex_scored = []
        for ex in exercises:
            ok, _ = _is_eligible(ex, ctx)
            if not ok:
                continue
            if ex.code in history_skipped:
                continue
            sc, rationale = _score_activity(ex, ctx)
            if ex.code in history_executed:
                sc -= 1.5
            ex_scored.append((sc, ex, rationale))
        ex_scored.sort(key=lambda kv: -kv[0])

        # place up to two different exercises in the morning (a warm-up + a
        # main session) instead of a single one, for more movement per day
        MAX_MORNING_SPORT = 2
        placed_sport = 0
        for sc, ex, rationale in ex_scored:
            if placed_sport >= MAX_MORNING_SPORT:
                break
            fam = _family_key(ex)
            if fam in used_families:
                continue
            sched_dur = max(MIN_ACTIVITY_DURATION, ex.duration_min)
            if sched_dur > _available("morning"):
                continue
            start_t = _advance_clock("morning", sched_dur)
            chosen.append({
                "time_slot": "morning",
                "start_time": start_t,
                "activity_code": ex.code,
                "duration_min": sched_dur,
                "rationale": "🏃 ספורט בוקר: " + ("; ".join(rationale) or "התאמת בסיס"),
            })
            used_codes.add(ex.code)
            used_families.add(fam)
            used_categories_per_slot["morning"].add("sport")
            total_score += sc
            placed_sport += 1

    # ---- STEP 2: regular activities ---------------------------------------
    eligible_scored = []
    for act in activities:
        ok, _ = _is_eligible(act, ctx)
        if not ok:
            continue
        if act.code in history_skipped:
            continue
        score, rationale = _score_activity(act, ctx)
        if act.code in history_executed:
            score -= 1.5  # mild diversity penalty
        eligible_scored.append((score, act, rationale))

    eligible_scored.sort(key=lambda kv: (-kv[0], kv[1].duration_min))

    # which slot names actually exist today (for time-hint resolution)
    existing_slot_names = {s["name"] for s in slots}

    for score, act, rationale in eligible_scored:
        if act.code in used_codes:
            continue
        # don't schedule the same base activity twice in one day
        fam = _family_key(act)
        if fam in used_families:
            continue

        sched_dur = max(MIN_ACTIVITY_DURATION, act.duration_min)

        # physical activity is concentrated in the MORNING only
        physical_only_morning = act.category == "physical"

        # if the NAME states a time of day, only allow that slot (when it
        # exists today) — prevents 'morning' activities landing in the evening
        name_hint = _name_time_hint(act.name_he)
        if name_hint is not None and name_hint not in existing_slot_names:
            name_hint = None  # that slot is closed today (e.g. Saturday) → ignore

        # pick best slot for this activity
        best_slot = None
        best_eff = float("-inf")
        for slot in slots:
            # physical activity → only slots flagged allow_physical (morning)
            if physical_only_morning and not slot.get("allow_physical"):
                continue
            if name_hint is not None and slot["name"] != name_hint:
                continue
            if _available(slot["name"]) < sched_dur:
                continue
            # don't double-up same category in same slot
            if act.category in used_categories_per_slot[slot["name"]]:
                continue
            # respect institution time rules — peek at where the activity
            # would land in this slot without advancing the clock
            if _violates_time_rule(_peek_clock(slot["name"]), sched_dur):
                continue
            eff = score
            if slot["name"] in ctx.preferences_time_slots:
                eff += 0.5
            # prefer physical/outing in morning, mental/cognitive midday, social late
            cat_slot_bonus = {
                ("physical", "morning"): 1.0,
                ("physical", "afternoon"): 0.5,
                ("cognitive", "noon"): 0.7,
                ("cognitive", "afternoon"): 0.5,
                ("social", "afternoon"): 0.7,
                ("social", "evening"): 0.5,
                ("mental", "morning"): 0.5,
                ("mental", "evening"): 0.5,
            }.get((act.category, slot["name"]), 0.0)
            eff += cat_slot_bonus
            if eff > best_eff:
                best_eff = eff
                best_slot = slot

        if best_slot is None:
            continue
        start_t = _advance_clock(best_slot["name"], sched_dur)
        chosen.append({
            "time_slot": best_slot["name"],
            "start_time": start_t,
            "activity_code": act.code,
            "duration_min": sched_dur,
            "rationale": "; ".join(rationale) or "התאמת בסיס",
        })
        used_codes.add(act.code)
        used_families.add(fam)
        used_categories_per_slot[best_slot["name"]].add(act.category)
        total_score += score

    # sort by slot order then time
    slot_order = {s["name"]: i for i, s in enumerate(slots)}
    chosen.sort(key=lambda it: (slot_order.get(it["time_slot"], 99), it["start_time"]))
    return chosen, total_score


# --- OPTIONAL: PuLP --------------------------------------------------------
def solve_pulp(
    ctx: ElderContext,
    activities: list[Activity],
    slots: list[dict],
    history_executed: set[str],
    history_skipped: set[str],
) -> tuple[list[dict], float]:
    import pulp  # noqa: WPS433

    eligible = []
    activity_scores: dict[str, float] = {}
    activity_rationale: dict[str, list[str]] = {}
    for act in activities:
        ok, _ = _is_eligible(act, ctx)
        if not ok or act.code in history_skipped:
            continue
        s, r = _score_activity(act, ctx)
        if act.code in history_executed:
            s -= 1.5
        activity_scores[act.code] = s
        activity_rationale[act.code] = r
        eligible.append(act)

    if not eligible:
        return [], 0.0

    prob = pulp.LpProblem("eldercare", pulp.LpMaximize)
    x = {(act.code, s["name"]): pulp.LpVariable(f"x_{act.code}_{s['name']}", cat="Binary")
         for act in eligible for s in slots}

    for act in eligible:
        prob += pulp.lpSum(x[(act.code, s["name"])] for s in slots) <= 1
    def _win(s):  # slot window length in minutes
        try:
            sh, sm = map(int, s["start"].split(":"))
            eh, em = map(int, s.get("end", "20:00").split(":"))
            return max(0, (eh * 60 + em) - (sh * 60 + sm))
        except Exception:
            return 180
    for slot in slots:
        prob += pulp.lpSum(x[(act.code, slot["name"])] * act.duration_min
                           for act in eligible) <= _win(slot)

    obj = []
    for act in eligible:
        for slot in slots:
            v = activity_scores[act.code]
            if slot["name"] in ctx.preferences_time_slots:
                v += 0.5
            obj.append(x[(act.code, slot["name"])] * v)
    prob += pulp.lpSum(obj)

    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=10)
    prob.solve(solver)

    items = []
    slot_order = {s["name"]: i for i, s in enumerate(slots)}
    for slot in slots:
        for act in eligible:
            var = x[(act.code, slot["name"])]
            if var.value() and var.value() > 0.5:
                items.append({
                    "time_slot": slot["name"],
                    "start_time": slot["start"],
                    "activity_code": act.code,
                    "duration_min": act.duration_min,
                    "rationale": "; ".join(activity_rationale[act.code]) or "התאמת בסיס",
                })
    items.sort(key=lambda it: (slot_order.get(it["time_slot"], 99), it["start_time"]))
    score = float(pulp.value(prob.objective) or 0.0)
    return items, score


def solve_daily_plan(
    ctx: ElderContext,
    activities: list[Activity],
    slots: list[dict] | None = None,
    history_executed_codes: set[str] | None = None,
    history_skipped_codes: set[str] | None = None,
    prefer_pulp: bool = False,
    exercises: list[Activity] | None = None,
    plan_date: dt.date | str | None = None,
    enrolled_programs: list[dict] | None = None,
    elder_demographic_codes: set[str] | None = None,
    institution_rules: dict | None = None,
) -> tuple[list[dict], float]:
    if slots is None:
        slots = get_slots_for_date(plan_date)
    history_executed_codes = history_executed_codes or set()
    history_skipped_codes = history_skipped_codes or set()

    if prefer_pulp:
        try:
            return solve_pulp(ctx, activities, slots,
                              history_executed_codes, history_skipped_codes)
        except Exception:
            pass  # fall through to greedy
    return solve_greedy(
        ctx, activities, slots,
        history_executed_codes, history_skipped_codes,
        exercises=exercises,
        plan_date=plan_date,
        enrolled_programs=enrolled_programs,
        elder_demographic_codes=elder_demographic_codes,
        institution_rules=institution_rules,
    )


# --- PERSIST ----------------------------------------------------------------
def save_plan(conn, elder_id, plan_date, items, score) -> int:
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM plan_items WHERE plan_id IN "
        "(SELECT id FROM daily_plans WHERE elder_id = ? AND plan_date = ?)",
        (elder_id, plan_date),
    )
    cur.execute(
        "DELETE FROM daily_plans WHERE elder_id = ? AND plan_date = ?",
        (elder_id, plan_date),
    )
    cur.execute(
        "INSERT INTO daily_plans (elder_id, plan_date, optimizer_version, objective_score) "
        "VALUES (?, ?, ?, ?)",
        (elder_id, plan_date, VERSION, score),
    )
    plan_id = cur.lastrowid
    for it in items:
        cur.execute(
            "INSERT INTO plan_items "
            "(plan_id, time_slot, start_time, activity_code, duration_min, rationale) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (plan_id, it["time_slot"], it["start_time"],
             it["activity_code"], it["duration_min"], it["rationale"]),
        )
    conn.commit()
    return plan_id


def fetch_history_codes(conn, elder_id, days_back=3):
    cutoff = (dt.date.today() - dt.timedelta(days=days_back)).isoformat()
    rows = conn.execute("""
        SELECT pi.activity_code, pi.executed, pi.skipped_reason
        FROM plan_items pi
        JOIN daily_plans dp ON dp.id = pi.plan_id
        WHERE dp.elder_id = ? AND dp.plan_date >= ?
    """, (elder_id, cutoff)).fetchall()
    executed = {r["activity_code"] for r in rows if r["executed"]}
    skipped = {r["activity_code"] for r in rows
               if not r["executed"] and r["skipped_reason"] == "refused"}
    return executed, skipped


def generate_plan_for_elder(elder_id, plan_date=None):
    plan_date = plan_date or dt.date.today().isoformat()
    conn = get_connection()
    try:
        ctx = load_elder_context(conn, elder_id)
        activities = load_activities(conn)
        exercises = load_exercises(conn)
        executed, skipped = fetch_history_codes(conn, elder_id)
        # pull elder's demographic codes for holiday relevance filtering
        prof = conn.execute(
            "SELECT demographic_codes FROM elder_profile WHERE elder_id = ?",
            (elder_id,),
        ).fetchone()
        demo_codes = _split_csv(prof["demographic_codes"]) if prof else set()
        enrolled = load_enrolled_programs(conn, elder_id, plan_date)
        rules = load_institution_rules(conn, elder_id)
        items, score = solve_daily_plan(
            ctx, activities,
            history_executed_codes=executed,
            history_skipped_codes=skipped,
            exercises=exercises,
            plan_date=plan_date,
            enrolled_programs=enrolled,
            elder_demographic_codes=demo_codes,
            institution_rules=rules,
        )
        plan_id = save_plan(conn, elder_id, plan_date, items, score)
        return {
            "elder_id": elder_id,
            "elder_name": ctx.full_name,
            "plan_date": plan_date,
            "plan_id": plan_id,
            "items": items,
            "objective_score": score,
            "limitations_count": len(ctx.limitations),
            "needs_count": len(ctx.needs),
        }
    finally:
        conn.close()


# --- WEEKLY -----------------------------------------------------------------
def week_start_sunday(d: dt.date) -> dt.date:
    """Return the Sunday on/before d (Hebrew/Israeli week starts Sunday)."""
    # weekday(): Monday=0 ... Sunday=6
    days_since_sunday = (d.weekday() + 1) % 7
    return d - dt.timedelta(days=days_since_sunday)


def generate_weekly_plan_for_elder(
    elder_id: int,
    start_date: dt.date | str | None = None,
) -> dict:
    """Generate 7 daily plans starting Sunday. Returns summary."""
    if start_date is None:
        start_date = week_start_sunday(dt.date.today())
    elif isinstance(start_date, str):
        start_date = dt.date.fromisoformat(start_date)
        start_date = week_start_sunday(start_date)

    days = []
    for i in range(7):
        d = start_date + dt.timedelta(days=i)
        days.append(generate_plan_for_elder(elder_id, d.isoformat()))

    total_items = sum(len(d["items"]) for d in days)
    return {
        "elder_id": elder_id,
        "start_date": start_date.isoformat(),
        "end_date": (start_date + dt.timedelta(days=6)).isoformat(),
        "days": days,
        "total_items": total_items,
        "elder_name": days[0]["elder_name"] if days else "",
    }


# --- CLI --------------------------------------------------------------------
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="ElderCare planner")
    p.add_argument("--elder-id", type=int, required=True)
    p.add_argument("--date", type=str, default=None, help="YYYY-MM-DD (daily)")
    p.add_argument("--week", type=str, default=None,
                   help="YYYY-MM-DD any date in target week (generates 7 days)")
    args = p.parse_args()

    if args.week:
        wk = generate_weekly_plan_for_elder(args.elder_id, args.week)
        print(f"Week {wk['start_date']}..{wk['end_date']} for "
              f"{wk['elder_name']}: {wk['total_items']} items across 7 days")
        for d in wk["days"]:
            print(f"  {d['plan_date']}: {len(d['items'])} items, "
                  f"score {d['objective_score']:.1f}")
    else:
        r = generate_plan_for_elder(args.elder_id, args.date)
        print(f"Plan for {r['elder_name']} on {r['plan_date']}:")
        print(f"  Score: {r['objective_score']:.2f}  "
              f"Limits: {r['limitations_count']}  Needs: {r['needs_count']}  "
              f"Items: {len(r['items'])}")
        for it in r["items"]:
            print(f"    [{it['start_time']} {it['time_slot']:10}] "
                  f"{it['activity_code']} ({it['duration_min']}m) - {it['rationale']}")
