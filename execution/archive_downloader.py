#!/usr/bin/env python3
"""
Archive.org Corpus Downloader for Historical Figure Chatbot Template
Downloads books from Internet Archive based on persona sources.json.
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Optional

from persona_manager import PersonaManager

# Internet Archive search and download endpoints
SEARCH_URL = "https://archive.org/advancedsearch.php"
METADATA_URL = "https://archive.org/metadata/"
DOWNLOAD_URL = "https://archive.org/download/"

# Priority 1: Core Books
PRIORITY_1 = [
    {
        "title": "The Death and Life of Great American Cities",
        "author": "Jane Jacobs",
        "year": 1961,
        "search_terms": "death and life great american cities jacobs"
    },
    {
        "title": "The Economy of Cities",
        "author": "Jane Jacobs",
        "year": 1969,
        "search_terms": "economy of cities jane jacobs"
    },
    {
        "title": "Cities and the Wealth of Nations",
        "author": "Jane Jacobs",
        "year": 1984,
        "search_terms": "cities wealth of nations jane jacobs"
    },
    {
        "title": "Systems of Survival",
        "author": "Jane Jacobs",
        "year": 1992,
        "search_terms": "systems of survival jane jacobs"
    },
    {
        "title": "The Nature of Economies",
        "author": "Jane Jacobs",
        "year": 2000,
        "search_terms": "nature of economies jane jacobs"
    },
    {
        "title": "Dark Age Ahead",
        "author": "Jane Jacobs",
        "year": 2004,
        "search_terms": "dark age ahead jane jacobs"
    }
]

# Priority 2: Compiled Works
PRIORITY_2 = [
    {
        "title": "Vital Little Plans: The Short Works of Jane Jacobs",
        "author": "Jane Jacobs",
        "year": 2016,
        "search_terms": "vital little plans jane jacobs"
    }
]


def search_archive(search_terms: str, limit: int = 10) -> List[Dict]:
    """Search Internet Archive for items matching search terms."""
    params = {
        "q": search_terms,
        "output": "json",
        "rows": limit,
        "fl[]": ["identifier", "title", "creator", "year", "mediatype"]
    }

    try:
        response = requests.get(SEARCH_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("response", {}).get("docs", [])
    except Exception as e:
        print(f"Error searching archive: {e}")
        return []


def get_item_metadata(identifier: str) -> Optional[Dict]:
    """Get detailed metadata for an Archive.org item."""
    try:
        response = requests.get(f"{METADATA_URL}{identifier}", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching metadata for {identifier}: {e}")
        return None


def find_best_text_file(metadata: Dict) -> Optional[str]:
    """Find the best text file format from item metadata."""
    files = metadata.get("files", [])

    # Preference order: plain text > PDF > DjVu
    for fmt in ["txt", "pdf", "djvu"]:
        for file in files:
            name = file.get("name", "")
            if name.endswith(f".{fmt}") and not name.endswith("_djvu.txt"):
                return name

    return None


def download_file(identifier: str, filename: str, output_path: Path) -> bool:
    """Download a file from Archive.org."""
    url = f"{DOWNLOAD_URL}{identifier}/{filename}"

    try:
        print(f"  Downloading: {url}")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"  ✓ Saved to: {output_path}")
        return True
    except Exception as e:
        print(f"  ✗ Error downloading: {e}")
        return False


def download_book(book_info: Dict, output_dir: Path) -> bool:
    """Search for and download a book from Archive.org."""
    print(f"\n{'='*60}")
    print(f"Searching for: {book_info['title']} ({book_info['year']})")
    print(f"{'='*60}")

    # Search for the book
    results = search_archive(book_info["search_terms"])

    if not results:
        print("✗ No results found")
        return False

    print(f"Found {len(results)} potential matches:")
    for i, result in enumerate(results[:5], 1):
        print(f"  {i}. {result.get('title', 'Unknown')} ({result.get('year', 'N/A')})")
        print(f"     ID: {result.get('identifier', 'N/A')}")

    # Try the top result
    top_result = results[0]
    identifier = top_result.get("identifier")

    if not identifier:
        print("✗ No valid identifier found")
        return False

    print(f"\nUsing: {identifier}")

    # Get metadata to find downloadable files
    metadata = get_item_metadata(identifier)
    if not metadata:
        print("✗ Could not fetch metadata")
        return False

    # Find best text file
    filename = find_best_text_file(metadata)
    if not filename:
        print("✗ No text file found (txt, pdf, or djvu)")
        return False

    # Determine output filename
    safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_'
                        for c in book_info['title'])
    safe_title = safe_title.replace(' ', '_')
    extension = filename.split('.')[-1]
    output_filename = f"{safe_title}_{book_info['year']}.{extension}"
    output_path = output_dir / output_filename

    # Skip if already downloaded
    if output_path.exists():
        print(f"✓ Already exists: {output_path}")
        return True

    # Download the file
    success = download_file(identifier, filename, output_path)

    if success:
        # Save metadata for reference
        metadata_path = output_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump({
                "title": book_info["title"],
                "author": book_info["author"],
                "year": book_info["year"],
                "archive_identifier": identifier,
                "archive_filename": filename,
                "download_url": f"{DOWNLOAD_URL}{identifier}/{filename}"
            }, f, indent=2)

    return success


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

    # Set up output directory from persona config
    corpus_paths = PersonaManager.get_corpus_paths(persona_config)
    corpus_raw = corpus_paths['raw']
    corpus_raw.mkdir(parents=True, exist_ok=True)

    print(f"{persona_config['metadata']['name']} Corpus Downloader")
    print("=" * 60)
    print(f"Output directory: {corpus_raw}")
    print()

    # Load books from sources.json
    all_books = sources.get('priority_1', []) + sources.get('priority_2', [])
    successful = 0
    failed = 0

    for book in all_books:
        try:
            if download_book(book, corpus_raw):
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
    print(f"Download Summary:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(all_books)}")
    print(f"{'='*60}")

    if failed > 0:
        print("\nNote: Some downloads failed. You may need to:")
        print("  1. Manually search archive.org for the missing books")
        print("  2. Check if they're available under different titles")
        print("  3. Download PDFs manually to corpus/raw/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download corpus from Archive.org for historical figure chatbot"
    )
    parser.add_argument(
        "--persona",
        default="jane-jacobs",
        help="Persona ID to download corpus for (default: jane-jacobs)"
    )
    args = parser.parse_args()

    main(persona_id=args.persona)
