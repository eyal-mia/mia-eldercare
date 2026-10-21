"""
Display-only Hebrew labels.

The planning engine stores English tags in plan rationales and goal tags
(e.g. "aerobic_low(34)"). This module turns them into readable Hebrew chips on
screen. Nothing here changes what the engine computes or stores.
"""

from __future__ import annotations

import html
import re

TAG_HE = {
    "aerobic_low": "אירובי קל", "arabic_content": "תוכן בערבית",
    "art_therapy": "טיפול באמנות", "balance": "שיווי משקל",
    "balanced_diet": "תזונה מאוזנת", "behavioral_activation": "הפעלה התנהגותית",
    "breathing": "נשימה", "complex_cognitive": "אתגר קוגניטיבי",
    "complex_self_care_alone": "טיפול עצמי", "core": "חיזוק מרכז הגוף",
    "creative": "יצירה", "crisis_plan": "תוכנית משבר",
    "cultural_familiar": "תוכן תרבותי מוכר", "daily_movement": "תנועה יומית",
    "family_inclusive": "שילוב המשפחה", "fine_motor": "מוטוריקה עדינה",
    "flexibility": "גמישות", "gait_training": "אימון הליכה",
    "gentle_touch": "מגע עדין", "grief_group": "קבוצת התמודדות עם אובדן",
    "group_activity": "פעילות קבוצתית", "hope_focus": "מיקוד בתקווה",
    "intergenerational": "מפגש בין-דורי", "language_learning": "לימוד שפה",
    "learning_new": "למידה חדשה", "light_exposure": "חשיפה לאור",
    "light_exposure_evening": "אור בשעות הערב", "maintain_social": "שמירה על קשרים",
    "meaning_focus": "משמעות", "memory_games": "משחקי זיכרון",
    "mindfulness": "מיינדפולנס", "mirror_therapy": "טיפול במראה",
    "moderate_cognitive": "גירוי קוגניטיבי", "music_familiar": "מוזיקה מוכרת",
    "music_therapy": "טיפול במוזיקה", "native_language_group": "קבוצה בשפת האם",
    "nature_exposure": "שהייה בטבע", "one_on_one": "מפגש אישי",
    "outings": "יציאות", "passive_motion": "תנועה פסיבית",
    "peer_family": "משפחה וחברים", "peer_support": "תמיכת עמיתים",
    "peer_visits": "ביקורי עמיתים", "pelvic_floor": "רצפת אגן",
    "pet_companionship": "בעלי חיים", "phone_calls": "שיחות טלפון",
    "physiotherapy": "פיזיותרפיה", "predictable_routine": "שגרה צפויה",
    "pursed_lip": "נשימת שפתיים", "quadriceps_strength": "חיזוק רגליים",
    "range_of_motion": "טווחי תנועה", "relaxation": "הרפיה",
    "religious_appropriate": "התאמה דתית", "reminiscence": "העלאת זיכרונות",
    "reminiscence_careful": "זיכרונות ברגישות", "rhythmic_movement": "תנועה קצבית",
    "routine": "שגרה", "self_expression": "ביטוי עצמי",
    "sensory_stim": "גירוי חושי", "skill_building": "פיתוח מיומנויות",
    "skill_recognition": "הכרה ביכולות", "sleep_hygiene": "הרגלי שינה",
    "social": "קשר חברתי", "social_engagement": "מעורבות חברתית",
    "soothing_voice": "קול מרגיע", "speech_therapy": "תקשורת ודיבור",
    "spiritual_support": "תמיכה רוחנית", "structured_routine": "שגרה מובנית",
    "swimming": "שחייה", "tactile": "מגע ותחושה",
    "timed_voiding": "הרגלי שירותים", "upper_body_low": "פלג גוף עליון",
    "validation": "תיקוף רגשי", "voice_exercise": "תרגול קול",
    "water_aerobics": "התעמלות במים", "weight_bearing_low": "נשיאת משקל קלה",
    "yoga": "יוגה",
    # contraindication tags (shown in "זהירות(...)")
    "competitive": "תחרותיות", "complex_instructions": "הוראות מורכבות",
    "deep_squat": "כריעה עמוקה", "heavy_lifting": "הרמה כבדה",
    "high_balance_demand": "דרישת שיווי משקל גבוהה", "high_intensity": "מאמץ גבוה",
    "high_pressure_competitive": "תחרות לחוצה",
    "long_no_bathroom_access": "זמן ארוך בלי שירותים", "loud_crowds": "רעש וקהל",
    "sudden_position_change": "שינוי תנוחה פתאומי", "trigger_topics": "נושאים רגישים",
}

SOURCE_KIND_HE = {"assisted_living": "הדיור המוגן", "city": "העירייה"}

CATEGORY_HE = {
    "physical": "פיזית", "cognitive": "קוגניטיבית", "social": "חברתית",
    "mental": "נפשית", "sport": "ספורט", "medical": "רפואית",
    "nursing": "סיעודית", "meal": "ארוחה", "external": "פעילות סביבתית",
    "holiday": "חג", "general": "כללי",
}

MEAL_HE = {"MEAL_BREAKFAST": "ארוחת בוקר", "MEAL_LUNCH": "ארוחת צהריים",
           "MEAL_DINNER": "ארוחת ערב"}


def tag_he(tag: str) -> str:
    tag = (tag or "").strip()
    return TAG_HE.get(tag, tag.replace("_", " "))


def holiday_name(code: str) -> str | None:
    try:
        from models.holidays import HOLIDAYS
    except Exception:
        return None
    for h in HOLIDAYS.values():
        if h.get("code") == code:
            return h.get("name_he")
    return None


def item_name(code: str, name: str | None) -> str:
    """Readable name for a plan item when the bank lookup came back empty."""
    if code in MEAL_HE:
        return MEAL_HE[code]
    if code and code.startswith("HOL_"):
        return holiday_name(code) or name or code
    return name or code


def category_label(cat: str | None) -> str:
    return CATEGORY_HE.get(cat or "general", cat or "")


_TAG_RE = re.compile(r"^([a-z][a-z0-9_]*)\((\d+(?:\.\d+)?)\)$")


def rationale_html(text: str | None) -> str:
    """Turn a stored rationale string into Hebrew chips (HTML)."""
    if not text:
        return ""
    text = str(text)
    lead = ""
    m = re.match(r"^(🏃 ספורט בוקר:|🎉 חג:|➕ הוסף ידנית:)\s*(.*)$", text)
    if m:
        lead, text = m.group(1).rstrip(":"), m.group(2)
    m = re.match(r"^🏛️\s*([a-z_]+):\s*(.*)$", text)
    if m:
        src = SOURCE_KIND_HE.get(m.group(1), m.group(1))
        return (f"<span class='why-lead'>🏛️ פעילות סביבתית · {html.escape(src)}</span>"
                f"<span class='why-chip'>{html.escape(m.group(2))}</span>")
    chips = []
    for part in [p.strip() for p in text.split(";") if p.strip()]:
        tm = _TAG_RE.match(part)
        if tm:
            chips.append(f"<span class='why-chip' title='משקל {tm.group(2)}'>"
                         f"{html.escape(tag_he(tm.group(1)))}</span>")
            continue
        cm = re.match(r"^זהירות\((.*)\)$", part)
        if cm:
            names = ", ".join(tag_he(x) for x in cm.group(1).split(",") if x)
            chips.append(f"<span class='why-chip warn'>⚠️ זהירות: {html.escape(names)}</span>")
            continue
        if part == "העדפה":
            part = "קטגוריה מועדפת"
        elif part == "🎯 יעד":
            part = "🎯 יעד טיפול"
        chips.append(f"<span class='why-chip soft'>{html.escape(part)}</span>")
    out = ""
    if lead:
        out += f"<span class='why-lead'>{html.escape(lead)}</span>"
    return out + "".join(chips)


def tags_html(csv: str | None) -> str:
    """Goal target tags (';' separated) as Hebrew chips."""
    parts = [p.strip() for p in (csv or "").replace(",", ";").split(";") if p.strip()]
    return "".join(f"<span class='why-chip'>{html.escape(tag_he(p))}</span>" for p in parts)
