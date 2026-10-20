"""
Role-based permissions (demo level).

Every role-holder in `org_staff` has a `role_key`. Role keys are grouped into
four permission profiles. The profile decides which screens appear in the
sidebar and which actions are enabled. This is a UI-level demo of the
hierarchy the institution asked for ("an instructor should not see medical or
social information"); it is NOT authentication.
"""

from __future__ import annotations

import streamlit as st

# role_key -> permission profile
ROLE_TO_PROFILE = {
    "director": "director",
    "activity_manager": "activity_manager",
    "occupational_therapist": "clinical",
    "nurse": "clinical",
    "social_worker": "clinical",
    "instructor": "instructor",
}
DEFAULT_PROFILE = "clinical"   # role-holders added by hand ("custom")

# role_key options offered in the staff form (value, Hebrew label)
ROLE_OPTIONS = [
    ("director", "הנהלת המוסד"),
    ("activity_manager", "ניהול תעסוקה"),
    ("occupational_therapist", "ריפוי בעיסוק"),
    ("nurse", "סיעוד"),
    ("social_worker", "עבודה סוציאלית"),
    ("instructor", "הדרכת תעסוקה"),
]

PROFILES = {
    "director": {
        "label": "הנהלה",
        "desc": "כל המסכים והפעולות, כולל ניהול בעלי תפקידים",
    },
    "activity_manager": {
        "label": "ניהול תעסוקה",
        "desc": "כל המסכים, תכנון לכל המוסד, כללי המוסד ובנקי הידע",
    },
    "clinical": {
        "label": "צוות מקצועי",
        "desc": "תיק הדייר/ת המלא, יעדים, תוכניות ומעקב",
    },
    "instructor": {
        "label": "מדריך/ת תעסוקה",
        "desc": "תוכניות ותיעוד ביצוע בלבד, בלי מידע רפואי וסוציאלי",
    },
}

# screens (view keys) each profile may open
_ALL_VIEWS = ["caregiver", "goals", "weekly", "daily", "tracking",
              "manager", "rules", "knowledge", "staff", "accessibility"]
VIEWS = {
    "director": _ALL_VIEWS,
    "activity_manager": _ALL_VIEWS,
    "clinical": _ALL_VIEWS,
    "instructor": ["daily", "weekly", "tracking", "accessibility"],
}

# actions -> profiles allowed
ACTIONS = {
    "view_sensitive":  {"director", "activity_manager", "clinical"},
    "edit_resident":   {"director", "activity_manager", "clinical"},
    "generate_plans":  {"director", "activity_manager", "clinical"},
    "bulk_plans":      {"director", "activity_manager"},
    "export_reports":  {"director", "activity_manager"},
    "edit_rules":      {"director", "activity_manager"},
    "edit_kb":         {"director", "activity_manager"},
    "manage_staff":    {"director"},
    "track":           {"director", "activity_manager", "clinical", "instructor"},
}

# human-readable action names (for the permissions matrix screen)
ACTION_LABELS = [
    ("view_sensitive", "צפייה במידע רפואי, סוציאלי ות״ז"),
    ("edit_resident", "עריכת תיק דייר/ת ויעדים"),
    ("generate_plans", "הפקת תוכנית יומית ושבועית"),
    ("track", "סימון ביצוע וחוות דעת"),
    ("bulk_plans", "תכנון לכל המוסד"),
    ("export_reports", "ייצוא דוחות"),
    ("edit_rules", "עריכת כללי המוסד"),
    ("edit_kb", "עריכת בנקי ידע"),
    ("manage_staff", "ניהול בעלי תפקידים"),
]

NO_PERMISSION = "אין לך הרשאה לפעולה זו"


def profile_of(role_key: str | None) -> str:
    return ROLE_TO_PROFILE.get(role_key or "", DEFAULT_PROFILE)


def current_profile() -> str:
    return st.session_state.get("current_user_profile") or "director"


def can(action: str) -> bool:
    return current_profile() in ACTIONS.get(action, set())


def can_view(view_key: str) -> bool:
    return view_key in VIEWS.get(current_profile(), _ALL_VIEWS)


def allowed_views() -> list[str]:
    return VIEWS.get(current_profile(), _ALL_VIEWS)


def help_if_denied(action: str, text: str | None = None) -> str | None:
    """Tooltip for a disabled control."""
    return None if can(action) else NO_PERMISSION if text is None else text
