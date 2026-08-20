"""
ElderCare - Care-plan goals.

The optimizer derives up to 5 care goals for an elder from their strongest
needs (the weighted need-tags computed in load_elder_context). Each goal maps
to a set of "target tags"; activities that advance those tags get a scoring
bonus, so the plan actively works toward the goals. Goals are stored per elder
and can be edited/added/deleted manually in the UI; manual edits are kept and
not overwritten unless the user regenerates.
"""

from __future__ import annotations


# goal_key -> (Hebrew goal text, set of need-tags that advance the goal)
GOAL_CLUSTERS: list[tuple[str, str, set[str]]] = [
    ("balance", "שיפור שיווי משקל ומניעת נפילות",
     {"balance", "gait_training", "weight_bearing_low"}),
    ("fitness", "שיפור כושר גופני, סיבולת ותנועה יומית",
     {"aerobic_low", "daily_movement", "quadriceps_strength",
      "swimming", "water_aerobics", "upper_body_low"}),
    ("mobility", "שיפור גמישות וטווחי תנועה",
     {"flexibility", "range_of_motion"}),
    ("cognitive", "שימור ושיפור תפקוד קוגניטיבי וזיכרון",
     {"memory_games", "moderate_cognitive", "complex_cognitive",
      "reminiscence", "learning_new"}),
    ("social", "הפחתת בדידות וחיזוק קשרים חברתיים",
     {"social", "peer_visits", "group_activity", "peer_support",
      "phone_calls", "outings", "social_engagement"}),
    ("mental", "חיזוק רווחה נפשית ושיפור מצב רוח",
     {"mindfulness", "art_therapy", "hope_focus", "validation",
      "behavioral_activation", "light_exposure", "creative",
      "music_therapy", "relaxation", "self_expression", "meaning_focus"}),
    ("respiratory", "שיפור תפקוד נשימתי והרגעה",
     {"breathing", "pursed_lip"}),
    ("grief", "תמיכה בתהליך אבל והתמודדות עם אובדן",
     {"grief_group", "spiritual_support"}),
    ("spiritual", "מענה לצרכים רוחניים ותרבותיים",
     {"religious_appropriate", "spiritual_support",
      "native_language_group", "arabic_content", "cultural_familiar"}),
    ("family", "חיזוק הקשר המשפחתי והבין-דורי",
     {"family_inclusive", "intergenerational"}),
    ("routine", "ביסוס שגרה יציבה ומובנית ושיפור שינה",
     {"structured_routine", "predictable_routine", "sleep_hygiene"}),
    ("continence", "שיפור שליטה בסוגרים",
     {"pelvic_floor", "timed_voiding"}),
    ("speech", "שיפור דיבור, קול ותקשורת",
     {"speech_therapy", "voice_exercise"}),
    ("sensory", "גירוי חושי ושמירה על ערנות",
     {"sensory_stim", "music_familiar", "gentle_touch", "passive_motion"}),
    ("rehab", "שיקום תפקודי (פיזיותרפיה / ריפוי בעיסוק)",
     {"physiotherapy", "mirror_therapy"}),
]

# Fallback goals used to top up to 5 when the elder has few matched needs.
_DEFAULT_FILLERS = [
    ("שמירה על פעילות גופנית יומית",
     "aerobic_low;daily_movement;flexibility"),
    ("שמירה על מעורבות חברתית",
     "social;group_activity"),
    ("גירוי קוגניטיבי שוטף",
     "moderate_cognitive;memory_games"),
    ("חיזוק רווחה נפשית",
     "mindfulness;creative;music_therapy"),
    ("ביסוס שגרה יומית מובנית",
     "structured_routine"),
]

GOAL_BONUS = 2.0        # per priority point, added to activities that match a goal
NUM_AUTO_GOALS = 5


def generate_goals(needs: set[str], need_weights: dict[str, float]) -> list[dict]:
    """Pure function: derive up to 5 care goals from the elder's weighted needs.
    Returns list of dicts: {goal_text, target_tags(csv), priority(1..5), source}."""
    scored = []
    for key, text, tags in GOAL_CLUSTERS:
        matched = tags & needs
        if not matched:
            continue
        score = sum(need_weights.get(t, 0.0) for t in matched)
        if score <= 0:
            continue
        scored.append((score, text, matched))

    scored.sort(key=lambda kv: -kv[0])
    top = scored[:NUM_AUTO_GOALS]

    goals: list[dict] = []
    # priority 5 for the strongest goal, descending
    prio = 5
    used_texts = set()
    for score, text, matched in top:
        goals.append({
            "goal_text": text,
            "target_tags": ";".join(sorted(matched)),
            "priority": max(1, prio),
            "source": "auto",
        })
        used_texts.add(text)
        prio -= 1

    # top up to 5 with generic fillers if the profile was sparse
    fi = 0
    while len(goals) < NUM_AUTO_GOALS and fi < len(_DEFAULT_FILLERS):
        text, tags = _DEFAULT_FILLERS[fi]
        fi += 1
        if text in used_texts:
            continue
        goals.append({
            "goal_text": text,
            "target_tags": tags,
            "priority": max(1, prio),
            "source": "auto",
        })
        used_texts.add(text)
        prio -= 1

    return goals


# ---- DB helpers -------------------------------------------------------------
def load_goals(conn, elder_id: int, active_only: bool = True) -> list[dict]:
    try:
        q = "SELECT * FROM care_goals WHERE elder_id = ?"
        if active_only:
            q += " AND active = 1"
        q += " ORDER BY priority DESC, id"
        rows = conn.execute(q, (elder_id,)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def save_goals(conn, elder_id: int, goals: list[dict],
               replace: bool = True) -> None:
    cur = conn.cursor()
    if replace:
        cur.execute("DELETE FROM care_goals WHERE elder_id = ?", (elder_id,))
    for g in goals:
        cur.execute(
            "INSERT INTO care_goals "
            "(elder_id, goal_text, target_tags, priority, source, active) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (elder_id, g.get("goal_text", ""), g.get("target_tags", ""),
             int(g.get("priority", 3)), g.get("source", "auto"),
             int(g.get("active", 1))),
        )
    conn.commit()


def ensure_goals(conn, elder_id: int, needs: set[str],
                 need_weights: dict[str, float]) -> list[dict]:
    """Return the elder's goals, auto-generating + saving them if none exist."""
    existing = load_goals(conn, elder_id, active_only=False)
    if existing:
        return existing
    goals = generate_goals(needs, need_weights)
    if goals:
        save_goals(conn, elder_id, goals, replace=True)
    return load_goals(conn, elder_id, active_only=False)


def regenerate_goals(conn, elder_id: int, needs: set[str],
                     need_weights: dict[str, float]) -> list[dict]:
    """Force-regenerate auto goals, replacing existing ones."""
    goals = generate_goals(needs, need_weights)
    save_goals(conn, elder_id, goals, replace=True)
    return load_goals(conn, elder_id, active_only=False)


def goal_bonus_map(goals: list[dict]) -> dict[str, float]:
    """tag -> scoring bonus, from active goals weighted by priority."""
    out: dict[str, float] = {}
    for g in goals:
        if not int(g.get("active", 1)):
            continue
        prio = int(g.get("priority", 3))
        tags = (g.get("target_tags") or "")
        for tag in tags.replace(",", ";").split(";"):
            tag = tag.strip()
            if not tag:
                continue
            out[tag] = max(out.get(tag, 0.0), prio * GOAL_BONUS)
    return out
