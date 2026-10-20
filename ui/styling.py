"""
MIA-inspired CSS for the Streamlit app.
- Elderly-friendly typography (larger base font, larger click targets)
- Full RTL for Hebrew (sidebar moves to the right, content flips)
- Category color palette
- Day-of-week cards
- Activity item cards with colored category strips
"""

import streamlit as st
import streamlit.components.v1 as components


# Domain colour-coding from the MIA design system (forest-teal theme). Each
# soft background is paired with a deep text colour so category pills stay
# readable at WCAG 2.0 AA (contrast >= 4.5:1).
CATEGORY_COLORS = {
    "sport":      {"bg": "#DBEEE1", "border": "#2A7849", "text": "#14432A", "icon": "🏃"},
    "physical":   {"bg": "#E1EAF5", "border": "#2E68A8", "text": "#163A5C", "icon": "💪"},
    "cognitive":  {"bg": "#ECE4F5", "border": "#7A4FAA", "text": "#3B2659", "icon": "🧠"},
    "social":     {"bg": "#F5E9D6", "border": "#A15F0C", "text": "#5C3607", "icon": "👥"},
    "mental":     {"bg": "#F5DFE7", "border": "#AE4069", "text": "#5E2239", "icon": "🌿"},
    "medical":    {"bg": "#F5DDD9", "border": "#AE3529", "text": "#5E1C16", "icon": "🏥"},
    "nursing":    {"bg": "#D8E9E1", "border": "#1D6A56", "text": "#0E3A2E", "icon": "🩺"},
    "preferences": {"bg": "#F4E7CD", "border": "#935A0B", "text": "#5A3707", "icon": "⭐"},
    "external":   {"bg": "#E7ECD6", "border": "#55652A", "text": "#333D18", "icon": "🏛️"},
    "holiday":    {"bg": "#F4E7CD", "border": "#935A0B", "text": "#5A3707", "icon": "🎉"},
    "general":    {"bg": "#E4EAE5", "border": "#66766F", "text": "#2B3A33", "icon": "📌"},
    "meal":       {"bg": "#F4E7CD", "border": "#935A0B", "text": "#5A3707", "icon": "🍽️"},
}


# Base CSS that applies for all languages.
# Design: calm, modern SaaS — white cards on a light neutral canvas, one brand
# colour (forest teal), clear hierarchy, no heavy gradients. The accessibility
# rules (focus ring, contrast, reduced motion, skip link) are kept as-is.
BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Hebrew:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root {
  --brand: #1D6A56; --brand-600: #175746; --brand-700: #124437;
  --brand-50: #EEF6F2; --brand-100: #DCEDE5; --brand-200: #BBDACB;
  --ink: #13201B; --ink-2: #33433D; --muted: #56665F;
  --line: #E2E8E4; --line-2: #CBD5CF;
  --canvas: #F4F6F5; --card: #FFFFFF; --soft: #F2F5F3;
  --accent-soft: var(--brand-50); --accent-text: var(--brand-700);
  --r-lg: 16px; --r-md: 12px; --r-sm: 8px;
  --sh-sm: 0 1px 2px rgba(16,24,40,.05);
  --sh-md: 0 4px 14px rgba(16,24,40,.06);
}

/* ---- SCROLLBAR (visible, not oversized) ---- */
* { scrollbar-width: auto; scrollbar-color: #9DB5AA transparent; }
::-webkit-scrollbar { width: 12px !important; height: 12px !important; }
::-webkit-scrollbar-track { background: transparent !important; }
::-webkit-scrollbar-thumb {
  background: #A9BFB4 !important; border-radius: 8px !important;
  border: 3px solid var(--canvas) !important; min-height: 48px !important;
}
::-webkit-scrollbar-thumb:hover { background: var(--brand) !important; }

/* "Back to top" floating button */
.back-to-top-link {
  position: fixed; bottom: 24px; right: 24px;
  width: 46px; height: 46px;
  background: var(--brand); color: white !important;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.25rem; font-weight: 700;
  text-decoration: none !important;
  box-shadow: 0 6px 18px rgba(16,24,40,.18);
  z-index: 9999; transition: transform .15s, background .15s;
}
.back-to-top-link:hover { transform: translateY(-2px); background: var(--brand-600); color: white !important; }

/* ============ CANVAS ============ */
[data-testid="stApp"], [data-testid="stAppViewContainer"] { background: var(--canvas) !important; }
body { background: var(--canvas); }
[data-testid="stMainBlockContainer"] {
  max-width: 1240px;
  padding-top: 1.2rem !important;
  padding-bottom: 4rem !important;
}
/* thin brand line across the top — DESKTOP ONLY (on phones Streamlit puts the
   "open sidebar" control in this header, so it keeps its normal height) */
@media (min-width: 769px) {
  [data-testid="stHeader"] {
    background: var(--brand) !important;
    height: 3px !important; min-height: 3px !important;
  }
  [data-testid="stToolbar"], [data-testid="stAppDeployButton"] { display: none !important; }
}

/* ============ SIDEBAR ============ */
[data-testid="stSidebar"] {
  background: #FFFFFF !important;
  border-inline-end: 1px solid var(--line);
  box-shadow: none;
}
[data-testid="stSidebarContent"] { padding-top: .4rem; }
.brand-logo {
  display: flex; align-items: center; gap: .7rem;
  padding: .2rem .1rem .9rem; margin-bottom: .4rem;
  border-bottom: 1px solid var(--line);
}
.brand-mark {
  width: 40px; height: 40px; border-radius: 12px; flex: 0 0 auto;
  background: var(--brand); color: #fff; font-weight: 800; font-size: 1.25rem;
  display: inline-flex; align-items: center; justify-content: center;
}
.brand-logo .logo-name { display: block; font-size: 1.25rem; font-weight: 800; color: var(--ink); line-height: 1.1; }
.brand-logo .logo-tag { display: block; font-size: .68rem; color: var(--muted); line-height: 1.3; }
.sb-group {
  font-size: .78rem; font-weight: 700; color: var(--muted);
  letter-spacing: .03em; margin: 1.05rem 0 .35rem;
}
.sb-user { display: flex; align-items: center; gap: .6rem; margin: .45rem 0 .35rem; }
.sb-avatar {
  width: 36px; height: 36px; border-radius: 50%; flex: 0 0 auto;
  background: var(--brand-100); color: var(--brand-700);
  font-weight: 700; font-size: .9rem;
  display: inline-flex; align-items: center; justify-content: center;
}
.sb-user-name { font-weight: 700; font-size: .95rem; line-height: 1.25; color: var(--ink); }
.sb-user-role { font-size: .8rem; color: var(--muted); line-height: 1.25; }
.sb-perm {
  display: inline-block; font-size: .78rem; color: var(--ink-2);
  background: var(--soft); border: 1px solid var(--line);
  border-radius: 999px; padding: .1rem .6rem; margin-bottom: .1rem;
}
.sb-perm b { color: var(--brand-700); }
.sb-sep { border-top: 1px solid var(--line); margin: 1rem 0 .5rem; }

/* Sidebar nav buttons — quiet list rows with an icon */
[data-testid="stSidebar"] .stButton button {
  justify-content: flex-start !important; text-align: start !important;
  background: transparent !important; border: 0 !important;
  border-inline-start: 3px solid transparent !important;
  color: var(--ink-2) !important; box-shadow: none !important;
  border-radius: 10px !important; margin-bottom: 2px;
  font-weight: 500 !important; font-size: .98rem !important;
  min-height: 2.55rem !important; padding: .45rem .7rem !important;
  transition: background .12s ease;
}
[data-testid="stSidebar"] .stButton button [data-testid="stIconMaterial"] { color: var(--muted); }
[data-testid="stSidebar"] .stButton button:hover { background: var(--soft) !important; transform: none; }
/* ACTIVE nav item (higher specificity than the row rule above) */
[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-primary"] {
  background: var(--brand-50) !important;
  border-inline-start: 3px solid var(--brand) !important;
  color: var(--brand-700) !important; font-weight: 700 !important;
}
[data-testid="stSidebar"] .stButton button[data-testid="stBaseButton-primary"] [data-testid="stIconMaterial"] { color: var(--brand); }
/* resident prev / next: small square icon buttons */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton button {
  justify-content: center !important; min-height: 2.3rem !important;
  padding: .25rem .4rem !important; border: 1px solid var(--line-2) !important;
  background: #fff !important; font-size: .9rem !important;
}
[data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label { font-size: .95rem; }
[data-testid="stSidebar"] [data-testid="stExpander"] {
  border: 1px solid var(--line) !important; border-radius: 12px !important; box-shadow: none !important;
}

/* A COLLAPSED expander must fully hide its content (Streamlit/RTL quirk). */
[data-testid="stMain"] details:not([open]) > [data-testid="stExpanderDetails"],
[data-testid="stSidebar"] details:not([open]) > [data-testid="stExpanderDetails"] {
  display: none !important;
}

/* ============ PAGE HEADER ============ */
.page-head { display: flex; align-items: center; gap: .9rem; margin: .1rem 0 1.15rem; }
.ph-icon {
  font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
  font-feature-settings: 'liga'; -webkit-font-feature-settings: 'liga';
  direction: ltr; font-size: 26px; line-height: 1; font-weight: normal;
  width: 48px; height: 48px; border-radius: 14px; flex: 0 0 auto;
  background: var(--brand-50); color: var(--brand);
  display: inline-flex; align-items: center; justify-content: center;
}
.page-head h1 {
  font-size: 1.6rem !important; font-weight: 700 !important;
  color: var(--ink) !important; margin: 0 !important; padding: 0 !important; line-height: 1.25 !important;
}
.page-head p { margin: .15rem 0 0 !important; color: var(--muted); font-size: .97rem; }
.section-label { font-weight: 700; color: var(--ink-2); font-size: .95rem; margin: .7rem 0 .45rem; }

/* ============ CARDS ============ */
[data-testid="stMain"] [data-testid="stExpander"],
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--card) !important;
  border: 1px solid var(--line) !important;
  border-radius: 14px !important;
  box-shadow: var(--sh-sm) !important;
  overflow: hidden;
}
[data-testid="stExpander"] summary { font-weight: 600; }

/* ---- METRICS ---- */
[data-testid="stMetric"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 14px; padding: .8rem 1rem; box-shadow: var(--sh-sm);
}
[data-testid="stMetricLabel"] p { color: var(--muted) !important; font-size: .88rem !important; font-weight: 600 !important; }
[data-testid="stMetricValue"] { color: var(--ink); font-weight: 700; font-size: 1.7rem; }

/* ---- BUTTONS ---- */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {
  font-size: 1rem !important; font-weight: 600 !important;
  padding: .5rem 1rem !important; min-height: 2.6rem !important;
  border-radius: 10px !important; border-width: 1px !important;
}
[data-testid="stMain"] [data-testid="stBaseButton-primary"],
[data-testid="stMain"] [data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--brand) !important; border: 1px solid var(--brand) !important;
  color: #fff !important; box-shadow: var(--sh-sm) !important;
}
[data-testid="stMain"] [data-testid="stBaseButton-primary"]:hover,
[data-testid="stMain"] [data-testid="stBaseButton-primaryFormSubmit"]:hover {
  background: var(--brand-600) !important; border-color: var(--brand-600) !important;
}
[data-testid="stMain"] [data-testid="stBaseButton-secondary"],
[data-testid="stMain"] [data-testid="stBaseButton-secondaryFormSubmit"] {
  background: #fff !important; border: 1px solid var(--line-2) !important; color: var(--ink-2) !important;
}
[data-testid="stMain"] [data-testid="stBaseButton-secondary"]:hover {
  background: var(--soft) !important; border-color: var(--brand-200) !important;
}
button:disabled { opacity: .55; cursor: not-allowed !important; }

/* ---- HEADINGS ---- */
[data-testid="stMain"] h1, [data-testid="stMain"] h2,
[data-testid="stMain"] h3, [data-testid="stMain"] h4 { color: var(--ink) !important; }

/* ---- TABS: segmented control ---- */
.stTabs [data-baseweb="tab-list"] {
  background: #E9EEEB; border: 0; border-radius: 12px;
  padding: 4px; gap: 0 !important; flex-wrap: wrap !important;
  box-shadow: none;
}
.stTabs [data-baseweb="tab"] {
  font-size: .92rem !important; font-weight: 600 !important;
  padding: .4rem .55rem !important; min-height: 2.3rem !important;
  border-radius: 9px !important; white-space: nowrap !important;
  color: var(--ink-2) !important; background: transparent !important; border: 0 !important;
}
.stTabs [data-baseweb="tab"]:hover { background: rgba(255,255,255,.6) !important; }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  background: #fff !important; color: var(--brand-700) !important;
  box-shadow: 0 1px 3px rgba(16,24,40,.12);
}
.stTabs [data-baseweb="tab"][aria-selected="true"] * { color: var(--brand-700) !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1rem; }

/* ---- INPUTS ---- */
[data-testid="stMain"] input, [data-testid="stMain"] textarea,
[data-testid="stMain"] [data-baseweb="select"] > div,
[data-testid="stMain"] [data-baseweb="input"] {
  border-radius: 10px !important;
  border: 1px solid var(--line-2) !important;
  background: #fff !important;
}
/* ...but the tiny search input INSIDE a select / multiselect must stay
   transparent and borderless (otherwise a white box covers the first letter). */
[data-testid="stMain"] [data-baseweb="select"] input {
  border: none !important; background: transparent !important;
  border-radius: 0 !important; box-shadow: none !important; min-width: 2px !important;
}

/* ---- MULTISELECT TAGS (RTL): full Hebrew label, × on the left ---- */
[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  overflow: visible !important; padding-inline: 6px !important;
}
[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="tag"] {
  direction: rtl !important; flex-direction: row !important;
  max-width: none !important; overflow: visible !important;
  margin: 2px 4px !important; padding-inline-start: 10px !important;
  padding-inline-end: 4px !important; column-gap: 4px !important;
  background: var(--brand-50) !important; color: var(--brand-700) !important;
  border-radius: 999px !important;
}
[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="tag"] span[title],
[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="tag"] > span {
  max-width: none !important; overflow: visible !important; text-overflow: clip !important;
}
[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="tag"] > span[title] { order: 1 !important; }
[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="tag"] > span:not([title]) {
  order: 2 !important; flex: 0 0 auto !important;
}

/* ---- DATAFRAMES ---- */
[data-testid="stMain"] [data-testid="stDataFrame"] {
  border: 1px solid var(--line); border-radius: 12px; overflow: hidden; box-shadow: var(--sh-sm);
}

/* ---- TYPOGRAPHY ---- */
html, body,
[class*="st-"]:not([data-testid="stIconMaterial"]),
button, input, textarea, select,
[data-testid="stMarkdownContainer"] {
  font-family: 'IBM Plex Sans Hebrew', 'IBM Plex Sans', system-ui, 'Segoe UI', 'Arial', sans-serif;
  font-size: 16px;
  line-height: 1.6;                 /* >= 1.5 for readability (WCAG 1.4.8) */
}
/* NEVER let the text font touch Streamlit's Material icons (ligature font). */
span[data-testid="stIconMaterial"],
[data-testid="stIconMaterial"] {
  font-family: 'Material Symbols Rounded', 'Material Symbols Outlined',
               'Material Icons Rounded', 'Material Icons' !important;
  font-weight: normal !important; font-style: normal !important;
  letter-spacing: normal !important; text-transform: none !important;
  white-space: nowrap !important; word-wrap: normal !important;
  direction: ltr !important;
  font-feature-settings: 'liga' !important; -webkit-font-feature-settings: 'liga' !important;
  text-rendering: optimizeLegibility !important; -webkit-font-smoothing: antialiased !important;
}
p, li, [data-testid="stMarkdownContainer"] p { letter-spacing: normal; }
h1 { font-size: 1.9rem !important; font-weight: 700 !important; }
h2 { font-size: 1.5rem !important; font-weight: 700 !important; }
h3 { font-size: 1.25rem !important; font-weight: 700 !important; }
h4 { font-size: 1.08rem !important; font-weight: 700 !important; margin-top: .4rem !important; }

.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stSelectbox div[role="combobox"], .stDateInput input {
  font-size: 1rem !important; min-height: 2.6rem !important;
}
.stTextInput label, .stTextArea label, .stNumberInput label,
.stSelectbox label, .stDateInput label, .stRadio label, .stCheckbox label,
.stMultiSelect label, .stSlider label, .stTimeInput label {
  font-size: .95rem !important; font-weight: 600 !important; color: var(--ink-2) !important;
}

/* =====================================================================
   ACCESSIBILITY — ת"י 5568 / WCAG 2.0 AA
   ===================================================================== */
/* 2.4.7 Focus Visible — a clear, high-contrast keyboard focus ring */
[data-testid="stApp"] a:focus,
[data-testid="stApp"] button:focus-visible,
[data-testid="stApp"] input:focus,
[data-testid="stApp"] textarea:focus,
[data-testid="stApp"] select:focus,
[data-testid="stApp"] summary:focus,
[data-testid="stApp"] [role="button"]:focus-visible,
[data-testid="stApp"] [role="tab"]:focus-visible,
[data-testid="stApp"] [data-baseweb="tab"]:focus-visible,
[data-testid="stApp"] [tabindex]:focus-visible,
[data-testid="stSidebar"] .stButton button:focus-visible {
  outline: 3px solid var(--brand-700) !important;
  outline-offset: 2px !important;
  box-shadow: 0 0 0 3px #ffffff, 0 0 0 6px var(--brand-700) !important;
  border-radius: 8px !important;
}
[data-baseweb="select"]:focus-within,
[data-baseweb="input"]:focus-within {
  outline: 3px solid var(--brand-700) !important; outline-offset: 1px !important;
}
/* 1.4.1 Use of Colour — in-content links carry an underline */
[data-testid="stMain"] a:not(.back-to-top-link):not([class*="brand"]) {
  color: var(--brand-700); text-decoration: underline; text-underline-offset: 2px;
}
/* 2.3.3 respect the OS "reduce motion" setting */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important; animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important; scroll-behavior: auto !important;
  }
}
/* 2.4.1 Bypass Blocks — skip link that appears on focus */
.sr-only {
  position: absolute !important; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}
.skip-link {
  position: fixed; top: -80px; inset-inline-start: 12px; z-index: 100000;
  background: var(--brand-700); color: #fff !important; padding: .6rem 1rem;
  border-radius: 0 0 10px 10px; text-decoration: none !important;
  font-weight: 700; font-size: 1rem; transition: top .15s;
}
.skip-link:focus { top: 0; outline: 3px solid #fde047; outline-offset: 2px; }

/* ============ COMPONENTS ============ */
/* Institution banner */
.org-banner {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--r-lg); padding: .9rem 1.2rem; margin-bottom: .7rem;
  box-shadow: var(--sh-sm);
}
.org-banner-top { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }
.org-banner-name { font-size: 1.2rem; font-weight: 700; color: var(--ink); }
.org-banner-manager { font-size: .92rem; color: var(--muted); }
.org-banner-row { display: flex; gap: .4rem; flex-wrap: wrap; margin-top: .5rem; }
.org-chip {
  display: inline-flex; align-items: center; gap: .25rem;
  background: var(--soft); border: 1px solid var(--line); border-radius: 999px;
  padding: .1rem .65rem; font-size: .86rem; color: var(--ink-2);
}
.org-banner-desc { font-size: .88rem; color: var(--muted); margin-top: .55rem; }

/* Resident card */
.eldercare-header {
  display: flex; align-items: center; gap: 1rem;
  background: linear-gradient(135deg, #FFFFFF 0%, var(--brand-50) 100%);
  border: 1px solid var(--line); border-radius: var(--r-lg);
  padding: 1rem 1.25rem; margin: .4rem 0 .9rem; box-shadow: var(--sh-sm);
}
.eh-avatar {
  width: 58px; height: 58px; border-radius: 50%; flex: 0 0 auto;
  background: var(--brand); color: #fff; font-weight: 700; font-size: 1.3rem;
  display: inline-flex; align-items: center; justify-content: center;
}
.eldercare-header h2 { margin: 0 0 .35rem !important; padding: 0 !important; font-size: 1.45rem !important; color: var(--ink) !important; }
.eldercare-header .subtitle { display: flex; flex-wrap: wrap; gap: .35rem; }
.eh-chip {
  background: #fff; border: 1px solid var(--brand-100); color: var(--brand-700);
  border-radius: 999px; padding: .05rem .65rem; font-size: .86rem; font-weight: 500;
}

/* Resident strip on the resident sub-screens */
.resident-banner {
  display: flex; align-items: center; gap: .55rem; flex-wrap: wrap;
  background: var(--card); border: 1px solid var(--line); border-radius: var(--r-md);
  padding: .5rem .8rem; margin: 0 0 1rem; font-size: 1rem; color: var(--ink);
  box-shadow: var(--sh-sm);
}
.rb-avatar {
  width: 30px; height: 30px; border-radius: 50%; background: var(--brand-100); color: var(--brand-700);
  display: inline-flex; align-items: center; justify-content: center; font-size: .8rem; font-weight: 700;
}
.resident-banner .rb-room { font-size: .86rem; background: var(--soft); border-radius: 999px; padding: .05rem .6rem; color: var(--ink-2); }
.resident-banner .rb-hint { font-size: .8rem; color: var(--muted); margin-inline-start: auto; }

/* Staff */
.staff-card {
  background: #fff; border: 1px solid var(--line); border-radius: 14px;
  padding: .8rem 1rem; margin-bottom: .7rem; box-shadow: var(--sh-sm);
}
.staff-card.me { border-color: var(--brand-200); box-shadow: 0 0 0 3px var(--brand-50); }
.staff-card-role { color: var(--brand-700); font-weight: 700; font-size: .85rem; }
.staff-card-name { font-weight: 700; font-size: 1.08rem; margin: .1rem 0 .25rem; color: var(--ink); }
.staff-card-row { color: var(--muted); font-size: .92rem; }
.perm-chip { display: inline-block; margin-top: .45rem; background: var(--brand-50); color: var(--brand-700);
  border-radius: 999px; padding: .05rem .6rem; font-size: .8rem; font-weight: 600; }
.me-tag { font-size: .72rem; background: var(--brand); color: #fff; border-radius: 999px; padding: 0 .45rem; vertical-align: middle; }
.entered-by { color: var(--muted); font-size: .88rem; margin: .2rem 0 .7rem;
  background: var(--soft); border: 1px solid var(--line); border-radius: 999px;
  padding: .15rem .75rem; display: inline-block; }

/* Plan item (daily plan + tracking) */
.plan-item {
  display: flex; align-items: center; gap: .55rem; flex-wrap: wrap;
  border-inline-start: 4px solid var(--cat, var(--line-2)); padding-inline-start: .7rem;
}
.pi-time {
  font-variant-numeric: tabular-nums; direction: ltr; font-weight: 700; font-size: .92rem;
  background: var(--soft); border-radius: 8px; padding: .05rem .5rem; color: var(--ink-2);
}
.pi-title { font-weight: 700; font-size: 1.05rem; color: var(--ink); }
.done-tick {
  display: inline-flex; width: 20px; height: 20px; border-radius: 50%;
  background: #1E7B4F; color: #fff; font-size: .72rem; align-items: center; justify-content: center;
  margin-inline-end: .35rem; vertical-align: middle;
}
.pi-meta { display: flex; flex-wrap: wrap; align-items: center; gap: .3rem .4rem; margin-top: .5rem; }
.pi-dur { color: var(--muted); font-size: .85rem; }
.why { color: var(--muted); font-size: .82rem; font-weight: 600; margin-inline-start: .35rem; }
.why-lead { font-size: .82rem; font-weight: 700; color: var(--ink-2); margin-inline-end: .15rem; }
.why-chip {
  display: inline-block; background: var(--brand-50); color: var(--brand-700);
  border-radius: 999px; padding: .02rem .55rem; font-size: .8rem; font-weight: 500; line-height: 1.6;
}
.why-chip.soft { background: var(--soft); color: var(--ink-2); }
.why-chip.warn { background: #FFF4E5; color: #8A4B08; }
.goal-tags { display: inline-flex; flex-wrap: wrap; gap: .25rem; margin-inline-start: .3rem; }
.status-pill { margin-inline-start: auto; font-size: .8rem; font-weight: 700; border-radius: 999px; padding: .05rem .65rem; }
.status-pill.done { background: #E3F4EA; color: #17603A; }
.status-pill.skip { background: #FDECEC; color: #9B1C1C; }
.status-pill.pending { background: var(--soft); color: var(--muted); }
.day-divider { font-weight: 700; color: var(--ink-2); margin: 1.2rem 0 .45rem; padding-bottom: .3rem; border-bottom: 1px solid var(--line); }
.activity-cat-pill {
  display: inline-block; padding: .02rem .6rem; border-radius: 999px;
  font-size: .78rem; font-weight: 700;
}

/* Weekly view */
.week-title { text-align: center; font-size: 1.1rem; color: var(--ink-2); }
.week-title b { color: var(--ink); }
.day-card {
  background: #fff; border: 1px solid var(--line); border-radius: 14px;
  padding: .9rem; margin-bottom: .6rem; box-shadow: var(--sh-sm);
}
.day-card-header {
  display: flex; align-items: center; justify-content: space-between; gap: .5rem;
  border-bottom: 1px solid var(--line); padding-bottom: .55rem; margin-bottom: .65rem;
}
.day-badge { display: inline-flex; align-items: center; gap: .5rem; font-weight: 700; color: var(--ink); font-size: 1.02rem; }
.day-number {
  background: var(--brand-50); color: var(--brand-700); border-radius: 999px;
  width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center;
  font-size: .9rem; font-weight: 700;
}
.day-date { color: var(--muted); font-size: .88rem; font-weight: 500; }
.day-stats { font-size: .82rem; color: var(--muted); font-weight: 600; background: var(--soft); border-radius: 999px; padding: .05rem .55rem; }
.day-today { border-color: var(--brand) !important; box-shadow: 0 0 0 3px var(--brand-50) !important; }
.day-today .day-number { background: var(--brand); color: #fff; }
.activity-item {
  display: flex; align-items: center; gap: .45rem;
  background: #F7F9F8; border-radius: 8px;
  border-inline-start: 3px solid var(--cat, var(--line-2));
  padding: .3rem .55rem; margin-bottom: .3rem; font-size: .9rem;
}
.activity-item.done { background: #EAF6EF; color: var(--muted); }
.activity-item.done .activity-name { text-decoration: line-through; }
.activity-time { font-weight: 700; direction: ltr; min-width: 2.9rem; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.day-empty { color: var(--muted); font-size: .85rem; font-style: italic; }

/* Facility group board */
.board-session { background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: .55rem .85rem; margin-bottom: .4rem; }
.bs-top { display: flex; flex-wrap: wrap; align-items: center; gap: .25rem .55rem; }
.bs-time { font-weight: 700; background: var(--soft); border-radius: 8px; padding: 0 .45rem; direction: ltr; }
.bs-label { color: var(--muted); font-size: .9rem; }
.bs-count { background: var(--brand-50); color: var(--brand-700); border-radius: 999px; padding: .02rem .6rem; font-weight: 700; font-size: .85rem; margin-inline-start: auto; white-space: nowrap; }
.bs-names { color: var(--muted); font-size: .85rem; margin-top: .3rem; }

/* Family contact card */
.family-card {
  background: #fff; border: 1px solid var(--line); border-radius: 14px;
  padding: .85rem 1rem; margin-bottom: .6rem; box-shadow: var(--sh-sm);
}
.family-card.primary { border-color: #E8C27A; background: #FFFBF2; }
.family-card .name { font-size: 1.05rem; font-weight: 700; color: var(--ink); }
.family-card .relation { color: var(--muted); font-size: .92rem; }
.family-card .phone { font-size: 1rem; color: var(--ink-2); font-weight: 600; margin-top: .3rem; }
.family-card .notes { font-size: .88rem; color: var(--muted); margin-top: .35rem; }
.primary-badge {
  display: inline-block; background: #F5E3BF; color: #6B4508;
  padding: .05rem .55rem; border-radius: 999px; font-size: .75rem; font-weight: 700;
  margin-inline-end: .4rem;
}

/* ============ PRINT ============ */
@media print {
  [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"],
  .back-to-top-link, .skip-link, .stButton, .stDownloadButton, .stFormSubmitButton {
    display: none !important;
  }
  [data-testid="stAppViewContainer"] { display: block !important; }
  [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
    width: 100% !important; max-width: 100% !important; padding: 0 !important; margin: 0 !important;
  }
  body, [data-testid="stApp"] { background: #fff !important; }
  * { box-shadow: none !important;
      -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}

/* ============ MOBILE / PHONE (≤ 768px) ============ */
@media (max-width: 768px) {
  html, body, [class*="st-"] { font-size: 15px; line-height: 1.5; }
  h1 { font-size: 1.45rem !important; }
  h2 { font-size: 1.25rem !important; }
  h3 { font-size: 1.1rem !important; }
  h4 { font-size: 1rem !important; }
  ::-webkit-scrollbar { width: 8px !important; height: 8px !important; }
  [data-testid="stMainBlockContainer"] { padding: .8rem .7rem 3rem !important; }
  /* the "expanded" sidebar becomes a fixed overlay on the RIGHT */
  [data-testid="stSidebar"] {
    position: fixed !important; top: 0 !important; bottom: 0 !important;
    right: 0 !important; left: auto !important;
    width: min(86vw, 330px) !important; max-width: 86vw !important;
    height: 100% !important; z-index: 999990 !important;
    box-shadow: -8px 0 34px rgba(15,23,42,0.30) !important;
  }
  [data-testid="stMain"] { width: 100% !important; }
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    width: 100% !important; flex: 1 1 100% !important; min-width: 0 !important;
  }
  .page-head h1 { font-size: 1.3rem !important; }
  .ph-icon { width: 40px; height: 40px; font-size: 22px; }
  .eldercare-header { padding: .8rem .9rem; }
  .eh-avatar { width: 46px; height: 46px; font-size: 1.05rem; }
  .eldercare-header h2 { font-size: 1.2rem !important; }
  .org-banner { padding: .7rem .85rem; }
  .stButton button, .stDownloadButton button, .stFormSubmitButton button {
    font-size: .95rem !important; padding: .45rem .8rem !important; min-height: 2.5rem !important;
  }
  .stTabs [data-baseweb="tab"] { font-size: .85rem !important; padding: .35rem .55rem !important; }
  [data-testid="stMetric"] { padding: .6rem .8rem; }
  [data-testid="stMetricValue"] { font-size: 1.35rem; }
  [data-testid="stDataFrame"], [data-testid="stTable"] { overflow-x: auto !important; }
  .back-to-top-link { width: 42px; height: 42px; font-size: 1.15rem; bottom: 16px; }
}
</style>
"""


# RTL-only overrides — applied just when language is Hebrew/Arabic.
RTL_CSS = """
<style>
html { scroll-behavior: smooth; }

/* RTL applies to the inner text content, NOT to the outer flex/scroll
   containers (flipping stAppViewContainer itself broke the scroll bar). */
[data-testid="stMain"] { direction: rtl; text-align: right; }
[data-testid="stSidebar"] { direction: rtl; text-align: right; }
[data-testid="stSidebar"] * { text-align: right; }

/* Markdown blocks and widget labels default to LEFT; force right. */
[data-testid="stMain"] [data-testid="stMarkdownContainer"],
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] h1,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] h3,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] h4,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] h5,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] ul,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] ol,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] li,
[data-testid="stMain"] [data-testid="stWidgetLabel"],
[data-testid="stMain"] [data-testid="stWidgetLabel"] p,
[data-testid="stMain"] label {
  text-align: right;
}
[data-testid="stMain"] .eldercare-header,
[data-testid="stMain"] .org-banner,
[data-testid="stMain"] .resident-banner { text-align: right; }

/* Sidebar on the RIGHT (RTL-correct) via row-reverse on the top-level
   [sidebar, main] container. The document stays LTR (only lang is set, not
   dir) because dir=rtl on <html> made Streamlit Cloud drop the sidebar. */
[data-testid="stAppViewContainer"] { flex-direction: row-reverse; }

.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stDateInput input { direction: rtl; text-align: right; }

/* DataFrames stay LTR. */
.stDataFrame, .stDataFrame table { direction: ltr; }

/* Phone / email / URL fragments stay LTR inside RTL prose. */
.ltr-text { direction: ltr; display: inline-block; unicode-bidi: embed; }

/* In RTL the floating "back to top" button moves to the left edge. */
.back-to-top-link { right: auto !important; left: 24px !important; }
</style>
"""


def inject(lang: str = "he") -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    if lang in {"he", "ar"}:
        st.markdown(RTL_CSS, unsafe_allow_html=True)

    # Set <html lang> on the REAL document so screen readers announce the correct
    # language (WCAG 3.1.1). st.markdown strips <script>, so use a 0-height
    # components iframe (its scripts DO run) that reaches the parent document.
    # NOTE: we deliberately set ONLY lang, not dir="rtl" — setting dir on <html>
    # made Streamlit Cloud's app iframe drop the sidebar entirely. Visual RTL is
    # applied via `direction: rtl` on stMain/stSidebar (RTL_CSS) instead.
    components.html(
        "<script>try{window.parent.document.documentElement.lang='" + lang + "';}"
        "catch(e){}</script>",
        height=0,
    )

    # Skip-to-content link (WCAG 2.4.1) — first focusable element on the page.
    skip_text = {"he": "דלג לתוכן הראשי", "ru": "Перейти к содержимому",
                 "en": "Skip to main content"}.get(lang, "Skip to main content")
    st.markdown(
        f'<a href="#page-top" class="skip-link">{skip_text}</a>'
        f'<a id="page-top" name="page-top"></a>',
        unsafe_allow_html=True,
    )

    # Floating "back to top" button — labelled for screen readers, emoji hidden.
    title_text = {"he": "חזרה למעלה", "ru": "Наверх", "en": "Back to top"}.get(lang, "Back to top")
    st.markdown(
        f'<a href="#page-top" class="back-to-top-link" title="{title_text}" '
        f'aria-label="{title_text}"><span aria-hidden="true">⬆️</span></a>',
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
