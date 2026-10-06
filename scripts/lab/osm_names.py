"""English display names for Almaty streets.

Prefers OSM ``name:en``; otherwise converts ``name:ru`` / ``name`` (Russian or
Kazakh) by translating the street-type word and transliterating the rest.
"""

from __future__ import annotations

import re

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
    # Kazakh-specific letters
    "ә": "a", "ғ": "g", "қ": "k", "ң": "n", "ө": "o", "ұ": "u", "ү": "u", "һ": "h", "і": "i",
}

# (pattern, English type word); the type word is moved to the end.
_TYPE_WORDS = [
    (r"\bпроспект\b|\bдаңғылы\b", "Avenue"),
    (r"\bулица\b|\bкөшесі\b", "Street"),
    (r"\bшоссе\b|\bтас жолы\b|\bтрасса\b|\bавтомагистраль\b", "Highway"),
    (r"\bбульвар\b|\bжелекжолы\b", "Boulevard"),
    (r"\bпереулок\b|\bтұйық көшесі\b|\bқиылысы\b", "Lane"),
    (r"\bплощадь\b|\bалаңы\b", "Square"),
    (r"\bмикрорайон\b|\bшағын ауданы\b", "Microdistrict"),
    (r"\bкольцо\b|\bайналма\b", "Ring Road"),
    (r"\bразвязка\b", "Interchange"),
    (r"\bмост\b|\bкөпірі\b", "Bridge"),
]

_EN_TYPE_CASE = {
    "avenue": "Avenue", "street": "Street", "highway": "Highway", "boulevard": "Boulevard",
    "lane": "Lane", "road": "Road", "ring": "Ring", "square": "Square", "bridge": "Bridge",
    "microdistrict": "Microdistrict", "interchange": "Interchange",
}


def transliterate(text: str) -> str:
    out = []
    for ch in text:
        low = ch.lower()
        if low in _TRANSLIT:
            rep = _TRANSLIT[low]
            out.append(rep.capitalize() if ch != low and rep else rep)
        else:
            out.append(ch)
    return "".join(out)


def _title_words(text: str) -> str:
    words = []
    for word in text.split():
        if word.isdigit() or any(ch.isdigit() for ch in word):
            words.append(word)
        elif word.lower() in _EN_TYPE_CASE:
            words.append(_EN_TYPE_CASE[word.lower()])
        else:
            words.append(word[:1].upper() + word[1:])
    return " ".join(words)


def english_name(tags: dict[str, str]) -> str | None:
    en = (tags.get("name:en") or "").strip()
    if en:
        return _title_words(re.sub(r"\s+", " ", en))
    # Kazakh names are nominative ("Абай даңғылы" -> "Abay"); Russian ones are
    # often genitive ("проспект Абая" -> "Abaya"), so prefer Kazakh when present.
    kazakh = tags.get("name:kk") or (
        tags.get("name") if re.search(r"[әғқңөұүһі]|көшесі|даңғылы", (tags.get("name") or "").lower()) else None
    )
    local = (kazakh or tags.get("name:ru") or tags.get("name") or "").strip()
    if not local:
        return None
    lowered = local.lower()
    type_word = None
    for pattern, word in _TYPE_WORDS:
        if re.search(pattern, lowered):
            lowered = re.sub(pattern, " ", lowered)
            type_word = word
            break
    core = re.sub(r"\s+", " ", lowered).strip(" -,.")
    core = transliterate(core)
    core = _title_words(core)
    if not core:
        return type_word
    return f"{core} {type_word}" if type_word else core


def short_name(name: str) -> str:
    """Compact form for section labels: 'Masanchi Street' -> 'Masanchi St'."""
    return (
        name.replace(" Street", " St")
        .replace(" Avenue", " Ave")
        .replace(" Boulevard", " Blvd")
        .replace(" Highway", " Hwy")
    )
