"""
MIA-inspired CSS for the Streamlit app.
- Elderly-friendly typography (larger base font, larger click targets)
- Full RTL for Hebrew (sidebar moves to the right, content flips)
- Category color palette
- Day-of-week cards
- Activity item cards with colored category strips
"""

import streamlit as st


CATEGORY_COLORS = {
    "sport":      {"bg": "#fef9c3", "border": "#ca8a04", "text": "#713f12", "icon": "🏃"},
    "physical":   {"bg": "#e0f2fe", "border": "#0284c7", "text": "#0c4a6e", "icon": "💪"},
    "cognitive":  {"bg": "#f3e8ff", "border": "#9333ea", "text": "#581c87", "icon": "🧠"},
    "social":     {"bg": "#ccfbf1", "border": "#0d9488", "text": "#134e4a", "icon": "👥"},
    "mental":     {"bg": "#fce7f3", "border": "#db2777", "text": "#831843", "icon": "🌿"},
    "medical":    {"bg": "#fee2e2", "border": "#dc2626", "text": "#7f1d1d", "icon": "🏥"},
    "nursing":    {"bg": "#dbeafe", "border": "#2563eb", "text": "#1e3a8a", "icon": "🩺"},
    "preferences": {"bg": "#fef3c7", "border": "#d97706", "text": "#78350f", "icon": "⭐"},
    "external":   {"bg": "#ede9fe", "border": "#6d28d9", "text": "#4c1d95", "icon": "🏛️"},
    "holiday":    {"bg": "#ffedd5", "border": "#ea580c", "text": "#7c2d12", "icon": "🎉"},
    "general":    {"bg": "#f3f4f6", "border": "#94a3b8", "text": "#374151", "icon": "📌"},
    "meal":       {"bg": "#fef3c7", "border": "#f59e0b", "text": "#78350f", "icon": "🍽️"},
}


# Base CSS that applies for all languages.
BASE_CSS = """
<style>
/* ---- SCROLLBAR (thick, always-visible, elderly-friendly) ---- */
* { scrollbar-width: auto; scrollbar-color: #2563eb #e0e7ff; }
::-webkit-scrollbar { width: 18px !important; height: 18px !important; }
::-webkit-scrollbar-track {
  background: #e0e7ff !important;
  border-radius: 9px !important;
}
::-webkit-scrollbar-thumb {
  background: #2563eb !important;
  border-radius: 9px !important;
  border: 3px solid #e0e7ff !important;
  min-height: 60px !important;
}
::-webkit-scrollbar-thumb:hover {
  background: #1e3a8a !important;
  border-color: #c7d2fe !important;
}
::-webkit-scrollbar-corner { background: #e0e7ff !important; }

/* "Back to top" floating button — replaces tiny scrollbar grabbing */
.back-to-top-link {
  position: fixed; bottom: 28px; right: 28px;
  width: 56px; height: 56px;
  background: #2563eb; color: white !important;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.7rem; font-weight: 700;
  text-decoration: none !important;
  box-shadow: 0 6px 20px rgba(30, 64, 175, 0.35);
  z-index: 9999;
  transition: transform 0.15s, box-shadow 0.15s;
}
.back-to-top-link:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 28px rgba(30, 64, 175, 0.45);
  background: #1e40af; color: white !important;
}

/* ============ WEBSITE THEME — bold, modern SaaS look ============ */
:root {
  --brand: #4f46e5; --brand-2: #6366f1; --brand-dark: #3730a3;
  --accent: #06b6d4;
  --canvas: #eaeef6; --card: #ffffff; --ink: #0f172a;
  --muted: #64748b; --line: #e5e9f2;
}

/* App canvas — soft blue-gray behind bright white cards */
[data-testid="stApp"], [data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1200px 500px at 100% -10%, #dbe4fb 0%, transparent 60%),
    var(--canvas) !important;
}
body { background: var(--canvas); }

/* Main content column */
[data-testid="stMainBlockContainer"] {
  max-width: 1200px;
  padding-top: 1.4rem !important;
  padding-bottom: 4rem !important;
}

/* Slim gradient brand strip across the very top */
[data-testid="stHeader"] {
  background: linear-gradient(90deg, var(--brand-dark), var(--brand), var(--accent)) !important;
  height: 0.42rem !important;
  min-height: 0.42rem !important;
  box-shadow: 0 2px 12px rgba(79,70,229,0.35);
}

/* ---- SIDEBAR as a bold branded nav rail ---- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #ffffff 0%, #f4f6fc 100%) !important;
  box-shadow: -10px 0 30px rgba(15,23,42,0.07);
  border-inline-start: 1px solid var(--line);
}
/* Brand logo block (rendered from app.py as .brand-logo) */
.brand-logo {
  background: linear-gradient(135deg, var(--brand-dark), var(--brand) 55%, var(--accent));
  color: #fff; border-radius: 16px;
  padding: 1rem 1.1rem; margin-bottom: 1rem;
  box-shadow: 0 8px 22px rgba(79,70,229,0.35);
  display: flex; align-items: center; gap: 0.6rem;
}
.brand-logo .logo-emoji { font-size: 2rem; line-height: 1; }
.brand-logo .logo-name { font-size: 1.35rem; font-weight: 800; letter-spacing: .3px; }
.brand-logo .logo-tag { display:block; font-size: .74rem; font-weight: 500; opacity: .9; }

/* Resident switcher label (under the brand) */
[data-testid="stSidebar"] .resident-pick-label {
  font-size: .82rem; font-weight: 700; color: var(--muted);
  margin: .1rem 0 .2rem;
}
/* Compact prev/next arrows for the resident switcher */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton button {
  min-height: 2.3rem !important; padding: 0.3rem 0.6rem !important;
  text-align: center !important; justify-content: center !important;
  font-size: 1.1rem !important; font-weight: 800 !important;
}

/* Sidebar group headers */
[data-testid="stSidebar"] h4 {
  color: var(--muted) !important; font-size: .82rem !important;
  text-transform: none; letter-spacing: .4px; margin: 0.6rem 0 0.35rem 0 !important;
}
/* Sidebar nav buttons — clean list rows */
[data-testid="stSidebar"] .stButton button {
  text-align: right !important; justify-content: flex-start !important;
  background: #ffffff !important;
  border: 1px solid var(--line) !important;
  color: var(--ink) !important; box-shadow: none !important;
  border-radius: 12px !important; margin-bottom: 0.28rem;
  font-weight: 600 !important;
  transition: all .15s ease;
}
[data-testid="stSidebar"] .stButton button:hover {
  background: #eef2ff !important; border-color: #c7d2fe !important;
  transform: translateX(-3px);
}
/* ---- ACTIVE nav item: strong, unmistakable highlight ----
   NOTE the selector: ".stButton button[data-testid=...]" gives this a higher
   specificity than the base ".stButton button" list-row rule above, so the
   highlight actually wins. With the weaker selector the active item was being
   painted white like the inactive ones — impossible to tell which view is open. */
[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, var(--brand-dark) 0%, var(--brand) 55%, var(--brand-2) 100%) !important;
  border: none !important;
  border-inline-start: 6px solid var(--accent) !important;  /* bright rail on the leading edge */
  color: #fff !important;
  font-weight: 800 !important;
  box-shadow: 0 10px 24px rgba(79,70,229,0.5) !important;
  transform: scale(1.03);
}
[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-primary"]:hover {
  transform: scale(1.03);
  filter: brightness(1.06);
}
/* "you are here" dot before the active label (RTL-neutral) */
[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-primary"] p::before {
  content: "\25CF\00A0";   /* ● + nbsp */
  color: var(--accent);
  font-size: 0.8em;
}

/* ---- CARDS: bold, elevated, rounded ---- */
[data-testid="stMain"] [data-testid="stExpander"],
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--card) !important;
  border: 1px solid var(--line) !important;
  border-radius: 18px !important;
  box-shadow: 0 10px 30px rgba(15,23,42,0.08) !important;
  overflow: hidden;
  transition: box-shadow .18s ease, transform .18s ease;
}
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"]:hover {
  box-shadow: 0 16px 40px rgba(15,23,42,0.12) !important;
  transform: translateY(-2px);
}

/* ---- METRICS: gradient stat cards with brand accent ---- */
[data-testid="stMetric"] {
  background: linear-gradient(180deg, #ffffff, #f7f9ff);
  border: 1px solid var(--line);
  border-inline-start: 5px solid var(--brand);
  border-radius: 16px; padding: 0.9rem 1.1rem;
  box-shadow: 0 6px 18px rgba(15,23,42,0.06);
}
[data-testid="stMetricValue"] { color: var(--brand-dark); font-weight: 800; }

/* ---- PRIMARY BUTTONS: vivid gradient, lift on hover ---- */
[data-testid="stMain"] [data-testid="stBaseButton-primary"],
[data-testid="stMain"] [data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(135deg, var(--brand), var(--brand-2)) !important;
  border: none !important; color: #fff !important;
  border-radius: 12px !important;
  box-shadow: 0 8px 20px rgba(79,70,229,0.35) !important;
}
[data-testid="stMain"] [data-testid="stBaseButton-primary"]:hover,
[data-testid="stMain"] [data-testid="stBaseButton-primaryFormSubmit"]:hover {
  filter: brightness(1.07); transform: translateY(-2px);
}
/* Secondary buttons */
[data-testid="stMain"] [data-testid="stBaseButton-secondary"] {
  border-radius: 12px !important; border: 1.5px solid var(--line) !important;
  background: #fff !important;
}

/* ---- HEADINGS: brand color ---- */
[data-testid="stMain"] h1, [data-testid="stMain"] h2 { color: var(--brand-dark) !important; }

/* ---- TABS: modern pill bar ---- */
[data-testid="stMain"] .stTabs [data-baseweb="tab-list"] {
  background: #fff; border: 1px solid var(--line);
  border-radius: 14px; padding: 0.35rem; gap: 0.25rem;
  box-shadow: 0 4px 14px rgba(15,23,42,0.05);
}
[data-testid="stMain"] .stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, var(--brand), var(--brand-2)) !important;
  color: #fff !important; border-radius: 10px;
}
[data-testid="stMain"] .stTabs [aria-selected="true"] * { color: #fff !important; }

/* ---- INPUTS: rounded, brand focus ---- */
[data-testid="stMain"] input, [data-testid="stMain"] textarea,
[data-testid="stMain"] [data-baseweb="select"] > div,
[data-testid="stMain"] [data-baseweb="input"] {
  border-radius: 12px !important;
}

/* ---- DATAFRAMES: framed card ---- */
[data-testid="stMain"] [data-testid="stDataFrame"] {
  border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
  box-shadow: 0 6px 18px rgba(15,23,42,0.05);
}

/* ---- ELDERLY-FRIENDLY TYPOGRAPHY ---- */
html, body, [class*="st-"] {
  font-size: 17px;
  line-height: 1.55;
}
h1 { font-size: 2.1rem !important; font-weight: 700 !important; }
h2 { font-size: 1.7rem !important; font-weight: 700 !important; }
h3 { font-size: 1.35rem !important; font-weight: 600 !important; }
h4 { font-size: 1.15rem !important; font-weight: 600 !important; }

/* Larger, easier-to-tap buttons */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {
  font-size: 1.05rem !important;
  font-weight: 600 !important;
  padding: 0.7rem 1.3rem !important;
  min-height: 2.9rem !important;
  border-radius: 10px !important;
  border-width: 2px !important;
}
.stButton button:hover { transform: translateY(-1px); transition: transform 0.15s; }

/* Larger inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stSelectbox div[role="combobox"], .stDateInput input {
  font-size: 1.05rem !important;
  padding: 0.65rem 0.85rem !important;
  min-height: 2.7rem !important;
}

/* Higher-contrast labels */
.stTextInput label, .stTextArea label, .stNumberInput label,
.stSelectbox label, .stDateInput label, .stRadio label, .stCheckbox label,
.stMultiSelect label, .stSlider label {
  font-size: 1.02rem !important;
  font-weight: 600 !important;
  color: #1f2937 !important;
}

/* Tabs: compact so all 8 fit on one row, but still readable for elderly users */
.stTabs [data-baseweb="tab-list"] {
  flex-wrap: wrap !important;       /* fall to second row if narrow */
  gap: 0.25rem !important;
}
.stTabs [data-baseweb="tab"] {
  font-size: 0.95rem !important;
  font-weight: 600 !important;
  padding: 0.55rem 0.75rem !important;
  min-height: 2.5rem !important;
  border-radius: 8px 8px 0 0 !important;
  white-space: nowrap !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  background: #dbeafe !important;
  border-bottom: 3px solid #2563eb !important;
}

/* Sidebar text */
[data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stRadio div { font-size: 1.05rem; }

/* Cards (st.container(border=True)) — softer shadow, padding */
[data-testid="stContainer"] { padding: 0.6rem 0.2rem; }

/* ---- Institution / organization banner (top of page) ---- */
.org-banner {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border: 2px solid #f59e0b;
  border-radius: 14px;
  padding: 1rem 1.4rem;
  margin-bottom: 0.9rem;
  box-shadow: 0 3px 10px rgba(245, 158, 11, 0.12);
}
.org-banner-top {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 1rem; flex-wrap: wrap;
}
.org-banner-name {
  font-size: 1.45rem; font-weight: 800; color: #78350f;
}
.org-banner-manager {
  font-size: 0.95rem; color: #92400e;
}
.org-banner-row {
  display: flex; gap: 1.2rem; flex-wrap: wrap;
  font-size: 0.95rem; color: #78350f; margin-top: 0.4rem;
}
.org-banner-contact {
  font-size: 0.92rem; color: #92400e; margin-top: 0.3rem;
}
.org-banner-desc {
  font-size: 0.88rem; color: #6b4513; margin-top: 0.45rem;
  border-top: 1px dashed #d97706; padding-top: 0.4rem; font-style: italic;
}

/* ---- Resident banner (sub-views: goals / daily / weekly / tracking) ---- */
.resident-banner {
  display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap;
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
  border: 1px solid #c7d2fe;
  border-inline-start: 6px solid var(--brand, #4f46e5);
  border-radius: 12px;
  padding: 0.6rem 1rem;
  margin: 0.2rem 0 1rem;
  font-size: 1.15rem; color: #1e3a8a;
  box-shadow: 0 4px 14px rgba(79,70,229,0.12);
}
.resident-banner .rb-room { font-size: 0.95rem; color: #4338ca; font-weight: 600; }
.resident-banner .rb-hint { font-size: 0.8rem; color: #6366f1; opacity: 0.8; }

/* ---- Header band ---- */
.eldercare-header {
  background: linear-gradient(135deg, #3730a3 0%, #4f46e5 55%, #06b6d4 120%);
  color: white;
  padding: 1.7rem 1.9rem;
  border-radius: 18px;
  margin-bottom: 1.2rem;
  box-shadow: 0 14px 34px rgba(79, 70, 229, 0.32);
}
.eldercare-header h2 { margin: 0 0 0.3rem 0; font-size: 1.8rem; color: white !important; }
.eldercare-header .subtitle { opacity: 0.92; font-size: 1.02rem; }

/* ---- Day cards (weekly view) ---- */
.day-card {
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 14px;
  padding: 1.1rem;
  margin-bottom: 0.85rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.day-card-header {
  display: flex; align-items: center; justify-content: space-between;
  border-bottom: 1px solid #f3f4f6;
  padding-bottom: 0.6rem; margin-bottom: 0.85rem;
}
.day-badge {
  display: inline-flex; align-items: center; gap: 0.5rem;
  font-weight: 700; color: #1e3a8a; font-size: 1.05rem;
}
.day-number {
  background: #2563eb; color: white;
  border-radius: 999px;
  width: 32px; height: 32px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 0.95rem; font-weight: 700;
}
.day-date { color: #6b7280; font-size: 0.92rem; }
.day-stats { font-size: 0.9rem; color: #6b7280; font-weight: 600; }
.day-today {
  border-color: #2563eb !important;
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.18);
}

/* ---- Activity item ---- */
.activity-item {
  border-right: 5px solid #94a3b8;
  background: #f9fafb;
  border-radius: 8px;
  padding: 0.6rem 0.9rem;
  margin-bottom: 0.5rem;
  font-size: 0.96rem;
}
.activity-item.done {
  background: #d1fae5;
  border-right-color: #059669;
  text-decoration: line-through;
  color: #6b7280;
}
.activity-time {
  display: inline-block; font-weight: 700; color: #1f2937; margin-left: 0.5rem;
}
.activity-cat-pill {
  display: inline-block;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  margin-right: 0.4rem;
}

/* ---- Family contact card ---- */
.family-card {
  background: #fffbeb;
  border: 2px solid #fde68a;
  border-radius: 12px;
  padding: 1rem;
  margin-bottom: 0.7rem;
}
.family-card.primary {
  background: #fef3c7;
  border-color: #f59e0b;
  box-shadow: 0 3px 10px rgba(245, 158, 11, 0.15);
}
.family-card .name { font-size: 1.1rem; font-weight: 700; color: #78350f; }
.family-card .relation { color: #92400e; font-size: 0.95rem; }
.family-card .phone { font-size: 1.05rem; color: #1f2937; font-weight: 600; margin-top: 0.3rem; }
.family-card .notes { font-size: 0.9rem; color: #6b7280; margin-top: 0.4rem; font-style: italic; }
.primary-badge {
  display: inline-block;
  background: #f59e0b; color: white;
  padding: 0.2rem 0.55rem; border-radius: 999px;
  font-size: 0.75rem; font-weight: 700; margin-right: 0.4rem;
}

/* ============ MOBILE / PHONE (≤ 768px) ============ */
@media (max-width: 768px) {
  /* tighter base type + spacing for small screens */
  html, body, [class*="st-"] { font-size: 15px; line-height: 1.5; }
  h1 { font-size: 1.5rem !important; }
  h2 { font-size: 1.28rem !important; }
  h3 { font-size: 1.12rem !important; }
  h4 { font-size: 1.0rem !important; }

  /* slimmer scrollbar on touch devices (18px is huge on a phone) */
  ::-webkit-scrollbar { width: 9px !important; height: 9px !important; }
  ::-webkit-scrollbar-thumb { border-width: 2px !important; }

  /* main column: full width, minimal side padding */
  [data-testid="stMainBlockContainer"] {
    padding: 0.8rem 0.7rem 3rem !important;
  }

  /* stack multi-column rows vertically so nothing is squished */
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
    flex-direction: column !important;
  }
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    width: 100% !important; flex: 1 1 100% !important; min-width: 0 !important;
  }

  /* brand logo smaller */
  .brand-logo { padding: 0.7rem 0.8rem; }
  .brand-logo .logo-emoji { font-size: 1.5rem; }
  .brand-logo .logo-name { font-size: 1.1rem; }
  .brand-logo .logo-tag { font-size: 0.66rem; }

  /* header band + banners: less padding, smaller text */
  .eldercare-header { padding: 1rem 1.1rem; border-radius: 14px; }
  .eldercare-header h2 { font-size: 1.3rem; }
  .eldercare-header .subtitle { font-size: 0.9rem; }
  .org-banner { padding: 0.7rem 0.9rem; }
  .org-banner-name { font-size: 1.15rem; }
  .resident-banner { font-size: 1rem; padding: 0.5rem 0.8rem; }

  /* cards: smaller radius + lighter shadow */
  [data-testid="stMain"] [data-testid="stExpander"],
  [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px !important;
    box-shadow: 0 4px 14px rgba(15,23,42,0.07) !important;
  }

  /* buttons: comfortable, not oversized */
  .stButton button, .stDownloadButton button, .stFormSubmitButton button {
    font-size: 0.98rem !important;
    padding: 0.55rem 0.9rem !important;
    min-height: 2.6rem !important;
  }

  /* tabs shrink so more fit before wrapping */
  .stTabs [data-baseweb="tab"] {
    font-size: 0.85rem !important;
    padding: 0.4rem 0.55rem !important;
  }

  /* metrics */
  [data-testid="stMetric"] { padding: 0.6rem 0.8rem; }
  [data-testid="stMetricValue"] { font-size: 1.4rem; }

  /* dataframes/tables scroll horizontally rather than overflow the page */
  [data-testid="stDataFrame"], [data-testid="stTable"] { overflow-x: auto !important; }

  /* back-to-top: smaller and tucked into the corner */
  .back-to-top-link { width: 44px; height: 44px; font-size: 1.3rem; bottom: 16px; }
}
</style>
"""


# RTL-only overrides — applied just when language is Hebrew/Arabic.
RTL_CSS = """
<style>
/* Smooth scrolling everywhere */
html { scroll-behavior: smooth; }

/* RTL applies to the inner text content, NOT to the outer flex/scroll
   containers — flipping `[data-testid="stAppViewContainer"]` itself was
   what broke the scroll bar. Apply direction only on stMain. */
/* RTL text. */
[data-testid="stMain"] { direction: rtl; text-align: right; }
[data-testid="stSidebar"] { direction: rtl; text-align: right; }
[data-testid="stSidebar"] * { text-align: right; }

/* Put the sidebar on the RIGHT (RTL-correct) by reversing ONLY the top-level
   app container's two sections. This is safe — unlike reversing every
   stHorizontalBlock, it touches just [sidebar, main], not inner columns, and
   the CSS is injected at top level so it never unmounts with the sidebar.
   DESKTOP ONLY: on phones the sidebar is a fixed overlay, so the flip would
   fight the overlay and cover the content — leave the default there. */
@media (min-width: 769px) {
  [data-testid="stAppViewContainer"] { flex-direction: row-reverse; }
}

/* Inputs RTL. */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stDateInput input { direction: rtl; text-align: right; }

/* DataFrames stay LTR. */
.stDataFrame, .stDataFrame table { direction: ltr; }

/* Phone / email / URL fragments stay LTR inside RTL prose. */
.ltr-text { direction: ltr; display: inline-block; unicode-bidi: embed; }

/* Day cards: switch border side. */
.activity-item { border-right: none; border-left: 5px solid #94a3b8; }
.activity-item.done { border-left-color: #059669; }

/* Activity time spacing flip. */
.activity-time { margin-left: 0; margin-right: 0.5rem; }
.activity-cat-pill { margin-right: 0; margin-left: 0.4rem; }
.primary-badge { margin-right: 0; margin-left: 0.4rem; }

/* In RTL the floating "back to top" button moves to the left edge. */
.back-to-top-link { right: auto !important; left: 28px !important; }
</style>
"""


def inject(lang: str = "he") -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    if lang in {"he", "ar"}:
        st.markdown(RTL_CSS, unsafe_allow_html=True)
        st.markdown(
            '<script>document.documentElement.lang="' + lang + '";'
            'document.documentElement.dir="rtl";</script>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<script>document.documentElement.lang="' + lang + '";'
            'document.documentElement.dir="ltr";</script>',
            unsafe_allow_html=True,
        )

    # Floating "back to top" button + invisible top anchor.
    # Title in user's language.
    title_text = {"he": "חזרה למעלה", "ru": "Наверх", "en": "Back to top"}.get(lang, "Back to top")
    st.markdown(
        f'<a name="page-top"></a>'
        f'<a href="#page-top" class="back-to-top-link" title="{title_text}">⬆️</a>',
        unsafe_allow_html=True,
    )


def category_color(category: str) -> dict:
    return CATEGORY_COLORS.get(category, {
        "bg": "#f3f4f6", "border": "#94a3b8", "text": "#374151", "icon": "📌",
    })


def render_category_pill(category: str, label: str = None) -> str:
    c = category_color(category)
    label = label or category
    return (
        f'<span class="activity-cat-pill" '
        f'style="background:{c["bg"]};color:{c["text"]};border:1px solid {c["border"]}40">'
        f'{c["icon"]} {label}</span>'
    )
