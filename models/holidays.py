"""
ElderCare - Holiday calendar.

Hardcoded Jewish + Christian holiday dates for 2026 (the demo year). Each
holiday carries a suggested activity that the optimizer auto-inserts on
the holiday date. Religious-Christian elders see Christian holidays;
Jewish-observant elders see Jewish holidays; the default is Jewish
(matches the SaaS's primary market).

Add more holidays by editing the dict below — keys are ISO dates.
"""

from __future__ import annotations
import datetime as dt


# code prefix HOL_* — kept short so they fit in plan_items.activity_code.
HOLIDAYS: dict[str, dict] = {
    # ============= Jewish 2026 =============
    "2026-03-03": {
        "code": "HOL_PURIM", "name_he": "פורים", "name_en": "Purim",
        "name_ru": "Пурим", "religion": "jewish",
        "activity_he": "🎭 חגיגת פורים - קריאת מגילה, שירת \"שושנת יעקב\", משלוח מנות וסעודה חגיגית",
        "activity_en": "Purim celebration — Megillah reading, songs, mishloach manot",
        "activity_ru": "Празднование Пурима — чтение Мегилы, угощения",
        "duration_min": 60, "time_slot": "morning",
    },
    "2026-04-02": {
        "code": "HOL_PESACH", "name_he": "פסח - יום ראשון", "name_en": "Passover - day 1",
        "name_ru": "Песах - 1 день", "religion": "jewish",
        "activity_he": "🍷 פסח - סיפור יציאת מצרים, שירת \"דיינו\", הזכרת ליל הסדר",
        "activity_en": "Passover — Exodus story, songs, seder reminiscence",
        "activity_ru": "Песах — рассказ об Исходе, песни",
        "duration_min": 75, "time_slot": "morning",
    },
    "2026-04-14": {
        "code": "HOL_YOMHASHOAH", "name_he": "יום השואה",
        "name_en": "Holocaust Remembrance Day", "name_ru": "День памяти Холокоста",
        "religion": "jewish_civil",
        "activity_he": "🕯️ יום השואה - שיחה רגישה (לבחור עם נציג המשפחה אם להשתתף)",
        "activity_en": "Holocaust Day — sensitive discussion (family consult)",
        "activity_ru": "День памяти Холокоста — деликатная беседа",
        "duration_min": 30, "time_slot": "morning",
    },
    "2026-04-21": {
        "code": "HOL_YOMHAZIKARON", "name_he": "יום הזיכרון",
        "name_en": "Memorial Day", "name_ru": "День памяти",
        "religion": "jewish_civil",
        "activity_he": "🕯️ יום הזיכרון - האזנה לטקס, סיפורי גבורה",
        "activity_en": "Memorial Day — ceremony listening, stories of valor",
        "activity_ru": "День памяти — церемония, рассказы о героях",
        "duration_min": 45, "time_slot": "morning",
    },
    "2026-04-22": {
        "code": "HOL_YOMHAATZMAUT", "name_he": "יום העצמאות",
        "name_en": "Independence Day", "name_ru": "День независимости",
        "religion": "jewish_civil",
        "activity_he": "🇮🇱 יום העצמאות - שירי ארץ ישראל, סיפורי תקופת המדינה",
        "activity_en": "Independence Day — Israeli songs, stories of statehood",
        "activity_ru": "День независимости — израильские песни, истории",
        "duration_min": 60, "time_slot": "morning",
    },
    "2026-05-05": {
        "code": "HOL_LAGBAOMER", "name_he": "ל\"ג בעומר",
        "name_en": "Lag BaOmer", "name_ru": "Лаг ба-Омер",
        "religion": "jewish",
        "activity_he": "🔥 ל\"ג בעומר - שירי מדורה, סיפור רבי שמעון בר יוחאי",
        "activity_en": "Lag BaOmer — bonfire songs, Rabbi Shimon stories",
        "activity_ru": "Лаг ба-Омер — песни у костра",
        "duration_min": 45, "time_slot": "afternoon",
    },
    "2026-05-22": {
        "code": "HOL_SHAVUOT", "name_he": "שבועות",
        "name_en": "Shavuot", "name_ru": "Шавуот",
        "religion": "jewish",
        "activity_he": "🌾 שבועות - לימוד עשרת הדיברות, מאכלי חלב, קישוט בפרחים",
        "activity_en": "Shavuot — Ten Commandments learning, dairy meal",
        "activity_ru": "Шавуот — изучение Десяти заповедей, молочные блюда",
        "duration_min": 60, "time_slot": "morning",
    },
    "2026-09-12": {
        "code": "HOL_ROSHHASHANAH", "name_he": "ראש השנה",
        "name_en": "Rosh HaShanah", "name_ru": "Рош а-Шана",
        "religion": "jewish",
        "activity_he": "🍎 ראש השנה - תקיעת שופר, תפוח בדבש, ברכות שנה טובה",
        "activity_en": "Rosh HaShanah — shofar, apple with honey, new-year blessings",
        "activity_ru": "Рош а-Шана — шофар, яблоко с мёдом",
        "duration_min": 60, "time_slot": "morning",
    },
    "2026-09-21": {
        "code": "HOL_YOMKIPPUR", "name_he": "יום כיפור",
        "name_en": "Yom Kippur", "name_ru": "Йом-Кипур",
        "religion": "jewish",
        "activity_he": "📿 יום כיפור - פעילות שקטה, האזנה לחזנות, מנוחה",
        "activity_en": "Yom Kippur — quiet activity, hazzanut listening, rest",
        "activity_ru": "Йом-Кипур — тихая активность, отдых",
        "duration_min": 45, "time_slot": "morning",
    },
    "2026-09-26": {
        "code": "HOL_SUKKOT", "name_he": "סוכות",
        "name_en": "Sukkot", "name_ru": "Суккот",
        "religion": "jewish",
        "activity_he": "🌿 סוכות - ביקור בסוכה, ארבעת המינים, שירי סוכות",
        "activity_en": "Sukkot — sukkah visit, Four Species, festive songs",
        "activity_ru": "Суккот — посещение шалаша, праздничные песни",
        "duration_min": 60, "time_slot": "morning",
    },
    "2026-10-04": {
        "code": "HOL_SIMCHATTORAH", "name_he": "שמחת תורה",
        "name_en": "Simchat Torah", "name_ru": "Симхат Тора",
        "religion": "jewish",
        "activity_he": "📖 שמחת תורה - ריקוד מעגלי, שמחת התורה",
        "activity_en": "Simchat Torah — circle dancing, Torah celebration",
        "activity_ru": "Симхат Тора — танцы кругом",
        "duration_min": 60, "time_slot": "morning",
    },
    "2026-12-05": {
        "code": "HOL_HANUKKAH1", "name_he": "חנוכה - יום ראשון",
        "name_en": "Hanukkah day 1", "name_ru": "Ханука - день 1",
        "religion": "jewish",
        "activity_he": "🕎 חנוכה - הדלקת נר ראשון, סופגניות, סיפור החשמונאים",
        "activity_en": "Hanukkah day 1 — candle lighting, sufganiyot, Maccabees story",
        "activity_ru": "Ханука — зажжение свечи, суфганиёт",
        "duration_min": 45, "time_slot": "evening",
    },
    "2026-12-12": {
        "code": "HOL_HANUKKAH8", "name_he": "חנוכה - יום שמיני",
        "name_en": "Hanukkah day 8", "name_ru": "Ханука - день 8",
        "religion": "jewish",
        "activity_he": "🕎 חנוכה - חנוכייה מלאה, סביבון, סופגניות",
        "activity_en": "Hanukkah final night — full menorah, dreidel, sufganiyot",
        "activity_ru": "Последняя ночь Хануки — полная менора",
        "duration_min": 45, "time_slot": "evening",
    },

    # ============= Christian 2026 =============
    "2026-01-07": {
        "code": "HOL_ORTHCHRISTMAS", "name_he": "חג המולד אורתודוקסי",
        "name_en": "Orthodox Christmas", "name_ru": "Православное Рождество",
        "religion": "christian_orthodox",
        "activity_he": "🎄 חג המולד אורתודוקסי - שירי מולד, סיפור הלידה",
        "activity_en": "Orthodox Christmas — carols, nativity story",
        "activity_ru": "Православное Рождество — колядки, рассказ о Рождестве",
        "duration_min": 60, "time_slot": "morning",
    },
    "2026-04-05": {
        "code": "HOL_EASTER_W", "name_he": "פסחא (מערבי)",
        "name_en": "Easter (Western)", "name_ru": "Пасха (зап.)",
        "religion": "christian",
        "activity_he": "✝️ פסחא - שיחה על תקווה ותחיה, פרחי אביב",
        "activity_en": "Easter — hope & resurrection talk, spring flowers",
        "activity_ru": "Пасха — беседа о надежде",
        "duration_min": 60, "time_slot": "morning",
    },
    "2026-04-12": {
        "code": "HOL_EASTER_O", "name_he": "פסחא (אורתודוקסי)",
        "name_en": "Easter (Orthodox)", "name_ru": "Пасха (правосл.)",
        "religion": "christian_orthodox",
        "activity_he": "✝️ פסחא אורתודוקסית - מסורת, שיחה רוחנית",
        "activity_en": "Orthodox Easter — tradition, spiritual talk",
        "activity_ru": "Православная Пасха — традиция",
        "duration_min": 60, "time_slot": "morning",
    },
    "2026-12-24": {
        "code": "HOL_CHRISTMASEVE", "name_he": "ערב חג המולד",
        "name_en": "Christmas Eve", "name_ru": "Сочельник",
        "religion": "christian",
        "activity_he": "🎄 ערב חג המולד - מנגינות, נרות, סיפור הלידה",
        "activity_en": "Christmas Eve — carols, candles, nativity story",
        "activity_ru": "Сочельник — колядки, свечи",
        "duration_min": 60, "time_slot": "evening",
    },
    "2026-12-25": {
        "code": "HOL_CHRISTMAS", "name_he": "חג המולד",
        "name_en": "Christmas", "name_ru": "Рождество",
        "religion": "christian",
        "activity_he": "🎁 חג המולד - מתנות, מנגינות, סעודה משפחתית",
        "activity_en": "Christmas — gifts, carols, family meal",
        "activity_ru": "Рождество — подарки, песни, ужин",
        "duration_min": 75, "time_slot": "morning",
    },
}


def holiday_for_date(plan_date: dt.date | str) -> dict | None:
    """Return the holiday dict for plan_date, or None."""
    if isinstance(plan_date, dt.date):
        plan_date = plan_date.isoformat()
    return HOLIDAYS.get(plan_date)


def is_relevant_for_elder(holiday: dict, elder_demographic_codes: set[str]) -> bool:
    """Decide if this elder should see the holiday given their demographic tags.

    Default: Jewish holidays for everyone unless explicitly Christian.
    Christian holidays only if elder has a Christian tag (we don't have one
    yet in the bank — caller can extend by adding CON_christian etc.).
    """
    religion = holiday.get("religion", "")
    if religion.startswith("christian"):
        # only if elder marked as Christian
        return "CON_christian" in elder_demographic_codes
    if religion == "jewish":
        # skip for explicitly Christian elders (no flag yet, so default include)
        return "CON_christian" not in elder_demographic_codes
    # civil holidays for everyone
    return True
