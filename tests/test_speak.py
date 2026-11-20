import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import speak  # noqa: E402


class CleanMarkdownTest(unittest.TestCase):
    def test_removes_code_blocks_and_formatting(self) -> None:
        md = "## 제목\n\n**굵게** 그리고 `code`\n\n```py\nprint(1)\n```\n- 항목 하나"
        self.assertEqual(speak.clean_markdown(md), "제목. 굵게 그리고 code. 항목 하나.")

    def test_tables_become_comma_lists(self) -> None:
        md = "| 이름 | 값 |\n|---|---|\n| A | 1 |"
        self.assertEqual(speak.clean_markdown(md), "이름, 값. A, 1.")

    def test_links_keep_label_and_drop_urls(self) -> None:
        md = "See [the docs](https://x.y/z) or https://a.b/c now"
        self.assertEqual(speak.clean_markdown(md), "See the docs or now.")

    def test_strips_emoji(self) -> None:
        self.assertEqual(speak.clean_markdown("⚠️ 주의 🚀"), "주의.")


class LanguageAndTruncateTest(unittest.TestCase):
    def test_detects_korean(self) -> None:
        self.assertEqual(speak.detect_lang("안녕하세요 반갑습니다 hello"), "ko")

    def test_defaults_to_english(self) -> None:
        self.assertEqual(speak.detect_lang("Hello world"), "en")

    def test_truncate_cuts_at_sentence(self) -> None:
        text = "First sentence here. Second sentence is longer than the limit allows."
        self.assertEqual(speak.truncate(text, 40), "First sentence here.")


class TranscriptTest(unittest.TestCase):
    def _write(self, entries: list) -> str:
        fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        fh.write("\n".join(json.dumps(e) for e in entries))
        fh.close()
        return fh.name

    def test_returns_text_after_last_user_entry(self) -> None:
        path = self._write([
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "old"}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result"}]}},
            {"type": "assistant", "message": {"content": [{"type": "thinking"}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "final"}]}},
        ])
        self.assertEqual(speak.last_reply_from_transcript(path), "final")

    def test_ignores_sidechain_entries(self) -> None:
        path = self._write([
            {"type": "user", "message": {"content": "hi"}},
            {"type": "assistant", "isSidechain": True,
             "message": {"content": [{"type": "text", "text": "agent"}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "main"}]}},
        ])
        self.assertEqual(speak.last_reply_from_transcript(path), "main")

    def test_prefers_last_assistant_message_field(self) -> None:
        data = {"last_assistant_message": "direct", "transcript_path": "missing.jsonl"}
        self.assertEqual(speak.reply_from_hook_input(data), "direct")


if __name__ == "__main__":
    unittest.main()
