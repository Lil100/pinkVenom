import asyncio
import ctypes
import os
import subprocess
import tempfile
import uuid
from datetime import datetime

import edge_tts
import psutil
import requests


# ──────────────────────────────────────────────
# 1. SYSTEM CONTEXT GATHERING
# ──────────────────────────────────────────────

def get_battery_info():
    """Return (percent, is_plugged) tuple from psutil."""
    battery = psutil.sensors_battery()
    if battery:
        return int(battery.percent), battery.power_plugged
    return None, None


def get_location():
    """Resolve city via IP geolocation. Returns city name or fallback."""
    # Try primary service (ipapi.co)
    try:
        resp = requests.get("https://ipapi.co/json/", timeout=15)
        resp.raise_for_status()
        data = resp.json()
        city = data.get("city")
        if city:
            return city
    except Exception:
        pass

    # Fallback to ip-api.com  
    try:
        resp = requests.get("http://ip-api.com/json/?fields=status,city", timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            city = data.get("city")
            if city:
                return city
    except Exception:
        pass

    return "an unknown location"


def get_formatted_time():
    """Return current time as 12-hour AM/PM string."""
    now = datetime.now()
    return now.strftime("%I:%M %p").lstrip("0")


# ──────────────────────────────────────────────
# 2. TEXT-TO-SPEECH ENGINE
# ──────────────────────────────────────────────

_VOICE = "en-GB-LibbyNeural"
_AUDIO_FILE = "pink_venom_output.mp3"


def _play_mp3_windows(path: str) -> None:
    """Play an MP3 file synchronously using the Windows MCI API."""
    abs_path = os.path.abspath(path)
    alias = "pv"  # short alias to avoid uniqueness issues; only one plays at a time
    # Close any previously opened instance (harmless if none open)
    ctypes.windll.winmm.mciSendStringW(f"close {alias}", None, 0, None)
    # Open the MP3 as an mpegvideo device
    ctypes.windll.winmm.mciSendStringW(
        f'open "{abs_path}" type mpegvideo alias {alias}', None, 0, None
    )
    # Play and WAIT for completion
    ctypes.windll.winmm.mciSendStringW(f"play {alias} wait", None, 0, None)
    # Close the device
    ctypes.windll.winmm.mciSendStringW(f"close {alias}", None, 0, None)


async def speak(text: str) -> None:
    """Synthesise text to audio and play it synchronously (blocks until done)."""
    print(f"  🎙️  Pink Venom: {text}")
    # Use a unique filename to prevent sequential calls from overwriting each other
    unique_id = uuid.uuid4().hex[:8]
    audio_path = os.path.join(tempfile.gettempdir(), f"pink_venom_{unique_id}.mp3")
    communicate = edge_tts.Communicate(text, _VOICE)
    await communicate.save(audio_path)
    # Play synchronously so the caller waits for playback to finish before returning
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _play_mp3_windows, audio_path)


# ──────────────────────────────────────────────
# 3. PROFILE ROUTING ENGINE
# ──────────────────────────────────────────────

_PROFILE_PATHS = {
    "codebase": None,
    "work":     r"C:\Users\Public\Lilian\MTECH-WORK",
    "personal": r"C:\Users\Public\Lilian\personal_Projects",
}


def launch_profile_environment(choice: str) -> bool:
    """
    Launch Chrome + VS Code pointed at the chosen profile directory.
    Returns True if a valid profile was launched, False otherwise.
    """
    directory = _PROFILE_PATHS.get(choice.lower().strip())
    if directory is None:
        # Codebase profile: launch VS Code without a specific folder
        if choice.lower().strip() == "codebase":
            subprocess.Popen(
                "code",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.Popen(
                "start chrome",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("  ✅  Launched Chrome + VS Code for profile 'codebase'")
            return True
        return False

    # Sanity-check the directory exists
    if not os.path.isdir(directory):
        print(f"  ⚠  Warning: directory '{directory}' not found, launching anyway.")

    # Launch Visual Studio Code in the target directory
    subprocess.Popen(
        f'code "{directory}"',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Launch Google Chrome
    subprocess.Popen(
        "start chrome",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print(f"  ✅  Launched Chrome + VS Code for profile '{choice}' → {directory}")
    return True


# ──────────────────────────────────────────────
# 4. BACKGROUND BATTERY MONITOR DAEMON
# ──────────────────────────────────────────────

async def battery_monitor_daemon() -> None:
    """
    Loop indefinitely every 4 hours; check battery and speak a
    check-in message with escalating warnings based on charge level.
    """
    CHECK_INTERVAL_SECONDS = 4 * 60 * 60  # 4 hours

    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

        percent, plugged = get_battery_info()
        base = "Four hours have slipped by, Lilian. I'm checking in. Do you require any adjustments?"

        if percent is not None and not plugged:
            if percent < 20:
                warning = (
                    f"Urgent warning — battery has dropped to {percent} percent. "
                    "Please connect to a power source as soon as possible."
                )
            elif percent < 40:
                warning = (
                    f"Just a heads up — battery is at {percent} percent and discharging. "
                    "You may want to check the power source."
                )
            else:
                warning = ""
            message = f"{base} {warning}" if warning else base
        else:
            # Either no battery data or plugged in → no extra warning needed
            message = base

        await speak(message)


# ──────────────────────────────────────────────
# 5. MAIN ORCHESTRATION
# ──────────────────────────────────────────────

async def main() -> None:
    # --- Non-blocking startup delay ---
    print("⏳ Pink Venom initialising…")
    await asyncio.sleep(3)

    # --- Gather context ---
    percent, plugged = get_battery_info()
    location = get_location()
    current_time = get_formatted_time()

    # --- Synthesise greeting ---
    if percent is not None:
        status = "plugged in and charging" if plugged else "discharging"
        greeting = (
            f"Hello Lilian. Pink Venom is online. "
            f"It is currently {current_time} here in {location}. "
            f"Power reserves are sitting at {percent} percent and {status}."
        )
    else:
        greeting = (
            f"Hello Lilian. Pink Venom is online. "
            f"It is currently {current_time} here in {location}. "
            f"I am unable to read battery metrics right now."
        )

    await speak(greeting)

    # --- Profile routing prompt (spoken + printed) ---
    prompt_text = "All systems are green, Let me know where we're focusing today and I'll spin up the environment."
    await speak(prompt_text)
    print("\n" + "─" * 55)
    print(f"  🤖  {prompt_text}")
    try:
        choice = input("  👤  ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  ⚠  No input received. Leaving spaces idle.")
        choice = ""

    if not launch_profile_environment(choice):
        fallback = (
            f"I'm sorry, '{choice}' is not a recognised profile. "
            "Leaving spaces idle for now. Let me know if you need anything."
        )
        await speak(fallback)

    # --- Spin up background battery monitor ---
    print("\n⏰ Starting 4-hour battery check-in daemon…")
    asyncio.create_task(battery_monitor_daemon())

    print("✅ Pink Venom is fully operational. The daemon will check in every 4 hours.\n")

    # Keep the event-loop alive so the daemon can fire later
    try:
        while True:
            await asyncio.sleep(3600)  # sleep 1 hour at a time
    except KeyboardInterrupt:
        print("\nShutting down Pink Venom. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())