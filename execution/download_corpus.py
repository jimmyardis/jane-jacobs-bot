#!/usr/bin/env python3
"""
Master Corpus Downloader for Historical Figure Chatbot Template
Runs all downloaders (Archive.org + Project Gutenberg) in sequence.

Usage:
    python execution/download_corpus.py --persona carl-jung
"""

import argparse
import archive_downloader
import gutenberg_downloader


def main(persona_id: str = "jane-jacobs"):
    """
    Run all corpus downloaders for a persona.

    Args:
        persona_id: Persona identifier (e.g., 'jane-jacobs')
    """
    print(f"\n{'#'*60}")
    print(f"# Corpus Download: {persona_id}")
    print(f"{'#'*60}\n")

    print(f"{'='*60}")
    print(f"  Source 1: Archive.org")
    print(f"{'='*60}")
    archive_downloader.main(persona_id=persona_id)

    print(f"\n{'='*60}")
    print(f"  Source 2: Project Gutenberg")
    print(f"{'='*60}")
    gutenberg_downloader.main(persona_id=persona_id)

    print(f"\n{'#'*60}")
    print(f"# All downloads complete for: {persona_id}")
    print(f"# Next step: python execution/corpus_cleaner.py --persona {persona_id}")
    print(f"{'#'*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download corpus from all sources for historical figure chatbot"
    )
    parser.add_argument(
        "--persona",
        default="jane-jacobs",
        help="Persona ID to download corpus for (default: jane-jacobs)"
    )
    args = parser.parse_args()

    main(persona_id=args.persona)
