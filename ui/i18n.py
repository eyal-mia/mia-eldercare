"""Tiny i18n helper. Loads locale JSON files and exposes t(key)."""

from pathlib import Path
import json

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
SUPPORTED = {"he": "עברית", "en": "English", "ru": "Русский"}
RTL_LANGS = {"he", "ar"}

_cache: dict[str, dict] = {}


def load(lang: str) -> dict:
    if lang not in _cache:
        path = LOCALES_DIR / f"{lang}.json"
        if not path.exists():
            path = LOCALES_DIR / "en.json"
        _cache[lang] = json.loads(path.read_text(encoding="utf-8"))
    return _cache[lang]


def t(key: str, lang: str = "he") -> str:
    return load(lang).get(key, key)


def is_rtl(lang: str) -> bool:
    return lang in RTL_LANGS
