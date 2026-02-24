#!/usr/bin/env python3
"""
Project Gutenberg Corpus Downloader for Historical Figure Chatbot Template
Downloads books from Project Gutenberg based on persona sources.json.
"""

import sys
import json
import argparse
import requests
from pathlib import Path
from typing import Dict, Optional

from persona_manager import PersonaManager

# Gutenberg URL patterns tried in order (most reliable first)
GUTENBERG_URL_PATTERNS = [
    "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt",
    "https://www.gutenberg.org/files/{id}/{id}-0.txt",
    "https://www.gutenberg.org/files/{id}/{id}.txt",
]


def download_gutenberg_book(book_info: Dict, output_dir: Path) -> bool:
    """Download a book from Project Gutenberg by ID."""
    gutenberg_id = book_info.get("gutenberg_id")
    if not gutenberg_id:
        print(f"  ✗ Missing gutenberg_id for: {book_info.get('title', 'unknown')}")
        return False

    print(f"\n{'='*60}")
    print(f"Downloading: {book_info['title']} ({book_info['year']})")
    print(f"  Gutenberg ID: {gutenberg_id}")
    print(f"{'='*60}")

    # Determine output filename
    safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_'
                         for c in book_info['title'])
    safe_title = safe_title.replace(' ', '_')
    output_filename = f"{safe_title}_{book_info['year']}.txt"
    output_path = output_dir / output_filename

    # Skip if already downloaded
    if output_path.exists():
        print(f"  ✓ Already exists: {output_path}")
        return True

    # Try each URL pattern in order
    for pattern in GUTENBERG_URL_PATTERNS:
        url = pattern.format(id=gutenberg_id)
        print(f"  Trying: {url}")
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                content = response.text

                # Basic sanity check — Gutenberg plain text files are usually >5KB
                if len(content) < 5000:
                    print(f"  ✗ Response too small ({len(content)} chars), skipping")
                    continue

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                size_kb = len(content) // 1024
                print(f"  ✓ Saved to: {output_path} ({size_kb}KB)")

                # Save metadata for reference
                metadata_path = output_path.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump({
                        "title": book_info["title"],
                        "author": book_info["author"],
                        "year": book_info["year"],
                        "gutenberg_id": gutenberg_id,
                        "download_url": url
                    }, f, indent=2)

                return True
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

    print(f"  ✗ All URL patterns failed for ID {gutenberg_id}")
    return False


def main(persona_id: str = "jane-jacobs"):
    """
    Main execution function.

    Args:
        persona_id: Persona identifier (e.g., 'jane-jacobs')
    """
    # Load persona configuration
    print(f"Loading persona: {persona_id}")
    try:
        persona_config = PersonaManager.load_persona(persona_id)
        print(f"✓ Loaded persona: {persona_config['metadata']['name']}\n")
    except Exception as e:
        print(f"✗ Error loading persona config: {e}")
        return

    # Load sources configuration
    sources = PersonaManager.get_sources_config(persona_id)
    if not sources:
        print(f"✗ No sources.json found for persona '{persona_id}'")
        print(f"  Create personas/{persona_id}/sources.json first")
        return

    # Set up output directory
    corpus_paths = PersonaManager.get_corpus_paths(persona_config)
    corpus_raw = corpus_paths['raw']
    corpus_raw.mkdir(parents=True, exist_ok=True)

    print(f"{persona_config['metadata']['name']} Gutenberg Downloader")
    print("=" * 60)
    print(f"Output directory: {corpus_raw}")
    print()

    # Filter to Gutenberg entries only
    all_books = sources.get('priority_1', []) + sources.get('priority_2', [])
    gutenberg_books = [b for b in all_books if b.get('source') == 'gutenberg']

    if not gutenberg_books:
        print("No Gutenberg entries found in sources.json (source: 'gutenberg')")
        return

    print(f"Found {len(gutenberg_books)} Gutenberg entry/entries")

    successful = 0
    failed = 0

    for book in gutenberg_books:
        try:
            if download_gutenberg_book(book, corpus_raw):
                successful += 1
            else:
                failed += 1
        except KeyboardInterrupt:
            print("\n\nDownload interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Gutenberg Download Summary:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(gutenberg_books)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download corpus from Project Gutenberg for historical figure chatbot"
    )
    parser.add_argument(
        "--persona",
        default="jane-jacobs",
        help="Persona ID to download corpus for (default: jane-jacobs)"
    )
    args = parser.parse_args()

    main(persona_id=args.persona)
