# 🕷️ Pink Venom — Voice-Enabled Desktop Assistant

**Pink Venom** is a desktop voice assistant for Windows that greets the user with a spoken system-status briefing, launches a tailored development environment (VS Code + Chrome) based on the user's chosen profile, and runs a background daemon that periodically checks in with battery status updates — all through natural text-to-speech.

---

## ✨ Features

| Feature | Description |
|---|---|
| **⏰ Time & Location Greeting** | Resolves the user's city via IP geolocation and announces the current time in a natural voice. |
| **🔋 Battery Status** | Reads live power metrics — percentage and charging/discharging state — and speaks them aloud. |
| **🗣️ Text-to-Speech** | Synthesises all messages using `edge-tts` (Microsoft Edge's neural TTS engine) with the `en-GB-LibbyNeural` voice. |
| **🚀 Profile-Based Environment Launch** | Prompts the user to pick a profile (`codebase`, `work`, `personal`) and automatically opens Visual Studio Code (pointed at the profile directory) alongside Google Chrome. |
| **⏳ 4-Hour Check-In Daemon** | A background coroutine reports in every 4 hours with the current battery level, escalating warnings when the charge drops below 40% or 20%. |
| **🔊 Windows Native Audio Playback** | Plays generated MP3 files via the Windows MCI API (`winmm.dll`) for low-latency, non-blocking audio. |

---

## 🧠 How It Works

### 1. System Context Gathering

On startup, Pink Venom collects three pieces of contextual information:

- **Battery** — via [`psutil.sensors_battery()`](https://psutil.readthedocs.io/en/latest/#psutil.sensors_battery). Returns the charge percentage and whether the AC adapter is plugged in.
- **Location** — via IP geolocation. Tries [`ipapi.co`](https://ipapi.co/json/) first, falling back to `ip-api.com` if the primary service fails. Resolves down to the city level.
- **Time** — formatted as a 12-hour AM/PM string (e.g. `"4:11 PM"`).

### 2. Text-to-Speech Engine

Uses the [`edge-tts`](https://github.com/rany2/edge-tts) library to call Microsoft Edge's free, high-quality neural TTS service. Audio is saved as a temporary MP3 file and played through the Windows MCI API (`winmm.dll`), which blocks until playback finishes — ensuring the greeting completes before the next action starts.

### 3. Profile Routing Engine

The user is prompted (via `input()`) to enter one of three profile names:

| Profile | Directory | Behaviour |
|---|---|---|
| `codebase` | *(none)* | Opens VS Code without a specific folder + Chrome. |
| `work` |` | Opens VS Code rooted at the work directory + Chrome. |
| `personal` |` | Opens VS Code rooted at the personal projects directory + Chrome. |

If the input doesn't match a recognised profile, Pink Venom falls back with a spoken apology and leaves existing windows idle.

### 4. Background Battery Monitor Daemon

After the initial interaction, a daemon coroutine is spawned via `asyncio.create_task()`. It runs indefinitely with a 4-hour sleep interval, then:

- Checks the current battery level.
- If **unplugged and below 20%** — issues an urgent warning to connect to power.
- If **unplugged and between 20–40%** — issues a gentle heads-up.
- If **plugged in or ≥40%** — delivers a neutral check-in message.

The daemon keeps the event loop alive indefinitely (sleeping one hour at a time) until the user presses `Ctrl+C`.

---

## 📦 Dependencies

All installable via `pip`:

```
edge-tts
psutil
requests
```

- `edge-tts` — Microsoft Edge TTS wrapper
- `psutil` — system & battery information
- `requests` — IP geolocation API calls

No external runtime dependencies beyond Python 3.8+ and a Windows operating system (the MCI playback call uses `ctypes` which is part of the standard library).

---

## 🚀 Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/Lil100/pinkVenom.git
cd pinkVenom

# 2. Install dependencies
pip install edge-tts psutil requests

# 3. Run the assistant
python pink_venom.py
```

The assistant will:

1. Wait 3 seconds (non-blocking delay for initialisation).
2. Speak a greeting that includes the current time, your location, and battery status.
3. Prompt you to enter a profile name (type `codebase`, `work`, or `personal` and press Enter).
4. Launch VS Code + Chrome for the chosen profile.
5. Start the 4-hour battery check-in daemon.

Press **`Ctrl+C`** at any time to shut down gracefully.

---

## 🗂️ Project Structure

```
pinkVenom/
├── pink_venom.py          # Main application (single-file system)
├── pink_venom_output.mp3  # Most recent TTS output (auto-generated)
├── README.md              # This file
└── (other project files / directories as needed)
```

---

## ⚙️ Configuration & Customisation

- **Voice** — Change `_VOICE` in `pink_venom.py` to any `edge-tts` supported voice (e.g. `"en-US-AriaNeural"`).
- **Profiles** — Add or modify entries in the `_PROFILE_PATHS` dictionary to point to other directories.
- **Check-in Interval** — Adjust `CHECK_INTERVAL_SECONDS` in the `battery_monitor_daemon()` function (default: 4 hours = 14 400 seconds).
- **Output Audio File** — Change `_AUDIO_FILE` to customise the name of the generated MP3.

---

## 🛠️ Technical Highlights

| Aspect | Detail |
|---|---|
| **Async Architecture** | Built entirely on `asyncio` — the TTS synthesis, playback, and battery daemon all run cooperatively on a single thread. |
| **Windows MCI Playback** | Uses `ctypes` to call `winmm.dll`'s `mciSendStringW` for native MP3 playback, avoiding the need for media-player subprocess calls. |
| **Fault Tolerance** | Geolocation uses a fallback chain; battery monitor degrades gracefully when no battery is present (e.g. a desktop PC). |
| **Unique Temp Files** | Each TTS call writes to a UUID-tagged temp file under `%TEMP%`, preventing race conditions when audio is regenerated. |

---

## 📄 License

This project is provided for personal and educational use. All trademarks and third-party libraries remain the property of their respective owners.

---

*Built with ❤️ for Lilian.*