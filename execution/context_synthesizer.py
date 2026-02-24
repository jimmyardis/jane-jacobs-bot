#!/usr/bin/env python3
"""
Context Synthesizer for Historical Figure Chatbot Template

Reads biographical/characterological source files from personas/{persona}/context/raw/
and uses the Anthropic API to synthesize them into a structured context_notes.md file.

The output is injected into the system prompt as 'Characterological Notes' — giving the
persona a lived, behavioral foundation beyond their published words.

IMPORTANT: This script calls the Anthropic API and will use tokens.
You will be prompted to confirm before any API call is made.

Usage:
    python execution/context_synthesizer.py --persona carl-jung
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

from persona_manager import PersonaManager

load_dotenv()


SYNTHESIS_PROMPT_TEMPLATE = """You are helping build a historically-grounded AI persona of {name}.

Below are biographical and characterological source texts about {name}. Your task is to synthesize these into a structured set of characterological notes that will be injected into the persona's system prompt.

Read all sources carefully, then produce a markdown document with the following sections. Be specific — cite particular anecdotes, quotes, and observations from the sources rather than making general claims. If sources contradict each other, note the contradiction.

## Personality Traits and Mannerisms
Observable traits: how they carried themselves, speech patterns, humor, silences, physicality, habits. Things that people who met them remarked upon.

## Behavior in Conversation and Debate
How did they engage others? Were they combative, generous, evasive, charming? How did they respond to criticism or disagreement? How did they treat students, peers, critics, strangers?

## Contradictions and Blind Spots
Known tensions between their public positions and private behavior. Areas where their thinking was inconsistent, biased, or where they refused to follow their own logic.

## Evolution of Thinking
How did their ideas change over their lifetime? What caused the shifts? What did they disavow or move away from? What remained constant?

## Key Relationships and Influences
Who shaped them most deeply (mentors, rivals, partners, children)? What did those relationships produce or cost them? What intellectual debts did they carry?

## Beyond the Published Work
What did they care about outside their professional identity? Hobbies, obsessions, fears, pleasures, private struggles. What did close friends know that readers didn't?

## How Contemporaries Described Them
Direct quotes or close paraphrases from people who knew them. Include both admiring and critical voices.

---

SOURCE TEXTS:
{source_texts}

---

Write the characterological notes now. Be concrete, specific, and honest about uncertainty where sources are thin.
"""


def load_source_files(context_raw_path: Path) -> list[tuple[str, str]]:
    """Load all text files from context/raw/. Returns list of (filename, content) tuples."""
    supported = {'.txt', '.md'}
    sources = []

    if not context_raw_path.exists():
        return sources

    for f in sorted(context_raw_path.iterdir()):
        if f.suffix.lower() in supported and f.name != '.gitkeep':
            try:
                content = f.read_text(encoding='utf-8', errors='replace')
                sources.append((f.name, content))
                print(f"  ✓ Loaded: {f.name} ({len(content):,} chars)")
            except Exception as e:
                print(f"  ✗ Could not read {f.name}: {e}")

    return sources


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


def main(persona_id: str):
    # Load persona
    print(f"Loading persona: {persona_id}")
    try:
        persona_config = PersonaManager.load_persona(persona_id)
        name = persona_config['metadata']['name']
        print(f"✓ Loaded persona: {name}\n")
    except Exception as e:
        print(f"✗ Error loading persona: {e}")
        sys.exit(1)

    # Find context/raw/ directory
    context_raw = PersonaManager.get_context_path(persona_config)
    print(f"Context source directory: {context_raw}")

    # Load source files
    print("\nLoading context source files...")
    sources = load_source_files(context_raw)

    if not sources:
        print(f"\n✗ No source files found in {context_raw}")
        print(f"  Add .txt or .md files to that directory, then re-run.")
        sys.exit(1)

    print(f"\n✓ Loaded {len(sources)} file(s)")

    # Build source text block — truncate to stay under 200k token limit
    MAX_SOURCE_CHARS = 750_000  # ~187,500 tokens, leaves room for prompt overhead
    source_texts = ""
    total_chars = 0
    for filename, content in sources:
        block = f"\n\n=== SOURCE: {filename} ===\n{content}"
        if total_chars + len(block) > MAX_SOURCE_CHARS:
            remaining = MAX_SOURCE_CHARS - total_chars
            if remaining > 5000:
                block = f"\n\n=== SOURCE: {filename} (truncated) ===\n{content[:remaining]}"
                source_texts += block
                print(f"  ⚠ Truncated {filename} to fit within token limit")
            else:
                print(f"  ⚠ Skipped {filename} — token limit reached")
            break
        source_texts += block
        total_chars += len(block)

    # Build full prompt
    full_prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
        name=name,
        source_texts=source_texts
    )

    # Estimate cost
    input_tokens = estimate_tokens(full_prompt)
    output_tokens = 2000  # generous estimate for output
    estimated_cost = (input_tokens * 3 + output_tokens * 15) / 1_000_000  # Sonnet pricing
    print(f"\nEstimated API usage:")
    print(f"  Input:  ~{input_tokens:,} tokens")
    print(f"  Output: ~{output_tokens:,} tokens (estimate)")
    print(f"  Cost:   ~${estimated_cost:.4f} (Sonnet rates)")

    # Confirm before calling API
    print(f"\nThis will call the Anthropic API and generate context_notes.md for {name}.")
    confirm = input("Proceed? (yes/no): ").strip().lower()
    if confirm not in ('yes', 'y'):
        print("Aborted.")
        sys.exit(0)

    # Call Anthropic API
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("✗ ANTHROPIC_API_KEY not set")
        sys.exit(1)

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    print(f"\nCalling Anthropic API...")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": full_prompt}]
        )
        notes = response.content[0].text
        actual_input = response.usage.input_tokens
        actual_output = response.usage.output_tokens
        print(f"✓ Received response ({actual_input:,} input / {actual_output:,} output tokens)")
    except Exception as e:
        print(f"✗ API call failed: {e}")
        sys.exit(1)

    # Save output
    project_root = Path(__file__).parent.parent
    output_path = project_root / "personas" / persona_id / "context_notes.md"

    output_path.write_text(notes, encoding='utf-8')
    print(f"\n✓ Saved context_notes.md to: {output_path}")
    print(f"\nNext step: restart api_server.py — it will automatically inject these notes")
    print(f"           into the system prompt as '## Characterological Notes'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Synthesize context sources into characterological notes for a persona"
    )
    parser.add_argument(
        "--persona",
        required=True,
        help="Persona ID (e.g., carl-jung)"
    )
    args = parser.parse_args()
    main(persona_id=args.persona)
