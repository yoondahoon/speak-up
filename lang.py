"""Language detection for spoken replies.

Strategy:
1. Count letters per writing system (Hangul, Kana, Cyrillic, Arabic, Devanagari, ...).
   A non-Latin script wins if it makes up a fair share of the letters. Replies mixed with
   English code identifiers still count as the reply's own language.
2. For Latin-script text, score common function words and accented letters.
3. When unsure, use a hint: READ_ALOUD_LANG, or Claude Code's `language` setting.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MIN_SCRIPT_LETTERS = 5
MIN_SCRIPT_SHARE = 0.15
MIN_LATIN_SCORE = 2

# script name -> (regex, default language, other languages using this script)
SCRIPTS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "hangul": (r"[가-힣ᄀ-ᇿ]", "ko", ()),
    "kana": (r"[぀-ヿ]", "ja", ()),
    "han": (r"[一-鿿]", "zh", ("ja", "yue")),
    "cyrillic": (r"[Ѐ-ӿ]", "ru", ("be", "uk", "bg", "sr", "mk", "be", "kk", "mn", "ky")),
    "arabic": (r"[؀-ۿݐ-ݿ]", "ar", ("ur", "fa", "ps")),
    "hebrew": (r"[֐-׿]", "he", ("yi",)),
    "greek": (r"[Ͱ-Ͽ]", "el", ()),
    "devanagari": (r"[ऀ-ॿ]", "hi", ("mr", "ne", "sa")),
    "bengali": (r"[ঀ-৿]", "bn", ("as",)),
    "gurmukhi": (r"[਀-੿]", "pa", ()),
    "gujarati": (r"[઀-૿]", "gu", ()),
    "tamil": (r"[஀-௿]", "ta", ()),
    "telugu": (r"[ఀ-౿]", "te", ()),
    "kannada": (r"[ಀ-೿]", "kn", ()),
    "malayalam": (r"[ഀ-ൿ]", "ml", ()),
    "sinhala": (r"[඀-෿]", "si", ()),
    "thai": (r"[฀-๿]", "th", ()),
    "lao": (r"[຀-໿]", "lo", ()),
    "myanmar": (r"[က-႟]", "my", ()),
    "khmer": (r"[ក-៿]", "km", ()),
    "georgian": (r"[Ⴀ-ჿ]", "ka", ()),
    "armenian": (r"[԰-֏]", "hy", ()),
    "ethiopic": (r"[ሀ-፿]", "am", ()),
}
LATIN = r"[A-Za-zÀ-ɏḀ-ỿ]"

# Distinctive letters that point to one script variant / Latin language.
# Order in SCRIPTS matters: a language whose markers are unique (be: ў, ur: ٹڈڑںے) is checked
# before one whose markers it also uses (uk: і, fa: پچگ), so be/ur are not misread as uk/fa.
SCRIPT_MARKERS = {"uk": "іїєґ", "be": "ў", "fa": "پچژگ", "ur": "ٹڈڑںے"}
LATIN_MARKERS = {
    "es": "ñ¿¡", "fr": "çœàèêëîïûù", "de": "äöüß", "pt": "ãõ", "ro": "ășț",
    "pl": "ąęłśżźń", "cs": "řůě", "tr": "ğış", "hu": "őű", "vi": "ơưđạảấầẩẫậắằẳẵặẹẻẽếềểễệịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ",
    "sv": "å", "da": "øæ", "is": "þð",
}
STOPWORDS = {
    "en": "the and is are you this that with for not have it was what can will",
    "es": "el la los las que es de y en por para una con no está pero como más",
    "fr": "le la les des est et que une pour pas vous avec dans sur ce qui mais",
    "de": "der die das und ist nicht ein eine ich sie mit zu auf für den sich auch",
    "it": "il lo gli che è di e non una per sono con della questo come anche",
    "pt": "o os as que é de e não um uma para com você está mas como isso",
    "nl": "de het een en is niet dat van ik je voor met zijn ook maar",
    "sv": "och är det att inte en jag du för med som på har",
    "da": "og er det at ikke en jeg du for med som på har",
    "nb": "og er det å ikke en jeg du for med som på har",
    "fi": "ja on ei se että minä sinä tämä mutta kuin ovat",
    "pl": "i w nie jest to że na się z do jak co",
    "cs": "a je se na že to v ne jsem jak pro",
    "tr": "ve bir bu için değil ile da de ne çok ama",
    "vi": "và là của không có được cho này những một trong",
    "id": "dan yang ini itu tidak ada untuk dengan saya anda di",
    "ro": "și este nu de la în că un o pentru cu",
    "hu": "és a az hogy nem egy van ez is meg",
    "sw": "na ni ya wa kwa katika hii hiyo kama",
    "tl": "ang ng sa mga ay na hindi ko mo",
}
_STOPSETS = {lang: set(words.split()) for lang, words in STOPWORDS.items()}

# Claude Code `language` setting values (English and native names) -> ISO code.
LANGUAGE_NAMES = {
    "english": "en", "korean": "ko", "한국어": "ko", "japanese": "ja", "日本語": "ja",
    "chinese": "zh", "中文": "zh", "简体中文": "zh", "繁體中文": "zh", "cantonese": "yue",
    "spanish": "es", "español": "es", "french": "fr", "français": "fr",
    "german": "de", "deutsch": "de", "italian": "it", "italiano": "it",
    "portuguese": "pt", "português": "pt", "dutch": "nl", "nederlands": "nl",
    "russian": "ru", "русский": "ru", "ukrainian": "uk", "українська": "uk",
    "polish": "pl", "polski": "pl", "czech": "cs", "čeština": "cs", "turkish": "tr",
    "türkçe": "tr", "arabic": "ar", "العربية": "ar", "persian": "fa", "farsi": "fa",
    "فارسی": "fa", "urdu": "ur", "hebrew": "he", "עברית": "he", "greek": "el",
    "hindi": "hi", "हिन्दी": "hi", "हिंदी": "hi", "bengali": "bn", "বাংলা": "bn",
    "tamil": "ta", "telugu": "te", "marathi": "mr", "thai": "th", "ไทย": "th",
    "vietnamese": "vi", "tiếng việt": "vi", "indonesian": "id", "bahasa indonesia": "id",
    "malay": "ms", "bahasa melayu": "ms", "filipino": "fil", "tagalog": "tl",
    "swedish": "sv", "svenska": "sv", "danish": "da", "dansk": "da",
    "norwegian": "nb", "norsk": "nb", "finnish": "fi", "suomi": "fi",
    "romanian": "ro", "română": "ro", "hungarian": "hu", "magyar": "hu",
    "swahili": "sw", "kiswahili": "sw",
}


def normalize_lang(value: str) -> str:
    """'Korean' / '한국어' / 'ko-KR' / 'pt_BR' -> 'ko' / 'ko' / 'ko-KR' / 'pt-BR'."""
    value = (value or "").strip()
    if not value:
        return ""
    named = LANGUAGE_NAMES.get(value.lower())
    if named:
        return named
    if re.fullmatch(r"[A-Za-z]{2,3}([-_][A-Za-z0-9]{2,4})?", value):
        parts = re.split(r"[-_]", value)
        return parts[0].lower() + ("-" + parts[1].upper() if len(parts) > 1 else "")
    return ""


def base(lang: str) -> str:
    return lang.split("-")[0] if lang else ""


def claude_language_setting(settings_path: Path | None = None) -> str:
    path = settings_path or Path.home() / ".claude" / "settings.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    value = data.get("language")
    return normalize_lang(value) if isinstance(value, str) else ""


def _script_lang(script: str, text: str, hint: str) -> str:
    _, default, others = SCRIPTS[script]
    for lang in others:
        if lang in SCRIPT_MARKERS and any(ch in text for ch in SCRIPT_MARKERS[lang]):
            return lang
    if base(hint) in (default, *others):
        return hint
    return default


def _latin_lang(text: str, hint: str) -> str:
    lowered = text.lower()
    words = re.findall(r"[^\W\d_]+", lowered)
    scores = {lang: sum(1 for w in words if w in stops) for lang, stops in _STOPSETS.items()}
    for lang, marks in LATIN_MARKERS.items():
        scores[lang] = scores.get(lang, 0) + 2 * min(5, sum(lowered.count(m) for m in marks))
    best, score = max(scores.items(), key=lambda kv: kv[1])
    ranked = sorted(scores.values(), reverse=True)
    hint_base = base(hint)
    if hint_base in scores and scores[hint_base] >= ranked[0] * 0.8 and scores[hint_base] > 0:
        return hint
    if score >= MIN_LATIN_SCORE:
        return best
    return hint if hint_base and not _is_non_latin(hint_base) else "en"


def _is_non_latin(lang: str) -> bool:
    return any(lang == d or lang in o for _, d, o in SCRIPTS.values())


def detect_lang(text: str, hint: str = "") -> str:
    """Return an ISO language code (possibly with region, e.g. 'pt-BR' from the hint)."""
    hint = normalize_lang(hint)
    counts = {name: len(re.findall(rx, text)) for name, (rx, _, _) in SCRIPTS.items()}
    if counts["kana"]:
        counts["kana"] += counts["han"]          # Japanese mixes kanji with kana
        counts["han"] = 0
    letters = sum(counts.values()) + len(re.findall(LATIN, text))
    script, n = max(counts.items(), key=lambda kv: kv[1])
    if n >= MIN_SCRIPT_LETTERS and n >= MIN_SCRIPT_SHARE * max(letters, 1):
        return _script_lang(script, text, hint)
    return _latin_lang(text, hint)
