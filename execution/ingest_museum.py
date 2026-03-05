#!/usr/bin/env python3
"""
Local ingest script for museum persona corpora.

Chunks cleaned corpus text, generates 384-dim embeddings using
sentence-transformers all-MiniLM-L6-v2 (no API tokens), and stores
vectors in ~/.chroma/museum/ — consistent with the existing Taylor
and Mencken collections.

Prerequisites:
    pip install sentence-transformers

Usage:
    python execution/ingest_museum.py --persona jane-jacobs
    python execution/ingest_museum.py --persona alexander-hamilton
    python execution/ingest_museum.py --persona thomas-jefferson
    python execution/ingest_museum.py --persona carl-jung
    python execution/ingest_museum.py --all
    python execution/ingest_museum.py --all --dry-run
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict

import chromadb
from chromadb.config import Settings

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CHROMA_PATH = Path.home() / ".chroma" / "museum"
EMBED_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE_TOKENS = 500   # target tokens per chunk
BATCH_SIZE = 64           # embedding batch size

SUPPORTED_PERSONAS = [
    "alexander-hamilton",
    "thomas-jefferson",
    "carl-jung",
    "jane-jacobs",
    "hl-mencken",
    "john-taylor-of-caroline",
    "adam-smith",
]

# Files to skip during ingestion (exact filename match within cleaned/ dir)
EXCLUDED_FILES: Dict[str, set] = {
    "thomas-jefferson": {
        # Exact duplicate of The_Writings_of_Thomas_Jefferson_1854.txt
        "The_Writings_of_Thomas_Jefferson__1854_Collection__1854.txt",
    },
}


# ---------------------------------------------------------------------------
# Chunking  (paragraph-aware, mirrors chunker_embedder.py logic)
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int, overlap: int = 50) -> List[str]:
    words = text.split()
    words_per_chunk = int(chunk_size / 1.3)
    words_overlap = int(overlap / 1.3)
    chunks, start = [], 0
    while start < len(words):
        chunk = " ".join(words[start : start + words_per_chunk]).strip()
        if chunk:
            chunks.append(chunk)
        start += words_per_chunk - words_overlap
    return chunks


def chunk_by_paragraphs(text: str, target: int = CHUNK_SIZE_TOKENS) -> List[str]:
    words_per_chunk = int(target / 1.3)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current, current_size = [], [], 0

    for para in paragraphs:
        para_words = len(para.split())
        if para_words > words_per_chunk * 1.5:
            if current:
                chunks.append(" ".join(current))
                current, current_size = [], 0
            chunks.extend(chunk_text(para, target))
        elif current_size + para_words > words_per_chunk:
            if current:
                chunks.append(" ".join(current))
            current, current_size = [para], para_words
        else:
            current.append(para)
            current_size += para_words

    if current:
        chunks.append(" ".join(current))
    return chunks


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def ingest_persona(
    persona_id: str,
    chroma_client,
    embed_model,
    dry_run: bool = False,
) -> int:
    project_root = Path(__file__).parent.parent
    cleaned_dir = project_root / "personas" / persona_id / "corpus" / "cleaned"
    excluded = EXCLUDED_FILES.get(persona_id, set())

    # Load persona config for collection name
    import json
    persona_json = project_root / "personas" / persona_id / "persona.json"
    if not persona_json.exists():
        print(f"  ✗ persona.json not found: {persona_json}")
        return 0
    with open(persona_json) as f:
        config = json.load(f)
    collection_name = config["corpus"]["collection_name"]

    # Gather cleaned text files
    txt_files = sorted(
        f for f in cleaned_dir.glob("*.txt")
        if not f.name.startswith("_") and f.name not in excluded
    )
    if not txt_files:
        print(f"  ✗ No cleaned .txt files found in {cleaned_dir}")
        return 0

    print(f"\n{'='*60}")
    print(f"Persona    : {persona_id}")
    print(f"Collection : {collection_name}")
    print(f"Files      : {len(txt_files)}")
    if excluded:
        print(f"Excluded   : {excluded}")

    # Inventory chunks before touching ChromaDB
    file_chunks: List[Dict] = []
    for txt_file in txt_files:
        text = txt_file.read_text(encoding="utf-8", errors="replace")
        chunks = chunk_by_paragraphs(text)
        # Extract year from filename (last 4-digit sequence)
        import re
        years = re.findall(r"\d{4}", txt_file.stem)
        year = years[-1] if years else "Unknown"
        title = txt_file.stem.replace("_", " ")
        file_chunks.append(
            {
                "filename": txt_file.name,
                "title": title,
                "year": year,
                "chunks": chunks,
            }
        )
        print(f"  {txt_file.name}: {len(chunks)} chunks")

    total_chunks = sum(len(fc["chunks"]) for fc in file_chunks)
    print(f"  Total chunks: {total_chunks}")

    if dry_run:
        print(f"  [DRY RUN] — skipping ChromaDB write")
        return total_chunks

    # Create/replace collection
    try:
        chroma_client.delete_collection(collection_name)
        print(f"  Replaced existing collection '{collection_name}'")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # Embed and upsert in batches
    upserted = 0
    for fc in file_chunks:
        chunks = fc["chunks"]
        ids, texts, metadatas, all_embeddings = [], [], [], []

        # Collect all chunks for this file, embed in batches
        for i, chunk in enumerate(chunks):
            ids.append(f"{fc['filename']}_{i}")
            texts.append(chunk)
            metadatas.append(
                {
                    "persona": persona_id,
                    "source": fc["filename"].replace(".txt", ""),
                    "title": fc["title"],
                    "year": fc["year"],
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
            )

        # Embed in sub-batches
        for batch_start in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[batch_start : batch_start + BATCH_SIZE]
            embeddings = embed_model.encode(
                batch_texts, show_progress_bar=False, convert_to_numpy=True
            )
            all_embeddings.extend(embeddings.tolist())
            print(
                f"    {fc['filename']}: embedded {min(batch_start + BATCH_SIZE, len(texts))}/{len(texts)}",
                end="\r",
            )

        collection.add(
            ids=ids,
            documents=texts,
            embeddings=all_embeddings,
            metadatas=metadatas,
        )
        upserted += len(texts)
        print(f"  ✓ {fc['filename']}: {len(texts)} chunks added")

    print(f"  ✓ Collection '{collection_name}' written — {upserted} total chunks")
    return upserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Ingest museum persona corpora into ~/.chroma/museum/ (384-dim, local)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--persona",
        choices=SUPPORTED_PERSONAS,
        metavar="ID",
        help=f"One of: {', '.join(SUPPORTED_PERSONAS)}",
    )
    group.add_argument("--all", action="store_true", help="Ingest all four personas")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count chunks only — no ChromaDB writes, no embeddings computed",
    )
    args = parser.parse_args()

    personas = SUPPORTED_PERSONAS if args.all else [args.persona]

    # Load embedding model (only if not dry-run)
    embed_model = None
    if not args.dry_run:
        print(f"Loading embedding model: {EMBED_MODEL}")
        try:
            from sentence_transformers import SentenceTransformer
            embed_model = SentenceTransformer(EMBED_MODEL)
            print(f"✓ Model loaded\n")
        except ImportError:
            print("✗ sentence-transformers not installed.")
            print("  Run: pip install sentence-transformers")
            sys.exit(1)

    # Connect to ChromaDB
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(anonymized_telemetry=False),
    )

    print(f"ChromaDB  : {CHROMA_PATH}")
    print(f"Personas  : {personas}")
    if args.dry_run:
        print(f"Mode      : DRY RUN — counting chunks only\n")

    total = 0
    for persona_id in personas:
        total += ingest_persona(persona_id, chroma_client, embed_model, dry_run=args.dry_run)

    print(f"\n{'='*60}")
    verb = "would create" if args.dry_run else "created"
    print(f"Done. Total chunks {verb}: {total}")

    if not args.dry_run:
        print("\nCurrent ~/.chroma/museum/ collections:")
        for col in chroma_client.list_collections():
            c = chroma_client.get_collection(col.name)
            print(f"  {col.name}: {c.count()} chunks")


if __name__ == "__main__":
    main()
