#!/usr/bin/env python3
"""
Corpus Cleaner for Jane Jacobs Chatbot
Extracts and cleans text from PDFs, plain text files, and DOCX files.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

from docx import Document


def clean_text(text: str) -> str:
    """Clean extracted text by removing artifacts and normalizing."""
    # Remove page numbers (common patterns)
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    text = re.sub(r'\n\s*-\s*\d+\s*-\s*\n', '\n', text)

    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r' +', ' ', text)

    # Remove header/footer artifacts (repeated short lines)
    lines = text.split('\n')
    cleaned_lines = []
    prev_short_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip very short lines that appear repeatedly (likely headers/footers)
        if len(stripped) < 40 and stripped:
            if stripped in prev_short_lines:
                continue
            prev_short_lines.append(stripped)
            if len(prev_short_lines) > 10:
                prev_short_lines.pop(0)

        cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)

    # Fix common OCR errors
    text = text.replace('ﬁ', 'fi')
    text = text.replace('ﬂ', 'fl')
    text = text.replace('ﬀ', 'ff')

    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")

    return text.strip()


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from a PDF file."""
    print(f"  Extracting text from PDF...")

    try:
        reader = PdfReader(pdf_path)
        text_parts = []

        total_pages = len(reader.pages)
        print(f"  Processing {total_pages} pages...")

        for i, page in enumerate(reader.pages, 1):
            if i % 10 == 0:
                print(f"    Page {i}/{total_pages}")

            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = '\n\n'.join(text_parts)
        print(f"  ✓ Extracted {len(full_text):,} characters")
        return full_text

    except Exception as e:
        print(f"  ✗ Error extracting PDF: {e}")
        return ""


def extract_docx_text(docx_path: Path) -> str:
    """Extract text from a DOCX file."""
    print(f"  Extracting text from DOCX...")

    try:
        doc = Document(docx_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        full_text = '\n\n'.join(paragraphs)
        print(f"  ✓ Extracted {len(full_text):,} characters")
        return full_text

    except Exception as e:
        print(f"  ✗ Error extracting DOCX: {e}")
        return ""


def extract_txt_text(txt_path: Path) -> str:
    """Read text from a plain text file."""
    print(f"  Reading plain text file...")

    try:
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        print(f"  ✓ Read {len(text):,} characters")
        return text

    except Exception as e:
        print(f"  ✗ Error reading text file: {e}")
        return ""


def process_file(file_path: Path, output_dir: Path) -> Optional[Dict]:
    """Process a single file and save cleaned text."""
    print(f"\n{'='*60}")
    print(f"Processing: {file_path.name}")
    print(f"{'='*60}")

    # Determine file type and extract text
    extension = file_path.suffix.lower()

    if extension == '.pdf':
        raw_text = extract_pdf_text(file_path)
    elif extension == '.docx':
        raw_text = extract_docx_text(file_path)
    elif extension in ['.txt', '.text']:
        raw_text = extract_txt_text(file_path)
    else:
        print(f"  ✗ Unsupported file type: {extension}")
        return None

    if not raw_text:
        print(f"  ✗ No text extracted")
        return None

    # Clean the text
    print(f"  Cleaning text...")
    cleaned_text = clean_text(raw_text)

    if len(cleaned_text) < 100:
        print(f"  ✗ Text too short after cleaning ({len(cleaned_text)} chars)")
        return None

    print(f"  ✓ Cleaned text: {len(cleaned_text):,} characters")

    # Generate output filename
    output_filename = file_path.stem + '.txt'
    output_path = output_dir / output_filename

    # Save cleaned text
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_text)

    print(f"  ✓ Saved to: {output_path}")

    # Load metadata if it exists
    metadata_path = file_path.with_suffix('.json')
    metadata = {}

    if metadata_path.exists():
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            print(f"  ✓ Loaded metadata: {metadata.get('title', 'Unknown')}")
        except Exception as e:
            print(f"  ⚠ Could not load metadata: {e}")

    return {
        'source_file': file_path.name,
        'output_file': output_filename,
        'original_length': len(raw_text),
        'cleaned_length': len(cleaned_text),
        'metadata': metadata
    }


def main():
    """Main execution function."""
    # Set up directories
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    corpus_raw = project_root / "corpus" / "raw"
    corpus_cleaned = project_root / "corpus" / "cleaned"

    corpus_cleaned.mkdir(parents=True, exist_ok=True)

    print("Jane Jacobs Corpus Cleaner")
    print("=" * 60)
    print(f"Input directory:  {corpus_raw}")
    print(f"Output directory: {corpus_cleaned}")
    print()

    # Find all processable files
    supported_extensions = ['.pdf', '.docx', '.txt', '.text']
    files_to_process = []

    for ext in supported_extensions:
        files_to_process.extend(corpus_raw.glob(f'*{ext}'))

    if not files_to_process:
        print("✗ No files found to process")
        print(f"  Looking for: {', '.join(supported_extensions)}")
        return

    print(f"Found {len(files_to_process)} file(s) to process\n")

    # Process each file
    results = []
    successful = 0
    failed = 0

    for file_path in sorted(files_to_process):
        try:
            result = process_file(file_path, corpus_cleaned)
            if result:
                results.append(result)
                successful += 1
            else:
                failed += 1
        except KeyboardInterrupt:
            print("\n\nProcessing interrupted by user")
            break
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Processing Summary:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(files_to_process)}")
    print(f"{'='*60}")

    # Save processing report
    if results:
        report_path = corpus_cleaned / "_cleaning_report.json"
        with open(report_path, 'w') as f:
            json.dump({
                'processed_files': results,
                'total_files': len(files_to_process),
                'successful': successful,
                'failed': failed
            }, f, indent=2)
        print(f"\n✓ Report saved to: {report_path}")

        # Print statistics
        total_chars = sum(r['cleaned_length'] for r in results)
        print(f"\nTotal cleaned text: {total_chars:,} characters")
        print(f"Average per file: {total_chars // len(results):,} characters")


if __name__ == "__main__":
    main()
