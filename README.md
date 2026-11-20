# read-aloud

**Talk to Claude Code and hear it answer, for free.** 🎙️ → 🤖 → 🔊

This plugin reads every reply out loud. Works with **Claude Code** and **OpenAI Codex** (CLI and app). Combine it with Claude Code's built-in `/voice`
dictation and you get a hands-free voice conversation with no extra cost.

- 💸 **Free and offline**: uses the voices already built into your OS. No API key, no account.
- 🌏 **Any language**: detects the reply's language (Korean, Japanese, Chinese, Arabic, Hindi,
  Thai, Russian, Spanish, French, German, Vietnamese and many more) and picks a matching voice.
- 🧹 **Speaks like a person**: skips code blocks, URLs, tables and markdown symbols.
- ⚡ **Never blocks**: speech runs in the background. A new reply cuts off the old one.

| OS | Engine | Setup |
|---|---|---|
| Windows | SAPI (`System.Speech`) | Nothing. For Korean, install the Korean language pack (voice "Heami") |
| macOS | `say` | Nothing. Download extra voices in System Settings → Accessibility → Spoken Content |
| Linux | `espeak-ng` | `sudo apt install espeak-ng` |

Requires **Python 3.9+**.

## Install

In Claude Code:

```
/plugin marketplace add yoondahoon/read-aloud
/plugin install read-aloud@read-aloud
```

Restart Claude Code. The next reply will be read aloud.

## Install for OpenAI Codex

Codex supports the same kind of Stop hook. Run once:

```
git clone https://github.com/yoondahoon/read-aloud
python read-aloud/speak.py install-codex
```

Then open Codex. It will say **"Hooks need review"**. Check that the command runs
`read-aloud/speak.py hook`, and choose **Trust**. Codex replies are read aloud from then on.
To remove it: `python read-aloud/speak.py uninstall-codex`.

The installer only adds its own entry to `~/.codex/hooks.json` and keeps your other hooks.
Keep the cloned folder where it is, because the hook points to it.

## Quick start: voice conversation in 3 steps

1. Install the plugin (above) and restart Claude Code.
2. Turn on voice input: `/voice tap`
3. With the input box empty, **tap Space**, speak, then **tap Space again** to send.
   Claude answers and read-aloud speaks the reply.

> Tip: on Windows terminals use `tap` mode. `hold` mode may show the mic but not record.
> Use earphones so the spoken reply is not picked up by the microphone.

## Usage

```
/read-aloud:speak off      # stop reading replies
/read-aloud:speak on       # start again
/read-aloud:speak stop     # stop the current speech
/read-aloud:speak status   # show settings
/read-aloud:speak voices   # list installed voices
```

### Voice input (`/voice`)

Voice input is Claude Code's own feature, not part of this plugin.

```
/voice tap    # tap Space to start, tap again to send (recommended)
/voice hold   # hold Space while speaking
/voice off
```

The dictation language follows the `language` setting in `/config` (e.g. `korean`).

## Languages

The language of each reply is detected automatically:

- **Non-Latin scripts** (Hangul, Kana, Han, Cyrillic, Arabic, Hebrew, Greek, Devanagari, Bengali,
  Tamil, Telugu, Thai, Lao, Khmer, Myanmar, Georgian, Armenian, Ethiopic, ...) by their letters.
  English code words inside a Korean reply still count as Korean.
- **Latin-script languages** (English, Spanish, French, German, Italian, Portuguese, Dutch,
  Swedish, Danish, Norwegian, Finnish, Polish, Czech, Turkish, Vietnamese, Indonesian, Romanian,
  Hungarian, Swahili, Tagalog) by common words and accented letters.
- When unsure, it uses your Claude Code `language` setting (e.g. `"language": "español"`), or
  `READ_ALOUD_LANG` if you set it (e.g. `pt-BR`, `es-MX`, `fr-CA` to pick a region).

Voice availability per engine:

| Engine | Languages |
|---|---|
| `edge` | 300+ neural voices in about 75 languages. Picked automatically |
| `sapi` (Windows) | Languages whose voice you installed (Settings → Time & language → Speech) |
| `say` (macOS) | Languages whose voice you downloaded (Accessibility → Spoken Content) |
| `espeak` (Linux) | 100+ languages built in (robotic but clear) |

If no voice exists for a language, the system's default voice is used.

## Privacy

- **No API key, no account, no sign-up.** Nothing in this plugin is tied to anyone's keys.
- With the default engines (`sapi`, `say`, `espeak`) everything stays on your computer.
- With `edge`, the reply text is sent to Microsoft's Read Aloud service to make the audio.
  Don't use `edge` if your replies may contain secrets.
- Voice input (`/voice`) is Claude Code's own feature and uses your own Claude account.

## Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `READ_ALOUD_ENGINE` | `auto` | `sapi`, `say`, `espeak`, or `edge` |
| `READ_ALOUD_VOICE` | auto | Exact voice name, e.g. `Microsoft Heami Desktop` |
| `READ_ALOUD_VOICE_KO` (`_EN`, `_ES`, any code) | auto | Voice for one language only, e.g. `ko-KR-InJoonNeural` |
| `READ_ALOUD_LANG` | from `/config` | Fallback language when detection is unsure, e.g. `pt-BR` |
| `READ_ALOUD_RATE` | `0` | Speed. SAPI/edge: `-10`..`10`. macOS `say`: words per minute |
| `READ_ALOUD_MAX_CHARS` | `1200` | Longer replies are cut at a sentence boundary |

Set them once for every app (Claude Code and Codex):

```
python speak.py set engine edge
python speak.py set voice_ko ko-KR-InJoonNeural
python speak.py set rate 2
python speak.py set rate          # remove a setting
```

These go to `~/.claude/read-aloud/config.json`. The plugin also reads `READ_ALOUD_*` from the
`env` block of `~/.claude/settings.json` and from real environment variables (highest priority).

### Optional: nicer neural voices (`edge`)

```
pip install edge-tts
```

Then set `READ_ALOUD_ENGINE=edge`. Korean voices: `ko-KR-SunHiNeural` (female, default), `ko-KR-InJoonNeural` (male), `ko-KR-HyunsuMultilingualNeural` (male). If edge fails (offline, service change), it falls back to the system voice. This is free and needs no key, but it is **online** and uses
Microsoft Edge's Read Aloud service through the unofficial `edge-tts` package, so it may change or
stop working at any time. The default engines stay fully offline.

## How it works

A Claude Code `Stop` hook runs `speak.py` when Claude finishes a reply. The script reads the final
reply, turns markdown into plain sentences, then starts the OS speech engine as a detached process
and returns at once.

## Without the plugin system

Clone the repo and add this to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [{ "hooks": [{ "type": "command",
      "command": "bash /path/to/read-aloud/hooks/run.sh hook" }] }]
  }
}
```

## Test

```
python -m unittest discover -s tests
```

---

## 한국어 안내

Claude Code와 **말로 대화하는** 무료 플러그인이에요. 말로 묻고(`/voice`), 답변을 소리로 들어요(read-aloud).

- 운영체제에 들어있는 음성을 써서 API 키도, 비용도 필요 없어요. 인터넷이 없어도 돼요.
- 답변 언어를 자동으로 알아내서 그 나라 목소리로 읽어요. 한국어, 영어, 일본어, 중국어, 스페인어, 아랍어, 힌디어, 태국어 등 전 세계 언어를 지원해요.
- API 키나 계정이 필요 없어요. 기본 목소리는 PC 안에서만 동작하고, `edge` 목소리를 쓸 때만 답변 글이 Microsoft 서버로 가요.
- 코드 블록, 링크, 표 기호는 빼고 문장만 읽어요.

**설치** (Claude Code 안에서 입력)

```
/plugin marketplace add yoondahoon/read-aloud
/plugin install read-aloud@read-aloud
```

**Codex에서 쓰기**: `git clone https://github.com/yoondahoon/read-aloud` 후 `python read-aloud/speak.py install-codex`를 실행하고, Codex를 열어 **"Hooks need review"**가 나오면 **Trust**를 누르세요.

**끄기/켜기**: `/read-aloud:speak off`, `/read-aloud:speak on`

**말로 묻기**: Claude Code에 내장된 `/voice tap`을 켜고, 입력창이 빈 상태에서 **스페이스바를 한 번 누르고 → 말하고 → 다시 한 번 누르면** 보내져요. (Windows에서는 `hold`보다 `tap`이 잘 돼요.) `/config`의 언어를 한국어로 해두면 한국어로 받아써요. read-aloud와 같이 쓰면 말로 묻고 소리로 답을 들을 수 있어요.

**더 자연스러운 목소리**: `pip install edge-tts` 후 설정에 `READ_ALOUD_ENGINE=edge`, 남자 목소리는 `READ_ALOUD_VOICE_KO=ko-KR-InJoonNeural`을 넣으세요. (인터넷 필요, 실패하면 기본 목소리로 자동 전환)

Windows에서 한국어 목소리가 안 나오면 설정 → 시간 및 언어 → 언어에서 **한국어 언어팩**을 설치하세요.

## License

MIT
