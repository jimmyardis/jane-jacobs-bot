#!/usr/bin/env python3
"""
ElevenLabs Voice Preview Tool
Audition voices for historical figure personas before committing to persona.json.

Usage:
  # Play a persona's current configured voice (once voice_id is set in persona.json)
  python execution/voice_preview.py --persona alexander-hamilton --text "The national bank is not a luxury. It is a necessity."

  # Try a specific voice_id (before setting it in persona.json)
  python execution/voice_preview.py --persona alexander-hamilton --voice-id abc123def456 --text "The national bank is not a luxury."

  # List all available ElevenLabs voices (no TTS call, just metadata)
  python execution/voice_preview.py --list-voices

  # Search voices by name/description keyword
  python execution/voice_preview.py --search-voices "scottish"

  # Adjust voice settings for a trial
  python execution/voice_preview.py --persona adam-smith --voice-id abc123 --text "..." --stability 0.6 --similarity 0.8

Output: saves MP3 to /tmp/<persona>_<voice_id>.mp3 and prints the path.
"""

import argparse
import os
import sys
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"


# ── Helpers ──────────────────────────────────────────────────────────────────

def require_api_key():
    if not ELEVENLABS_API_KEY:
        print("✗  ELEVENLABS_API_KEY not found in .env")
        print("   Add it: echo 'ELEVENLABS_API_KEY=your_key' >> ~/.env")
        sys.exit(1)


def auth_headers():
    return {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}


def load_persona_voice(persona_id: str) -> dict:
    """Load voice settings from persona.json."""
    project_root = Path(__file__).parent.parent
    config_path = project_root / "personas" / persona_id / "persona.json"

    if not config_path.exists():
        print(f"✗  persona.json not found for '{persona_id}': {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    voice = config.get("voice")
    if not voice:
        print(f"✗  No 'voice' field in {persona_id}/persona.json")
        print("   Add a voice block or pass --voice-id to override.")
        sys.exit(1)

    name = config.get("metadata", {}).get("name", persona_id)
    return voice, name


# ── Commands ─────────────────────────────────────────────────────────────────

def list_voices(search: str = None):
    """List available ElevenLabs voices (reads voice library, no TTS cost)."""
    require_api_key()

    resp = requests.get(f"{ELEVENLABS_BASE}/voices", headers=auth_headers())
    if not resp.ok:
        print(f"✗  ElevenLabs API error {resp.status_code}: {resp.text}")
        sys.exit(1)

    voices = resp.json().get("voices", [])

    if search:
        q = search.lower()
        voices = [
            v for v in voices
            if q in v.get("name", "").lower()
            or any(q in lbl.lower() for lbl in v.get("labels", {}).values())
            or q in v.get("description", "").lower()
        ]
        print(f"\nVoices matching '{search}' ({len(voices)} found):\n")
    else:
        print(f"\nAll available voices ({len(voices)} total):\n")

    # Sort by category then name
    voices.sort(key=lambda v: (v.get("category", "z"), v.get("name", "")))

    for v in voices:
        labels = v.get("labels", {})
        label_str = "  ".join(f"{k}: {val}" for k, val in labels.items() if val)
        category = v.get("category", "unknown")
        print(f"  {v['name']:<30}  id: {v['voice_id']}")
        print(f"  {'':30}  category: {category}")
        if label_str:
            print(f"  {'':30}  {label_str}")
        desc = v.get("description") or ""
        if desc:
            print(f"  {'':30}  {desc[:90]}")
        print()


def preview_voice(
    persona_id: str,
    text: str,
    voice_id_override: str = None,
    stability: float = None,
    similarity_boost: float = None,
    style: float = None,
    output_path: str = None,
):
    """Call ElevenLabs TTS and save MP3."""
    require_api_key()

    # Load persona voice settings
    voice_cfg, persona_name = load_persona_voice(persona_id)

    # Override individual fields if passed on CLI
    vid = voice_id_override or voice_cfg.get("voice_id")
    if not vid:
        print("✗  No voice_id set. Pass --voice-id or set it in persona.json.")
        sys.exit(1)

    stab  = stability       if stability       is not None else voice_cfg.get("stability", 0.5)
    sim   = similarity_boost if similarity_boost is not None else voice_cfg.get("similarity_boost", 0.75)
    sty   = style           if style           is not None else voice_cfg.get("style", 0.3)
    model = voice_cfg.get("model_id", "eleven_multilingual_v2")

    print(f"\nPersona    : {persona_name} ({persona_id})")
    print(f"Voice ID   : {vid}")
    print(f"Model      : {model}")
    print(f"Stability  : {stab}  Similarity: {sim}  Style: {sty}")
    print(f"Text       : {text[:80]}{'...' if len(text) > 80 else ''}\n")

    payload = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": stab,
            "similarity_boost": sim,
            "style": sty,
            "use_speaker_boost": True,
        },
    }

    print("Calling ElevenLabs TTS...")
    resp = requests.post(
        f"{ELEVENLABS_BASE}/text-to-speech/{vid}",
        headers=auth_headers(),
        json=payload,
        timeout=30,
    )

    if not resp.ok:
        print(f"✗  ElevenLabs error {resp.status_code}")
        try:
            detail = resp.json()
            print(f"   {detail}")
        except Exception:
            print(f"   {resp.text[:200]}")
        sys.exit(1)

    # Save MP3
    if output_path is None:
        safe_vid = vid[:8]
        output_path = f"/tmp/{persona_id}_{safe_vid}.mp3"

    Path(output_path).write_bytes(resp.content)
    size_kb = len(resp.content) / 1024

    print(f"✓  Saved {size_kb:.1f} KB → {output_path}")
    print(f"\n   Play it:  mpg123 {output_path}")
    print(f"         or:  afplay {output_path}   (macOS)")
    print(f"         or:  vlc {output_path}")

    # Print the command to set this voice_id in persona.json if it worked
    if voice_id_override:
        print(f"\n   If this voice sounds right, set in {persona_id}/persona.json:")
        print(f'     "voice_id": "{vid}",')


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Audition ElevenLabs voices for historical figure personas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list-voices",    action="store_true", help="List all available voices")
    mode.add_argument("--search-voices",  metavar="QUERY",     help="Search voices by keyword")

    parser.add_argument("--persona",    metavar="ID",    help="Persona ID (e.g. alexander-hamilton)")
    parser.add_argument("--text",       metavar="TEXT",  help="Text to speak")
    parser.add_argument("--voice-id",   metavar="ID",    help="Override voice_id from persona.json")
    parser.add_argument("--stability",  type=float,      help="Voice stability 0.0–1.0")
    parser.add_argument("--similarity", type=float,      help="Similarity boost 0.0–1.0")
    parser.add_argument("--style",      type=float,      help="Style 0.0–1.0")
    parser.add_argument("--output",     metavar="PATH",  help="Output MP3 path (default: /tmp/<persona>_<voice>.mp3)")

    args = parser.parse_args()

    if args.list_voices:
        list_voices()
    elif args.search_voices:
        list_voices(search=args.search_voices)
    else:
        if not args.persona:
            parser.error("--persona is required for TTS preview")
        if not args.text:
            parser.error("--text is required for TTS preview")
        preview_voice(
            persona_id=args.persona,
            text=args.text,
            voice_id_override=args.voice_id,
            stability=args.stability,
            similarity_boost=args.similarity,
            style=args.style,
            output_path=args.output,
        )


if __name__ == "__main__":
    main()
