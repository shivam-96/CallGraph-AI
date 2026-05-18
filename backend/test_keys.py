# -*- coding: utf-8 -*-
"""
test_keys.py - Validates all API keys in .env using minimal/zero token usage.
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 output so emoji render on Windows terminals
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Load .env from the same directory as this script
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

OK   = "[OK]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"

# ─── Testers ─────────────────────────────────────────────────────────────────

def test_openai_key(api_key: str) -> str:
    """Hits GET /v1/models — costs 0 tokens."""
    if not api_key or api_key.strip() == "":
        return f"{SKIP}  Key not set"
    try:
        resp = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            return f"{OK}   Valid"
        err = resp.json().get("error", {}).get("message", resp.text[:120])
        return f"{FAIL} {resp.status_code} — {err}"
    except requests.RequestException as e:
        return f"{FAIL} Connection error: {e}"


def test_elevenlabs_key(api_key: str) -> str:
    """Hits GET /v1/user — costs 0 characters."""
    if not api_key or api_key.strip() == "":
        return f"{SKIP}  Key not set"
    try:
        resp = requests.get(
            "https://api.elevenlabs.io/v1/user",
            headers={"xi-api-key": api_key},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            tier = data.get("subscription", {}).get("tier", "unknown")
            chars_left = data.get("subscription", {}).get("character_count", "?")
            limit = data.get("subscription", {}).get("character_limit", "?")
            return f"{OK}   Valid  |  Tier: {tier}  |  Chars used: {chars_left}/{limit}"
        try:
            err = resp.json().get("detail", {})
            if isinstance(err, dict):
                err = err.get("message", resp.text[:120])
        except Exception:
            err = resp.text[:120]
        return f"{FAIL} {resp.status_code} — {err}"
    except requests.RequestException as e:
        return f"{FAIL} Connection error: {e}"


def test_deepgram_key(api_key: str) -> str:
    """Hits GET /v1/projects — costs 0 credits."""
    if not api_key or api_key.strip() == "":
        return f"{SKIP}  Key not set"
    try:
        resp = requests.get(
            "https://api.deepgram.com/v1/projects",
            headers={"Authorization": f"Token {api_key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            projects = resp.json().get("projects", [])
            count = len(projects)
            name = projects[0].get("name", "—") if projects else "—"
            return f"{OK}   Valid  |  Projects: {count}  |  First: {name}"
        try:
            err = resp.json().get("err_msg", resp.text[:120])
        except Exception:
            err = resp.text[:120]
        return f"{FAIL} {resp.status_code} — {err}"
    except requests.RequestException as e:
        return f"{FAIL} Connection error: {e}"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 60)
    print("  CallGraph AI — API Key Validator")
    print(f"  .env path: {env_path}")
    print("=" * 60)

    results = {
        "OpenAI    ": test_openai_key(os.getenv("OPENAI_API_KEY", "")),
        "ElevenLabs": test_elevenlabs_key(os.getenv("ELEVENLABS_API_KEY", "")),
        "Deepgram  ": test_deepgram_key(os.getenv("DEEPGRAM_API_KEY", "")),
    }

    all_ok = True
    for service, status in results.items():
        print(f"  {service}  {status}")
        if FAIL in status or SKIP in status:
            all_ok = False

    print("=" * 60)
    if all_ok:
        print("  All keys valid — ready to launch CallGraph AI!")
    else:
        print("  Some keys are missing or invalid. Update backend/.env")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
