import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engines"))
import edge  # noqa: E402
import speak  # noqa: E402

VOICES = [{"ShortName": n, "Locale": "-".join(n.split("-")[:2])} for n in (
    "ko-KR-SunHiNeural", "ko-KR-InJoonNeural", "en-US-AriaNeural",
    "en-US-AndrewMultilingualNeural", "en-GB-SoniaNeural", "es-ES-AlvaroNeural",
    "es-MX-DaliaNeural", "sw-KE-ZuriNeural")]


class PreferredVoiceTest(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.object(edge, "list_voices", return_value=VOICES)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_korean_defaults_to_injoon(self) -> None:
        self.assertEqual(edge.resolve_voice("auto:ko"), "ko-KR-InJoonNeural")

    def test_english_defaults_to_smooth_voice(self) -> None:
        self.assertEqual(edge.resolve_voice("auto:en"), "en-US-AndrewMultilingualNeural")

    def test_region_request_keeps_region(self) -> None:
        self.assertEqual(edge.resolve_voice("auto:es-MX"), "es-MX-DaliaNeural")
        self.assertEqual(edge.resolve_voice("auto:en-GB"), "en-GB-SoniaNeural")

    def test_language_without_preference_still_resolves(self) -> None:
        self.assertEqual(edge.resolve_voice("auto:sw"), "sw-KE-ZuriNeural")

    def test_explicit_voice_wins(self) -> None:
        self.assertEqual(edge.resolve_voice("ko-KR-SunHiNeural"), "ko-KR-SunHiNeural")


class AutoEngineTest(unittest.TestCase):
    def test_auto_uses_edge_when_installed(self) -> None:
        with mock.patch.object(speak, "env", return_value="auto"), \
             mock.patch.object(speak, "edge_available", return_value=True):
            self.assertEqual(speak.pick_engine(), "edge")

    def test_auto_uses_os_voice_without_edge(self) -> None:
        with mock.patch.object(speak, "env", return_value="auto"), \
             mock.patch.object(speak, "edge_available", return_value=False):
            self.assertIn(speak.pick_engine(), ("sapi", "say", "espeak"))


if __name__ == "__main__":
    unittest.main()
