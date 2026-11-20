# read-aloud

A Claude Code plugin.

Have Claude Code **read its replies out loud**, for free.

- 💸 **Free and offline**: uses the voices already built into your OS. No API key, no account.
- 🌏 **Auto language**: picks a Korean, Japanese, Chinese or English voice based on the reply.
- 🧹 **Speaks like a person**: skips code blocks, URLs, tables and markdown symbols.
- ⚡ **Never blocks**: speech runs in the background. A new reply cuts off the old one.

| OS | Engine | Setup |
|---|---|---|
| Windows | SAPI (`System.Speech`) | Nothing. For Korean, install the Korean language pack (voice "Heami") |
| macOS | `say` | Nothing. Download extra voices in System Settings → Accessibility → Spoken Content |
| Linux | `espeak-ng` | `sudo apt install espeak-ng` |

Requires **Python 3.8+**.

## Install

In Claude Code:

```
/plugin marketplace add yoondahoon/read-aloud
/plugin install read-aloud@read-aloud
```

Restart Claude Code. The next reply will be read aloud.

## Usage

```
/read-aloud:speak off      # stop reading replies
/read-aloud:speak on       # start again
/read-aloud:speak stop     # stop the current speech
/read-aloud:speak status   # show settings
/read-aloud:speak voices   # list installed voices
```

### Talk both ways

Claude Code has built-in push-to-talk dictation. Type `/voice`, then **hold Space** and speak.
Together with read-aloud you can ask by voice and hear the answer.
The dictation language follows the `language` setting in `/config`.

## Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `READ_ALOUD_ENGINE` | `auto` | `sapi`, `say`, `espeak`, or `edge` |
| `READ_ALOUD_VOICE` | auto | Exact voice name, e.g. `Microsoft Heami Desktop` |
| `READ_ALOUD_VOICE_KO` (`_EN`, `_JA`, `_ZH`) | auto | Voice for one language only, e.g. `ko-KR-InJoonNeural` |
| `READ_ALOUD_RATE` | `0` | Speed. SAPI/edge: `-10`..`10`. macOS `say`: words per minute |
| `READ_ALOUD_MAX_CHARS` | `1200` | Longer replies are cut at a sentence boundary |

You can set them in `~/.claude/settings.json`:

```json
{ "env": { "READ_ALOUD_RATE": "2" } }
```

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

Claude Code의 답변을 **무료로 소리 내어 읽어주는** 플러그인이에요.

- 운영체제에 들어있는 음성을 써서 API 키도, 비용도 필요 없어요. 인터넷이 없어도 돼요.
- 답변이 한국어면 한국어 목소리로, 영어면 영어 목소리로 자동으로 읽어요.
- 코드 블록, 링크, 표 기호는 빼고 문장만 읽어요.

**설치** (Claude Code 안에서 입력)

```
/plugin marketplace add yoondahoon/read-aloud
/plugin install read-aloud@read-aloud
```

**끄기/켜기**: `/read-aloud:speak off`, `/read-aloud:speak on`

**말로 묻기**: Claude Code에 내장된 `/voice`를 켜고 **스페이스바를 누른 채** 말하세요. `/config`의 언어를 한국어로 해두면 한국어로 받아써요. read-aloud와 같이 쓰면 말로 묻고 소리로 답을 들을 수 있어요.

Windows에서 한국어 목소리가 안 나오면 설정 → 시간 및 언어 → 언어에서 **한국어 언어팩**을 설치하세요.

## License

MIT
