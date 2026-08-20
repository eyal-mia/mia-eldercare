"""
ElderCare - Streamlit UI (user + manager).

Three persona views via sidebar:
- Caregiver: profile + daily + weekly plan + execution + measurements + import
- Manager:   org dashboard + reports
- Knowledge: knowledge banks viewer + refresh

Launch:  streamlit run ui/app.py
"""

from __future__ import annotations
from pathlib import Path
import sys
import datetime as dt
import json

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd

from data.schema import init_database, get_connection, refresh_knowledge_banks
from models.optimizer import (
    generate_plan_for_elder,
    generate_weekly_plan_for_elder,
    week_start_sunday,
)
from ui.i18n import t, SUPPORTED, is_rtl
from ui import file_import
from ui import styling
from reports import export as report_export


# ---------------- bootstrap ----------------
st.set_page_config(page_title="MIA", layout="wide", initial_sidebar_state="expanded")
init_database()


def _ensure_demo_seeded() -> None:
    """On a fresh host (e.g. Streamlit Community Cloud) the database starts
    empty. Seed the demo residents + care goals + this-week plans once so the
    shared link is populated immediately. Guarded by an emptiness check, so it
    runs only on a cold start, never on ordinary reruns."""
    conn = get_connection()
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM elders WHERE active = 1"
        ).fetchone()[0]
    finally:
        conn.close()
    if n == 0:
        with st.spinner("טוען נתוני דמו (פעם ראשונה בלבד, עשוי לקחת עד דקה)..."):
            import seed_demo_elders
            seed_demo_elders.seed(verbose=False)


try:
    _ensure_demo_seeded()
except Exception as _seed_err:  # never let seeding block the app from loading
    st.warning(f"טעינת נתוני הדמו דילגה: {_seed_err}")


HEBREW_DAYS = ["day_sunday", "day_monday", "day_tuesday", "day_wednesday",
               "day_thursday", "day_friday", "day_saturday"]
HEBREW_MONTHS = ["", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
                 "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]


def hebrew_date(d: dt.date) -> str:
    return f"{d.day} {HEBREW_MONTHS[d.month]}"


def day_index_hebrew(d: dt.date) -> int:
    """0 = Sunday ... 6 = Saturday"""
    return (d.weekday() + 1) % 7


# ---------------- session state ----------------
if "lang" not in st.session_state:
    st.session_state.lang = "he"
if "elder_id" not in st.session_state:
    st.session_state.elder_id = None
if "view" not in st.session_state:
    st.session_state.view = "caregiver"
if "week_start" not in st.session_state:
    st.session_state.week_start = week_start_sunday(dt.date.today())


# Inject CSS at the TOP LEVEL (into the main document), NOT inside the sidebar.
# Injecting inside the sidebar meant the styles vanished whenever the sidebar
# collapsed/unmounted — which broke RTL and hid the menu.
LANG = st.session_state.lang
styling.inject(LANG)


# ---------------- sidebar ----------------
with st.sidebar:
    st.session_state.lang = st.selectbox(
        "Language / שפה",
        options=list(SUPPORTED.keys()),
        index=list(SUPPORTED.keys()).index(st.session_state.lang),
        format_func=lambda c: SUPPORTED[c],
    )
    LANG = st.session_state.lang

    st.markdown(
        '<div class="brand-logo">'
        '<span class="logo-emoji">🏡</span>'
        '<span><span class="logo-name">MIA</span>'
        '<span class="logo-tag">Maximizing of Independence &amp; Autonomy</span></span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ---- resident switcher (top of the sidebar, right under the brand) ----
    # This is the single, app-wide "current resident" control. It stays in sync
    # with st.session_state.elder_id even when other views change it (e.g. the
    # manager directory click-through), via a shadow value that detects external
    # changes — so we never clobber the user's dropdown pick and never ignore an
    # external switch.
    _sc = get_connection()
    _sb_elders = _sc.execute(
        "SELECT id, full_name FROM elders WHERE active = 1 ORDER BY full_name"
    ).fetchall()
    _sc.close()
    if _sb_elders:
        _sb_ids = [e["id"] for e in _sb_elders]
        _sb_names = {e["id"]: e["full_name"] for e in _sb_elders}
        st.session_state._elder_ids = _sb_ids

        # sync the picker from elder_id ONLY when elder_id was changed elsewhere
        if (st.session_state.elder_id != st.session_state.get("_elder_id_shadow")
                and st.session_state.elder_id in _sb_ids):
            st.session_state.nav_elder_pick = st.session_state.elder_id
        if st.session_state.get("nav_elder_pick") not in _sb_ids:
            st.session_state.nav_elder_pick = (
                st.session_state.elder_id
                if st.session_state.elder_id in _sb_ids else _sb_ids[0]
            )

        def _shift_resident(delta: int):
            ids = st.session_state.get("_elder_ids", [])
            if not ids:
                return
            i = ids.index(st.session_state.nav_elder_pick)
            st.session_state.nav_elder_pick = ids[min(max(i + delta, 0), len(ids) - 1)]

        st.markdown(
            f"<div class='resident-pick-label'>🧓 {t('current_resident', LANG)}</div>",
            unsafe_allow_html=True,
        )
        st.selectbox(
            t("current_resident", LANG),
            options=_sb_ids,
            format_func=lambda i: _sb_names.get(i, "-"),
            key="nav_elder_pick",
            label_visibility="collapsed",
        )
        _cur_i = _sb_ids.index(st.session_state.nav_elder_pick)
        _pn = st.columns(2)
        _pn[0].button("→", key="sb_prev_res", width="stretch",
                      disabled=_cur_i == 0, on_click=_shift_resident, args=(-1,),
                      help=t("prev_resident", LANG))
        _pn[1].button("←", key="sb_next_res", width="stretch",
                      disabled=_cur_i >= len(_sb_ids) - 1,
                      on_click=_shift_resident, args=(1,),
                      help=t("next_resident", LANG))
        # commit the pick as the app-wide current resident
        st.session_state.elder_id = st.session_state.nav_elder_pick
        st.session_state._elder_id_shadow = st.session_state.elder_id

    # navigation is split into two groups: elder-specific data vs general
    # (institution-wide) data. Buttons let us render group headers.
    def _nav_button(view_key: str, icon: str, label_key: str):
        active = st.session_state.view == view_key
        if st.button(
            f"{icon} {t(label_key, LANG)}",
            key=f"nav_{view_key}",
            width="stretch",
            type="primary" if active else "secondary",
        ):
            st.session_state.view = view_key
            st.rerun()

    # ----- ELDER DATA -----
    st.markdown(f"#### 👤 {t('nav_group_elder', LANG)}")
    _nav_button("caregiver", "👤", "nav_profile")
    _nav_button("goals", "🎯", "nav_goals")
    _nav_button("daily", "📅", "nav_daily_plan")
    _nav_button("weekly", "🗓️", "nav_weekly_plan")
    _nav_button("tracking", "📌", "nav_tracking")

    st.markdown("---")

    # ----- GENERAL DATA -----
    st.markdown(f"#### 🏢 {t('nav_group_general', LANG)}")
    _nav_button("manager", "📊", "nav_admin")
    _nav_button("knowledge", "📚", "nav_knowledge")
    _nav_button("rules", "📋", "nav_rules")

    st.markdown("---")


# ---------------- helpers ----------------
def _list_elders(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT id, full_name, room_number, primary_language, active "
        "FROM elders WHERE active = 1 ORDER BY full_name"
    ).fetchall()
    return [dict(r) for r in rows]


def _split(csv: str | None) -> list[str]:
    if not csv:
        return []
    return [p.strip() for p in csv.replace(",", ";").split(";") if p.strip()]


def _join(items: list[str]) -> str:
    return ";".join(items)


def _get_or_create_plan(conn, elder_id: int, plan_date_iso: str) -> int:
    """Return the daily_plans.id for (elder_id, plan_date), creating a blank
    one if it doesn't exist yet. Lets manual additions land in a date that
    hasn't been auto-generated."""
    row = conn.execute(
        "SELECT id FROM daily_plans WHERE elder_id = ? AND plan_date = ?",
        (elder_id, plan_date_iso),
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO daily_plans (elder_id, plan_date, optimizer_version, objective_score) "
        "VALUES (?, ?, ?, ?)",
        (elder_id, plan_date_iso, "manual", 0.0),
    )
    conn.commit()
    return cur.lastrowid


def _add_item_to_plan(conn, elder_id: int, plan_date_iso: str,
                      activity_code: str, time_slot: str,
                      start_time: str, duration_min: int,
                      rationale: str) -> bool:
    """Insert a plan_item. Returns False if the same code is already in the
    plan for that date (to avoid duplicates)."""
    plan_id = _get_or_create_plan(conn, elder_id, plan_date_iso)
    existing = conn.execute(
        "SELECT id FROM plan_items WHERE plan_id = ? AND activity_code = ?",
        (plan_id, activity_code),
    ).fetchone()
    if existing:
        return False
    conn.execute(
        "INSERT INTO plan_items "
        "(plan_id, time_slot, start_time, activity_code, duration_min, rationale) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (plan_id, time_slot, start_time, activity_code, duration_min, rationale),
    )
    conn.commit()
    return True


def _infer_slot_from_time(hhmm: str) -> str:
    try:
        h = int(hhmm.split(":")[0])
    except Exception:
        return "morning"
    if h < 12:
        return "morning"
    if h < 15:
        return "noon"
    if h < 18:
        return "afternoon"
    return "evening"


# =====================================================================
# SHARED: current-resident resolution + banner for the resident sub-views
# =====================================================================
def _current_elder_id(conn) -> int | None:
    """The app-wide selected resident (set by the sidebar switcher). Falls back
    to the first active resident so sub-views always have someone to show."""
    eid = st.session_state.get("elder_id")
    row = conn.execute(
        "SELECT id FROM elders WHERE id = ? AND active = 1", (eid,)
    ).fetchone() if eid else None
    if not row:
        row = conn.execute(
            "SELECT id FROM elders WHERE active = 1 ORDER BY full_name LIMIT 1"
        ).fetchone()
        if row:
            st.session_state.elder_id = row["id"]
    return row["id"] if row else None


def _resident_banner(conn, elder_id, LANG) -> None:
    """Compact banner naming the resident these sub-view figures belong to.
    Keeps every sub-screen in sync with the sidebar resident switcher."""
    row = conn.execute(
        "SELECT full_name, room_number FROM elders WHERE id = ?", (elder_id,)
    ).fetchone()
    if not row:
        return
    room = row["room_number"] or "-"
    st.markdown(
        f"<div class='resident-banner'>🧓 <b>{row['full_name']}</b>"
        f"<span class='rb-room'>· {t('room_number', LANG)} {room}</span>"
        f"<span class='rb-hint'>({t('current_resident', LANG)})</span></div>",
        unsafe_allow_html=True,
    )


# =====================================================================
# CAREGIVER VIEW
# =====================================================================
def view_caregiver(LANG: str):
    conn = get_connection()
    elders = _list_elders(conn)

    with st.sidebar:
        st.markdown("---")
        with st.expander("➕ " + t("add_elder", LANG), expanded=not elders):
            with st.form("add_elder_form"):
                name = st.text_input(t("elder_name", LANG))
                birth = st.date_input(
                    t("birth_date", LANG),
                    value=dt.date(1940, 1, 1),
                    min_value=dt.date(1900, 1, 1),
                    max_value=dt.date.today(),
                )
                gender = st.selectbox(
                    t("gender", LANG),
                    options=["female", "male"],
                    format_func=lambda v: t(v, LANG),
                )
                room = st.text_input(t("room_number", LANG))
                lang_pref = st.selectbox(
                    t("primary_language", LANG),
                    options=list(SUPPORTED.keys()),
                    format_func=lambda c: SUPPORTED[c],
                )
                if st.form_submit_button(t("save", LANG)):
                    if name.strip():
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO elders (organization_id, full_name, birth_date, gender, room_number, primary_language) "
                            "VALUES ((SELECT id FROM organizations LIMIT 1), ?, ?, ?, ?, ?)",
                            (name.strip(), birth.isoformat(), gender, room, lang_pref),
                        )
                        elder_id = cur.lastrowid
                        cur.execute(
                            "INSERT INTO elder_profile (elder_id) VALUES (?)",
                            (elder_id,),
                        )
                        conn.commit()
                        st.session_state.elder_id = elder_id
                        st.success(t("elder_added", LANG))
                        st.rerun()

        # resident selection now lives in the main sidebar (top, under the brand)

    if not elders:
        st.info(t("no_elder_selected", LANG))
        conn.close()
        return

    elder_id = st.session_state.elder_id
    elder = conn.execute("SELECT * FROM elders WHERE id = ?", (elder_id,)).fetchone()
    profile = conn.execute("SELECT * FROM elder_profile WHERE elder_id = ?", (elder_id,)).fetchone()

    # ---- ORGANIZATION (institution) banner ----
    org = conn.execute("""
        SELECT o.* FROM organizations o
        JOIN elders e ON e.organization_id = o.id
        WHERE e.id = ?
    """, (elder_id,)).fetchone()
    if org:
        def _g(key):
            try:
                v = org[key]
                return v if v else ""
            except (KeyError, IndexError):
                return ""
        org_emoji = _g("logo_emoji") or "🏥"
        org_name = _g("name")
        org_addr = _g("address")
        org_city = _g("city")
        org_phone = _g("phone")
        org_email = _g("email")
        org_contact = _g("contact_person")
        org_manager = _g("manager_name")
        org_desc = _g("description")
        addr_full = ", ".join(p for p in (org_addr, org_city) if p)
        # rules come from the Word file (global rules bank), with DB rules as fallback
        try:
            from models import rules_doc as _rd
            org_rules = "\n".join(_rd.read_rules())
        except Exception:
            org_rules = _g("institution_rules")
        st.markdown(
            f"""
            <div class="org-banner">
              <div class="org-banner-top">
                <span class="org-banner-name">{org_emoji} {org_name}</span>
                {f'<span class="org-banner-manager">👔 {org_manager}</span>' if org_manager else ''}
              </div>
              <div class="org-banner-row">
                {f'<span>📍 {addr_full}</span>' if addr_full else ''}
                {f'<span>📞 <span class="ltr-text">{org_phone}</span></span>' if org_phone else ''}
                {f'<span>✉️ <span class="ltr-text">{org_email}</span></span>' if org_email else ''}
              </div>
              {f'<div class="org-banner-contact">👤 {org_contact}</div>' if org_contact else ''}
              {f'<div class="org-banner-desc">{org_desc}</div>' if org_desc else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if org_rules and org_rules.strip():
            rules_lines = [ln.strip() for ln in org_rules.split("\n") if ln.strip()]
            with st.expander(f"📋 כללי המוסד ({len(rules_lines)})", expanded=False):
                for ln in rules_lines:
                    st.markdown(f"• {ln}")

    # MIA-style elder header
    age = ""
    if elder["birth_date"]:
        try:
            birth = dt.date.fromisoformat(elder["birth_date"])
            age = f"{(dt.date.today() - birth).days // 365} שנים"
        except Exception:
            pass
    st.markdown(
        f"""<div class="eldercare-header">
        <h2>👤 {elder['full_name']}</h2>
        <div class="subtitle">
          {t('room_number', LANG)} {elder['room_number'] or '-'} ·
          {age} · {t(elder['gender'] or 'other', LANG)} ·
          {SUPPORTED.get(elder['primary_language'], '-')}
        </div></div>""",
        unsafe_allow_html=True,
    )

    # (resident prev/next switcher now lives in the sidebar, under the brand)

    # ---- participation summary (overall activity participation data) ----
    _pc = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    _prow = conn.execute("""
        SELECT COUNT(*) AS sched,
               COALESCE(SUM(CASE WHEN pi.executed=1 THEN 1 ELSE 0 END),0) AS done,
               COALESCE(SUM(CASE WHEN pi.executed=0 AND pi.skipped_reason IS NOT NULL
                             THEN 1 ELSE 0 END),0) AS skipped,
               AVG(pi.instructor_rating) AS avg_rating
        FROM plan_items pi JOIN daily_plans dp ON dp.id = pi.plan_id
        WHERE dp.elder_id = ? AND dp.plan_date >= ?
          AND pi.activity_code NOT LIKE 'MEAL_%'
    """, (elder_id, _pc)).fetchone()
    with st.expander(f"📊 {t('participation_title', LANG)} (30 יום)", expanded=False):
        sched = _prow["sched"] or 0
        pcols = st.columns(4)
        pcols[0].metric(t("tracking_summary_done", LANG), _prow["done"] or 0)
        pcols[1].metric(t("tracking_summary_skipped", LANG), _prow["skipped"] or 0)
        pcols[2].metric(t("completion_rate", LANG),
                        f"{((_prow['done'] or 0)/sched*100) if sched else 0:.0f}%")
        pcols[3].metric("⭐ " + t("instructor_review_title", LANG),
                        f"{_prow['avg_rating']:.1f}" if _prow["avg_rating"] else "—")
        # participation by category
        catrows = conn.execute("""
            SELECT CASE
                     WHEN ka.code IS NOT NULL THEN ka.category
                     WHEN ke.code IS NOT NULL THEN 'sport'
                     WHEN ep.id IS NOT NULL THEN 'external'
                     WHEN pi.activity_code LIKE 'HOL_%' THEN 'holiday'
                     ELSE 'general' END AS cat,
                   COUNT(*) AS total,
                   COALESCE(SUM(CASE WHEN pi.executed=1 THEN 1 ELSE 0 END),0) AS done
            FROM plan_items pi JOIN daily_plans dp ON dp.id = pi.plan_id
            LEFT JOIN kb_activities ka ON ka.code = pi.activity_code
            LEFT JOIN kb_exercises  ke ON ke.code = pi.activity_code
            LEFT JOIN external_programs ep ON ('EXT_'||ep.id)=pi.activity_code
            WHERE dp.elder_id = ? AND dp.plan_date >= ?
              AND pi.activity_code NOT LIKE 'MEAL_%'
            GROUP BY cat ORDER BY total DESC
        """, (elder_id, _pc)).fetchall()
        if catrows:
            catmap = {"sport": "🏃 ספורט", "physical": "💪 פיזית",
                      "cognitive": "🧠 קוגניטיבית", "social": "👥 חברתית",
                      "mental": "🌿 נפשית", "external": "🏛️ חיצונית",
                      "holiday": "🎉 חג", "general": "📌 כללי"}
            dfp = pd.DataFrame([{
                "קטגוריה": catmap.get(r["cat"], r["cat"]),
                "מתוזמן": r["total"], "בוצע": r["done"],
            } for r in catrows])
            st.markdown(f"**{t('participation_by_category', LANG)}**")
            st.bar_chart(dfp.set_index("קטגוריה")[["מתוזמן", "בוצע"]], height=260)
        else:
            st.caption("אין עדיין נתוני השתתפות.")

    # short tab labels for a single-line row that fits on one screen
    # NOTE: daily & weekly care plans moved OUT to their own sidebar views
    # (📅 תוכנית טיפול יומית / 🗓️ תוכנית טיפול שבועית).
    tabs = st.tabs([
        "📋 " + t("tab_short_profile", LANG),
        "🕊️ " + t("tab_short_culture", LANG),
        "👨‍👩‍👧 " + t("tab_short_family", LANG),
        "🏛️ " + t("tab_short_external", LANG),
        "📈 " + t("tab_short_tests", LANG),
        "📥 " + t("tab_short_import", LANG),
    ])

    with tabs[0]:
        _render_profile_tab(conn, elder_id, profile, LANG)
    with tabs[1]:
        _render_culture_tab(conn, elder_id, profile, LANG)
    with tabs[2]:
        _render_family_tab(conn, elder_id, LANG)
    with tabs[3]:
        _render_external_tab(conn, elder_id, LANG)
    with tabs[4]:
        _render_measurements_tab(conn, elder_id, LANG)
    with tabs[5]:
        _render_import_tab(conn, elder_id, LANG)

    conn.close()


# ---------- PROFILE TAB ----------
def _render_profile_tab(conn, elder_id, profile, LANG):
    diseases = conn.execute("SELECT code, name_he, name_en FROM kb_diseases ORDER BY name_he").fetchall()
    meds = conn.execute("SELECT code, name_he, name_en FROM kb_medications ORDER BY name_he").fetchall()
    conditions = conn.execute("SELECT code, name_he, name_en, dimension FROM kb_conditions ORDER BY dimension, name_he").fetchall()
    activities = conn.execute("SELECT code, name_he, name_en, category FROM kb_activities ORDER BY category, name_he").fetchall()

    name_field = "name_he" if LANG == "he" else "name_en"

    st.markdown(f"#### 🏥 {t('diseases_codes', LANG)} / 💊 {t('medications_codes', LANG)}")
    cc = st.columns(2)
    with cc[0]:
        sel_diseases = st.multiselect(
            t("diseases_codes", LANG),
            options=[r["code"] for r in diseases],
            format_func=lambda c: next((f"{r[name_field]}" for r in diseases if r["code"] == c), c),
            default=_split(profile["medical_codes"]) if profile else [],
        )
    with cc[1]:
        sel_meds = st.multiselect(
            t("medications_codes", LANG),
            options=[r["code"] for r in meds],
            format_func=lambda c: next((f"{r[name_field]}" for r in meds if r["code"] == c), c),
            default=_split(profile["medication_codes"]) if profile else [],
        )

    st.markdown(f"#### 🧩 {t('conditions_codes', LANG)}")
    cond_by_dim = {}
    for r in conditions:
        cond_by_dim.setdefault(r["dimension"], []).append(r)

    dim_to_field = {
        "nursing": "nursing_codes",
        "cognitive": "cognitive_codes",
        "mental": "mental_codes",
        "social": "social_codes",
        "family": "family_codes",
        # cultural codes are managed in the dedicated Culture & Religion tab
    }
    sel_by_dim = {}
    # only show dimensions that map to a CSV codes field (skip demographic — it
    # has structured columns rendered separately below)
    visible_dims = [d for d in cond_by_dim.keys() if d in dim_to_field]
    cols = st.columns(2)
    for i, dim in enumerate(visible_dims):
        rows = cond_by_dim[dim]
        with cols[i % 2]:
            field = dim_to_field[dim]
            try:
                current = _split(profile[field]) if profile else []
            except (KeyError, IndexError):
                current = []
            label_key = f"dim_{dim}"
            label = t(label_key, LANG) if t(label_key, LANG) != label_key else dim
            sel_by_dim[dim] = st.multiselect(
                label,
                options=[r["code"] for r in rows],
                format_func=lambda c, rr=rows: next(
                    (f"{r[name_field]}" for r in rr if r["code"] == c), c
                ),
                default=current,
            )

    # ---------- LIVING ENVIRONMENT (= demographic dimension) ----------
    st.markdown(f"#### 🏠 {t('dim_demographic', LANG)} — {t('living_section', LANG)}")
    st.caption(t("living_help", LANG))

    def _pget(key, default=None):
        if not profile:
            return default
        try:
            return profile[key]
        except (KeyError, IndexError):
            return default

    lcols = st.columns(4)
    arrangement_opts = ["home_alone", "home_family", "assisted_living",
                        "sheltered_housing", "nursing_home", "day_center"]
    current_arr = _pget("living_arrangement") or "assisted_living"
    if current_arr not in arrangement_opts:
        current_arr = "assisted_living"
    living_arrangement = lcols[0].selectbox(
        t("living_arrangement", LANG),
        options=arrangement_opts,
        index=arrangement_opts.index(current_arr),
        format_func=lambda v: t(f"living_{v}", LANG)
                              if t(f"living_{v}", LANG) != f"living_{v}" else v,
    )
    residence_floor = lcols[1].number_input(
        t("residence_floor", LANG),
        min_value=0, max_value=40,
        value=int(_pget("residence_floor", 0) or 0),
        step=1,
    )
    has_elevator = lcols[2].checkbox(
        t("has_elevator", LANG),
        value=bool(int(_pget("has_elevator", 1) or 0)),
    )
    outdoor_opts = ["full", "limited", "none"]
    current_out = _pget("outdoor_accessibility") or "full"
    if current_out not in outdoor_opts:
        current_out = "full"
    outdoor_accessibility = lcols[3].selectbox(
        t("outdoor_accessibility", LANG),
        options=outdoor_opts,
        index=outdoor_opts.index(current_out),
        format_func=lambda v: t(f"outdoor_{v}", LANG)
                              if t(f"outdoor_{v}", LANG) != f"outdoor_{v}" else v,
    )

    if residence_floor > 2 and not has_elevator and outdoor_accessibility != "none":
        st.warning("⚠️ קומה גבוהה ללא מעלית - האופטימייזר יחסום פעילויות חוץ אוטומטית")
    if outdoor_accessibility == "none":
        st.info("ℹ️ אין נגישות לחוץ - פעילויות outdoor (טיולים, חצר) ייחסמו")

    # ---------- MEAL TIMES (auto-blocked in the plan) ----------
    st.markdown(f"#### 🍽️ {t('meals_section', LANG)}")
    st.caption(t("meals_help", LANG))

    def _parse_time(s, fallback):
        try:
            h, m = map(int, str(s).split(":"))
            return dt.time(hour=h, minute=m)
        except Exception:
            return fallback

    bcols = st.columns(3)
    with bcols[0]:
        st.markdown(f"**🌅 {t('meal_breakfast', LANG)}**")
        breakfast_t = st.time_input(
            t("meal_time", LANG),
            value=_parse_time(_pget("breakfast_time"), dt.time(8, 0)),
            key=f"meal_b_t_{elder_id}",
        )
        breakfast_d = st.number_input(
            t("meal_duration", LANG),
            min_value=10, max_value=120,
            value=int(_pget("breakfast_duration", 60) or 60),
            step=5,
            key=f"meal_b_d_{elder_id}",
        )
    with bcols[1]:
        st.markdown(f"**☀️ {t('meal_lunch', LANG)}**")
        lunch_t = st.time_input(
            t("meal_time", LANG),
            value=_parse_time(_pget("lunch_time"), dt.time(12, 0)),
            key=f"meal_l_t_{elder_id}",
        )
        lunch_d = st.number_input(
            t("meal_duration", LANG),
            min_value=10, max_value=120,
            value=int(_pget("lunch_duration", 60) or 60),
            step=5,
            key=f"meal_l_d_{elder_id}",
        )
    with bcols[2]:
        st.markdown(f"**🌙 {t('meal_dinner', LANG)}**")
        dinner_t = st.time_input(
            t("meal_time", LANG),
            value=_parse_time(_pget("dinner_time"), dt.time(18, 0)),
            key=f"meal_d_t_{elder_id}",
        )
        dinner_d = st.number_input(
            t("meal_duration", LANG),
            min_value=10, max_value=120,
            value=int(_pget("dinner_duration", 60) or 60),
            step=5,
            key=f"meal_d_d_{elder_id}",
        )

    st.markdown(f"#### ⚖️ {t('weights_section', LANG)}")
    st.caption(t("weights_help", LANG))

    def _safe_weight(p, key, fallback=5.0):
        if not p:
            return float(fallback)
        try:
            v = p[key]
        except (KeyError, IndexError):
            return float(fallback)
        if v is None:
            return float(fallback)
        try:
            v = float(v)
        except (TypeError, ValueError):
            return float(fallback)
        return max(1.0, min(10.0, v))

    # 5 discrete levels — easier than a slider, very clear semantics
    WEIGHT_LEVELS = [
        (1.0,  "1 · " + t("weight_level_minimal", LANG)),
        (3.0,  "3 · " + t("weight_level_low", LANG)),
        (5.0,  "5 · " + t("weight_level_medium", LANG)),
        (7.0,  "7 · " + t("weight_level_high", LANG)),
        (10.0, "10 · " + t("weight_level_critical", LANG)),
    ]

    def _closest_level_idx(value: float) -> int:
        return min(range(len(WEIGHT_LEVELS)),
                   key=lambda i: abs(WEIGHT_LEVELS[i][0] - value))

    weight_fields = [
        ("weight_medical", "dim_medical"),
        ("weight_medication", "dim_medication"),
        ("weight_nursing", "dim_nursing"),
        ("weight_cognitive", "dim_cognitive"),
        ("weight_mental", "dim_mental"),
        ("weight_social", "dim_social"),
        ("weight_family", "dim_family"),
        ("weight_demographic", "dim_demographic"),
        ("weight_cultural", "dim_cultural"),
    ]

    wcols = st.columns(3)
    weight_values = {}
    for i, (field, label) in enumerate(weight_fields):
        with wcols[i % 3]:
            current = _safe_weight(profile, field, 5.0)
            chosen_idx = st.selectbox(
                t(label, LANG),
                options=list(range(len(WEIGHT_LEVELS))),
                format_func=lambda i: WEIGHT_LEVELS[i][1],
                index=_closest_level_idx(current),
                key=f"sel_{field}_{elder_id}",   # per-elder key so switching elder
                                                  # rebinds to that elder's value
            )
            weight_values[field] = WEIGHT_LEVELS[chosen_idx][0]

    # preference weight — separate row
    pref_current = _safe_weight(profile, "weight_preference", 6.0)
    pref_idx = st.selectbox(
        t("dim_preference", LANG),
        options=list(range(len(WEIGHT_LEVELS))),
        format_func=lambda i: WEIGHT_LEVELS[i][1],
        index=_closest_level_idx(pref_current),
        key=f"sel_weight_preference_{elder_id}",
    )
    weight_values["weight_preference"] = WEIGHT_LEVELS[pref_idx][0]

    st.markdown(f"#### 🎯 {t('capability_level', LANG)} & {t('preferences_categories', LANG)}")
    st.caption(t("capability_help", LANG))
    # capability_level — selectbox with descriptive labels (1=dep, 5=indep)
    cap_default = 3
    if profile:
        try:
            _cv = profile["capability_level"]
            if _cv is not None:
                cap_default = max(1, min(5, int(_cv)))
        except (KeyError, IndexError, TypeError, ValueError):
            cap_default = 3
    CAP_LEVELS = [
        (1, "1 · " + t("cap_level_full_dep", LANG)),
        (2, "2 · " + t("cap_level_high_dep", LANG)),
        (3, "3 · " + t("cap_level_mid_dep", LANG)),
        (4, "4 · " + t("cap_level_mostly_indep", LANG)),
        (5, "5 · " + t("cap_level_full_indep", LANG)),
    ]
    cap_idx = st.selectbox(
        t("capability_level", LANG),
        options=list(range(len(CAP_LEVELS))),
        format_func=lambda i: CAP_LEVELS[i][1],
        index=cap_default - 1,
        key=f"sel_capability_{elder_id}",
    )
    cap = CAP_LEVELS[cap_idx][0]

    cat_options = sorted({r["category"] for r in activities})
    cc2 = st.columns(2)
    with cc2[0]:
        pref_cats = st.multiselect(
            t("preferences_categories", LANG),
            options=cat_options,
            format_func=lambda c: t(f"cat_{c}", LANG) if t(f"cat_{c}", LANG) != f"cat_{c}" else c,
            default=_split(profile["preferences_categories"]) if profile else [],
        )
    with cc2[1]:
        slot_opts = ["morning", "noon", "afternoon", "evening"]
        pref_slots = st.multiselect(
            t("preferences_time_slots", LANG),
            options=slot_opts,
            format_func=lambda s: t(f"time_{s}", LANG),
            default=_split(profile["preferences_time_slots"]) if profile else [],
        )

    # backward compat: profile column may be either new (preferred) or old (avoid).
    if profile:
        _pkeys = profile.keys()
        if "preferred_activity_codes" in _pkeys:
            _preferred_default = _split(profile["preferred_activity_codes"])
        elif "avoid_activity_codes" in _pkeys:
            _preferred_default = _split(profile["avoid_activity_codes"])
        else:
            _preferred_default = []
    else:
        _preferred_default = []

    st.markdown(f"#### ⭐ {t('preferred_activities', LANG)}")
    st.caption(t("preferred_activities_help", LANG))
    preferred = st.multiselect(
        t("preferred_activities", LANG),
        options=[r["code"] for r in activities],
        format_func=lambda c, aa=activities: next(
            (f"{r[name_field]}" for r in aa if r["code"] == c), c
        ),
        default=_preferred_default,
        label_visibility="collapsed",
    )

    if st.button("💾 " + t("save", LANG), type="primary"):
        cur = conn.cursor()
        cur.execute("""
            UPDATE elder_profile SET
              medical_codes = ?, medication_codes = ?,
              nursing_codes = ?, cognitive_codes = ?, mental_codes = ?,
              social_codes = ?, family_codes = ?,
              preferences_categories = ?, preferences_time_slots = ?,
              preferred_activity_codes = ?,
              weight_medical = ?, weight_medication = ?, weight_nursing = ?,
              weight_cognitive = ?, weight_mental = ?, weight_social = ?,
              weight_family = ?, weight_demographic = ?, weight_cultural = ?,
              weight_preference = ?,
              capability_level = ?,
              living_arrangement = ?, residence_floor = ?,
              has_elevator = ?, outdoor_accessibility = ?,
              breakfast_time = ?, breakfast_duration = ?,
              lunch_time = ?, lunch_duration = ?,
              dinner_time = ?, dinner_duration = ?,
              updated_at = CURRENT_TIMESTAMP
            WHERE elder_id = ?
        """, (
            _join(sel_diseases), _join(sel_meds),
            _join(sel_by_dim.get("nursing", [])),
            _join(sel_by_dim.get("cognitive", [])),
            _join(sel_by_dim.get("mental", [])),
            _join(sel_by_dim.get("social", [])),
            _join(sel_by_dim.get("family", [])),
            _join(pref_cats), _join(pref_slots), _join(preferred),
            weight_values["weight_medical"], weight_values["weight_medication"],
            weight_values["weight_nursing"], weight_values["weight_cognitive"],
            weight_values["weight_mental"], weight_values["weight_social"],
            weight_values["weight_family"], weight_values["weight_demographic"],
            weight_values["weight_cultural"],
            weight_values["weight_preference"],
            cap,
            living_arrangement, int(residence_floor),
            int(bool(has_elevator)), outdoor_accessibility,
            breakfast_t.strftime("%H:%M"), int(breakfast_d),
            lunch_t.strftime("%H:%M"), int(lunch_d),
            dinner_t.strftime("%H:%M"), int(dinner_d),
            elder_id,
        ))
        conn.commit()
        st.success(t("profile_saved", LANG))


# ---------- FAMILY CONTACTS TAB ----------
RELATION_OPTIONS = [
    "son", "daughter", "wife", "husband", "spouse",
    "grandchild", "sibling", "niece", "nephew",
    "neighbor", "friend", "other",
]


def _render_family_tab(conn, elder_id, LANG):
    contacts = conn.execute(
        "SELECT * FROM family_contacts WHERE elder_id = ? "
        "ORDER BY is_primary DESC, name",
        (elder_id,),
    ).fetchall()

    if not contacts:
        st.info(t("family_no_contacts", LANG))
    else:
        # render colored cards (primary contact highlighted)
        for c in contacts:
            primary_cls = " primary" if c["is_primary"] else ""
            primary_badge = (
                f'<span class="primary-badge">⭐ {t("primary_badge", LANG)}</span>'
                if c["is_primary"] else ""
            )
            lives_with = "🏠 " + t("family_lives_with", LANG) + "  " if c["lives_with_elder"] else ""
            relation_label = t(f"rel_{c['relation']}", LANG)
            if relation_label == f"rel_{c['relation']}":
                relation_label = c["relation"] or ""

            phone_html = (
                f'<div class="phone">📞 <span class="ltr-text">{c["phone"]}</span></div>'
                if c["phone"] else ""
            )
            email_html = (
                f'<div class="phone" style="font-size:0.95rem;">✉️ '
                f'<span class="ltr-text">{c["email"]}</span></div>'
                if c["email"] else ""
            )
            notes_html = (
                f'<div class="notes">{c["notes"]}</div>' if c["notes"] else ""
            )

            st.markdown(
                f"""
                <div class="family-card{primary_cls}">
                  {primary_badge}
                  <span class="name">👤 {c["name"]}</span>
                  <span class="relation"> · {relation_label}</span>
                  <div style="margin-top:0.3rem;color:#92400e;font-size:0.9rem;">{lives_with}</div>
                  {phone_html}
                  {email_html}
                  {notes_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
            # action buttons
            bcols = st.columns([1, 1, 6])
            with bcols[0]:
                if st.button("🗑️ " + t("delete", LANG), key=f"fc_del_{c['id']}"):
                    conn.execute("DELETE FROM family_contacts WHERE id = ?", (c["id"],))
                    conn.commit()
                    st.rerun()
            with bcols[1]:
                if not c["is_primary"]:
                    if st.button("⭐ " + t("family_is_primary", LANG), key=f"fc_pri_{c['id']}"):
                        conn.execute(
                            "UPDATE family_contacts SET is_primary = 0 WHERE elder_id = ?",
                            (elder_id,),
                        )
                        conn.execute(
                            "UPDATE family_contacts SET is_primary = 1 WHERE id = ?",
                            (c["id"],),
                        )
                        conn.commit()
                        st.rerun()

    # add new contact form
    st.markdown("---")
    st.markdown(f"### ➕ {t('family_add', LANG)}")
    with st.form(f"add_family_{elder_id}", clear_on_submit=True):
        cols = st.columns([2, 2, 2, 1])
        new_name = cols[0].text_input(t("family_name", LANG))
        new_relation = cols[1].selectbox(
            t("family_relation", LANG),
            options=RELATION_OPTIONS,
            format_func=lambda r: (
                t(f"rel_{r}", LANG)
                if t(f"rel_{r}", LANG) != f"rel_{r}" else r
            ),
        )
        new_phone = cols[2].text_input(t("family_phone", LANG))
        new_primary = cols[3].checkbox(t("family_is_primary", LANG))

        cols2 = st.columns([3, 1, 2])
        new_email = cols2[0].text_input(t("family_email", LANG))
        new_lives = cols2[1].checkbox(t("family_lives_with", LANG))
        new_notes = cols2[2].text_input(t("family_notes", LANG))

        if st.form_submit_button("💾 " + t("save", LANG), type="primary"):
            if new_name.strip():
                cur = conn.cursor()
                if new_primary:
                    cur.execute(
                        "UPDATE family_contacts SET is_primary = 0 WHERE elder_id = ?",
                        (elder_id,),
                    )
                cur.execute(
                    "INSERT INTO family_contacts "
                    "(elder_id, relation, name, phone, email, is_primary, lives_with_elder, notes) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (elder_id, new_relation, new_name.strip(), new_phone,
                     new_email, int(new_primary), int(new_lives), new_notes),
                )
                conn.commit()
                st.success(t("saved_ok", LANG))
                st.rerun()


# ---------- CULTURE & RELIGION TAB ----------
RELIGION_OPTIONS = ["none", "jewish", "muslim", "christian", "hindu"]
RELIGIOSITY_OPTIONS = ["very_observant", "observant", "secular"]


def _render_culture_tab(conn, elder_id, profile, LANG):
    from models.optimizer import religion_tags  # local import to avoid cycle on cold start

    st.markdown(f"### 🕊️ {t('nav_culture', LANG)}")
    st.caption(t("culture_help", LANG))

    def _pget(key, default=None):
        if not profile:
            return default
        try:
            return profile[key]
        except (KeyError, IndexError):
            return default

    # --- cultural identities (CON_cultural codes) ---
    cultural_rows = conn.execute(
        "SELECT code, name_he, name_en FROM kb_conditions "
        "WHERE dimension = 'cultural' ORDER BY name_he"
    ).fetchall()
    name_field = "name_he" if LANG == "he" else "name_en"
    st.markdown(f"#### 🌍 {t('cultural_identities', LANG)}")
    current_cultural = _split(_pget("cultural_codes") or "")
    sel_cultural = st.multiselect(
        t("cultural_identities", LANG),
        options=[r["code"] for r in cultural_rows],
        format_func=lambda c, rr=cultural_rows: next(
            (f"{r[name_field]}" for r in rr if r["code"] == c), c
        ),
        default=current_cultural,
        label_visibility="collapsed",
    )

    st.markdown("---")

    # --- religion + observance ---
    st.markdown(f"#### 🛐 {t('religion_section', LANG)}")
    rcols = st.columns(2)
    current_religion = _pget("religion") or "none"
    if current_religion not in RELIGION_OPTIONS:
        current_religion = "none"
    new_religion = rcols[0].selectbox(
        t("religion", LANG),
        options=RELIGION_OPTIONS,
        index=RELIGION_OPTIONS.index(current_religion),
        format_func=lambda v: t(f"religion_{v}", LANG)
                              if t(f"religion_{v}", LANG) != f"religion_{v}" else v,
    )

    new_religiosity = "secular"
    if new_religion != "none":
        current_level = _pget("religiosity_level") or "observant"
        if current_level not in RELIGIOSITY_OPTIONS:
            current_level = "observant"
        new_religiosity = rcols[1].selectbox(
            t("religiosity_level", LANG),
            options=RELIGIOSITY_OPTIONS,
            index=RELIGIOSITY_OPTIONS.index(current_level),
            format_func=lambda v: t(f"religiosity_{v}", LANG)
                                  if t(f"religiosity_{v}", LANG) != f"religiosity_{v}" else v,
        )

    # --- live preview of derived tags ---
    rtags = religion_tags(new_religion, new_religiosity)
    if rtags["limitations"] or rtags["needs"]:
        st.markdown(f"#### 📋 {t('religion_preview', LANG)}")
        pcols = st.columns(2)
        with pcols[0]:
            st.markdown(f"**🚫 {t('religion_limitations_label', LANG)}**")
            if rtags["limitations"]:
                for lim in rtags["limitations"]:
                    st.markdown(
                        f"<span style='background:#fee2e2;color:#7f1d1d;"
                        f"padding:3px 9px;border-radius:6px;margin-left:4px;"
                        f"display:inline-block;margin-bottom:4px;'>"
                        f"{lim}</span>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption(t("religion_no_limits", LANG))
        with pcols[1]:
            st.markdown(f"**✨ {t('religion_needs_label', LANG)}**")
            if rtags["needs"]:
                for need in rtags["needs"]:
                    st.markdown(
                        f"<span style='background:#d1fae5;color:#065f46;"
                        f"padding:3px 9px;border-radius:6px;margin-left:4px;"
                        f"display:inline-block;margin-bottom:4px;'>"
                        f"{need}</span>",
                        unsafe_allow_html=True,
                    )

    st.markdown("---")
    if st.button("💾 " + t("save", LANG), type="primary", key="save_culture"):
        cur = conn.cursor()
        cur.execute("""
            UPDATE elder_profile SET
              cultural_codes = ?,
              religion = ?,
              religiosity_level = ?,
              updated_at = CURRENT_TIMESTAMP
            WHERE elder_id = ?
        """, (
            _join(sel_cultural),
            new_religion,
            new_religiosity if new_religion != "none" else None,
            elder_id,
        ))
        conn.commit()
        st.success(t("saved_ok", LANG))
        st.rerun()


# ---------- EXTERNAL PROGRAMS TAB ----------
DAY_KEY_TO_LABEL = {
    "sun": "א", "mon": "ב", "tue": "ג", "wed": "ד",
    "thu": "ה", "fri": "ו", "sat": "ש",
}


def _render_external_tab(conn, elder_id, LANG):
    enrolled_ids = {
        r["program_id"] for r in conn.execute(
            "SELECT program_id FROM elder_program_enrollment WHERE elder_id = ?",
            (elder_id,),
        ).fetchall()
    }
    programs = conn.execute("""
        SELECT * FROM external_programs
        WHERE source_kind IN ('assisted_living', 'city')
        ORDER BY source_kind, name
    """).fetchall()

    by_source = {"assisted_living": [], "city": []}
    for p in programs:
        by_source.setdefault(p["source_kind"], []).append(p)

    titles = {
        "he": {"assisted_living": "🏠 פעילויות הדיור המוגן",
               "city": "🏛️ פעילויות העירייה"},
        "en": {"assisted_living": "🏠 Assisted-Living Programs",
               "city": "🏛️ City Programs"},
        "ru": {"assisted_living": "🏠 Программы пансионата",
               "city": "🏛️ Городские программы"},
    }[LANG]

    for source, progs in by_source.items():
        if not progs:
            continue
        org_name = progs[0]["organization"] or ""
        st.markdown(f"### {titles[source]} — {org_name}")

        for p in progs:
            enrolled = p["id"] in enrolled_ids
            day_chips = " ".join(
                f'<span style="background:#e0f2fe;color:#0c4a6e;padding:2px 8px;'
                f'border-radius:6px;margin-left:3px;font-size:0.85rem;">'
                f"{DAY_KEY_TO_LABEL[d.strip()]}</span>"
                for d in (p["recurring_days"] or "").split(";")
                if d.strip() in DAY_KEY_TO_LABEL
            )
            with st.container(border=True):
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(
                        f"**{'✅ ' if enrolled else ''}{p['name']}**  "
                        f"<span style='color:#6b7280'>· {p['category']}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"🕐 {p['start_time']} · ⏱️ {p['duration_min']} דק'  "
                        f"&nbsp; {day_chips}",
                        unsafe_allow_html=True,
                    )
                    if p["address"]:
                        st.caption(f"📍 {p['address']}")
                    if p["contact"]:
                        st.caption(f"📞 {p['contact']}")
                    if p["notes"]:
                        st.caption(f"📝 {p['notes']}")
                with cols[1]:
                    if enrolled:
                        if st.button("❌ הסר הרשמה", key=f"unenroll_{p['id']}",
                                     width="stretch"):
                            conn.execute(
                                "DELETE FROM elder_program_enrollment "
                                "WHERE elder_id = ? AND program_id = ?",
                                (elder_id, p["id"]),
                            )
                            conn.commit()
                            st.rerun()
                    else:
                        if st.button("➕ הרשם", key=f"enroll_{p['id']}",
                                     type="primary", width="stretch"):
                            conn.execute(
                                "INSERT OR IGNORE INTO elder_program_enrollment "
                                "(elder_id, program_id) VALUES (?, ?)",
                                (elder_id, p["id"]),
                            )
                            conn.commit()
                            st.rerun()

                    with st.popover("📅 הוסף ליום",
                                    width="stretch"):
                        chosen_date = st.date_input(
                            "תאריך", value=dt.date.today(),
                            key=f"add_date_{p['id']}",
                        )
                        if st.button("➕ הוסף", key=f"do_add_{p['id']}",
                                     type="primary"):
                            time_slot = _infer_slot_from_time(p["start_time"] or "")
                            ok = _add_item_to_plan(
                                conn, elder_id, chosen_date.isoformat(),
                                activity_code=f"EXT_{p['id']}",
                                time_slot=time_slot,
                                start_time=p["start_time"] or "10:00",
                                duration_min=int(p["duration_min"] or 60),
                                rationale=f"🏛️ {p['organization']}: {p['name']}",
                            )
                            if ok:
                                st.success(f"נוסף ל-{chosen_date.isoformat()}")
                            else:
                                st.info("כבר קיים בתוכנית")
                            st.rerun()


# ---------- DAILY PLAN TAB ----------
def _render_daily_plan_tab(conn, elder_id, LANG):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        plan_date = st.date_input(
            t("plan_for_date", LANG),
            value=dt.date.today(),
            key="plan_date",
        )
    plan_date_iso = plan_date.isoformat()

    plan = conn.execute(
        "SELECT * FROM daily_plans WHERE elder_id = ? AND plan_date = ?",
        (elder_id, plan_date_iso),
    ).fetchone()

    with c2:
        if st.button("✨ " + t("generate_plan", LANG), type="primary", width="stretch"):
            try:
                result = generate_plan_for_elder(elder_id, plan_date_iso)
                st.success(
                    f"{t('plan_generated', LANG)} - "
                    f"{len(result['items'])} {t('activities_count', LANG)}"
                )
                st.rerun()
            except Exception as e:
                import traceback as _tb
                st.error(t("error_generic", LANG) + str(e))
                with st.expander("פרטי שגיאה (טכני)"):
                    st.code(_tb.format_exc())
    with c3:
        if plan and st.button("🔄 " + t("regenerate", LANG), width="stretch"):
            try:
                generate_plan_for_elder(elder_id, plan_date_iso)
                st.rerun()
            except Exception as e:
                import traceback as _tb
                st.error(t("error_generic", LANG) + str(e))
                with st.expander("פרטי שגיאה (טכני)"):
                    st.code(_tb.format_exc())

    # manual add picker — visible whether a plan exists or not
    with st.expander("➕ הוסף פעילות ידנית"):
        src = st.radio(
            "מקור",
            options=["activities", "exercises", "external"],
            format_func=lambda s: {
                "activities": "📚 מבנק פעילויות",
                "exercises": "🏃 מבנק תרגילים",
                "external": "🏛️ מתוכניות חיצוניות",
            }[s],
            horizontal=True,
            key=f"manual_src_{plan_date_iso}",
        )
        if src == "activities":
            rows = conn.execute(
                "SELECT code, name_he, name_en, duration_min "
                "FROM kb_activities ORDER BY name_he LIMIT 500"
            ).fetchall()
        elif src == "exercises":
            rows = conn.execute(
                "SELECT code, name_he, name_en, duration_min "
                "FROM kb_exercises ORDER BY name_he LIMIT 500"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT 'EXT_' || id AS code, name AS name_he, "
                "name AS name_en, duration_min "
                "FROM external_programs ORDER BY name"
            ).fetchall()

        name_field = "name_he" if LANG == "he" else "name_en"
        chosen_code = st.selectbox(
            "פעילות",
            options=[r["code"] for r in rows],
            format_func=lambda c, rr=rows: next(
                (f"{r[name_field]} ({r['code']})" for r in rr if r["code"] == c), c
            ),
            key=f"manual_pick_{plan_date_iso}",
        )
        mcols = st.columns([2, 2, 2, 1])
        slot_choice = mcols[0].selectbox(
            "חלון זמן",
            options=["morning", "noon", "afternoon", "evening"],
            format_func=lambda s: t(f"time_{s}", LANG),
            key=f"manual_slot_{plan_date_iso}",
        )
        time_input = mcols[1].text_input(
            "שעה (HH:MM)", value={"morning": "10:00", "noon": "12:30",
                                  "afternoon": "16:00", "evening": "19:00"}[slot_choice],
            key=f"manual_time_{plan_date_iso}",
        )
        chosen_row = next((r for r in rows if r["code"] == chosen_code), None)
        # sqlite3.Row doesn't support .get() — read by key with a try/except
        default_dur = 30
        if chosen_row is not None:
            try:
                default_dur = int(chosen_row["duration_min"] or 30)
            except (KeyError, IndexError, TypeError, ValueError):
                default_dur = 30
        manual_dur = mcols[2].number_input(
            "משך (דק')", min_value=5, max_value=180,
            value=default_dur,
            key=f"manual_dur_{plan_date_iso}",
        )
        if mcols[3].button("➕ הוסף", type="primary",
                           key=f"manual_add_{plan_date_iso}"):
            try:
                chosen_name = chosen_row[name_field] if chosen_row else chosen_code
            except (KeyError, IndexError):
                chosen_name = chosen_code
            chosen_name = chosen_name or ""
            ok = _add_item_to_plan(
                conn, elder_id, plan_date_iso,
                activity_code=chosen_code,
                time_slot=slot_choice,
                start_time=time_input,
                duration_min=int(manual_dur),
                rationale=f"➕ הוסף ידנית: {chosen_name}",
            )
            if ok:
                st.success("נוסף לתוכנית")
            else:
                st.info("כבר קיים בתוכנית")
            st.rerun()

    if not plan:
        st.info(t("no_plan_today", LANG))
        return

    items = conn.execute("""
        SELECT pi.*,
               COALESCE(ka.name_he, ke.name_he,
                        ep.name,
                        CASE pi.activity_code
                          WHEN 'MEAL_BREAKFAST' THEN 'ארוחת בוקר'
                          WHEN 'MEAL_LUNCH'     THEN 'ארוחת צהריים'
                          WHEN 'MEAL_DINNER'    THEN 'ארוחת ערב'
                        END,
                        SUBSTR(pi.activity_code, 5)) AS name_he,
               COALESCE(ka.name_en, ke.name_en,
                        ep.name,
                        CASE pi.activity_code
                          WHEN 'MEAL_BREAKFAST' THEN 'Breakfast'
                          WHEN 'MEAL_LUNCH'     THEN 'Lunch'
                          WHEN 'MEAL_DINNER'    THEN 'Dinner'
                        END,
                        SUBSTR(pi.activity_code, 5)) AS name_en,
               COALESCE(ka.description_he, ke.description_he,
                        ep.notes, '') AS description_he,
               CASE
                 WHEN pi.activity_code LIKE 'MEAL_%' THEN 'meal'
                 WHEN ka.code IS NOT NULL THEN ka.category
                 WHEN ke.code IS NOT NULL THEN 'sport'
                 WHEN ep.id IS NOT NULL  THEN 'external'
                 WHEN pi.activity_code LIKE 'HOL_%' THEN 'holiday'
                 ELSE 'general'
               END AS category
        FROM plan_items pi
        LEFT JOIN kb_activities ka ON ka.code = pi.activity_code
        LEFT JOIN kb_exercises  ke ON ke.code = pi.activity_code
        LEFT JOIN external_programs ep
               ON ('EXT_' || ep.id) = pi.activity_code
        WHERE pi.plan_id = ?
        ORDER BY CASE pi.time_slot
            WHEN 'morning' THEN 1 WHEN 'noon' THEN 2
            WHEN 'afternoon' THEN 3 WHEN 'evening' THEN 4 ELSE 5 END,
            pi.start_time
    """, (plan["id"],)).fetchall()

    if not items:
        st.warning("האופטימייזר לא הצליח לבחור פעילויות לפרופיל הנוכחי - בדוק שיש לדייר/ת לפחות אבחנה אחת בפרופיל.")
        return

    done_count = sum(1 for i in items if i["executed"])
    mcols = st.columns(3)
    mcols[0].metric(t("activities_count", LANG), len(items))
    mcols[1].metric(t("completed_count", LANG), done_count)
    mcols[2].metric(t("obj_score", LANG), f"{plan['objective_score']:.1f}")

    name_field = "name_he" if LANG == "he" else "name_en"
    current_slot = None
    for it in items:
        if it["time_slot"] != current_slot:
            current_slot = it["time_slot"]
            st.markdown(f"### 🕐 {t(f'time_{current_slot}', LANG)}")

        category = it["category"] or "general"
        c = styling.category_color(category)
        cat_label = t(f"cat_{category}", LANG)
        if cat_label == f"cat_{category}":
            cat_label = category

        with st.container(border=True):
            cols = st.columns([3, 1, 1])
            with cols[0]:
                title = it[name_field] or it["activity_code"]
                done_marker = "✅ " if it["executed"] else ""
                st.markdown(
                    f"<div style='border-right:4px solid {c['border']};padding-right:10px;'>"
                    f"<strong style='color:{c['text']};font-size:1.05rem;'>{done_marker}"
                    f"🕐 {it['start_time']} - {title}</strong></div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    styling.render_category_pill(category, cat_label) +
                    f" <span style='color:#6b7280;font-size:0.85rem;'>⏱️ {it['duration_min']} {t('duration_min', LANG)} | 🎯 {it['rationale'] or '-'}</span>",
                    unsafe_allow_html=True,
                )
                if it["description_he"]:
                    st.caption(it["description_he"])
                if it["execution_notes"]:
                    st.info(f"📝 {it['execution_notes']}")
                if it["skipped_reason"]:
                    st.warning(f"⚠️ {t('skip_reason', LANG)}: {t(it['skipped_reason'], LANG)}")
            with cols[1]:
                if not it["executed"]:
                    if st.button("✅ " + t("mark_done", LANG), key=f"done_{it['id']}", width="stretch"):
                        conn.execute(
                            "UPDATE plan_items SET executed=1, executed_at=CURRENT_TIMESTAMP WHERE id=?",
                            (it["id"],),
                        )
                        conn.commit()
                        st.rerun()
            with cols[2]:
                if not it["executed"]:
                    with st.popover("❌ " + t("mark_skipped", LANG), width="stretch"):
                        reason = st.selectbox(
                            t("skip_reason", LANG),
                            options=["refused", "unavailable", "weather", "other"],
                            format_func=lambda r: t(r, LANG),
                            key=f"reason_sel_{it['id']}",
                        )
                        note = st.text_input(t("execution_notes", LANG), key=f"note_{it['id']}")
                        if st.button(t("save", LANG), key=f"skip_save_{it['id']}"):
                            conn.execute(
                                "UPDATE plan_items SET skipped_reason=?, execution_notes=? WHERE id=?",
                                (reason, note, it["id"]),
                            )
                            conn.commit()
                            st.rerun()


# ---------- WEEKLY PLAN TAB ----------
def _render_weekly_plan_tab(conn, elder_id, LANG):
    week_start = st.session_state.week_start

    # week navigator
    ncols = st.columns([1, 3, 1, 1])
    with ncols[0]:
        if st.button("← " + t("prev_week", LANG), width="stretch", key="prev_wk"):
            st.session_state.week_start = week_start - dt.timedelta(days=7)
            st.rerun()
    with ncols[1]:
        end = week_start + dt.timedelta(days=6)
        st.markdown(
            f"### 🗓️ {t('week_range', LANG)} {hebrew_date(week_start)} – {hebrew_date(end)}"
        )
    with ncols[2]:
        if st.button(t("current_week", LANG), width="stretch", key="this_wk"):
            st.session_state.week_start = week_start_sunday(dt.date.today())
            st.rerun()
    with ncols[3]:
        if st.button(t("next_week", LANG) + " →", width="stretch", key="next_wk"):
            st.session_state.week_start = week_start + dt.timedelta(days=7)
            st.rerun()

    if st.button("✨ " + t("generate_weekly", LANG), type="primary", key="gen_weekly"):
        with st.spinner(t("generating", LANG)):
            try:
                generate_weekly_plan_for_elder(elder_id, st.session_state.week_start)
                st.success(t("plan_generated", LANG))
                st.rerun()
            except Exception as e:
                import traceback as _tb
                st.error(t("error_generic", LANG) + str(e))
                with st.expander("פרטי שגיאה (טכני)"):
                    st.code(_tb.format_exc())

    name_field = "name_he" if LANG == "he" else "name_en"
    today_iso = dt.date.today().isoformat()

    # Render 7 day cards in 3 columns (one row of 3, one of 3, one of 1)
    for row_start in (0, 3, 6):
        row_cols = st.columns(3)
        for offset in range(3):
            idx = row_start + offset
            if idx >= 7:
                break
            current = st.session_state.week_start + dt.timedelta(days=idx)
            with row_cols[offset]:
                _render_day_card(conn, elder_id, current, idx, LANG, name_field, today_iso)


def _render_day_card(conn, elder_id, day_date, day_idx, LANG, name_field, today_iso):
    plan = conn.execute(
        "SELECT * FROM daily_plans WHERE elder_id = ? AND plan_date = ?",
        (elder_id, day_date.isoformat()),
    ).fetchone()
    items = []
    done = 0
    if plan:
        items = conn.execute("""
            SELECT pi.*,
                   COALESCE(ka.name_he, ke.name_he,
                            ep.name, SUBSTR(pi.activity_code, 5)) AS name_he,
                   COALESCE(ka.name_en, ke.name_en,
                            ep.name, SUBSTR(pi.activity_code, 5)) AS name_en,
                   CASE
                     WHEN ka.code IS NOT NULL THEN ka.category
                     WHEN ke.code IS NOT NULL THEN 'sport'
                     WHEN ep.id IS NOT NULL  THEN 'external'
                     WHEN pi.activity_code LIKE 'HOL_%' THEN 'holiday'
                     ELSE 'general'
                   END AS category
            FROM plan_items pi
            LEFT JOIN kb_activities ka ON ka.code = pi.activity_code
            LEFT JOIN kb_exercises  ke ON ke.code = pi.activity_code
            LEFT JOIN external_programs ep
                   ON ('EXT_' || ep.id) = pi.activity_code
            WHERE pi.plan_id = ?
            ORDER BY CASE pi.time_slot
                WHEN 'morning' THEN 1 WHEN 'noon' THEN 2
                WHEN 'afternoon' THEN 3 WHEN 'evening' THEN 4 ELSE 5 END,
                pi.start_time
        """, (plan["id"],)).fetchall()
        done = sum(1 for i in items if i["executed"])

    is_today = day_date.isoformat() == today_iso
    today_cls = " day-today" if is_today else ""
    day_name = t(HEBREW_DAYS[day_idx], LANG)
    date_str = hebrew_date(day_date)

    inner_items_html = ""
    for it in items:
        cat = it["category"] or "general"
        c = styling.category_color(cat)
        done_cls = " done" if it["executed"] else ""
        title = it[name_field] or it["activity_code"]
        inner_items_html += (
            f'<div class="activity-item{done_cls}" '
            f'style="border-right-color:{c["border"]};">'
            f'<span class="activity-time">{it["start_time"]}</span> '
            f'<span style="color:{c["text"]}">{c["icon"]}</span> '
            f'<span>{title}</span>'
            f'</div>'
        )
    if not items:
        inner_items_html = (
            f'<div style="color:#9ca3af;font-style:italic;font-size:0.85rem;">'
            f'{t("no_activities_day", LANG)}</div>'
        )

    st.markdown(
        f"""
        <div class="day-card{today_cls}">
          <div class="day-card-header">
            <div class="day-badge">
              <span class="day-number">{day_idx + 1}</span>
              <span>{day_name}</span>
              <span class="day-date">{date_str}</span>
            </div>
            <div class="day-stats">{done}/{len(items)} {t('completed_count', LANG)}</div>
          </div>
          {inner_items_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # action buttons per day (regenerate single day)
    bcol = st.columns([1, 1])
    with bcol[0]:
        if st.button("✨ " + t("generate", LANG),
                     key=f"day_gen_{day_date.isoformat()}", width="stretch"):
            try:
                generate_plan_for_elder(elder_id, day_date.isoformat())
                st.rerun()
            except Exception as e:
                st.error(str(e))
    with bcol[1]:
        if plan and st.button("📝 " + t("nav_daily_plan", LANG),
                              key=f"day_open_{day_date.isoformat()}", width="stretch"):
            st.session_state.plan_date = day_date
            st.toast(f"Open Daily Plan tab to manage {day_date.isoformat()}")


# ---------- MEASUREMENTS TAB ----------
# Assessment tests. Based on the day-center measurement tool (Prof. Sharon Barak)
# plus the classic geriatric tests. Each: code, Hebrew name, max_score (or None),
# interpretation note.
MEASUREMENT_TESTS = [
    ("MMSE",    "MMSE - מבחן קוגניציה", 30,
     "0-30 · ציון גבוה = טוב יותר · <24 חשד לירידה קוגניטיבית"),
    ("AD8",     "AD8 - זיכרון וריכוז (8 שאלות)", 8,
     "0-8 · ציון גבוה = יותר ירידה · ≥2 חשד לדמנציה"),
    ("PHQ2",    "PHQ-2 - דיכאון והנאה", 6,
     "0-6 · ≥3 יתכן דיכאון, צורך בהערכה נוספת"),
    ("FRAILTY", "שבריריות - מודל Fried", 5,
     "0=איתן · 1-2=טרום-שברירי · 3-5=שברירי"),
    ("BARTHEL", "אינדקס ברתל - תפקוד יומיום", 100,
     "0-100 · ציון גבוה = עצמאי יותר"),
    ("TUG",     "מבדק קום ולך (TUG) - שניות", None,
     "שניות · נמוך = טוב יותר · ≥12 שנ' סיכון נפילה"),
    ("STS5",    "קימה מישיבה 5 פעמים - שניות", None,
     "שניות · נמוך = טוב יותר · ≥15 שנ' חולשת שרירים"),
    ("GAIT4M",  "מהירות הליכה 4 מטר - מ'/שנייה", None,
     "מ'/שנייה · גבוה = טוב יותר · <0.8 הליכה איטית"),
    ("GRIP",    "כוח אחיזה - ק\"ג", None,
     "ק\"ג · גבוה = טוב יותר (כוח שרירים)"),
    ("MOOD",    "מצב רוח", 10,
     "1-10 · גבוה = טוב יותר"),
    ("PAIN",    "כאב", 10,
     "0-10 · נמוך = טוב יותר"),
]


def _render_measurements_tab(conn, elder_id, LANG):
    tests = MEASUREMENT_TESTS
    name_of = {c: nm for c, nm, _, _ in tests}
    max_of = {c: mx for c, _, mx, _ in tests}
    note_of = {c: note for c, _, _, note in tests}

    with st.form("add_measurement"):
        cols = st.columns([3, 2, 2, 1])
        code = cols[0].selectbox(
            t("measurement_test", LANG),
            options=[c for c, _, _, _ in tests],
            format_func=lambda c: name_of[c],
        )
        score = cols[1].number_input(t("measurement_score", LANG), value=0.0, step=0.5)
        mdate = cols[2].date_input(t("measurement_date", LANG), value=dt.date.today())
        submitted = cols[3].form_submit_button("➕ " + t("add_measurement", LANG))
        st.caption("ℹ️ " + note_of.get(code, ""))
        if submitted:
            conn.execute(
                "INSERT INTO measurements (elder_id, measurement_date, test_code, score, max_score) "
                "VALUES (?, ?, ?, ?, ?)",
                (elder_id, mdate.isoformat(), code, score, max_of.get(code)),
            )
            conn.commit()
            st.rerun()

    rows = conn.execute(
        "SELECT * FROM measurements WHERE elder_id = ? ORDER BY measurement_date DESC LIMIT 300",
        (elder_id,),
    ).fetchall()
    if not rows:
        st.info("אין עדיין מדידות. הוסף מדידה ראשונה למעלה.")
        return

    df = pd.DataFrame([dict(r) for r in rows])
    df["מבחן"] = df["test_code"].map(lambda c: name_of.get(c, c))
    st.dataframe(
        df[["measurement_date", "מבחן", "score", "max_score", "notes"]].rename(
            columns={"measurement_date": "תאריך", "score": "ציון",
                     "max_score": "מקסימום", "notes": "הערות"}),
        width="stretch", hide_index=True,
    )

    # trend per test
    for test_code in df["test_code"].unique():
        sub = df[df["test_code"] == test_code].sort_values("measurement_date")
        if len(sub) >= 2:
            st.markdown(f"#### {name_of.get(test_code, test_code)}")
            st.caption("ℹ️ " + note_of.get(test_code, ""))
            st.line_chart(sub.set_index("measurement_date")["score"], height=200)


# ---------- IMPORT TAB ----------
def _render_import_tab(conn, elder_id, LANG):
    st.info(t("import_help", LANG))
    upload = st.file_uploader(
        t("import", LANG),
        type=["pdf", "docx", "xlsx", "xls", "txt"],
    )
    if upload is None:
        return
    text = file_import.extract_text(upload.name, upload.read())
    with st.expander("📄 " + upload.name):
        st.text_area("", text[:5000], height=200, label_visibility="collapsed")

    matches = file_import.match_codes_in_text(text, conn)
    cols = st.columns(3)
    name_field = "name_he" if LANG == "he" else "name_en"

    apply_buckets = {"diseases": [], "medications": [], "conditions": []}
    for col, key, label_key in [
        (cols[0], "diseases", "diseases_codes"),
        (cols[1], "medications", "medications_codes"),
        (cols[2], "conditions", "conditions_codes"),
    ]:
        with col:
            st.markdown(f"**{t(label_key, LANG)}** ({len(matches[key])})")
            for m in matches[key]:
                if st.checkbox(
                    f"{m[name_field]} ({m['code']})",
                    key=f"imp_{key}_{m['code']}",
                    value=True,
                ):
                    apply_buckets[key].append(m["code"])

    if st.button("➕ " + t("save", LANG), type="primary"):
        profile = conn.execute(
            "SELECT * FROM elder_profile WHERE elder_id = ?", (elder_id,)
        ).fetchone()
        existing_medical = set(_split(profile["medical_codes"]))
        existing_meds = set(_split(profile["medication_codes"]))
        new_medical = sorted(existing_medical | set(apply_buckets["diseases"]))
        new_meds = sorted(existing_meds | set(apply_buckets["medications"]))

        cond_codes = apply_buckets["conditions"]
        dim_updates = {}
        if cond_codes:
            placeholders = ",".join("?" * len(cond_codes))
            rows = conn.execute(
                f"SELECT code, dimension FROM kb_conditions WHERE code IN ({placeholders})",
                cond_codes,
            ).fetchall()
            for r in rows:
                dim_updates.setdefault(r["dimension"], []).append(r["code"])

        dim_field = {
            "nursing": "nursing_codes", "cognitive": "cognitive_codes",
            "mental": "mental_codes", "social": "social_codes",
            "family": "family_codes", "demographic": "demographic_codes",
        }
        cur = conn.cursor()
        cur.execute(
            "UPDATE elder_profile SET medical_codes = ?, medication_codes = ? WHERE elder_id = ?",
            (_join(new_medical), _join(new_meds), elder_id),
        )
        for dim, codes in dim_updates.items():
            field = dim_field.get(dim)
            if not field:
                continue
            existing = set(_split(profile[field]))
            merged = sorted(existing | set(codes))
            cur.execute(
                f"UPDATE elder_profile SET {field} = ? WHERE elder_id = ?",
                (_join(merged), elder_id),
            )
        conn.commit()
        st.success(t("saved_ok", LANG))


# =====================================================================
# MANAGER VIEW
# =====================================================================
def _goal_achievement(conn, elder_id: int, days_back: int = 30) -> list[dict]:
    """For each active care goal, what fraction of the scheduled activities that
    advance it (share a target tag) were actually executed. Returns a list of
    {goal, priority, planned, done, pct}."""
    from models import goals as goals_mod
    goals = goals_mod.load_goals(conn, elder_id, active_only=True)
    if not goals:
        return []
    cutoff = (dt.date.today() - dt.timedelta(days=days_back)).isoformat()
    rows = conn.execute("""
        SELECT pi.executed AS executed,
               COALESCE(ka.strengthens, ke.strengthens, ep.strengthens, '') AS tags
        FROM plan_items pi JOIN daily_plans dp ON dp.id = pi.plan_id
        LEFT JOIN kb_activities ka ON ka.code = pi.activity_code
        LEFT JOIN kb_exercises  ke ON ke.code = pi.activity_code
        LEFT JOIN external_programs ep ON ('EXT_' || ep.id) = pi.activity_code
        WHERE dp.elder_id = ? AND dp.plan_date >= ?
          AND pi.activity_code NOT LIKE 'MEAL_%'
    """, (elder_id, cutoff)).fetchall()

    def _tags(s):
        return {t.strip() for t in (s or "").replace(",", ";").split(";") if t.strip()}

    items = [(r["executed"], _tags(r["tags"])) for r in rows]
    out = []
    for g in goals:
        gtags = _tags(g["target_tags"])
        planned = [(ex, tg) for ex, tg in items if tg & gtags]
        n = len(planned)
        done = sum(1 for ex, _ in planned if ex)
        out.append({
            "goal": g["goal_text"], "priority": int(g["priority"]),
            "planned": n, "done": done,
            "pct": (done / n * 100) if n else None,
        })
    return out


def _generate_facility_weekly(conn):
    """Build ONE weekly GROUP-activities board for the whole institution, chosen
    to give the best combined coverage of every resident's needs + care goals.

    Greedy weighted set-cover: each slot picks the group activity that serves the
    most *under-served* residents (a resident already scheduled this week counts
    for less), so coverage spreads across everyone rather than piling onto the
    same few. Returns (board, resident_cover)."""
    from models.optimizer import load_elder_context
    from models import goals as goals_mod

    elders = conn.execute(
        "SELECT id, full_name FROM elders WHERE active = 1 ORDER BY full_name"
    ).fetchall()
    residents = []
    for e in elders:
        try:
            ctx = load_elder_context(conn, e["id"])
        except Exception:
            continue
        gtags = set()
        for g in goals_mod.load_goals(conn, e["id"], active_only=True):
            for tg in (g.get("target_tags") or "").replace(",", ";").split(";"):
                tg = tg.strip()
                if tg:
                    gtags.add(tg)
        residents.append({
            "id": e["id"], "name": e["full_name"],
            "cap": int(getattr(ctx, "capability_level", 3) or 3),
            "tags": (set(ctx.needs) | gtags) - {""},
        })
    if not residents:
        return [], []

    # candidate GROUP activities — dedup by base family, keep group-friendly ones
    rows = conn.execute(
        "SELECT code, name_he, category, strengthens, min_capability_level, "
        "group_size_max, duration_min FROM kb_activities WHERE group_size_max >= 6"
    ).fetchall()
    seen_fam, candidates = set(), []
    for a in rows:
        fam = (a["name_he"] or "").split(" - ")[0].strip()
        if fam in seen_fam:
            continue
        seen_fam.add(fam)
        tags = set((a["strengthens"] or "").replace(",", ";").split(";")) - {""}
        if not tags:
            continue
        candidates.append({
            "name": a["name_he"] or a["code"], "family": fam,
            "category": a["category"] or "general", "tags": tags,
            "min_cap": int(a["min_capability_level"] or 1),
            "dur": int(a["duration_min"] or 45),
        })

    today = dt.date.today()
    week_start = today - dt.timedelta(days=(today.weekday() + 1) % 7)
    DAY_NAMES = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    WEEK_SLOTS = [("בוקר", "09:00", "morning"), ("צהריים", "11:00", "cognitive"),
                  ("אחר הצהריים", "16:30", "social")]
    FRI_SLOTS = [("בוקר", "10:00", "morning")]
    SAT_SLOTS = [("אחר הצהריים", "16:30", "social")]

    def _slot_bonus(cat, kind):
        return {
            ("physical", "morning"): 1.0, ("cognitive", "cognitive"): 1.0,
            ("social", "social"): 1.0, ("mental", "social"): 0.6,
            ("cognitive", "morning"): 0.3, ("social", "cognitive"): 0.3,
        }.get((cat, kind), 0.0)

    cover = {r["id"]: 0 for r in residents}
    fam_used, board = {}, []

    for di in range(7):
        d = week_start + dt.timedelta(days=di)
        wd = d.weekday()
        slots = FRI_SLOTS if wd == 4 else (SAT_SLOTS if wd == 5 else WEEK_SLOTS)
        day_entry = {"name": DAY_NAMES[di], "date": d.isoformat(), "sessions": []}
        used_cat_today = set()
        for label, tm, kind in slots:
            best, best_score, best_served = None, -1.0, []
            for c in candidates:
                if fam_used.get(c["family"], 0) >= 2:
                    continue
                if c["category"] in used_cat_today:
                    continue
                served = [r for r in residents
                          if r["cap"] >= c["min_cap"] and (r["tags"] & c["tags"])]
                if not served:
                    continue
                score = sum(1.0 / (1 + cover[r["id"]]) for r in served)
                score += _slot_bonus(c["category"], kind)
                if score > best_score:
                    best, best_score, best_served = c, score, served
            if best is None:
                continue
            for r in best_served:
                cover[r["id"]] += 1
            fam_used[best["family"]] = fam_used.get(best["family"], 0) + 1
            used_cat_today.add(best["category"])
            day_entry["sessions"].append({
                "time": tm, "label": label, "name": best["name"],
                "category": best["category"], "served": len(best_served),
                "served_names": [r["name"] for r in best_served],
            })
        board.append(day_entry)

    resident_cover = sorted(
        [{"name": r["name"], "count": cover[r["id"]]} for r in residents],
        key=lambda x: x["count"],
    )
    return board, resident_cover


def view_manager(LANG: str):
    conn = get_connection()
    st.markdown(f"# 📊 {t('nav_admin', LANG)}")

    elders = _list_elders(conn)

    # ---- RESIDENT DIRECTORY: click a name → open that resident's page ----
    st.markdown(f"### 👥 {t('manager_directory', LANG)}")
    st.caption(t("manager_open_resident", LANG))
    cutoff30 = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    dir_cols = st.columns(3)
    for i, e in enumerate(elders):
        # quick participation rate for the badge
        row = conn.execute("""
            SELECT COUNT(*) AS sched,
                   COALESCE(SUM(CASE WHEN pi.executed=1 THEN 1 ELSE 0 END),0) AS done
            FROM plan_items pi JOIN daily_plans dp ON dp.id = pi.plan_id
            WHERE dp.elder_id = ? AND dp.plan_date >= ?
              AND pi.activity_code NOT LIKE 'MEAL_%'
        """, (e["id"], cutoff30)).fetchone()
        sched, doned = row["sched"], row["done"]
        rate = (doned / sched * 100) if sched else 0
        with dir_cols[i % 3]:
            if st.button(
                f"🧓 {e['full_name']}  ·  {rate:.0f}%",
                key=f"dir_{e['id']}", width="stretch",
                help=f"חדר {e['room_number'] or '-'}",
            ):
                st.session_state.elder_id = e["id"]
                st.session_state.view = "caregiver"
                st.rerun()

    st.markdown("---")

    # ---- GOAL ACHIEVEMENT per resident ----------------------------------
    st.markdown("### 🎯 מידת השגת יעדי הטיפול")
    st.caption("לכל יעד: אחוז הפעילויות שמקדמות אותו שבוצעו בפועל (30 יום)")
    ga_elder = st.selectbox(
        t("select_elder", LANG),
        options=[e["id"] for e in elders] if elders else [],
        format_func=lambda i: next(e["full_name"] for e in elders if e["id"] == i),
        key="ga_elder_picker",
    ) if elders else None
    if ga_elder:
        ach = _goal_achievement(conn, ga_elder, 30)
        if not ach:
            st.info("לדייר/ת זה אין עדיין יעדים. צור יעדים בלשונית 🎯 יעדי תוכנית הטיפול.")
        else:
            # overall (priority-weighted) achievement
            wsum = sum(g["priority"] for g in ach if g["pct"] is not None)
            wach = sum(g["priority"] * g["pct"] for g in ach if g["pct"] is not None)
            overall = (wach / wsum) if wsum else 0
            st.metric("מדד השגה כולל (משוקלל לפי עדיפות)", f"{overall:.0f}%")
            for g in ach:
                stars = "⭐" * g["priority"]
                if g["pct"] is None:
                    st.markdown(f"**{g['goal']}** {stars}")
                    st.caption("אין עדיין פעילויות מתוזמנות שמקדמות יעד זה")
                else:
                    st.markdown(
                        f"**{g['goal']}** {stars} — "
                        f"{g['done']}/{g['planned']} בוצעו ({g['pct']:.0f}%)")
                    st.progress(min(1.0, g["pct"] / 100))

    st.markdown("---")

    # ---- bulk regenerate plans -----------------------------------------
    with st.expander("🔄 צור תוכניות לכל הדיירים (לכל ימי השבוע)"):
        st.caption("מפעיל את האופטימייזר עבור כל דייר/ת לכל יום בשבוע הנוכחי")
        if st.button("✨ צור תוכניות עכשיו", type="primary", key="bulk_regen"):
            import datetime as _dt
            import traceback as _tb
            from models.optimizer import generate_plan_for_elder as _gen
            today = _dt.date.today()
            week_start = today - _dt.timedelta(days=(today.weekday() + 1) % 7)
            ok_count = 0
            fail_count = 0
            errors = []
            progress = st.progress(0.0, text="מתחיל...")
            total = len(elders) * 7
            done = 0
            for e in elders:
                for i in range(7):
                    plan_date = (week_start + _dt.timedelta(days=i)).isoformat()
                    done += 1
                    progress.progress(
                        done / total,
                        text=f"{e['full_name']} · {plan_date}",
                    )
                    try:
                        res = _gen(e["id"], plan_date)
                        ok_count += 1
                    except Exception as ex:
                        fail_count += 1
                        errors.append(
                            f"{e['full_name']} {plan_date}: "
                            f"{type(ex).__name__}: {ex}"
                        )
            progress.empty()
            st.success(f"✅ הצליח: {ok_count} תוכניות   ❌ נכשל: {fail_count}")
            if errors:
                with st.expander("🐛 פרטי השגיאות"):
                    for err in errors[:20]:
                        st.code(err)

    # ---- FACILITY-WIDE WEEKLY GROUP-ACTIVITIES BOARD --------------------
    st.markdown("---")
    st.markdown("### 🗓️ לוח פעילויות קבוצתיות שבועי למוסד")
    st.caption("לוח שבועי אחד לכל המוסד, שנבנה לתת את המענה הקבוצתי המיטבי "
               "לצרכים וליעדי הטיפול של כלל הדיירים. לכל פעילות מוצג כמה דיירים "
               "היא משרתת, וכיסוי המפגשים מתחלק באופן הוגן בין הדיירים.")
    if st.button("✨ צור לוח קבוצתי שבועי מיטבי", type="primary",
                 key="gen_facility_weekly"):
        with st.spinner("בונה לוח שבועי לכלל הדיירים..."):
            fb, fc = _generate_facility_weekly(conn)
            st.session_state["facility_board"] = fb
            st.session_state["facility_cover"] = fc

    fb = st.session_state.get("facility_board")
    if fb:
        fc = st.session_state.get("facility_cover", [])
        if fc:
            counts = [r["count"] for r in fc]
            mcol = st.columns(3)
            mcol[0].metric("ממוצע מפגשים לדייר/ת בשבוע",
                           f"{sum(counts) / len(counts):.1f}")
            mcol[1].metric("מינימום לדייר/ת", min(counts))
            mcol[2].metric("מקסימום לדייר/ת", max(counts))
        CAT_HE = {"physical": "🏃 גופני", "cognitive": "🧠 קוגניטיבי",
                  "social": "👥 חברתי", "mental": "🌿 רגשי", "general": "📌 כללי"}
        for day in fb:
            if not day["sessions"]:
                continue
            st.markdown(f"**📆 יום {day['name']}**  ·  {day['date']}")
            for s in day["sessions"]:
                catlab = CAT_HE.get(s["category"], s["category"])
                names = "، ".join(s["served_names"][:14])
                more = (f" +{len(s['served_names']) - 14}"
                        if len(s["served_names"]) > 14 else "")
                st.markdown(
                    f"<div style='padding:0.5rem 0.9rem;background:#fff;"
                    f"border:1px solid #e5e9f2;border-radius:10px;"
                    f"margin-bottom:0.4rem;'>"
                    f"<b>{s['time']}</b> · <b>{s['name']}</b> "
                    f"<span style='color:#4338ca;'>({s['label']} · {catlab})</span> "
                    f"<span style='background:#dcfce7;color:#166534;"
                    f"border-radius:999px;padding:0.1rem 0.6rem;font-weight:700;'>"
                    f"👥 {s['served']} דיירים</span>"
                    f"<div style='color:#6b7280;font-size:0.85rem;"
                    f"margin-top:0.2rem;'>{names}{more}</div></div>",
                    unsafe_allow_html=True,
                )
        with st.expander("👥 כיסוי לפי דייר/ת (מס' מפגשים קבוצתיים בשבוע)"):
            st.dataframe(
                pd.DataFrame(fc).rename(columns={
                    "name": "דייר/ת", "count": "מפגשים קבוצתיים בשבוע"}),
                hide_index=True, width="stretch",
            )

    st.markdown("---")
    days_back = st.slider(t("report_period_days", LANG), 1, 90, 14)
    cutoff = (dt.date.today() - dt.timedelta(days=days_back)).isoformat()

    cols = st.columns(4)
    cols[0].metric("👥 Elders", len(elders))

    items_total = conn.execute("""
        SELECT COUNT(*) FROM plan_items pi
        JOIN daily_plans dp ON dp.id = pi.plan_id
        WHERE dp.plan_date >= ?
    """, (cutoff,)).fetchone()[0]
    items_done = conn.execute("""
        SELECT COUNT(*) FROM plan_items pi
        JOIN daily_plans dp ON dp.id = pi.plan_id
        WHERE dp.plan_date >= ? AND pi.executed = 1
    """, (cutoff,)).fetchone()[0]
    rate = (items_done / items_total * 100) if items_total else 0

    cols[1].metric(t("executed_total", LANG), items_done)
    cols[2].metric(t("items_scheduled", LANG), items_total)
    cols[3].metric(t("completion_rate", LANG), f"{rate:.0f}%")

    # ---- STATISTICS CHARTS ---------------------------------------------
    st.markdown("---")
    st.markdown("### 📈 גרפים סטטיסטיים")
    chart_view = st.radio(
        "סוג גרף",
        options=["by_elder", "by_date", "by_category"],
        horizontal=True,
        format_func=lambda v: {
            "by_elder": "👤 לפי דייר/ת",
            "by_date": "📅 לפי תאריך",
            "by_category": "🎯 לפי סוג פעילות",
        }[v],
        label_visibility="collapsed",
    )

    if chart_view == "by_elder":
        df_elder = pd.read_sql("""
            SELECT e.full_name AS elder,
                   COUNT(pi.id) AS scheduled,
                   COALESCE(SUM(CASE WHEN pi.executed=1 THEN 1 ELSE 0 END), 0) AS done
            FROM elders e
            LEFT JOIN daily_plans dp ON dp.elder_id = e.id AND dp.plan_date >= ?
            LEFT JOIN plan_items pi ON pi.plan_id = dp.id
            WHERE e.active = 1
            GROUP BY e.id, e.full_name
            ORDER BY scheduled DESC
        """, conn, params=(cutoff,))

        if df_elder.empty or df_elder["scheduled"].sum() == 0:
            st.info("אין עדיין מספיק נתונים לגרף.")
        else:
            df_elder.columns = ["דייר/ת", "מתוזמן", "בוצע"]
            st.markdown("#### פעילויות מתוכננות לעומת בוצעו")
            st.bar_chart(df_elder.set_index("דייר/ת")[["מתוזמן", "בוצע"]],
                         height=320)

            df_elder["אחוז ביצוע"] = (
                df_elder["בוצע"] / df_elder["מתוזמן"].clip(lower=1) * 100
            ).round(1)
            st.markdown("#### אחוז ביצוע (%)")
            st.bar_chart(df_elder.set_index("דייר/ת")["אחוז ביצוע"], height=280)

    elif chart_view == "by_date":
        df_date = pd.read_sql("""
            SELECT dp.plan_date AS plan_date,
                   COUNT(pi.id) AS scheduled,
                   COALESCE(SUM(CASE WHEN pi.executed=1 THEN 1 ELSE 0 END), 0) AS done
            FROM daily_plans dp
            LEFT JOIN plan_items pi ON pi.plan_id = dp.id
            WHERE dp.plan_date >= ?
            GROUP BY dp.plan_date
            ORDER BY dp.plan_date
        """, conn, params=(cutoff,))

        if df_date.empty:
            st.info("אין עדיין מספיק נתונים לגרף.")
        else:
            df_date.columns = ["תאריך", "מתוזמן", "בוצע"]
            st.markdown("#### פעילויות לפי תאריך")
            st.line_chart(df_date.set_index("תאריך")[["מתוזמן", "בוצע"]],
                          height=320)

            df_date["אחוז ביצוע"] = (
                df_date["בוצע"] / df_date["מתוזמן"].clip(lower=1) * 100
            ).round(1)
            st.markdown("#### אחוז ביצוע יומי (%)")
            st.area_chart(df_date.set_index("תאריך")["אחוז ביצוע"], height=240)

    else:  # by_category
        df_cat = pd.read_sql("""
            SELECT
              CASE
                WHEN ka.code IS NOT NULL THEN ka.category
                WHEN ke.code IS NOT NULL THEN 'sport'
                WHEN ep.id IS NOT NULL  THEN 'external'
                WHEN pi.activity_code LIKE 'HOL_%' THEN 'holiday'
                ELSE 'general'
              END AS category,
              COUNT(pi.id) AS total,
              COALESCE(SUM(CASE WHEN pi.executed=1 THEN 1 ELSE 0 END), 0) AS done
            FROM plan_items pi
            JOIN daily_plans dp ON dp.id = pi.plan_id
            LEFT JOIN kb_activities ka ON ka.code = pi.activity_code
            LEFT JOIN kb_exercises  ke ON ke.code = pi.activity_code
            LEFT JOIN external_programs ep ON ('EXT_' || ep.id) = pi.activity_code
            WHERE dp.plan_date >= ?
            GROUP BY category
            ORDER BY total DESC
        """, conn, params=(cutoff,))

        if df_cat.empty:
            st.info("אין עדיין מספיק נתונים לגרף.")
        else:
            cat_labels = {
                "sport": "🏃 ספורט", "physical": "💪 פיזית",
                "cognitive": "🧠 קוגניטיבית", "social": "👥 חברתית",
                "mental": "🌿 נפשית", "medical": "🏥 רפואית",
                "nursing": "🩺 סיעודית", "external": "🏛️ חיצונית",
                "holiday": "🎉 חג", "general": "📌 כללי",
            }
            df_cat["category"] = df_cat["category"].map(
                lambda c: cat_labels.get(c, c)
            )
            df_cat.columns = ["קטגוריה", "סהכ", "בוצעו"]

            # pie chart via Altair
            try:
                import altair as alt
                st.markdown("#### חלוקה לפי קטגוריה")
                pie = (
                    alt.Chart(df_cat)
                    .mark_arc(innerRadius=50, outerRadius=130)
                    .encode(
                        theta=alt.Theta("סהכ:Q"),
                        color=alt.Color("קטגוריה:N",
                                        legend=alt.Legend(title="קטגוריה")),
                        tooltip=["קטגוריה", "סהכ", "בוצעו"],
                    )
                    .properties(height=380)
                )
                st.altair_chart(pie, width="stretch")
            except Exception as e:
                st.warning(f"Altair pie chart failed: {e}")

            st.markdown("#### עמודות - סך הכל ובוצעו")
            st.bar_chart(df_cat.set_index("קטגוריה")[["סהכ", "בוצעו"]],
                         height=320)

            df_cat["אחוז ביצוע"] = (
                df_cat["בוצעו"] / df_cat["סהכ"].clip(lower=1) * 100
            ).round(1)
            st.markdown("#### אחוז ביצוע לפי קטגוריה (%)")
            st.bar_chart(df_cat.set_index("קטגוריה")["אחוז ביצוע"], height=260)

    st.markdown("---")
    st.markdown("### Per-elder summary")
    per_elder = []
    for e in elders:
        sched = conn.execute("""
            SELECT COUNT(*) FROM plan_items pi
            JOIN daily_plans dp ON dp.id = pi.plan_id
            WHERE dp.plan_date >= ? AND dp.elder_id = ?
        """, (cutoff, e["id"])).fetchone()[0]
        done = conn.execute("""
            SELECT COUNT(*) FROM plan_items pi
            JOIN daily_plans dp ON dp.id = pi.plan_id
            WHERE dp.plan_date >= ? AND dp.elder_id = ? AND pi.executed = 1
        """, (cutoff, e["id"])).fetchone()[0]
        per_elder.append({
            "id": e["id"],
            t("elder_name", LANG): e["full_name"],
            t("room_number", LANG): e["room_number"] or "-",
            t("items_scheduled", LANG): sched,
            t("executed_total", LANG): done,
            t("completion_rate", LANG): f"{(done/sched*100) if sched else 0:.0f}%",
        })
    if per_elder:
        st.dataframe(pd.DataFrame(per_elder).drop(columns=["id"]),
                     width="stretch", hide_index=True)

    st.markdown("### " + t("report_summary", LANG))
    target_id = st.selectbox(
        t("select_elder", LANG),
        options=[e["id"] for e in elders] if elders else [],
        format_func=lambda i: next(e["full_name"] for e in elders if e["id"] == i),
    ) if elders else None

    ecols = st.columns(3)
    if target_id:
        if ecols[0].button("📄 " + t("report_export_word", LANG)):
            out = report_export.elder_summary_docx(conn, target_id, days_back, LANG)
            with open(out, "rb") as f:
                st.download_button("⬇️ Download", f.read(), file_name=Path(out).name)
        if ecols[1].button("📕 " + t("report_export_pdf", LANG)):
            out = report_export.elder_summary_pdf(conn, target_id, days_back, LANG)
            with open(out, "rb") as f:
                st.download_button("⬇️ Download", f.read(), file_name=Path(out).name)
        if ecols[2].button("📊 " + t("report_export_excel", LANG)):
            out = report_export.elder_summary_xlsx(conn, target_id, days_back, LANG)
            with open(out, "rb") as f:
                st.download_button("⬇️ Download", f.read(), file_name=Path(out).name)

    conn.close()


# =====================================================================
# KNOWLEDGE VIEW
# =====================================================================
def view_knowledge(LANG: str):
    conn = get_connection()
    st.markdown(f"# 📚 {t('nav_knowledge', LANG)}")

    if st.button("🔄 " + t("refresh_kb", LANG)):
        counts = refresh_knowledge_banks(conn)
        st.success(json.dumps(counts))

    cols = st.columns(5)
    cols[0].metric(t("kb_diseases_count", LANG),
                   conn.execute("SELECT COUNT(*) FROM kb_diseases").fetchone()[0])
    cols[1].metric(t("kb_medications_count", LANG),
                   conn.execute("SELECT COUNT(*) FROM kb_medications").fetchone()[0])
    cols[2].metric(t("kb_conditions_count", LANG),
                   conn.execute("SELECT COUNT(*) FROM kb_conditions").fetchone()[0])
    cols[3].metric(t("kb_activities_count", LANG),
                   conn.execute("SELECT COUNT(*) FROM kb_activities").fetchone()[0])
    cols[4].metric(t("kb_exercises_count", LANG),
                   conn.execute("SELECT COUNT(*) FROM kb_exercises").fetchone()[0])

    tabs = st.tabs(["Diseases", "Medications", "Conditions", "Activities",
                    "🏃 " + t("exercises_section", LANG)])
    for tab, table in zip(tabs, ["kb_diseases", "kb_medications", "kb_conditions",
                                  "kb_activities", "kb_exercises"]):
        with tab:
            df = pd.read_sql(f"SELECT * FROM {table}", conn)
            st.dataframe(df, width="stretch", hide_index=True)

    # ---- 🌐 ONLINE DATA SOURCES ----------------------------------------
    st.markdown("---")
    st.markdown("### 🌐 מאגרי מידע מקוונים")
    st.caption("קישורים למאגרי ידע חיצוניים (מרשמי תרופות, סיווגי מחלות, מאגרי "
               "מחקר והנחיות). ניתן להוסיף ולמחוק מאגרים לפי הצורך.")

    CAT_LABELS = {
        "diseases": "🦠 מחלות", "medications": "💊 תרופות",
        "conditions": "🩺 מצבים", "activities": "🎯 פעילויות",
        "research": "🔬 מחקר", "general": "🌐 כללי",
    }
    src_rows = conn.execute(
        "SELECT * FROM kb_online_sources WHERE active = 1 ORDER BY id"
    ).fetchall()

    if src_rows:
        for s in src_rows:
            c1, c2 = st.columns([11, 1])
            with c1:
                cat = CAT_LABELS.get(s["category"], s["category"] or "🌐 כללי")
                desc = (f"<div style='color:#6b7280;font-size:0.9rem;"
                        f"margin-top:0.2rem;'>{s['description']}</div>"
                        if s["description"] else "")
                st.markdown(
                    f"<div style='padding:0.6rem 0.9rem;background:#f9fafb;"
                    f"border-right:5px solid #4f46e5;border-radius:8px;"
                    f"margin-bottom:0.5rem;'>"
                    f"<span style='background:#eef2ff;color:#4338ca;"
                    f"border-radius:999px;padding:0.1rem 0.6rem;font-size:0.8rem;"
                    f"font-weight:700;'>{cat}</span> "
                    f"<b>{s['name']}</b><br>"
                    f"<a href='{s['url']}' target='_blank' class='ltr-text' "
                    f"style='color:#4f46e5;'>{s['url']}</a>{desc}</div>",
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("🗑️", key=f"del_src_{s['id']}", help="מחק מאגר"):
                    conn.execute("DELETE FROM kb_online_sources WHERE id = ?",
                                 (s["id"],))
                    conn.commit()
                    st.rerun()
    else:
        st.info("אין עדיין מאגרים מקוונים. הוסף מאגר ראשון למטה.")

    with st.expander("➕ הוספת מאגר מידע מקוון"):
        with st.form("add_online_source", clear_on_submit=True):
            nm = st.text_input("שם המאגר",
                               placeholder="לדוגמה: מאגר התרופות – משרד הבריאות")
            url = st.text_input("כתובת (URL)", placeholder="https://...")
            cat = st.selectbox("קטגוריה", options=list(CAT_LABELS.keys()),
                               format_func=lambda k: CAT_LABELS[k])
            desc = st.text_area("תיאור קצר",
                                placeholder="על מה המאגר ולמה הוא שימושי")
            if st.form_submit_button("➕ הוסף מאגר", type="primary"):
                if nm.strip() and url.strip():
                    u = url.strip()
                    if not (u.startswith("http://") or u.startswith("https://")):
                        u = "https://" + u
                    conn.execute(
                        "INSERT INTO kb_online_sources "
                        "(name, url, category, description) VALUES (?, ?, ?, ?)",
                        (nm.strip(), u, cat, desc.strip()),
                    )
                    conn.commit()
                    st.success("המאגר נוסף ✓")
                    st.rerun()
                else:
                    st.warning("יש להזין שם וכתובת")

    st.info("📋 כללי המוסד עברו ללשונית נפרדת בתפריט הצדדי: "
            "**📋 כללי המוסד**.")
    conn.close()


# =====================================================================
# RULES VIEW  (📋 כללי המוסד) — dedicated tab
# =====================================================================
def view_rules(LANG: str):
    from models import rules_doc
    from models.optimizer import parse_institution_rules

    st.markdown(f"# 📋 {t('nav_rules', LANG)}")
    st.caption(
        "בנק הכללים נשמר בקובץ Word: `knowledge_banks/rules_bank.docx`. "
        "האופטימייזר קורא אותו מחדש בכל יצירת תוכנית. "
        "כל שורה היא כלל אחד."
    )

    rules_list = rules_doc.read_rules()

    # ---- (A) FREE-TEXT EDITOR (primary - one rule per line) ----
    st.markdown("### 📝 עריכת הכללים (מלל חופשי - שורה לכל כלל)")
    bulk_text = st.text_area(
        "כללי המוסד",
        value="\n".join(rules_list),
        height=280,
        key="rules_bulk_editor",
        label_visibility="collapsed",
        placeholder=(
            "כל שורה = כלל אחד. לדוגמה:\n"
            "אין פעילות אחרי 20:00\n"
            "אין פעילות לפני 08:00\n"
            "ארוחת ערב ב-18:00 בחדר האוכל המרכזי\n"
            "ביקור משפחה - עד 3 איש בו זמנית\n"
            "אין פעילות חיצונית ביום שבת"
        ),
    )
    bcols = st.columns([2, 2, 6])
    if bcols[0].button("💾 שמור כללים", type="primary",
                       key="rules_save", width="stretch"):
        rules_doc.set_rules_from_text(bulk_text)
        st.success("הכללים נשמרו לקובץ Word ✓")
        st.rerun()
    if bcols[1].button("🗑️ מחק הכל", key="rules_clear_all",
                       width="stretch"):
        rules_doc.write_rules([])
        st.success("כל הכללים נמחקו")
        st.rerun()

    st.markdown("---")

    # ---- (B) QUICK-ADD a single rule ----
    st.markdown("### ➕ הוספת כלל מהירה")
    with st.form("rules_quick_add", clear_on_submit=True):
        acols = st.columns([6, 1])
        new_rule = acols[0].text_input(
            "כלל חדש",
            placeholder="לדוגמה: אין פעילות אחרי 20:00",
            label_visibility="collapsed",
        )
        if acols[1].form_submit_button("➕ הוסף", type="primary",
                                       width="stretch"):
            if new_rule.strip():
                rules_doc.add_rule(new_rule.strip())
                st.toast("✓ הכלל נוסף")
                st.rerun()
            else:
                st.warning("יש להזין טקסט")

    st.markdown("---")

    # ---- (C) RULES LIST with per-rule delete + enforcement badge ----
    st.markdown(f"### 📜 הכללים הקיימים ({len(rules_list)})")
    if rules_list:
        import re as _re_ui
        for idx, rule in enumerate(rules_list):
            rcols = st.columns([9, 1])
            with rcols[0]:
                has_time = bool(_re_ui.search(r"\d{1,2}:\d{2}", rule))
                has_forbid = any(k in rule for k in
                                 ("אין", "אסור", "no ", "not "))
                has_when = any(k in rule for k in
                               ("אחרי", "after", "לפני", "before", "עד "))
                is_enforced = has_time and has_forbid and has_when
                badge = "🤖 נאכף אוטומטית" if is_enforced else "👁️ לידיעת הצוות"
                badge_color = "#059669" if is_enforced else "#6b7280"
                st.markdown(
                    f"<div style='padding:0.6rem 0.9rem;background:#f9fafb;"
                    f"border-right:5px solid {badge_color};"
                    f"border-radius:8px;margin-bottom:0.5rem;'>"
                    f"<span style='font-weight:700;color:#374151;'>{idx+1}.</span> "
                    f"<span style='font-size:1.02rem;'>{rule}</span> "
                    f"<span style='background:{badge_color}20;color:{badge_color};"
                    f"padding:2px 10px;border-radius:999px;font-size:0.78rem;"
                    f"font-weight:600;margin-right:0.5rem;'>{badge}</span></div>",
                    unsafe_allow_html=True,
                )
            with rcols[1]:
                if st.button("🗑️", key=f"rule_del_{idx}",
                             help="מחק כלל זה", width="stretch"):
                    rules_doc.delete_rule(idx)
                    st.toast(f"נמחק: {rule[:40]}")
                    st.rerun()
    else:
        st.info("אין כללים עדיין. הוסף בעורך למעלה ⬆️")

    # ---- (D) what the optimizer enforces + download ----
    st.markdown("---")
    ecols = st.columns([1, 1, 2])
    parsed = parse_institution_rules("\n".join(rules_list))
    after_val = parsed["no_activity_after_minutes"]
    ecols[0].metric(
        "🚫 אסור פעילות אחרי",
        f"{after_val//60:02d}:{after_val%60:02d}" if after_val else "—",
    )
    before_val = parsed["no_activity_before_minutes"]
    ecols[1].metric(
        "🚫 אסור פעילות לפני",
        f"{before_val//60:02d}:{before_val%60:02d}" if before_val else "—",
    )
    with ecols[2]:
        st.caption(
            "⚠️ רק כללי **זמן** (אין פעילות אחרי/לפני HH:MM) נאכפים אוטומטית. "
            "שאר הכללים מוצגים לצוות בבאנר המוסד אצל כל דייר/ת."
        )
        try:
            if rules_doc.RULES_DOC_PATH.exists():
                with open(rules_doc.RULES_DOC_PATH, "rb") as _f:
                    st.download_button(
                        "⬇️ הורד את קובץ הכללים (Word)",
                        _f.read(),
                        file_name="rules_bank.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
        except Exception:
            pass


# =====================================================================
# CARE PLAN TRACKING VIEW  (📌 מעקב תוכנית הטיפול)
# =====================================================================
# reason value -> translation key. 'refused' feeds the optimizer penalty.
TRACK_REASONS = [
    ("no_desire_refused", "reason_no_desire"),   # → stored as 'refused'
    ("health", "reason_health"),
    ("unavailable", "unavailable"),
    ("weather", "weather"),
    ("other", "other"),
]
# map UI reason value to the stored skipped_reason
_REASON_STORE = {"no_desire_refused": "refused", "health": "health",
                 "unavailable": "unavailable", "weather": "weather",
                 "other": "other"}
_REASON_FROM_STORE = {v: k for k, v in _REASON_STORE.items()}


def view_tracking(LANG: str):
    conn = get_connection()
    st.markdown(f"# 📌 {t('nav_tracking', LANG)}")
    st.caption(t("tracking_help", LANG))

    elders = _list_elders(conn)
    if not elders:
        st.info(t("no_elder_selected", LANG))
        conn.close()
        return

    # resident follows the sidebar switcher (single source of truth)
    elder_id = _current_elder_id(conn)
    _resident_banner(conn, elder_id, LANG)
    rng = st.selectbox(
        t("tracking_range", LANG),
        options=[7, 14, 30],
        format_func=lambda d: {7: t("tracking_last7", LANG),
                               14: t("tracking_last14", LANG),
                               30: t("tracking_last30", LANG)}[d],
        key="track_range",
    )
    cutoff = (dt.date.today() - dt.timedelta(days=rng)).isoformat()
    today_iso = dt.date.today().isoformat()

    items = conn.execute("""
        SELECT pi.*, dp.plan_date AS plan_date,
               COALESCE(ka.name_he, ke.name_he, ep.name,
                 CASE pi.activity_code
                   WHEN 'MEAL_BREAKFAST' THEN 'ארוחת בוקר'
                   WHEN 'MEAL_LUNCH' THEN 'ארוחת צהריים'
                   WHEN 'MEAL_DINNER' THEN 'ארוחת ערב' END) AS name_he,
               CASE
                 WHEN pi.activity_code LIKE 'MEAL_%' THEN 'meal'
                 WHEN ka.code IS NOT NULL THEN ka.category
                 WHEN ke.code IS NOT NULL THEN 'sport'
                 WHEN ep.id IS NOT NULL THEN 'external'
                 WHEN pi.activity_code LIKE 'HOL_%' THEN 'holiday'
                 ELSE 'general' END AS category
        FROM plan_items pi
        JOIN daily_plans dp ON dp.id = pi.plan_id
        LEFT JOIN kb_activities ka ON ka.code = pi.activity_code
        LEFT JOIN kb_exercises  ke ON ke.code = pi.activity_code
        LEFT JOIN external_programs ep ON ('EXT_' || ep.id) = pi.activity_code
        WHERE dp.elder_id = ? AND dp.plan_date >= ? AND dp.plan_date <= ?
          AND pi.activity_code NOT LIKE 'MEAL_%'
        ORDER BY dp.plan_date DESC,
          CASE pi.time_slot WHEN 'morning' THEN 1 WHEN 'noon' THEN 2
               WHEN 'afternoon' THEN 3 WHEN 'evening' THEN 4 ELSE 5 END,
          pi.start_time
    """, (elder_id, cutoff, today_iso)).fetchall()

    if not items:
        st.info(t("tracking_no_items", LANG))
        conn.close()
        return

    done = sum(1 for i in items if i["executed"])
    skipped = sum(1 for i in items if not i["executed"] and i["skipped_reason"])
    pending = len(items) - done - skipped
    scols = st.columns(4)
    scols[0].metric(t("tracking_summary_done", LANG), done)
    scols[1].metric(t("tracking_summary_skipped", LANG), skipped)
    scols[2].metric(t("tracking_summary_pending", LANG), pending)
    scols[3].metric(t("completion_rate", LANG),
                    f"{(done/len(items)*100) if items else 0:.0f}%")

    # most-refused (30 days) — shows the optimizer weighting input
    refused = conn.execute("""
        SELECT COALESCE(ka.name_he, ke.name_he, ep.name, pi.activity_code) AS nm,
               COUNT(*) AS cnt
        FROM plan_items pi
        JOIN daily_plans dp ON dp.id = pi.plan_id
        LEFT JOIN kb_activities ka ON ka.code = pi.activity_code
        LEFT JOIN kb_exercises  ke ON ke.code = pi.activity_code
        LEFT JOIN external_programs ep ON ('EXT_' || ep.id) = pi.activity_code
        WHERE dp.elder_id = ? AND dp.plan_date >= ?
          AND pi.executed = 0 AND pi.skipped_reason = 'refused'
        GROUP BY nm ORDER BY cnt DESC LIMIT 5
    """, (elder_id, (dt.date.today() - dt.timedelta(days=30)).isoformat())).fetchall()
    if refused:
        with st.expander(f"⚖️ {t('tracking_most_refused', LANG)}", expanded=False):
            for r in refused:
                st.markdown(f"• **{r['nm']}** — {r['cnt']}× → "
                            f"עונש בתכנון: −{r['cnt']*8} נקודות")

    st.markdown("---")

    # group by date
    current_date = None
    for it in items:
        if it["plan_date"] != current_date:
            current_date = it["plan_date"]
            try:
                dobj = dt.date.fromisoformat(current_date)
                dname = t(HEBREW_DAYS[day_index_hebrew(dobj)], LANG)
                st.markdown(f"### 📅 {dname} · {hebrew_date(dobj)}")
            except Exception:
                st.markdown(f"### 📅 {current_date}")

        c = styling.category_color(it["category"] or "general")
        with st.container(border=True):
            cols = st.columns([3, 1, 1])
            with cols[0]:
                mark = ("✅" if it["executed"]
                        else ("❌" if it["skipped_reason"] else "⬜"))
                st.markdown(
                    f"<strong style='color:{c['text']};'>{mark} "
                    f"🕐 {it['start_time']} - {it['name_he']}</strong>",
                    unsafe_allow_html=True,
                )
                if it["executed"]:
                    st.caption(f"✅ {t('tracking_done', LANG)}"
                               + (f" · {it['executed_at'][:16]}"
                                  if it["executed_at"] else ""))
                elif it["skipped_reason"]:
                    stored = it["skipped_reason"]
                    ui_reason = _REASON_FROM_STORE.get(stored, "other")
                    rlabel = t(dict(TRACK_REASONS).get(ui_reason, "other"), LANG)
                    st.warning(f"❌ {t('tracking_not_done', LANG)} · {rlabel}")
                if it["execution_notes"]:
                    st.caption(f"📝 {it['execution_notes']}")
            with cols[1]:
                if not it["executed"]:
                    if st.button("✅ " + t("tracking_done", LANG),
                                 key=f"tk_done_{it['id']}", width="stretch"):
                        conn.execute(
                            "UPDATE plan_items SET executed=1, "
                            "executed_at=CURRENT_TIMESTAMP, skipped_reason=NULL "
                            "WHERE id=?", (it["id"],))
                        conn.commit()
                        st.rerun()
                else:
                    if st.button("↩️ " + t("tracking_reset", LANG),
                                 key=f"tk_reset_{it['id']}", width="stretch"):
                        conn.execute(
                            "UPDATE plan_items SET executed=0, executed_at=NULL "
                            "WHERE id=?", (it["id"],))
                        conn.commit()
                        st.rerun()
            with cols[2]:
                if not it["executed"]:
                    with st.popover("❌ " + t("tracking_not_done", LANG),
                                    width="stretch"):
                        cur_stored = it["skipped_reason"] or "refused"
                        cur_ui = _REASON_FROM_STORE.get(cur_stored, "no_desire_refused")
                        reason = st.selectbox(
                            t("skip_reason", LANG),
                            options=[r[0] for r in TRACK_REASONS],
                            index=[r[0] for r in TRACK_REASONS].index(cur_ui)
                            if cur_ui in [r[0] for r in TRACK_REASONS] else 0,
                            format_func=lambda v: t(dict(TRACK_REASONS)[v], LANG),
                            key=f"tk_reason_{it['id']}",
                        )
                        note = st.text_area(
                            t("execution_notes", LANG),
                            value=it["execution_notes"] or "",
                            key=f"tk_note_{it['id']}", height=80,
                        )
                        if st.button("💾 " + t("save", LANG),
                                     key=f"tk_save_{it['id']}",
                                     type="primary", width="stretch"):
                            conn.execute(
                                "UPDATE plan_items SET executed=0, "
                                "skipped_reason=?, execution_notes=? WHERE id=?",
                                (_REASON_STORE.get(reason, "other"), note, it["id"]))
                            conn.commit()
                            st.rerun()

            # ---- instructor review of the resident for this activity ----
            cur_rating = it["instructor_rating"]
            rating_badge = (f"⭐{cur_rating}" if cur_rating
                            else t("instructor_rating_none", LANG))
            with st.expander(f"👩‍🏫 {t('instructor_review_title', LANG)} · {rating_badge}"):
                rate_opts = [5, 4, 3, 2, 1]
                default_idx = (rate_opts.index(int(cur_rating))
                               if cur_rating in rate_opts else 2)
                new_rating = st.selectbox(
                    t("instructor_rating_label", LANG),
                    options=rate_opts,
                    index=default_idx,
                    format_func=lambda r: "⭐" * r + f"  {t(f'rate_{r}', LANG)}",
                    key=f"rate_{it['id']}",
                )
                new_review = st.text_area(
                    t("instructor_review_label", LANG),
                    value=it["instructor_review"] or "",
                    key=f"review_{it['id']}", height=80,
                )
                if st.button("💾 " + t("save", LANG),
                             key=f"review_save_{it['id']}",
                             type="primary"):
                    conn.execute(
                        "UPDATE plan_items SET instructor_rating=?, "
                        "instructor_review=? WHERE id=?",
                        (int(new_rating), new_review, it["id"]))
                    conn.commit()
                    st.success(t("instructor_review_saved", LANG))
                    st.rerun()

    conn.close()


# =====================================================================
# CARE PLAN GOALS VIEW  (🎯 יעדי תוכנית הטיפול)
# =====================================================================
def view_goals(LANG: str):
    from models import goals as goals_mod
    from models.optimizer import load_elder_context

    conn = get_connection()
    st.markdown(f"# 🎯 {t('nav_goals', LANG)}")
    st.caption(t("goals_help", LANG))

    elders = _list_elders(conn)
    if not elders:
        st.info(t("no_elder_selected", LANG))
        conn.close()
        return

    # resident follows the sidebar switcher (single source of truth)
    elder_id = _current_elder_id(conn)
    _resident_banner(conn, elder_id, LANG)

    goals = goals_mod.load_goals(conn, elder_id, active_only=False)

    # --- generate / regenerate buttons ---
    gcols = st.columns([2, 2, 4])
    if not goals:
        if gcols[0].button("✨ " + t("goals_generate", LANG), type="primary",
                           key="goals_gen"):
            try:
                ctx = load_elder_context(conn, elder_id)
                goals_mod.regenerate_goals(conn, elder_id, ctx.needs, ctx.need_weights)
                st.success(t("goals_saved", LANG))
                st.rerun()
            except Exception as e:
                st.error(t("error_generic", LANG) + str(e))
    else:
        if gcols[0].button("🔄 " + t("goals_regenerate", LANG),
                           key="goals_regen"):
            try:
                ctx = load_elder_context(conn, elder_id)
                goals_mod.regenerate_goals(conn, elder_id, ctx.needs, ctx.need_weights)
                st.success(t("goals_saved", LANG))
                st.rerun()
            except Exception as e:
                st.error(t("error_generic", LANG) + str(e))

    st.markdown("---")

    if not goals:
        st.info(t("goals_none", LANG))
    else:
        st.markdown(f"### 📜 {t('goals_existing', LANG)} ({len(goals)})")
        # editable rows (no form, so delete buttons work alongside edits)
        for g in goals:
            gid = g["id"]
            src_label = (t("goal_source_auto", LANG) if g["source"] == "auto"
                         else t("goal_source_manual", LANG))
            src_color = "#2563eb" if g["source"] == "auto" else "#7c3aed"
            with st.container(border=True):
                cols = st.columns([6, 2, 1, 1])
                new_text = cols[0].text_input(
                    t("goal_text", LANG), value=g["goal_text"],
                    key=f"gtext_{gid}", label_visibility="collapsed",
                )
                new_prio = cols[1].selectbox(
                    t("goal_priority", LANG),
                    options=[5, 4, 3, 2, 1],
                    index=[5, 4, 3, 2, 1].index(int(g["priority"]))
                    if int(g["priority"]) in [5, 4, 3, 2, 1] else 2,
                    format_func=lambda p: "⭐" * p,
                    key=f"gprio_{gid}", label_visibility="collapsed",
                )
                new_active = cols[2].checkbox(
                    t("goal_active", LANG), value=bool(g["active"]),
                    key=f"gact_{gid}",
                )
                if cols[3].button("🗑️", key=f"gdel_{gid}", help="מחק",
                                  width="stretch"):
                    conn.execute("DELETE FROM care_goals WHERE id = ?", (gid,))
                    conn.commit()
                    st.rerun()
                # tags + source badge
                st.markdown(
                    f"<span style='background:{src_color}20;color:{src_color};"
                    f"padding:1px 8px;border-radius:999px;font-size:0.72rem;"
                    f"font-weight:600;'>{src_label}</span> "
                    f"<span style='color:#9ca3af;font-size:0.78rem;'>🏷️ "
                    f"{g['target_tags'] or '-'}</span>",
                    unsafe_allow_html=True,
                )

        if st.button("💾 " + t("save", LANG), type="primary", key="goals_save_all"):
            cur = conn.cursor()
            for g in goals:
                gid = g["id"]
                cur.execute(
                    "UPDATE care_goals SET goal_text=?, priority=?, active=?, "
                    "source=CASE WHEN source='auto' AND goal_text<>? "
                    "THEN 'manual' ELSE source END WHERE id=?",
                    (st.session_state.get(f"gtext_{gid}", g["goal_text"]),
                     int(st.session_state.get(f"gprio_{gid}", g["priority"])),
                     int(bool(st.session_state.get(f"gact_{gid}", g["active"]))),
                     st.session_state.get(f"gtext_{gid}", g["goal_text"]),
                     gid),
                )
            conn.commit()
            st.success(t("goals_saved", LANG))
            st.rerun()

    # --- add a new manual goal ---
    st.markdown("---")
    st.markdown(f"### ➕ {t('goal_add', LANG)}")
    with st.form("add_goal_form", clear_on_submit=True):
        acols = st.columns([6, 2, 1])
        add_text = acols[0].text_input(
            t("goal_text", LANG),
            placeholder="לדוגמה: לצאת לחצר לפחות פעם ביום",
            label_visibility="collapsed",
        )
        add_prio = acols[1].selectbox(
            t("goal_priority", LANG), options=[5, 4, 3, 2, 1], index=2,
            format_func=lambda p: "⭐" * p, label_visibility="collapsed",
        )
        if acols[2].form_submit_button("➕", type="primary", width="stretch"):
            if add_text.strip():
                conn.execute(
                    "INSERT INTO care_goals "
                    "(elder_id, goal_text, target_tags, priority, source, active) "
                    "VALUES (?, ?, '', ?, 'manual', 1)",
                    (elder_id, add_text.strip(), int(add_prio)),
                )
                conn.commit()
                st.toast("✓")
                st.rerun()
            else:
                st.warning("יש להזין טקסט")

    conn.close()


# =====================================================================
# DAILY / WEEKLY CARE PLAN — dedicated resident sub-views (moved out of the
# profile tabs; they follow the sidebar resident switcher)
# =====================================================================
def view_daily(LANG: str):
    conn = get_connection()
    st.markdown(f"# 📅 {t('nav_daily_plan', LANG)}")
    if not _list_elders(conn):
        st.info(t("no_elder_selected", LANG))
        conn.close()
        return
    elder_id = _current_elder_id(conn)
    _resident_banner(conn, elder_id, LANG)
    _render_daily_plan_tab(conn, elder_id, LANG)
    conn.close()


def view_weekly(LANG: str):
    conn = get_connection()
    st.markdown(f"# 🗓️ {t('nav_weekly_plan', LANG)}")
    if not _list_elders(conn):
        st.info(t("no_elder_selected", LANG))
        conn.close()
        return
    elder_id = _current_elder_id(conn)
    _resident_banner(conn, elder_id, LANG)
    _render_weekly_plan_tab(conn, elder_id, LANG)
    conn.close()


# =====================================================================
# DISPATCH
# =====================================================================
LANG = st.session_state.lang
if st.session_state.view == "caregiver":
    view_caregiver(LANG)
elif st.session_state.view == "manager":
    view_manager(LANG)
elif st.session_state.view == "rules":
    view_rules(LANG)
elif st.session_state.view == "goals":
    view_goals(LANG)
elif st.session_state.view == "daily":
    view_daily(LANG)
elif st.session_state.view == "weekly":
    view_weekly(LANG)
elif st.session_state.view == "tracking":
    view_tracking(LANG)
else:
    view_knowledge(LANG)
