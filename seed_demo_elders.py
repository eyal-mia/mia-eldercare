"""
ElderCare - Demo seeder.
Inserts 30 realistic elderly residents with characteristic comorbidity
patterns, fills their 9-dimension profile, and generates a daily plan
for each so the UI is immediately populated.

Idempotent: skips elders whose name already exists.
Run:  python seed_demo_elders.py
"""

from __future__ import annotations
from pathlib import Path
import sys
import datetime as dt

# make Hebrew console output safe on any Windows codepage
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from data.schema import init_database, get_connection
from models.optimizer import generate_plan_for_elder


# Each demo elder: (name, birth_year, gender, room, lang,
#   medical, medication, nursing, cognitive, mental, social, family, demographic,
#   capability, preferred_categories, preferred_slots, weights{dim:w})
DEMO_ELDERS = [
    {
        "name": "רחל כהן",
        "birth_year": 1944, "gender": "female", "room": "101", "lang": "he",
        "medical": ["DIS001", "DIS002", "DIS004"],   # סוכרת + יל"ד + ארתריטיס ברך
        "medication": ["MED001", "MED004", "MED005"], # מטפורמין, סטטין, ACE-i
        "nursing": ["CON001"],   # עצמאית
        "cognitive": ["CON005"], # ירידה קלה
        "mental": [],
        "social": ["CON008"],    # בודדה
        "family": ["CON010"],    # תמיכה משפחתית
        "demographic": [],
        "capability": 4,
        "pref_cats": ["physical", "social"],
        "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 8, "medication": 6, "nursing": 4, "cognitive": 7,
                    "mental": 5, "social": 9, "family": 7, "demographic": 5, "cultural": 4},
        "cultural": [],
        "living": {"arrangement": "assisted_living", "floor": 1,
                   "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT003", "ACT014", "ACT017"],  # מים, קבוצת שיחה, ביקור מתנדבים
        "notes": "כאבי ברכיים, מעדיפה התעמלות במים",
        "family_contacts": [
            {"relation": "daughter", "name": "מירב כהן-לוי", "phone": "052-3456789",
             "email": "meirav.l@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "איש קשר עיקרי, מבקרת פעמיים בשבוע"},
            {"relation": "son", "name": "אמיר כהן", "phone": "054-7654321",
             "email": "amir.cohen@yahoo.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "גר בחו\"ל, שיחות וידיאו"},
            {"relation": "grandchild", "name": "נועה לוי", "phone": "058-1112233",
             "email": "", "is_primary": 0, "lives_with_elder": 0,
             "notes": "נכדה, מבקרת פעם בחודש"},
        ],
    },
    {
        "name": "משה לוי",
        "birth_year": 1948, "gender": "male", "room": "102", "lang": "he",
        "medical": ["DIS007", "DIS010"],   # פרקינסון + דיכאון
        "medication": ["MED009", "MED012"], # ל-דופא + SSRI
        "nursing": ["CON001"],
        "cognitive": ["CON004"],   # קוגניציה תקינה
        "mental": [],
        "social": [],
        "family": ["CON010"],
        "demographic": [],
        "capability": 3,
        "pref_cats": ["physical", "cognitive", "social"],
        "pref_slots": ["morning"],
        "weights": {"medical": 9, "medication": 8, "nursing": 5, "cognitive": 6,
                    "mental": 8, "social": 7, "family": 6, "demographic": 5, "cultural": 6},
        "cultural": ["CON014"],  # עולה חדש
        "living": {"arrangement": "assisted_living", "floor": 2,
                   "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT005", "ACT008", "ACT012"],  # טאי צ'י, דיבור, אומנות
        "notes": "פרקינסון - מעדיף פעילות בבוקר כשהתרופה פעילה",
        "family_contacts": [
            {"relation": "wife", "name": "נינה לוי", "phone": "050-9876543",
             "email": "", "is_primary": 1, "lives_with_elder": 1,
             "notes": "אשה, מטפלת עיקרית, גם דוברת רוסית"},
            {"relation": "son", "name": "סשה לוי", "phone": "054-2223344",
             "email": "sasha.levy@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן, בקשר יומיומי"},
        ],
    },
    {
        "name": "שרה גולדברג",
        "birth_year": 1935, "gender": "female", "room": "103", "lang": "he",
        "medical": ["DIS006", "DIS009"],   # דמנציה בינונית + COPD
        "medication": ["MED010", "MED011"], # דונפזיל + ממנטין
        "nursing": ["CON002"],   # תלות חלקית
        "cognitive": ["CON006"],
        "mental": [],
        "social": [],
        "family": ["CON011"],    # ללא משפחה
        "demographic": [],
        "capability": 2,
        "pref_cats": ["mental", "cognitive"],
        "pref_slots": ["morning"],
        "weights": {"medical": 9, "medication": 7, "nursing": 8, "cognitive": 10,
                    "mental": 9, "social": 6, "family": 5, "demographic": 6, "cultural": 8},
        "cultural": ["CON013"],  # ניצולת שואה
        "living": {"arrangement": "nursing_home", "floor": 1,
                   "elevator": True, "outdoor": "limited"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT013", "ACT022", "ACT023"],  # מוסיקה, בעלי חיים, חדר חושים
        "notes": "ניצולת שואה - להימנע מתכנים טריגריים, מוסיקה מרגיעה",
        "family_contacts": [
            {"relation": "niece", "name": "טליה רוזן", "phone": "052-1234500",
             "email": "talia.rozen@walla.co.il", "is_primary": 1, "lives_with_elder": 0,
             "notes": "אחיינית, איש קשר עיקרי (אין ילדים)"},
        ],
    },
    {
        "name": "אברהם פרידמן",
        "birth_year": 1951, "gender": "male", "room": "104", "lang": "he",
        "medical": ["DIS014", "DIS002"],   # אחרי שבץ + יל"ד
        "medication": ["MED002", "MED005"], # וורפרין + ACE-i
        "nursing": ["CON002"],
        "cognitive": ["CON005"],
        "mental": [],
        "social": ["CON009"],
        "family": ["CON010"],
        "demographic": [],
        "capability": 3,
        "pref_cats": ["physical", "social"],
        "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 9, "medication": 8, "nursing": 7, "cognitive": 6,
                    "mental": 5, "social": 7, "family": 6, "demographic": 7, "cultural": 3},
        "cultural": [],
        "living": {"arrangement": "home_family", "floor": 0,
                   "elevator": False, "outdoor": "full"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT024", "ACT008", "ACT030"],  # פיזיו, דיבור, קפה ועיתון
        "notes": "פוסט שבץ - פיזיותרפיה וריפוי בדיבור פעילים",
        "family_contacts": [
            {"relation": "wife", "name": "שולה פרידמן", "phone": "050-3334455",
             "email": "shula.f@gmail.com", "is_primary": 1, "lives_with_elder": 1,
             "notes": "אשה, מטפלת עיקרית"},
            {"relation": "son", "name": "רון פרידמן", "phone": "054-6677889",
             "email": "ron.fri@hotmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן בכור, רופא"},
            {"relation": "daughter", "name": "ענת פרידמן-כץ", "phone": "058-9988776",
             "email": "anat.fk@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בת"},
        ],
    },
    {
        "name": "ברכה שטרן",
        "birth_year": 1938, "gender": "female", "room": "105", "lang": "he",
        "medical": ["DIS003", "DIS008", "DIS012"],   # אוסטאופורוזיס + אי"ל + שמיעה
        "medication": ["MED006", "MED008"], # בטא בלוקר + פוורסמיד
        "nursing": ["CON001"],
        "cognitive": ["CON004"],
        "mental": [],
        "social": ["CON009"],
        "family": ["CON010"],
        "demographic": [],
        "capability": 4,
        "pref_cats": ["social", "physical"],
        "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 8, "medication": 7, "nursing": 5, "cognitive": 5,
                    "mental": 5, "social": 8, "family": 7, "demographic": 5, "cultural": 7},
        "cultural": ["CON016"],  # דתית
        "living": {"arrangement": "sheltered_housing", "floor": 3,
                   "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "very_observant",
        "preferred": ["ACT027", "ACT007", "ACT014"],  # תפילה, נשימה, קבוצת שיחה
        "notes": "דתית - לכבד זמני תפילה, פעילות נפרדת מגדרית",
        "family_contacts": [
            {"relation": "son", "name": "יהודה שטרן", "phone": "052-7788991",
             "email": "yehuda.s@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "בן בכור, רב הקהילה"},
            {"relation": "daughter", "name": "חיה רובינשטיין", "phone": "054-1122334",
             "email": "", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בת, מבקרת בכל שבת"},
        ],
    },
    {
        "name": "יוסף ברק",
        "birth_year": 1942, "gender": "male", "room": "106", "lang": "he",
        "medical": ["DIS001", "DIS002", "DIS013"],   # סוכרת + יל"ד + ראייה
        "medication": ["MED015", "MED005"],          # אינסולין + ACE-i
        "nursing": ["CON001"],
        "cognitive": ["CON004"],
        "mental": [],
        "social": ["CON008"],
        "family": ["CON011"],
        "demographic": [],
        "capability": 4,
        "pref_cats": ["cognitive", "social", "mental"],
        "pref_slots": ["morning", "afternoon", "evening"],
        "weights": {"medical": 8, "medication": 8, "nursing": 4, "cognitive": 6,
                    "mental": 6, "social": 9, "family": 8, "demographic": 7, "cultural": 3},
        "cultural": [],
        "living": {"arrangement": "home_alone", "floor": 4,
                   "elevator": False, "outdoor": "none"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT013", "ACT014", "ACT017"],  # מוסיקה, שיחה, מתנדבים
        "notes": "ליקוי ראייה - הדפסה מוגדלת, פעילות שמע. גר בקומה 4 ללא מעלית - אין יציאה מהבית!",
        "family_contacts": [
            {"relation": "neighbor", "name": "דליה אבני", "phone": "050-4455667",
             "email": "", "is_primary": 1, "lives_with_elder": 0,
             "notes": "שכנה - איש קשר היחיד (אין משפחה)"},
        ],
    },
    {
        "name": "עליזה מזרחי",
        "birth_year": 1945, "gender": "female", "room": "107", "lang": "ar",
        "medical": ["DIS011", "DIS010", "DIS003"],   # חרדה + דיכאון + אוסטאופורוזיס
        "medication": ["MED012", "MED013"],          # SSRI + בנזודיאזפינים
        "nursing": ["CON001"],
        "cognitive": ["CON004"],
        "mental": ["CON012"],     # אבל טרי
        "social": ["CON008"],
        "family": ["CON010"],
        "demographic": [],
        "capability": 4,
        "pref_cats": ["mental", "social"],
        "pref_slots": ["morning"],
        "weights": {"medical": 7, "medication": 7, "nursing": 4, "cognitive": 5,
                    "mental": 10, "social": 8, "family": 7, "demographic": 6, "cultural": 8},
        "cultural": ["CON015"],  # דוברת ערבית
        "living": {"arrangement": "home_family", "floor": 0,
                   "elevator": False, "outdoor": "full"},
        "religion": "muslim", "religiosity": "observant",
        "preferred": ["ACT020", "ACT028", "ACT019"],  # קבוצת אבל, שפת אם, מיינדפולנס
        "notes": "אבל טרי - דוברת ערבית, מעדיפה קבוצת תמיכה",
        "family_contacts": [
            {"relation": "daughter", "name": "סלמא מזרחי", "phone": "052-5566778",
             "email": "salma.m@gmail.com", "is_primary": 1, "lives_with_elder": 1,
             "notes": "בת, גרה איתה, דוברת ערבית ועברית"},
            {"relation": "son", "name": "כרים מזרחי", "phone": "054-8899001",
             "email": "karim.miz@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן, רופא בבית חולים סורוקה"},
        ],
    },
    {
        "name": "דוד אזולאי",
        "birth_year": 1946, "gender": "male", "room": "108", "lang": "he",
        "medical": ["DIS007", "DIS002", "DIS015"],   # פרקינסון + יל"ד + אינקונטיננציה
        "medication": ["MED009", "MED005", "MED008"], # ל-דופא + ACE-i + פוורסמיד
        "nursing": ["CON002"],
        "cognitive": ["CON005"],
        "mental": [],
        "social": ["CON009"],
        "family": ["CON010"],
        "demographic": [],
        "capability": 3,
        "pref_cats": ["physical", "cognitive"],
        "pref_slots": ["morning"],
        "weights": {"medical": 9, "medication": 8, "nursing": 8, "cognitive": 7,
                    "mental": 5, "social": 6, "family": 5, "demographic": 6, "cultural": 3},
        "cultural": [],
        "living": {"arrangement": "home_family", "floor": 1,
                   "elevator": True, "outdoor": "limited"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT004", "ACT005", "ACT026"],  # איזון, טאי צ'י, רצפת אגן
        "notes": "פרקינסון + אינקונטיננציה - מפגשים קצרים ליד שירותים",
        "family_contacts": [
            {"relation": "wife", "name": "אילנה אזולאי", "phone": "050-2233445",
             "email": "ilana.az@gmail.com", "is_primary": 1, "lives_with_elder": 1,
             "notes": "אשה, מטפלת עיקרית"},
            {"relation": "son", "name": "אלון אזולאי", "phone": "054-7788990",
             "email": "alon.az@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן יחיד"},
        ],
    },
    {
        "name": "אסתר רובין",
        "birth_year": 1940, "gender": "female", "room": "109", "lang": "he",
        "medical": ["DIS006", "DIS001"],   # דמנציה + סוכרת
        "medication": ["MED011", "MED001"], # ממנטין + מטפורמין
        "nursing": ["CON002"],
        "cognitive": ["CON006"],
        "mental": [],
        "social": [],
        "family": ["CON010"],
        "demographic": [],
        "capability": 2,
        "pref_cats": ["mental", "social"],
        "pref_slots": ["morning"],
        "weights": {"medical": 9, "medication": 7, "nursing": 8, "cognitive": 9,
                    "mental": 7, "social": 7, "family": 8, "demographic": 6, "cultural": 3},
        "cultural": [],
        "living": {"arrangement": "nursing_home", "floor": 2,
                   "elevator": True, "outdoor": "limited"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT011", "ACT013", "ACT023"],  # רמיניסנציה, מוסיקה, חדר חושים
        "notes": "דמנציה בינונית - גרייה חושית, מוסיקה, רמיניסנציה",
        "family_contacts": [
            {"relation": "daughter", "name": "גלית רובין-שטראוס", "phone": "052-3344556",
             "email": "galit.rs@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "בת, איש קשר עיקרי, מבקרת 3 פעמים בשבוע"},
            {"relation": "son", "name": "אביב רובין", "phone": "054-5566778",
             "email": "aviv.r@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן"},
        ],
    },
    {
        "name": "יעקב שמש",
        "birth_year": 1954, "gender": "male", "room": "110", "lang": "he",
        "medical": ["DIS014", "DIS009", "DIS010"],   # פוסט שבץ + COPD + דיכאון
        "medication": ["MED003", "MED012"],          # אספירין + SSRI
        "nursing": ["CON001"],
        "cognitive": ["CON004"],
        "mental": [],
        "social": ["CON009"],
        "family": ["CON010"],
        "demographic": [],
        "capability": 3,
        "pref_cats": ["physical", "social", "cognitive"],
        "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 8, "medication": 6, "nursing": 5, "cognitive": 6,
                    "mental": 8, "social": 8, "family": 6, "demographic": 7, "cultural": 3},
        "cultural": [],
        "living": {"arrangement": "home_family", "floor": 2,
                   "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT007", "ACT024", "ACT014"],  # נשימה, פיזיו, קבוצת שיחה
        "notes": "פוסט שבץ + COPD - אימון נשימה, פיזיותרפיה",
        "family_contacts": [
            {"relation": "wife", "name": "רחל שמש", "phone": "050-6677889",
             "email": "rachel.shemesh@gmail.com", "is_primary": 1, "lives_with_elder": 1,
             "notes": "אשה"},
            {"relation": "daughter", "name": "טל שמש-בר", "phone": "054-9900112",
             "email": "tal.sb@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בת בכורה"},
            {"relation": "son", "name": "ניר שמש", "phone": "058-2233440",
             "email": "nir.shemesh@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן צעיר, מהנדס"},
        ],
    },

    # ============================================================
    # 20 additional demo residents (rooms 111-130). Same institution
    # (נווה שקט), varied conditions / capability tiers / religions /
    # languages so the demo shows the planner's full range.
    # ============================================================
    {
        "name": "חנה ברקוביץ'",
        "birth_year": 1943, "gender": "female", "room": "111", "lang": "he",
        "medical": ["DIS001", "DIS004"],   # סוכרת + ארתריטיס ברך
        "medication": ["MED001", "MED004"], # מטפורמין + סטטין
        "nursing": ["CON001"], "cognitive": ["CON005"], "mental": [],
        "social": ["CON008"], "family": ["CON010"], "demographic": [],
        "capability": 4,
        "pref_cats": ["physical", "social"], "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 8, "medication": 6, "nursing": 4, "cognitive": 6,
                    "mental": 5, "social": 8, "family": 7, "demographic": 5, "cultural": 4},
        "cultural": [],
        "living": {"arrangement": "assisted_living", "floor": 2, "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT003", "ACT014", "ACT004"],
        "notes": "כאבי ברכיים מארתריטיס - התעמלות במים, הליכות קצרות",
        "family_contacts": [
            {"relation": "daughter", "name": "אורלי ברקוביץ'-שגב", "phone": "052-4411220",
             "email": "orly.bs@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "בת, איש קשר עיקרי, מבקרת פעמיים בשבוע"},
            {"relation": "son", "name": "גיל ברקוביץ'", "phone": "054-3322110",
             "email": "gil.b@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן, מתגורר בצפון"},
        ],
    },
    {
        "name": "שמעון דהן",
        "birth_year": 1947, "gender": "male", "room": "112", "lang": "he",
        "medical": ["DIS002", "DIS008", "DIS010"],   # יל"ד + אי ספיקת לב + דיכאון
        "medication": ["MED006", "MED008", "MED012"], # בטא בלוקר + פורוסמיד + SSRI
        "nursing": ["CON001"], "cognitive": ["CON004"], "mental": [],
        "social": ["CON009"], "family": ["CON010"], "demographic": [],
        "capability": 3,
        "pref_cats": ["mental", "social", "physical"], "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 9, "medication": 8, "nursing": 5, "cognitive": 5,
                    "mental": 8, "social": 7, "family": 6, "demographic": 6, "cultural": 4},
        "cultural": [],
        "living": {"arrangement": "assisted_living", "floor": 1, "elevator": True, "outdoor": "limited"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT007", "ACT014", "ACT013"],
        "notes": "אי ספיקת לב - מאמץ מבוקר, ניטור עייפות. דיכאון קל.",
        "family_contacts": [
            {"relation": "wife", "name": "ג'קלין דהן", "phone": "050-7712340",
             "email": "", "is_primary": 1, "lives_with_elder": 1,
             "notes": "אשה, מטפלת עיקרית"},
            {"relation": "son", "name": "ליאור דהן", "phone": "054-8823450",
             "email": "lior.dahan@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן"},
        ],
    },
    {
        "name": "מרים אלקיים",
        "birth_year": 1939, "gender": "female", "room": "113", "lang": "he",
        "medical": ["DIS006", "DIS003"],   # דמנציה בינונית + אוסטאופורוזיס
        "medication": ["MED010", "MED011"], # דונפזיל + ממנטין
        "nursing": ["CON002"], "cognitive": ["CON006"], "mental": [],
        "social": [], "family": ["CON010"], "demographic": [],
        "capability": 2,
        "pref_cats": ["mental", "cognitive"], "pref_slots": ["morning"],
        "weights": {"medical": 8, "medication": 7, "nursing": 8, "cognitive": 10,
                    "mental": 8, "social": 6, "family": 7, "demographic": 6, "cultural": 4},
        "cultural": [],
        "living": {"arrangement": "nursing_home", "floor": 1, "elevator": True, "outdoor": "limited"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT011", "ACT013", "ACT023"],
        "notes": "דמנציה בינונית - רמיניסנציה, מוסיקה מוכרת, שגרה יציבה",
        "family_contacts": [
            {"relation": "daughter", "name": "רונית אלקיים-סבן", "phone": "052-6633440",
             "email": "ronit.es@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "בת, איש קשר עיקרי, מבקרת יומיום"},
            {"relation": "son", "name": "יורם אלקיים", "phone": "054-5544330",
             "email": "yoram.a@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן"},
        ],
    },
    {
        "name": "אליהו נחמיאס",
        "birth_year": 1950, "gender": "male", "room": "114", "lang": "he",
        "medical": ["DIS007", "DIS002"],   # פרקינסון + יל"ד
        "medication": ["MED009", "MED005"], # ל-דופא + ACE-i
        "nursing": ["CON002"], "cognitive": ["CON005"], "mental": [],
        "social": ["CON009"], "family": ["CON010"], "demographic": [],
        "capability": 3,
        "pref_cats": ["physical", "cognitive"], "pref_slots": ["morning"],
        "weights": {"medical": 9, "medication": 8, "nursing": 7, "cognitive": 7,
                    "mental": 5, "social": 6, "family": 6, "demographic": 5, "cultural": 3},
        "cultural": [],
        "living": {"arrangement": "assisted_living", "floor": 2, "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT005", "ACT004", "ACT007"],
        "notes": "פרקינסון - פעילות בבוקר כשהתרופה בשיא, טאי צ'י ואיזון",
        "family_contacts": [
            {"relation": "wife", "name": "סוזן נחמיאס", "phone": "050-3311220",
             "email": "", "is_primary": 1, "lives_with_elder": 1,
             "notes": "אשה, מטפלת עיקרית"},
            {"relation": "daughter", "name": "דנה נחמיאס-אלון", "phone": "054-2211330",
             "email": "dana.na@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בת, פיזיותרפיסטית"},
        ],
    },
    {
        "name": "פנינה גבאי",
        "birth_year": 1941, "gender": "female", "room": "115", "lang": "he",
        "medical": ["DIS009", "DIS011"],   # COPD + חרדה
        "medication": ["MED013", "MED012"], # בנזודיאזפינים + SSRI
        "nursing": ["CON001"], "cognitive": ["CON004"], "mental": [],
        "social": ["CON008"], "family": ["CON010"], "demographic": [],
        "capability": 3,
        "pref_cats": ["mental", "social"], "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 8, "medication": 7, "nursing": 5, "cognitive": 5,
                    "mental": 9, "social": 7, "family": 6, "demographic": 6, "cultural": 4},
        "cultural": [],
        "living": {"arrangement": "assisted_living", "floor": 3, "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT007", "ACT019", "ACT013"],
        "notes": "COPD + חרדה - אימון נשימה, מיינדפולנס, הרגעה",
        "family_contacts": [
            {"relation": "son", "name": "אבנר גבאי", "phone": "052-9922110",
             "email": "avner.g@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "בן, איש קשר עיקרי"},
        ],
    },
    {
        "name": "יצחק פרץ",
        "birth_year": 1945, "gender": "male", "room": "116", "lang": "he",
        "medical": ["DIS014", "DIS001"],   # פוסט שבץ + סוכרת
        "medication": ["MED003", "MED015"], # אספירין + אינסולין
        "nursing": ["CON002"], "cognitive": ["CON005"], "mental": [],
        "social": ["CON009"], "family": ["CON010"], "demographic": [],
        "capability": 3,
        "pref_cats": ["physical", "social"], "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 9, "medication": 8, "nursing": 7, "cognitive": 6,
                    "mental": 5, "social": 7, "family": 6, "demographic": 6, "cultural": 3},
        "cultural": [],
        "living": {"arrangement": "home_family", "floor": 0, "elevator": False, "outdoor": "full"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT024", "ACT008", "ACT004"],
        "notes": "פוסט שבץ + סוכרת - פיזיותרפיה, ריפוי דיבור, איזון סוכר",
        "family_contacts": [
            {"relation": "wife", "name": "מזל פרץ", "phone": "050-4433221",
             "email": "", "is_primary": 1, "lives_with_elder": 1,
             "notes": "אשה, מטפלת עיקרית"},
            {"relation": "son", "name": "קובי פרץ", "phone": "054-6655443",
             "email": "kobi.peretz@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן בכור"},
            {"relation": "daughter", "name": "סיגל פרץ-לוי", "phone": "058-7766554",
             "email": "sigal.pl@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בת"},
        ],
    },
    {
        "name": "לאה סויסה",
        "birth_year": 1937, "gender": "female", "room": "117", "lang": "he",
        "medical": ["DIS006", "DIS012"],   # דמנציה + ירידת שמיעה
        "medication": ["MED010", "MED011"], # דונפזיל + ממנטין
        "nursing": ["CON002"], "cognitive": ["CON006"], "mental": [],
        "social": [], "family": ["CON011"], "demographic": [],
        "capability": 2,
        "pref_cats": ["mental", "cognitive"], "pref_slots": ["morning"],
        "weights": {"medical": 8, "medication": 7, "nursing": 8, "cognitive": 10,
                    "mental": 9, "social": 6, "family": 5, "demographic": 6, "cultural": 8},
        "cultural": ["CON013"],  # ניצולת שואה
        "living": {"arrangement": "nursing_home", "floor": 1, "elevator": True, "outdoor": "limited"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT013", "ACT022", "ACT023"],
        "notes": "ניצולת שואה + ירידת שמיעה - להימנע מטריגרים, תקשורת ויזואלית, מוסיקה מרגיעה",
        "family_contacts": [
            {"relation": "niece", "name": "אביגיל דורון", "phone": "052-1122335",
             "email": "avigail.d@walla.co.il", "is_primary": 1, "lives_with_elder": 0,
             "notes": "אחיינית, איש קשר עיקרי (אין ילדים)"},
        ],
    },
    {
        "name": "אברהם וקנין",
        "birth_year": 1944, "gender": "male", "room": "118", "lang": "he",
        "medical": ["DIS002", "DIS013"],   # יל"ד + ליקוי ראייה
        "medication": ["MED005", "MED004"], # ACE-i + סטטין
        "nursing": ["CON001"], "cognitive": ["CON004"], "mental": [],
        "social": ["CON008"], "family": ["CON011"], "demographic": [],
        "capability": 4,
        "pref_cats": ["cognitive", "social", "mental"], "pref_slots": ["morning", "afternoon", "evening"],
        "weights": {"medical": 7, "medication": 6, "nursing": 4, "cognitive": 6,
                    "mental": 6, "social": 9, "family": 7, "demographic": 7, "cultural": 3},
        "cultural": [],
        "living": {"arrangement": "home_alone", "floor": 2, "elevator": True, "outdoor": "limited"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT013", "ACT014", "ACT017"],
        "notes": "ליקוי ראייה - פעילות מבוססת שמע, הדפסה מוגדלת. בודד.",
        "family_contacts": [
            {"relation": "neighbor", "name": "רותי שמעוני", "phone": "050-5566771",
             "email": "", "is_primary": 1, "lives_with_elder": 0,
             "notes": "שכנה - איש קשר עיקרי (אין משפחה קרובה)"},
        ],
    },
    {
        "name": "זהבה אוחיון",
        "birth_year": 1946, "gender": "female", "room": "119", "lang": "he",
        "medical": ["DIS003", "DIS010"],   # אוסטאופורוזיס + דיכאון
        "medication": ["MED012"],          # SSRI
        "nursing": ["CON001"], "cognitive": ["CON004"], "mental": ["CON012"],
        "social": ["CON008"], "family": ["CON010"], "demographic": [],
        "capability": 4,
        "pref_cats": ["mental", "social"], "pref_slots": ["morning"],
        "weights": {"medical": 7, "medication": 6, "nursing": 4, "cognitive": 5,
                    "mental": 10, "social": 8, "family": 7, "demographic": 5, "cultural": 5},
        "cultural": [],
        "living": {"arrangement": "sheltered_housing", "floor": 2, "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT020", "ACT019", "ACT014"],
        "notes": "אבל טרי על בן זוג + דיכאון - קבוצת תמיכה, הפעלה התנהגותית",
        "family_contacts": [
            {"relation": "daughter", "name": "מיטל אוחיון", "phone": "052-3344551",
             "email": "meital.o@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "בת, איש קשר עיקרי"},
            {"relation": "son", "name": "שי אוחיון", "phone": "054-4455662",
             "email": "shai.ohayon@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן"},
        ],
    },
    {
        "name": "ראובן חדד",
        "birth_year": 1940, "gender": "male", "room": "120", "lang": "he",
        "medical": ["DIS007", "DIS015"],   # פרקינסון + אינקונטיננציה
        "medication": ["MED009", "MED008"], # ל-דופא + פורוסמיד
        "nursing": ["CON002"], "cognitive": ["CON005"], "mental": [],
        "social": ["CON009"], "family": ["CON010"], "demographic": [],
        "capability": 2,
        "pref_cats": ["physical", "cognitive"], "pref_slots": ["morning"],
        "weights": {"medical": 9, "medication": 8, "nursing": 8, "cognitive": 7,
                    "mental": 5, "social": 6, "family": 5, "demographic": 6, "cultural": 3},
        "cultural": [],
        "living": {"arrangement": "nursing_home", "floor": 1, "elevator": True, "outdoor": "limited"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT004", "ACT005", "ACT026"],
        "notes": "פרקינסון מתקדם + אינקונטיננציה - מפגשים קצרים ליד שירותים, תרגול רצפת אגן",
        "family_contacts": [
            {"relation": "daughter", "name": "אילנית חדד", "phone": "052-8877660",
             "email": "ilanit.h@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "בת, איש קשר עיקרי"},
        ],
    },
    {
        "name": "ציונה מלכה",
        "birth_year": 1948, "gender": "female", "room": "121", "lang": "he",
        "medical": ["DIS001", "DIS002", "DIS011"],   # סוכרת + יל"ד + חרדה
        "medication": ["MED001", "MED005", "MED013"], # מטפורמין + ACE-i + בנזו
        "nursing": ["CON001"], "cognitive": ["CON004"], "mental": [],
        "social": ["CON009"], "family": ["CON010"], "demographic": [],
        "capability": 4,
        "pref_cats": ["mental", "social", "physical"], "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 8, "medication": 7, "nursing": 4, "cognitive": 5,
                    "mental": 9, "social": 8, "family": 7, "demographic": 5, "cultural": 4},
        "cultural": [],
        "living": {"arrangement": "assisted_living", "floor": 3, "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT019", "ACT014", "ACT003"],
        "notes": "חרדה + סוכרת - מיינדפולנס והרגעה, פעילות אירובית מתונה",
        "family_contacts": [
            {"relation": "son", "name": "עופר מלכה", "phone": "052-1199220",
             "email": "ofer.malka@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "בן, איש קשר עיקרי"},
            {"relation": "daughter", "name": "הדס מלכה-כהן", "phone": "054-2288330",
             "email": "hadas.mc@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בת"},
        ],
    },
    {
        "name": "מרדכי בן-דוד",
        "birth_year": 1942, "gender": "male", "room": "122", "lang": "he",
        "medical": ["DIS008", "DIS009"],   # אי ספיקת לב + COPD
        "medication": ["MED006", "MED008"], # בטא בלוקר + פורוסמיד
        "nursing": ["CON002"], "cognitive": ["CON004"], "mental": [],
        "social": ["CON009"], "family": ["CON010"], "demographic": [],
        "capability": 3,
        "pref_cats": ["mental", "social"], "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 9, "medication": 8, "nursing": 6, "cognitive": 5,
                    "mental": 6, "social": 7, "family": 6, "demographic": 6, "cultural": 3},
        "cultural": [],
        "living": {"arrangement": "assisted_living", "floor": 1, "elevator": True, "outdoor": "limited"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT007", "ACT013", "ACT014"],
        "notes": "אי ספיקת לב + COPD - מאמץ נמוך מאוד, אימון נשימה, מנוחות",
        "family_contacts": [
            {"relation": "wife", "name": "אביבה בן-דוד", "phone": "050-6677880",
             "email": "", "is_primary": 1, "lives_with_elder": 1,
             "notes": "אשה, מטפלת עיקרית"},
            {"relation": "son", "name": "איתן בן-דוד", "phone": "054-7788991",
             "email": "eitan.bd@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן"},
        ],
    },
    {
        "name": "שושנה אמר",
        "birth_year": 1936, "gender": "female", "room": "123", "lang": "he",
        "medical": ["DIS006"],             # דמנציה מתקדמת
        "medication": ["MED010", "MED011"], # דונפזיל + ממנטין
        "nursing": ["CON002"], "cognitive": ["CON006"], "mental": [],
        "social": [], "family": ["CON010"], "demographic": [],
        "capability": 1,
        "pref_cats": ["mental"], "pref_slots": ["morning"],
        "weights": {"medical": 8, "medication": 7, "nursing": 9, "cognitive": 10,
                    "mental": 9, "social": 5, "family": 7, "demographic": 6, "cultural": 5},
        "cultural": [],
        "living": {"arrangement": "nursing_home", "floor": 1, "elevator": True, "outdoor": "limited"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT013", "ACT023", "ACT022"],
        "notes": "דמנציה מתקדמת, תפקוד ירוד מאוד - גרייה חושית עדינה, מוסיקה, נוכחות מרגיעה",
        "family_contacts": [
            {"relation": "daughter", "name": "עדנה אמר-פרי", "phone": "052-4455660",
             "email": "edna.ap@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "בת, איש קשר עיקרי, מבקרת יומיום"},
            {"relation": "son", "name": "רפי אמר", "phone": "054-5566771",
             "email": "rafi.amar@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן"},
        ],
    },
    {
        "name": "נתן גרינברג",
        "birth_year": 1949, "gender": "male", "room": "124", "lang": "ru",
        "medical": ["DIS014", "DIS010"],   # פוסט שבץ + דיכאון
        "medication": ["MED003", "MED012"], # אספירין + SSRI
        "nursing": ["CON002"], "cognitive": ["CON005"], "mental": [],
        "social": ["CON008"], "family": ["CON010"], "demographic": [],
        "capability": 3,
        "pref_cats": ["physical", "cognitive", "mental"], "pref_slots": ["morning"],
        "weights": {"medical": 8, "medication": 7, "nursing": 6, "cognitive": 7,
                    "mental": 8, "social": 8, "family": 6, "demographic": 6, "cultural": 7},
        "cultural": ["CON014"],  # עולה חדש
        "living": {"arrangement": "assisted_living", "floor": 2, "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT024", "ACT013", "ACT008"],
        "notes": "פוסט שבץ + דיכאון, עולה מרוסיה - שיקום מוטורי, תוכן בשפת האם, הפעלה",
        "family_contacts": [
            {"relation": "wife", "name": "לודמילה גרינברג", "phone": "050-8811990",
             "email": "", "is_primary": 1, "lives_with_elder": 1,
             "notes": "אשה, מטפלת עיקרית, דוברת רוסית"},
            {"relation": "son", "name": "מקסים גרינברג", "phone": "054-9922881",
             "email": "maxim.g@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן, מתרגם בעת הצורך"},
        ],
    },
    {
        "name": "גאולה טל",
        "birth_year": 1943, "gender": "female", "room": "125", "lang": "he",
        "medical": ["DIS004", "DIS003"],   # ארתריטיס + אוסטאופורוזיס
        "medication": ["MED004"],          # סטטין
        "nursing": ["CON001"], "cognitive": ["CON004"], "mental": [],
        "social": ["CON008"], "family": ["CON011"], "demographic": [],
        "capability": 4,
        "pref_cats": ["social", "physical"], "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 7, "medication": 5, "nursing": 4, "cognitive": 5,
                    "mental": 6, "social": 9, "family": 6, "demographic": 5, "cultural": 4},
        "cultural": [],
        "living": {"arrangement": "sheltered_housing", "floor": 2, "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT014", "ACT017", "ACT003"],
        "notes": "ארתריטיס + אוסטאופורוזיס, בודדה - פעילות נושאת משקל עדינה, מפגשים חברתיים",
        "family_contacts": [
            {"relation": "nephew", "name": "דורון טל", "phone": "052-2233446",
             "email": "doron.tal@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "אחיין, איש קשר עיקרי (אין ילדים)"},
        ],
    },
    {
        "name": "סעדיה עמר",
        "birth_year": 1938, "gender": "male", "room": "126", "lang": "he",
        "medical": ["DIS001", "DIS013", "DIS007"],   # סוכרת + ליקוי ראייה + פרקינסון
        "medication": ["MED015", "MED009"],          # אינסולין + ל-דופא
        "nursing": ["CON002"], "cognitive": ["CON005"], "mental": [],
        "social": ["CON009"], "family": ["CON010"], "demographic": [],
        "capability": 2,
        "pref_cats": ["physical", "mental"], "pref_slots": ["morning"],
        "weights": {"medical": 9, "medication": 8, "nursing": 8, "cognitive": 6,
                    "mental": 6, "social": 6, "family": 6, "demographic": 7, "cultural": 4},
        "cultural": [],
        "living": {"arrangement": "nursing_home", "floor": 1, "elevator": True, "outdoor": "limited"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT004", "ACT013", "ACT005"],
        "notes": "סוכרת + ליקוי ראייה + פרקינסון - פעילות מבוססת שמע, איזון, מפגשים קצרים",
        "family_contacts": [
            {"relation": "son", "name": "משה עמר", "phone": "052-3344557",
             "email": "moshe.amar@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "בן, איש קשר עיקרי"},
            {"relation": "daughter", "name": "יפה עמר-ביטון", "phone": "054-4455668",
             "email": "yaffa.ab@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בת"},
        ],
    },
    {
        "name": "אביבה רון",
        "birth_year": 1951, "gender": "female", "room": "127", "lang": "he",
        "medical": ["DIS011", "DIS010"],   # חרדה + דיכאון
        "medication": ["MED012"],          # SSRI
        "nursing": ["CON001"], "cognitive": ["CON004"], "mental": [],
        "social": ["CON009"], "family": ["CON010"], "demographic": [],
        "capability": 5,
        "pref_cats": ["mental", "social", "cognitive"], "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 6, "medication": 6, "nursing": 3, "cognitive": 6,
                    "mental": 9, "social": 8, "family": 6, "demographic": 5, "cultural": 4},
        "cultural": [],
        "living": {"arrangement": "sheltered_housing", "floor": 3, "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "secular",
        "preferred": ["ACT019", "ACT012", "ACT014"],
        "notes": "חרדה + דיכאון, תפקוד גבוה - מיינדפולנס, יצירה, מעורבות חברתית פעילה",
        "family_contacts": [
            {"relation": "daughter", "name": "נעמה רון-שגב", "phone": "052-5566772",
             "email": "naama.rs@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "בת, איש קשר עיקרי"},
            {"relation": "son", "name": "יונתן רון", "phone": "054-6677883",
             "email": "yonatan.ron@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן"},
        ],
    },
    {
        "name": "חיים כץ",
        "birth_year": 1946, "gender": "male", "room": "128", "lang": "he",
        "medical": ["DIS002", "DIS014", "DIS012"],   # יל"ד + פוסט שבץ + ירידת שמיעה
        "medication": ["MED005", "MED003"],          # ACE-i + אספירין
        "nursing": ["CON002"], "cognitive": ["CON005"], "mental": [],
        "social": ["CON008"], "family": ["CON010"], "demographic": [],
        "capability": 3,
        "pref_cats": ["physical", "cognitive"], "pref_slots": ["morning", "afternoon"],
        "weights": {"medical": 9, "medication": 8, "nursing": 7, "cognitive": 6,
                    "mental": 5, "social": 7, "family": 6, "demographic": 6, "cultural": 3},
        "cultural": [],
        "living": {"arrangement": "home_family", "floor": 1, "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT024", "ACT004", "ACT008"],
        "notes": "פוסט שבץ + ירידת שמיעה - פיזיותרפיה, תקשורת ויזואלית, איזון",
        "family_contacts": [
            {"relation": "wife", "name": "בלהה כץ", "phone": "050-7788992",
             "email": "", "is_primary": 1, "lives_with_elder": 1,
             "notes": "אשה, מטפלת עיקרית"},
            {"relation": "daughter", "name": "ליאת כץ-אור", "phone": "054-8899003",
             "email": "liat.ko@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בת"},
        ],
    },
    {
        "name": "תקווה ביטון",
        "birth_year": 1940, "gender": "female", "room": "129", "lang": "he",
        "medical": ["DIS006", "DIS001"],   # דמנציה בינונית + סוכרת
        "medication": ["MED011", "MED001"], # ממנטין + מטפורמין
        "nursing": ["CON002"], "cognitive": ["CON006"], "mental": [],
        "social": [], "family": ["CON010"], "demographic": [],
        "capability": 2,
        "pref_cats": ["mental", "cognitive"], "pref_slots": ["morning"],
        "weights": {"medical": 9, "medication": 7, "nursing": 8, "cognitive": 9,
                    "mental": 7, "social": 7, "family": 8, "demographic": 6, "cultural": 3},
        "cultural": [],
        "living": {"arrangement": "nursing_home", "floor": 2, "elevator": True, "outdoor": "limited"},
        "religion": "jewish", "religiosity": "observant",
        "preferred": ["ACT011", "ACT013", "ACT023"],
        "notes": "דמנציה בינונית + סוכרת - רמיניסנציה, גרייה חושית, שגרה יציבה",
        "family_contacts": [
            {"relation": "daughter", "name": "אורנה ביטון-דהן", "phone": "052-6677884",
             "email": "orna.bd@gmail.com", "is_primary": 1, "lives_with_elder": 0,
             "notes": "בת, איש קשר עיקרי, מבקרת יומיום"},
            {"relation": "son", "name": "אבי ביטון", "phone": "054-7788995",
             "email": "avi.biton@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן"},
        ],
    },
    {
        "name": "אהרון שרעבי",
        "birth_year": 1953, "gender": "male", "room": "130", "lang": "he",
        "medical": ["DIS009", "DIS007"],   # COPD + פרקינסון
        "medication": ["MED009"],          # ל-דופא
        "nursing": ["CON002"], "cognitive": ["CON004"], "mental": [],
        "social": ["CON009"], "family": ["CON010"], "demographic": [],
        "capability": 3,
        "pref_cats": ["physical", "social"], "pref_slots": ["morning"],
        "weights": {"medical": 9, "medication": 7, "nursing": 7, "cognitive": 6,
                    "mental": 5, "social": 7, "family": 6, "demographic": 5, "cultural": 7},
        "cultural": ["CON016"],  # דתי
        "living": {"arrangement": "assisted_living", "floor": 2, "elevator": True, "outdoor": "full"},
        "religion": "jewish", "religiosity": "very_observant",
        "preferred": ["ACT007", "ACT027", "ACT005"],
        "notes": "COPD + פרקינסון, דתי - אימון נשימה, טאי צ'י עדין, כיבוד זמני תפילה",
        "family_contacts": [
            {"relation": "wife", "name": "שרה שרעבי", "phone": "050-8899226",
             "email": "", "is_primary": 1, "lives_with_elder": 1,
             "notes": "אשה, מטפלת עיקרית"},
            {"relation": "son", "name": "עמרם שרעבי", "phone": "054-9900117",
             "email": "amram.sharabi@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בן בכור"},
            {"relation": "daughter", "name": "מרים שרעבי-עמר", "phone": "058-1122336",
             "email": "miriam.sa@gmail.com", "is_primary": 0, "lives_with_elder": 0,
             "notes": "בת"},
        ],
    },
]


# ============================================================
# CURATED CARE GOALS — distinct per resident, matched to each resident's
# physical / mental / cognitive condition. Inserted explicitly (source='demo')
# so residents do NOT all end up with the same generic auto-generated set.
# Each entry: (goal_text, target_tags, priority 5..1). Tags come from the
# activities' "strengthens" vocabulary so the optimizer still rewards matching
# activities and the manager goal-achievement view can measure progress.
# ============================================================
DEMO_GOALS = {
    # רחל — סוכרת + שחיקת ברכיים + בדידות (תפקוד גבוה, מעדיפה מים)
    "רחל כהן": [
        ("שמירה על מפרקי הברך וטווחי תנועה בעזרת פעילות במים", "water_aerobics;swimming;range_of_motion;quadriceps_strength", 5),
        ("איזון הסוכרת באמצעות פעילות אירובית מתונה וקבועה", "aerobic_low;daily_movement", 4),
        ("הפחתת בדידות וחיזוק קשרים חברתיים", "social;group_activity;peer_visits", 3),
        ("מניעת נפילות ושיפור יציבות", "balance;gait_training;weight_bearing_low", 2),
        ("חיזוק הקשר המשפחתי והבין-דורי", "family_inclusive;intergenerational", 1),
    ],
    # משה — פרקינסון + דיכאון (עולה חדש)
    "משה לוי": [
        ("שיפור שליטה מוטורית וריתמוס תנועה (פרקינסון)", "rhythmic_movement;balance;gait_training;flexibility", 5),
        ("שיפור מצב הרוח והפעלה התנהגותית (דיכאון)", "behavioral_activation;light_exposure;mindfulness;creative", 4),
        ("חיזוק קול ודיבור", "voice_exercise;speech_therapy", 3),
        ("חיזוק תחושת שייכות ותמיכה בקליטה", "social;cultural_familiar;group_activity", 2),
        ("שמירה על פעילות אירובית עדינה", "aerobic_low;daily_movement", 1),
    ],
    # שרה — דמנציה בינונית + COPD (תפקוד ירוד מאוד, ניצולת שואה)
    "שרה גולדברג": [
        ("שימור ערנות וגירוי חושי עדין (דמנציה)", "sensory_stim;music_familiar;passive_motion", 5),
        ("שיפור תפקוד נשימתי והרגעה (COPD)", "breathing;pursed_lip", 4),
        ("יצירת סביבה רגועה ובטוחה רגשית", "relaxation;music_therapy;mindfulness", 3),
        ("שימור זיכרון ורמיניסנציה מותאמת", "reminiscence;memory_games", 2),
        ("שמירה על טווחי תנועה וניידות בסיסית", "range_of_motion;passive_motion", 1),
    ],
    # אברהם — פוסט שבץ + יל"ד (שיקום פעיל)
    "אברהם פרידמן": [
        ("שיקום מוטורי לאחר שבץ (פיזיותרפיה)", "physiotherapy;mirror_therapy;range_of_motion;gait_training", 5),
        ("שיקום דיבור, קול ותקשורת", "speech_therapy;voice_exercise", 4),
        ("שיפור יציבה ומניעת נפילות לאחר שבץ", "balance;gait_training;weight_bearing_low", 3),
        ("שמירה על פעילות אירובית מתונה ובקרת לחץ דם", "aerobic_low;daily_movement;breathing", 2),
        ("שמירה על מעורבות חברתית", "social;group_activity", 1),
    ],
    # ברכה — אוסטאופורוזיס + אי ספיקת לב + ירידת שמיעה (תפקוד גבוה, דתית מאוד)
    "ברכה שטרן": [
        ("חיזוק צפיפות העצם בפעילות נושאת משקל (אוסטאופורוזיס)", "weight_bearing_low;quadriceps_strength;balance", 5),
        ("מענה לצרכים רוחניים ותרבותיים", "religious_appropriate;spiritual_support;reminiscence", 4),
        ("מניעת נפילות ושמירה על עצמאות", "balance;gait_training", 3),
        ("שמירה על קשרים חברתיים בהתאמת שמיעה", "social;group_activity;peer_visits", 2),
        ("פעילות אירובית עדינה ובקרת מאמץ (אי ספיקת לב)", "aerobic_low;breathing", 1),
    ],
    # יוסף — סוכרת + יל"ד + ליקוי ראייה + מרותק לבית (קומה 4 ללא מעלית)
    "יוסף ברק": [
        ("הפחתת בידוד וקשר חברתי מרחוק (מרותק לבית)", "phone_calls;social;peer_visits", 5),
        ("גירוי קוגניטיבי מבוסס שמע (ליקוי ראייה)", "moderate_cognitive;memory_games;music_therapy", 4),
        ("פעילות אירובית ביתית לאיזון הסוכרת", "aerobic_low;daily_movement", 3),
        ("חיזוק רווחה נפשית והרגעה", "mindfulness;relaxation;music_therapy", 2),
        ("תרגול נשימה והרגעה", "breathing", 1),
    ],
    # עליזה — חרדה + דיכאון + אבל טרי + אוסטאופורוזיס (דוברת ערבית)
    "עליזה מזרחי": [
        ("תמיכה בתהליך אבל והתמודדות עם אובדן", "grief_group;validation;spiritual_support", 5),
        ("הפחתת חרדה בעזרת נשימה ומיינדפולנס", "mindfulness;breathing;relaxation", 4),
        ("שיפור מצב הרוח והפעלה התנהגותית (דיכאון)", "behavioral_activation;creative;art_therapy;light_exposure", 3),
        ("חיזוק שייכות תרבותית בשפת האם", "native_language_group;arabic_content;cultural_familiar;social", 2),
        ("שמירה על צפיפות עצם ויציבות", "weight_bearing_low;balance", 1),
    ],
    # דוד — פרקינסון + יל"ד + אינקונטיננציה (תפקוד ירוד)
    "דוד אזולאי": [
        ("שיפור שיווי משקל וניידות (פרקינסון)", "balance;gait_training;rhythmic_movement;flexibility", 5),
        ("שיפור שליטה בסוגרים", "pelvic_floor;timed_voiding", 4),
        ("שמירה על טווחי תנועה וקול", "range_of_motion;voice_exercise", 3),
        ("גירוי קוגניטיבי שוטף", "moderate_cognitive;memory_games", 2),
        ("פעילות גופנית מתונה יומית", "aerobic_low;daily_movement", 1),
    ],
    # אסתר — דמנציה בינונית + סוכרת (תפקוד ירוד)
    "אסתר רובין": [
        ("שימור תפקוד קוגניטיבי ורמיניסנציה (דמנציה)", "memory_games;reminiscence;moderate_cognitive", 5),
        ("גירוי חושי ושמירה על ערנות", "sensory_stim;music_familiar;music_therapy", 4),
        ("פעילות אירובית עדינה לאיזון הסוכרת", "aerobic_low;daily_movement", 3),
        ("ביסוס שגרה יציבה ומובנית", "structured_routine", 2),
        ("חיזוק הקשר המשפחתי והבין-דורי", "family_inclusive;intergenerational", 1),
    ],
    # יעקב — פוסט שבץ + COPD + דיכאון
    "יעקב שמש": [
        ("שיפור תפקוד נשימתי וסיבולת (COPD)", "breathing;pursed_lip;aerobic_low", 5),
        ("שיקום מוטורי לאחר שבץ", "physiotherapy;range_of_motion;gait_training", 4),
        ("שיפור מצב הרוח והפעלה (דיכאון)", "behavioral_activation;light_exposure;mindfulness", 3),
        ("מניעת נפילות ושיפור יציבות", "balance;weight_bearing_low", 2),
        ("הפחתת בדידות וחיזוק קשרים חברתיים", "social;group_activity", 1),
    ],
    # --- 20 additional residents ---
    "חנה ברקוביץ'": [
        ("שמירה על מפרקי הברך וטווח תנועה (ארתריטיס)", "range_of_motion;quadriceps_strength;water_aerobics", 5),
        ("איזון הסוכרת בפעילות אירובית מתונה", "aerobic_low;daily_movement", 4),
        ("הפחתת בדידות וחיזוק קשרים חברתיים", "social;group_activity;peer_visits", 3),
        ("מניעת נפילות ושיפור יציבות", "balance;gait_training", 2),
        ("שמירה על חדות קוגניטיבית", "moderate_cognitive;memory_games", 1),
    ],
    "שמעון דהן": [
        ("פעילות אירובית עדינה ובקרת מאמץ (אי ספיקת לב)", "aerobic_low;breathing;daily_movement", 5),
        ("שיפור מצב הרוח והפעלה התנהגותית (דיכאון)", "behavioral_activation;light_exposure;mindfulness", 4),
        ("תרגול נשימה והרגעה", "breathing;relaxation", 3),
        ("חיזוק מעורבות חברתית", "social;group_activity", 2),
        ("שמירה על שגרה יציבה ומובנית", "structured_routine", 1),
    ],
    "מרים אלקיים": [
        ("שימור תפקוד קוגניטיבי ורמיניסנציה (דמנציה)", "memory_games;reminiscence;moderate_cognitive", 5),
        ("גירוי חושי ושמירה על ערנות", "sensory_stim;music_familiar;music_therapy", 4),
        ("חיזוק צפיפות העצם ויציבות (אוסטאופורוזיס)", "weight_bearing_low;balance", 3),
        ("ביסוס שגרה יציבה ומובנית", "structured_routine", 2),
        ("חיזוק הקשר המשפחתי", "family_inclusive;intergenerational", 1),
    ],
    "אליהו נחמיאס": [
        ("שיפור שליטה מוטורית וריתמוס תנועה (פרקינסון)", "rhythmic_movement;balance;gait_training;flexibility", 5),
        ("מניעת נפילות ושיפור יציבות", "balance;weight_bearing_low", 4),
        ("שמירה על טווחי תנועה וגמישות", "range_of_motion;flexibility", 3),
        ("גירוי קוגניטיבי שוטף", "moderate_cognitive;memory_games", 2),
        ("פעילות אירובית עדינה ובקרת לחץ דם", "aerobic_low;daily_movement;breathing", 1),
    ],
    "פנינה גבאי": [
        ("שיפור תפקוד נשימתי והרגעה (COPD)", "breathing;pursed_lip;relaxation", 5),
        ("הפחתת חרדה בעזרת נשימה ומיינדפולנס", "mindfulness;breathing;relaxation", 4),
        ("חיזוק רווחה נפשית", "music_therapy;behavioral_activation", 3),
        ("שמירה על מעורבות חברתית", "social;group_activity;peer_visits", 2),
        ("פעילות אירובית עדינה", "aerobic_low;daily_movement", 1),
    ],
    "יצחק פרץ": [
        ("שיקום מוטורי לאחר שבץ (פיזיותרפיה)", "physiotherapy;mirror_therapy;range_of_motion;gait_training", 5),
        ("שיקום דיבור ותקשורת", "speech_therapy;voice_exercise", 4),
        ("איזון הסוכרת בפעילות אירובית מתונה", "aerobic_low;daily_movement", 3),
        ("שיפור יציבה ומניעת נפילות", "balance;weight_bearing_low", 2),
        ("שמירה על מעורבות חברתית", "social;group_activity", 1),
    ],
    "לאה סויסה": [
        ("שימור ערנות וגירוי חושי עדין (דמנציה)", "sensory_stim;music_familiar;passive_motion", 5),
        ("שימור זיכרון ורמיניסנציה מותאמת", "reminiscence;memory_games", 4),
        ("יצירת סביבה רגועה ובטוחה רגשית", "relaxation;music_therapy", 3),
        ("שמירה על טווחי תנועה בסיסית", "range_of_motion;passive_motion", 2),
        ("תקשורת מותאמת לירידת שמיעה", "validation;structured_routine", 1),
    ],
    "אברהם וקנין": [
        ("גירוי קוגניטיבי מבוסס שמע (ליקוי ראייה)", "moderate_cognitive;memory_games;music_therapy", 5),
        ("הפחתת בידוד וחיזוק קשרים חברתיים", "social;group_activity;peer_visits", 4),
        ("חיזוק רווחה נפשית והרגעה", "mindfulness;relaxation;music_therapy", 3),
        ("שמירה על פעילות אירובית ובקרת לחץ דם", "aerobic_low;daily_movement", 2),
        ("שמירה על קשר מרחוק", "phone_calls", 1),
    ],
    "זהבה אוחיון": [
        ("תמיכה בתהליך אבל והתמודדות עם אובדן", "grief_group;validation;spiritual_support", 5),
        ("שיפור מצב הרוח והפעלה התנהגותית (דיכאון)", "behavioral_activation;creative;light_exposure", 4),
        ("הרגעה והפחתת מתח", "mindfulness;relaxation", 3),
        ("חיזוק צפיפות העצם ויציבות (אוסטאופורוזיס)", "weight_bearing_low;balance", 2),
        ("חיזוק קשרים חברתיים", "social;group_activity;peer_visits", 1),
    ],
    "ראובן חדד": [
        ("שיפור שיווי משקל וניידות (פרקינסון)", "balance;gait_training;rhythmic_movement;flexibility", 5),
        ("שיפור שליטה בסוגרים", "pelvic_floor;timed_voiding", 4),
        ("שמירה על טווחי תנועה וקול", "range_of_motion;voice_exercise", 3),
        ("גירוי קוגניטיבי שוטף", "moderate_cognitive;memory_games", 2),
        ("פעילות גופנית מתונה יומית", "aerobic_low;daily_movement", 1),
    ],
    "ציונה מלכה": [
        ("הפחתת חרדה בעזרת נשימה ומיינדפולנס", "mindfulness;breathing;relaxation", 5),
        ("איזון הסוכרת בפעילות אירובית מתונה", "aerobic_low;daily_movement", 4),
        ("חיזוק מעורבות חברתית", "social;group_activity;peer_visits", 3),
        ("שמירה על יציבות ומניעת נפילות", "balance;gait_training", 2),
        ("חיזוק רווחה נפשית", "behavioral_activation;creative", 1),
    ],
    "מרדכי בן-דוד": [
        ("פעילות אירובית עדינה ובקרת מאמץ (אי ספיקת לב)", "aerobic_low;breathing;daily_movement", 5),
        ("שיפור תפקוד נשימתי (COPD)", "breathing;pursed_lip", 4),
        ("הרגעה והפחתת מתח", "relaxation;music_therapy;mindfulness", 3),
        ("שמירה על מעורבות חברתית", "social;group_activity", 2),
        ("שמירה על שגרה יציבה", "structured_routine", 1),
    ],
    "שושנה אמר": [
        ("שימור ערנות וגירוי חושי עדין (דמנציה מתקדמת)", "sensory_stim;music_familiar;passive_motion", 5),
        ("יצירת סביבה רגועה ובטוחה רגשית", "relaxation;music_therapy", 4),
        ("שימור זיכרון רגשי ורמיניסנציה", "reminiscence;memory_games", 3),
        ("שמירה על טווחי תנועה פסיביים", "range_of_motion;passive_motion", 2),
        ("נוכחות משפחתית ומגע מרגיע", "family_inclusive", 1),
    ],
    "נתן גרינברג": [
        ("שיקום מוטורי לאחר שבץ", "physiotherapy;range_of_motion;gait_training", 5),
        ("שיפור מצב הרוח והפעלה התנהגותית (דיכאון)", "behavioral_activation;light_exposure;mindfulness", 4),
        ("חיזוק שייכות בשפת האם ותמיכה בקליטה", "native_language_group;cultural_familiar;social", 3),
        ("מניעת נפילות ושיפור יציבות", "balance;weight_bearing_low", 2),
        ("שמירה על פעילות אירובית עדינה", "aerobic_low;daily_movement", 1),
    ],
    "גאולה טל": [
        ("חיזוק צפיפות העצם בפעילות נושאת משקל (אוסטאופורוזיס)", "weight_bearing_low;quadriceps_strength;balance", 5),
        ("שמירה על מפרקים וטווח תנועה (ארתריטיס)", "range_of_motion;water_aerobics", 4),
        ("הפחתת בדידות וחיזוק קשרים חברתיים", "social;group_activity;peer_visits", 3),
        ("מניעת נפילות ושמירה על עצמאות", "balance;gait_training", 2),
        ("פעילות אירובית עדינה", "aerobic_low;daily_movement", 1),
    ],
    "סעדיה עמר": [
        ("שיפור שיווי משקל וניידות (פרקינסון)", "balance;gait_training;rhythmic_movement;flexibility", 5),
        ("גירוי קוגניטיבי מבוסס שמע (ליקוי ראייה)", "moderate_cognitive;memory_games;music_therapy", 4),
        ("איזון הסוכרת בפעילות אירובית מתונה", "aerobic_low;daily_movement", 3),
        ("שמירה על טווחי תנועה", "range_of_motion", 2),
        ("חיזוק רווחה נפשית", "relaxation;music_therapy", 1),
    ],
    "אביבה רון": [
        ("הפחתת חרדה בעזרת נשימה ומיינדפולנס", "mindfulness;breathing;relaxation", 5),
        ("שיפור מצב הרוח והפעלה התנהגותית (דיכאון)", "behavioral_activation;creative;art_therapy;light_exposure", 4),
        ("מעורבות חברתית פעילה", "social;group_activity;peer_visits", 3),
        ("גירוי קוגניטיבי מאתגר", "moderate_cognitive;memory_games", 2),
        ("שמירה על כושר אירובי", "aerobic_low;daily_movement", 1),
    ],
    "חיים כץ": [
        ("שיקום מוטורי לאחר שבץ (פיזיותרפיה)", "physiotherapy;mirror_therapy;range_of_motion;gait_training", 5),
        ("שיפור יציבה ומניעת נפילות", "balance;weight_bearing_low", 4),
        ("שמירה על פעילות אירובית ובקרת לחץ דם", "aerobic_low;daily_movement;breathing", 3),
        ("תקשורת מותאמת לירידת שמיעה", "validation;structured_routine", 2),
        ("חיזוק מעורבות חברתית", "social;group_activity", 1),
    ],
    "תקווה ביטון": [
        ("שימור תפקוד קוגניטיבי ורמיניסנציה (דמנציה)", "memory_games;reminiscence;moderate_cognitive", 5),
        ("גירוי חושי ושמירה על ערנות", "sensory_stim;music_familiar;music_therapy", 4),
        ("פעילות אירובית עדינה לאיזון הסוכרת", "aerobic_low;daily_movement", 3),
        ("ביסוס שגרה יציבה ומובנית", "structured_routine", 2),
        ("חיזוק הקשר המשפחתי והבין-דורי", "family_inclusive;intergenerational", 1),
    ],
    "אהרון שרעבי": [
        ("שיפור תפקוד נשימתי וסיבולת (COPD)", "breathing;pursed_lip;aerobic_low", 5),
        ("שיפור שליטה מוטורית וריתמוס תנועה (פרקינסון)", "rhythmic_movement;balance;gait_training;flexibility", 4),
        ("מענה לצרכים רוחניים ותרבותיים", "religious_appropriate;spiritual_support;reminiscence", 3),
        ("מניעת נפילות ושיפור יציבות", "balance;weight_bearing_low", 2),
        ("חיזוק מעורבות חברתית", "social;group_activity", 1),
    ],
}


def _csv(items: list[str]) -> str:
    return ";".join(items)


# ============================================================
# DEMO ORGS + EXTERNAL PROGRAMS (Neve Shaket + City of Beer Sheva)
# ============================================================
NEVE_SHAKET_PROGRAMS = [
    # day codes: sun mon tue wed thu fri sat
    {"name": "יוגה בוקר לדיירים", "category": "physical",
     "days": "sun;tue;thu", "start": "08:30", "duration": 45,
     "strengthens": "flexibility;balance;mindfulness;breathing",
     "min_cap": 2, "address": "אולם פעילות, קומה 1",
     "contact": "ענת מורן 052-1112233",
     "notes": "יוגה מותאמת לכיסא + שטיח"},
    {"name": "חוג ציור וצביעה", "category": "cognitive",
     "days": "mon;wed", "start": "10:00", "duration": 60,
     "strengthens": "creative;art_therapy;social",
     "min_cap": 1, "address": "חדר אומנות, קומה 2",
     "contact": "דליה כץ 053-4445566",
     "notes": "צבעים וחומרים מסופקים"},
    {"name": "מקהלת נווה שקט", "category": "social",
     "days": "tue;thu", "start": "16:00", "duration": 60,
     "strengthens": "music_therapy;voice_exercise;social;rhythmic_movement",
     "min_cap": 1, "address": "אולם אירועים",
     "contact": "אבי פלד 054-7778899",
     "notes": "שירי ישראל ותקופה - האזנה גם אפשרית"},
    {"name": "לימוד תורה לנשים", "category": "social",
     "days": "wed", "start": "10:30", "duration": 45,
     "strengthens": "religious_appropriate;social;reminiscence",
     "min_cap": 2, "address": "ספרייה",
     "contact": "הרבנית רבקה 052-9991122",
     "notes": "פרשת השבוע, שיחה ערכית"},
    {"name": "קבוצת תמיכה לאבלים", "category": "mental",
     "days": "sun", "start": "16:30", "duration": 75,
     "strengthens": "grief_group;social;validation",
     "min_cap": 3, "address": "חדר ייעוץ פרטי",
     "contact": "פסיכולוגית קלינית רונית 052-3334477",
     "notes": "קבוצה סגורה - הרשמה מראש"},
    {"name": "ארוחת שבת קבוצתית", "category": "social",
     "days": "fri", "start": "12:00", "duration": 90,
     "strengthens": "social;structured_routine;religious_appropriate;family_inclusive",
     "min_cap": 1, "address": "חדר אוכל",
     "contact": "צוות הסיעוד",
     "notes": "סעודת ערב שבת - בני משפחה מוזמנים"},
    {"name": "צפיה במשחק כדורגל", "category": "social",
     "days": "sat", "start": "16:00", "duration": 90,
     "strengthens": "social",
     "min_cap": 1, "address": "אולם טלוויזיה",
     "contact": "פעיל המתנדבים",
     "notes": "שבת אחה\"צ - צפיה במשחק בליגה"},
    {"name": "משחקי קלפים וברידג'", "category": "cognitive",
     "days": "mon;thu", "start": "15:00", "duration": 90,
     "strengthens": "moderate_cognitive;social;memory_games",
     "min_cap": 3, "address": "פינת ישיבה",
     "contact": "קבוצת ותיקים", "notes": "ברידג' רציני + רמיקוב"},
]

CITY_PROGRAMS = [
    {"name": "הרצאה ב'יד לבנים' - היסטוריה מקומית", "category": "cognitive",
     "days": "tue", "start": "10:00", "duration": 90,
     "strengthens": "moderate_cognitive;social;reminiscence",
     "min_cap": 3, "address": "יד לבנים, רחוב הנשיא 12, באר שבע",
     "contact": "מרכז קהילתי 08-6464111",
     "notes": "תחבורה אפשרית - הסעות באחריות המשפחה"},
    {"name": "בריכה טיפולית במרכז קהילתי", "category": "physical",
     "days": "mon;wed;fri", "start": "08:00", "duration": 60,
     "strengthens": "swimming;water_aerobics;aerobic_low;range_of_motion",
     "min_cap": 2, "address": "מתנ\"ס שכונה ז, באר שבע",
     "contact": "מרכזת הבריכה 08-6464200",
     "notes": "דמי מנוי דרך מחלקת רווחה - 0 ש\"ח לדייר/ת"},
    {"name": "מועדון יום עירוני - יום סגול", "category": "social",
     "days": "wed", "start": "09:00", "duration": 240,
     "strengthens": "social;outings;daily_movement;structured_routine",
     "min_cap": 2, "address": "מועדון 'הסיגלית', רחוב יעלים",
     "contact": "מנהלת המועדון יסמין 050-1234567",
     "notes": "ארוחת בוקר + פעילות + ארוחת צהריים. הסעה ב-08:30"},
    {"name": "מרכז התרבות - הצגת תיאטרון", "category": "cognitive",
     "days": "thu", "start": "11:00", "duration": 120,
     "strengthens": "creative;social;moderate_cognitive",
     "min_cap": 3, "address": "מרכז התרבות, רחוב הפלמ\"ח 5",
     "contact": "מנהלת תיאטרון לדיירים 050-7654321",
     "notes": "כניסה מסובסדת 10 ש\"ח, מקומות לכיסאות גלגלים"},
    {"name": "טיול מודרך בעיר העתיקה", "category": "social",
     "days": "sun", "start": "09:30", "duration": 180,
     "strengthens": "outings;social;light_exposure;daily_movement;nature_exposure",
     "min_cap": 3, "address": "מרכז העיר העתיקה",
     "contact": "מדריך מטעם העירייה 052-9999111",
     "notes": "פעם בחודש - להתעדכן בלוח הזמנים"},
    {"name": "סדנת זיכרון במרפאה גריאטרית", "category": "cognitive",
     "days": "mon", "start": "14:00", "duration": 60,
     "strengthens": "memory_games;moderate_cognitive",
     "min_cap": 2, "address": "מרפאת רמב\"ם, רחוב יצחק רגר",
     "contact": "המרפאה הגריאטרית 08-6400500",
     "notes": "בהפניית רופא משפחה"},
]


def _seed_orgs_and_programs(cur, verbose: bool):
    # Get or create Neve Shaket org (with full contact details)
    row = cur.execute(
        "SELECT id FROM organizations WHERE name = ?", ("נווה שקט",)
    ).fetchone()
    if row:
        ns_id = row["id"]
        # update existing record with full details (idempotent)
        cur.execute("""
            UPDATE organizations SET
              kind = ?, country = ?, language = ?,
              address = ?, city = ?, phone = ?, email = ?,
              contact_person = ?, manager_name = ?, description = ?,
              website = ?, logo_emoji = ?, institution_rules = ?
            WHERE id = ?
        """, ("sheltered", "IL", "he",
              "רחוב יצחק רגר 102", "באר שבע",
              "08-6464100", "info@neve-shaket.org.il",
              "אבי כהן - אחראי משפחות 050-1234567",
              "ד״ר רונית לוי",
              "דיור מוגן ובית אבות סיעודי המתמחה בדיירים עם ירידה תפקודית, "
              "82 דיירים, 4 קומות + גינה טיפולית.",
              "https://neve-shaket.org.il",
              "🏡",
              # default rules — institution owner can edit these later
              "אין פעילות אחרי 20:00\n"
              "אין פעילות לפני 08:00\n"
              "ארוחת ערב ב-18:00 בחדר האוכל המרכזי\n"
              "ביקור משפחה - עד 3 איש בו זמנית, בחדר הדייר/ת\n"
              "אין פעילות חיצונית ביום שבת\n"
              "חזרה לחדר עד 21:30\n"
              "אנשי צוות זמינים 24/7 במוקד 105",
              ns_id))
    else:
        cur.execute("""
            INSERT INTO organizations (
              name, kind, country, language,
              address, city, phone, email,
              contact_person, manager_name, description, website, logo_emoji,
              institution_rules
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("נווה שקט", "sheltered", "IL", "he",
              "רחוב יצחק רגר 102", "באר שבע",
              "08-6464100", "info@neve-shaket.org.il",
              "אבי כהן - אחראי משפחות 050-1234567",
              "ד״ר רונית לוי",
              "דיור מוגן ובית אבות סיעודי המתמחה בדיירים עם ירידה תפקודית, "
              "82 דיירים, 4 קומות + גינה טיפולית.",
              "https://neve-shaket.org.il",
              "🏡",
              "אין פעילות אחרי 20:00\n"
              "אין פעילות לפני 08:00\n"
              "ארוחת ערב ב-18:00 בחדר האוכל המרכזי\n"
              "ביקור משפחה - עד 3 איש בו זמנית, בחדר הדייר/ת\n"
              "אין פעילות חיצונית ביום שבת\n"
              "חזרה לחדר עד 21:30\n"
              "אנשי צוות זמינים 24/7 במוקד 105"))
        ns_id = cur.lastrowid
        if verbose:
            print("  created org: נווה שקט")

    # Get or create City of Beer Sheva org
    row = cur.execute(
        "SELECT id FROM organizations WHERE name = ?", ("עיריית באר שבע",)
    ).fetchone()
    if row:
        city_id = row["id"]
        cur.execute("""
            UPDATE organizations SET
              kind = ?, country = ?, language = ?,
              address = ?, city = ?, phone = ?, email = ?,
              contact_person = ?, manager_name = ?, description = ?,
              website = ?, logo_emoji = ?
            WHERE id = ?
        """, ("community", "IL", "he",
              "רחוב מנחם בגין 1, באר שבע", "באר שבע",
              "08-6463111 (מוקד 106)", "rehava@br7.org.il",
              "מחלקת רווחה - גב' שירה בן-עמי 052-9999111",
              "מנהל אגף רווחה: מר רון אלוני",
              "האגף לרווחה ושירותים חברתיים, עיריית באר שבע. "
              "מועדוני יום, מתנ\"סים, פעילויות תרבות.",
              "https://www.beer-sheva.muni.il/welfare",
              "🏛️", city_id))
    else:
        cur.execute("""
            INSERT INTO organizations (
              name, kind, country, language,
              address, city, phone, email,
              contact_person, manager_name, description, website, logo_emoji
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("עיריית באר שבע", "community", "IL", "he",
              "רחוב מנחם בגין 1, באר שבע", "באר שבע",
              "08-6463111 (מוקד 106)", "rehava@br7.org.il",
              "מחלקת רווחה - גב' שירה בן-עמי 052-9999111",
              "מנהל אגף רווחה: מר רון אלוני",
              "האגף לרווחה ושירותים חברתיים, עיריית באר שבע. "
              "מועדוני יום, מתנ\"סים, פעילויות תרבות.",
              "https://www.beer-sheva.muni.il/welfare",
              "🏛️"))
        city_id = cur.lastrowid
        if verbose:
            print("  created org: עיריית באר שבע")

    # Update the default Demo Care Center → also tie all demo elders to
    # נווה שקט rather than the generic default, so the org banner reflects reality.
    cur.execute(
        "UPDATE elders SET organization_id = ? "
        "WHERE organization_id IS NULL OR organization_id = "
        "(SELECT id FROM organizations WHERE name = 'Demo Care Center')",
        (ns_id,),
    )

    # idempotent: wipe + re-seed programs
    cur.execute(
        "DELETE FROM external_programs WHERE source_kind IN ('assisted_living', 'city')"
    )

    for p in NEVE_SHAKET_PROGRAMS:
        cur.execute("""
            INSERT INTO external_programs
            (organization_id, name, organization, category, address, city,
             contact, languages, cost, notes,
             recurring_days, start_time, duration_min,
             strengthens, min_capability_level, source_kind)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ns_id, p["name"], "נווה שקט", p["category"], p["address"],
              "באר שבע", p["contact"], "he", "כלול בדמי שירות", p["notes"],
              p["days"], p["start"], p["duration"],
              p["strengthens"], p["min_cap"], "assisted_living"))
    for p in CITY_PROGRAMS:
        cur.execute("""
            INSERT INTO external_programs
            (organization_id, name, organization, category, address, city,
             contact, languages, cost, notes,
             recurring_days, start_time, duration_min,
             strengthens, min_capability_level, source_kind)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (city_id, p["name"], "עיריית באר שבע", p["category"], p["address"],
              "באר שבע", p["contact"], "he", "מסובסד", p["notes"],
              p["days"], p["start"], p["duration"],
              p["strengthens"], p["min_cap"], "city"))
    return ns_id, city_id


def _seed_default_enrollments(cur, elder_id, elder_name, ns_id, city_id):
    """Give each demo elder a couple of sensible enrollments so the demo
    visibly shows external programs in the plan."""
    presets = {
        "רחל כהן":      ["יוגה בוקר לדיירים", "בריכה טיפולית במרכז קהילתי"],
        "משה לוי":      ["יוגה בוקר לדיירים", "מקהלת נווה שקט"],
        "שרה גולדברג":  ["חוג ציור וצביעה", "מקהלת נווה שקט"],
        "אברהם פרידמן": ["בריכה טיפולית במרכז קהילתי", "משחקי קלפים וברידג'"],
        "ברכה שטרן":    ["לימוד תורה לנשים", "ארוחת שבת קבוצתית"],
        "יוסף ברק":     ["משחקי קלפים וברידג'", "הרצאה ב'יד לבנים' - היסטוריה מקומית"],
        "עליזה מזרחי":  ["קבוצת תמיכה לאבלים"],
        "דוד אזולאי":   ["יוגה בוקר לדיירים", "מועדון יום עירוני - יום סגול"],
        "אסתר רובין":   ["חוג ציור וצביעה", "מקהלת נווה שקט"],
        "יעקב שמש":     ["בריכה טיפולית במרכז קהילתי", "מועדון יום עירוני - יום סגול"],
        # --- 20 additional residents ---
        "חנה ברקוביץ'": ["בריכה טיפולית במרכז קהילתי", "יוגה בוקר לדיירים"],
        "שמעון דהן":    ["מקהלת נווה שקט", "צפיה במשחק כדורגל"],
        "מרים אלקיים":  ["סדנת זיכרון במרפאה גריאטרית", "חוג ציור וצביעה"],
        "אליהו נחמיאס": ["יוגה בוקר לדיירים", "סדנת זיכרון במרפאה גריאטרית"],
        "פנינה גבאי":   ["יוגה בוקר לדיירים", "מקהלת נווה שקט"],
        "יצחק פרץ":     ["בריכה טיפולית במרכז קהילתי", "משחקי קלפים וברידג'"],
        "לאה סויסה":    ["חוג ציור וצביעה", "מקהלת נווה שקט"],
        "אברהם וקנין":  ["הרצאה ב'יד לבנים' - היסטוריה מקומית", "מקהלת נווה שקט"],
        "זהבה אוחיון":  ["קבוצת תמיכה לאבלים", "חוג ציור וצביעה"],
        "ראובן חדד":    ["חוג ציור וצביעה"],
        "ציונה מלכה":   ["יוגה בוקר לדיירים", "בריכה טיפולית במרכז קהילתי"],
        "מרדכי בן-דוד": ["מקהלת נווה שקט"],
        "שושנה אמר":    ["מקהלת נווה שקט"],
        "נתן גרינברג":  ["בריכה טיפולית במרכז קהילתי", "מקהלת נווה שקט"],
        "גאולה טל":     ["בריכה טיפולית במרכז קהילתי", "ארוחת שבת קבוצתית"],
        "סעדיה עמר":    ["מקהלת נווה שקט"],
        "אביבה רון":    ["מרכז התרבות - הצגת תיאטרון", "טיול מודרך בעיר העתיקה"],
        "חיים כץ":      ["בריכה טיפולית במרכז קהילתי", "משחקי קלפים וברידג'"],
        "תקווה ביטון":  ["סדנת זיכרון במרפאה גריאטרית", "חוג ציור וצביעה"],
        "אהרון שרעבי":  ["ארוחת שבת קבוצתית", "יוגה בוקר לדיירים"],
    }
    wanted = presets.get(elder_name, [])
    if not wanted:
        return
    cur.execute("DELETE FROM elder_program_enrollment WHERE elder_id = ?", (elder_id,))
    for prog_name in wanted:
        row = cur.execute(
            "SELECT id FROM external_programs WHERE name = ?", (prog_name,)
        ).fetchone()
        if not row:
            continue
        cur.execute(
            "INSERT OR IGNORE INTO elder_program_enrollment "
            "(elder_id, program_id) VALUES (?, ?)",
            (elder_id, row["id"]),
        )


def seed(verbose: bool = True) -> None:
    init_database()
    conn = get_connection()
    cur = conn.cursor()

    org_id = cur.execute("SELECT id FROM organizations LIMIT 1").fetchone()[0]

    ns_id, city_id = _seed_orgs_and_programs(cur, verbose)
    conn.commit()

    # ensure the Word rules bank exists (creates it with defaults if missing)
    try:
        from models.rules_doc import read_rules, RULES_DOC_PATH
        rules = read_rules()
        if verbose:
            print(f"  rules bank: {len(rules)} rules in {RULES_DOC_PATH.name}")
    except Exception as e:
        print(f"  rules bank init skipped: {e}")

    created = 0
    plans_generated = 0
    # spread residents across functional tiers (1=very low .. 5=robust) so the
    # measurements, goals and plans vary meaningfully between residents.
    CAP_TIER = {
        "שרה גולדברג": 1,    # ירוד מאוד - דמנציה בינונית + COPD, בית אבות
        "אסתר רובין": 2,     # ירוד - דמנציה בינונית
        "דוד אזולאי": 2,      # ירוד - פרקינסון + אינקונטיננציה
        "משה לוי": 3,         # בינוני - פרקינסון
        "אברהם פרידמן": 3,   # בינוני - פוסט שבץ
        "יעקב שמש": 3,        # בינוני - פוסט שבץ + COPD
        "רחל כהן": 4,         # גבוה
        "עליזה מזרחי": 4,     # גבוה
        "ברכה שטרן": 5,       # גבוה מאוד / איתן
        "יוסף ברק": 5,        # גבוה מאוד / איתן
    }

    for spec in DEMO_ELDERS:
        # apply the functional-tier capability override
        spec["capability"] = CAP_TIER.get(spec["name"], spec.get("capability", 3))
        existing = cur.execute(
            "SELECT id FROM elders WHERE full_name = ?", (spec["name"],)
        ).fetchone()
        if existing:
            elder_id = existing["id"]
            if verbose:
                print(f"  exists:  {spec['name']} (id={elder_id})")
        else:
            # birth date: middle of birth year
            birth = dt.date(spec["birth_year"], 6, 15).isoformat()
            cur.execute(
                "INSERT INTO elders (organization_id, full_name, birth_date, gender, "
                "room_number, primary_language, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (org_id, spec["name"], birth, spec["gender"], spec["room"],
                 spec["lang"], spec["notes"]),
            )
            elder_id = cur.lastrowid
            created += 1
            if verbose:
                print(f"  created: {spec['name']} (id={elder_id})")

        # upsert profile
        w = spec["weights"]
        cur.execute("DELETE FROM elder_profile WHERE elder_id = ?", (elder_id,))
        living = spec.get("living", {})
        cur.execute("""
            INSERT INTO elder_profile (
              elder_id,
              medical_codes, medication_codes,
              nursing_codes, cognitive_codes, mental_codes,
              social_codes, family_codes, demographic_codes, cultural_codes,
              preferences_categories, preferences_time_slots,
              preferred_activity_codes,
              weight_medical, weight_medication, weight_nursing,
              weight_cognitive, weight_mental, weight_social,
              weight_family, weight_demographic, weight_cultural, weight_preference,
              capability_level,
              living_arrangement, residence_floor, has_elevator, outdoor_accessibility,
              religion, religiosity_level,
              breakfast_time, breakfast_duration,
              lunch_time, lunch_duration,
              dinner_time, dinner_duration
            ) VALUES (?,  ?,?,  ?,?,?,?,?,?,?,  ?,?,  ?,
                      ?,?,?,  ?,?,?,  ?,?,?,?,  ?,
                      ?,?,?,?,  ?,?,  ?,?,?,?,?,?)
        """, (
            elder_id,
            _csv(spec["medical"]), _csv(spec["medication"]),
            _csv(spec["nursing"]), _csv(spec["cognitive"]), _csv(spec["mental"]),
            _csv(spec["social"]), _csv(spec["family"]),
            _csv(spec["demographic"]), _csv(spec.get("cultural", [])),
            _csv(spec["pref_cats"]), _csv(spec["pref_slots"]),
            _csv(spec.get("preferred", [])),
            w["medical"], w["medication"], w["nursing"],
            w["cognitive"], w["mental"], w["social"],
            w["family"], w["demographic"], w.get("cultural", 5), 6.0,
            spec["capability"],
            living.get("arrangement", "assisted_living"),
            int(living.get("floor", 0)),
            int(bool(living.get("elevator", True))),
            living.get("outdoor", "full"),
            spec.get("religion", "none"),
            spec.get("religiosity", "secular"),
            # meals: one hour each; lunch at 12:00 so it ends before the
            # 13:00-16:00 rest window
            "08:00", 60,
            "12:00", 60,
            "18:00", 60,
        ))
        conn.commit()

        # family contacts - idempotent: wipe existing demo contacts first
        cur.execute("DELETE FROM family_contacts WHERE elder_id = ?", (elder_id,))
        for fc in spec.get("family_contacts", []):
            cur.execute(
                "INSERT INTO family_contacts "
                "(elder_id, relation, name, phone, email, is_primary, lives_with_elder, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (elder_id, fc.get("relation"), fc["name"], fc.get("phone"),
                 fc.get("email"), fc.get("is_primary", 0),
                 fc.get("lives_with_elder", 0), fc.get("notes")),
            )
        conn.commit()

        # seed a couple of baseline measurements (idempotent: clear demo ones first)
        cur.execute(
            "DELETE FROM measurements WHERE elder_id = ? AND notes = 'demo baseline'",
            (elder_id,),
        )
        today = dt.date.today()
        cap = spec["capability"]                 # 1 (dependent) .. 5 (independent)
        cog = set(spec["cognitive"]); med = set(spec["medical"])
        ment = set(spec["mental"]); nurs = set(spec["nursing"])
        has_dementia = bool(cog & {"CON005", "CON006", "CON007"} or med & {"DIS005", "DIS006"})
        has_depression = bool(med & {"DIS010"} or ment & {"CON100", "CON101", "CON102"})
        has_parkinson = "DIS007" in med
        frail = max(0, min(5, (5 - cap) + (1 if has_parkinson else 0)))
        # (test_code, base_score, max_score) — values reflect the resident's profile
        baselines = [
            ("MMSE",    {2: 12, 3: 20, 4: 26, 5: 28}.get(cap, 26) - (6 if has_dementia else 0), 30),
            ("AD8",     (5 if has_dementia else 1), 8),
            ("PHQ2",    (4 if has_depression else 1), 6),
            ("FRAILTY", frail, 5),
            ("BARTHEL", {1: 40, 2: 65, 3: 80, 4: 92, 5: 98}.get(cap, 90), 100),
            ("TUG",     round(8 + (5 - cap) * 2.5 + (3 if has_parkinson else 0), 1), None),
            ("STS5",    round(10 + (5 - cap) * 2.0, 1), None),
            ("GAIT4M",  round(max(0.4, 1.1 - (5 - cap) * 0.12), 2), None),
            ("GRIP",    round(max(10, 30 - (5 - cap) * 3), 1), None),
            ("MOOD",    (4 if has_depression else 7), 10),
        ]
        for test_code, base, maxs in baselines:
            # 3 measurements over 60 days with a mild improving trend
            for offset_days, delta in [(60, -1), (30, 0), (0, 1)]:
                d = (today - dt.timedelta(days=offset_days)).isoformat()
                val = base + delta * (0.5 if maxs is None else 1)
                cur.execute(
                    "INSERT INTO measurements (elder_id, measurement_date, "
                    "test_code, score, max_score, notes) VALUES (?, ?, ?, ?, ?, ?)",
                    (elder_id, d, test_code, round(val, 2), maxs, "demo baseline"),
                )
        conn.commit()

        # default external program enrollments (idempotent)
        _seed_default_enrollments(cur, elder_id, spec["name"], ns_id, city_id)
        conn.commit()

        # curated, per-resident care goals — distinct across residents and
        # matched to each one's physical / mental / cognitive condition. Inserted
        # explicitly so the plan generator's ensure_goals() keeps them instead of
        # producing the same generic auto set for everyone. Falls back to
        # auto-generation for any resident without a curated set.
        cur.execute("DELETE FROM care_goals WHERE elder_id = ?", (elder_id,))
        for goal_text, tags, prio in DEMO_GOALS.get(spec["name"], []):
            cur.execute(
                "INSERT INTO care_goals (elder_id, goal_text, target_tags, "
                "priority, source, active) VALUES (?, ?, ?, ?, 'demo', 1)",
                (elder_id, goal_text, tags, prio),
            )
        conn.commit()

        # generate plans for the current week (Sun -> Sat) so weekly view is full
        today = dt.date.today()
        # current week starts on the Sunday on/before today (he locale)
        days_since_sunday = (today.weekday() + 1) % 7
        week_start = today - dt.timedelta(days=days_since_sunday)
        days_to_seed = [week_start + dt.timedelta(days=i) for i in range(7)]

        success_days = 0
        for plan_date in days_to_seed:
            try:
                res = generate_plan_for_elder(elder_id, plan_date.isoformat())
                success_days += 1
            except Exception as e:
                import traceback
                print(f"    plan FAILED for {spec['name']} on {plan_date}: "
                      f"{type(e).__name__}: {e}")
                traceback.print_exc()
        if success_days:
            plans_generated += 1
            if verbose:
                print(f"    plans: {success_days}/7 days generated")

    conn.close()
    print(f"\nDemo seed done: {created} new elders, "
          f"{len(DEMO_ELDERS) - created} already existed, "
          f"{plans_generated} daily plans generated.")


if __name__ == "__main__":
    seed()
