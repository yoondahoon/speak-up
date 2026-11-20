import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lang  # noqa: E402

SAMPLES = {
    "ko": "안녕하세요. 오늘 `speak.py` 파일을 수정했어요.",
    "ja": "こんにちは。今日はファイルを修正しました。",
    "zh": "你好。我今天修改了这个文件，请测试一下。",
    "ru": "Привет. Сегодня я исправил этот файл.",
    "uk": "Привіт. Сьогодні я виправив цей файл, і все працює.",
    "be": "Прывітанне. Сёння я выправіў гэты файл, і ўсё працуе.",
    "ur": "آپ کیسے ہیں؟ میں نے آج یہ فائل ٹھیک کر دی ہے۔",
    "ar": "مرحبا. لقد قمت بتعديل هذا الملف اليوم.",
    "fa": "سلام. امروز این فایل را تغییر دادم و پیام جدید نوشتم.",
    "he": "שלום. היום תיקנתי את הקובץ הזה.",
    "el": "Γεια σας. Σήμερα διόρθωσα αυτό το αρχείο.",
    "hi": "नमस्ते। आज मैंने इस फ़ाइल को ठीक किया।",
    "th": "สวัสดีครับ วันนี้ผมแก้ไขไฟล์นี้แล้ว",
    "en": "Hello. I fixed the file today and it is working now.",
    "es": "Hola. Hoy he corregido el archivo y está funcionando para todos.",
    "fr": "Bonjour. J'ai corrigé le fichier et il est prêt pour vous.",
    "de": "Hallo. Ich habe die Datei heute repariert und sie ist fertig.",
    "pt": "Olá. Eu corrigi o arquivo e você não precisa fazer nada.",
    "it": "Ciao. Ho corretto il file e questo è pronto per te.",
    "vi": "Xin chào. Hôm nay tôi đã sửa tệp này và nó không còn lỗi.",
    "tr": "Merhaba. Bugün bu dosyayı düzelttim ve çok iyi çalışıyor.",
    "pl": "Cześć. Dzisiaj naprawiłem ten plik i wszystko działa.",
}


class DetectTest(unittest.TestCase):
    def test_detects_many_languages(self) -> None:
        for expected, text in SAMPLES.items():
            with self.subTest(lang=expected):
                self.assertEqual(lang.detect_lang(text), expected)

    def test_korean_with_lots_of_english_code(self) -> None:
        text = "`build_command` 함수에서 engine 값을 확인해요. README도 고쳤어요."
        self.assertEqual(lang.detect_lang(text), "ko")

    def test_hint_resolves_ambiguous_latin_text(self) -> None:
        self.assertEqual(lang.detect_lang("OK", hint="pt-BR"), "pt-BR")
        self.assertEqual(lang.detect_lang("OK"), "en")

    def test_hint_with_region_kept_for_same_language(self) -> None:
        self.assertEqual(lang.detect_lang(SAMPLES["es"], hint="es-MX"), "es-MX")

    def test_hint_ignored_when_script_disagrees(self) -> None:
        self.assertEqual(lang.detect_lang(SAMPLES["ko"], hint="es"), "ko")


class SettingTest(unittest.TestCase):
    def test_normalizes_names_and_codes(self) -> None:
        self.assertEqual(lang.normalize_lang("Korean"), "ko")
        self.assertEqual(lang.normalize_lang("한국어"), "ko")
        self.assertEqual(lang.normalize_lang("Español"), "es")
        self.assertEqual(lang.normalize_lang("pt_br"), "pt-BR")
        self.assertEqual(lang.normalize_lang("klingon spoken badly"), "")

    def test_reads_claude_language_setting(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            path.write_text(json.dumps({"language": "japanese"}), encoding="utf-8")
            self.assertEqual(lang.claude_language_setting(path), "ja")


if __name__ == "__main__":
    unittest.main()
