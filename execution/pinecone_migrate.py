#!/usr/bin/env python3
"""
Migrate ChromaDB museum collections to a standard Pinecone index.

Extracts raw 384-dim vectors directly from ChromaDB — no re-embedding.
Upserts each vector with persona_id, text, and source metadata so the
server can filter by persona at query time.

Prerequisites:
  - Pinecone index created at 384 dimensions, cosine metric (standard, no inference)
  - PINECONE_API_KEY and PINECONE_INDEX set in .env
  - pip install pinecone

Usage:
    python execution/pinecone_migrate.py                        # migrate all collections
    python execution/pinecone_migrate.py --dry-run              # count only, no writes
    python execution/pinecone_migrate.py --collection hl_mencken_corpus

Currently available in ~/.chroma/museum/:
    john_taylor_corpus   5,656 chunks  persona_id: john-taylor-of-caroline
    hl_mencken_corpus    7,465 chunks  persona_id: hl-mencken

Run this script again after ingesting additional personas to migrate them.
"""

import os
import sys
import time
import argparse
from pathlib import Path

from dotenv import load_dotenv
import chromadb
from pinecone import Pinecone

load_dotenv()

CHROMA_PATH = Path.home() / ".chroma" / "museum"
BATCH_SIZE = 100  # Pinecone standard upsert batch size


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def infer_persona_id(collection_name: str, metadata: dict) -> str:
    """
    Return a hyphen-format persona_id.

    Taylor chunks store persona as 'john_taylor_of_caroline' (underscores).
    Mencken chunks have no persona field; infer from the collection name.
    """
    raw = metadata.get("persona", "")
    if raw:
        return raw.replace("_", "-")

    # Strip known suffixes, then normalise underscores → hyphens
    name = collection_name
    for suffix in ("_corpus", "_discourse", "_chunks"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name.replace("_", "-")


def collection_type_from_name(collection_name: str) -> str:
    return "discourse" if "_discourse" in collection_name else "corpus"


def to_float_list(vec) -> list:
    """Convert a ChromaDB embedding (numpy array or list) to a plain Python float list."""
    try:
        return vec.tolist()          # numpy array
    except AttributeError:
        return [float(v) for v in vec]


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

def migrate_collection(
    chroma_collection,
    pinecone_index,
    dry_run: bool = False,
) -> int:
    col_name = chroma_collection.name
    col_type = collection_type_from_name(col_name)
    total = chroma_collection.count()

    print(f"\n{'='*60}")
    print(f"Collection : {col_name}")
    print(f"Chunks     : {total}")
    print(f"Type       : {col_type}")

    if total == 0:
        print("  (empty — skipping)")
        return 0

    upserted = 0
    skipped = 0
    offset = 0
    page_size = 200  # how many to pull from ChromaDB at once

    while offset < total:
        page = chroma_collection.get(
            limit=page_size,
            offset=offset,
            include=["embeddings", "documents", "metadatas"],
        )

        embeddings = page["embeddings"]
        docs = page["documents"]
        metas = page["metadatas"]
        ids = page["ids"]

        if not docs:
            break

        # Build Pinecone upsert vectors in sub-batches of BATCH_SIZE
        batch = []
        for orig_id, vec, doc, meta in zip(ids, embeddings, docs, metas):
            if not doc or not doc.strip():
                skipped += 1
                continue

            persona_id = infer_persona_id(col_name, meta)

            # Pinecone metadata limit: 40 KB per vector.
            # Cap text at 38,000 chars to leave room for other fields + JSON overhead.
            safe_text = doc[:38000] if len(doc) > 38000 else doc

            batch.append(
                {
                    "id": f"{col_name}__{orig_id}",
                    "values": to_float_list(vec),
                    "metadata": {
                        "persona_id": persona_id,
                        "collection_type": col_type,
                        "text": safe_text,
                        "title": meta.get("title", ""),
                        "source": meta.get("source", ""),
                        "chunk_index": int(meta.get("chunk_index", 0)),
                    },
                }
            )

            if len(batch) == BATCH_SIZE:
                if not dry_run:
                    pinecone_index.upsert(vectors=batch, namespace="")
                    time.sleep(0.05)
                upserted += len(batch)
                print(f"  {'[dry] ' if dry_run else ''}upserted {upserted}/{total}", end="\r")
                batch = []

        # Flush remainder from this page
        if batch:
            if not dry_run:
                pinecone_index.upsert(vectors=batch, namespace="")
                time.sleep(0.05)
            upserted += len(batch)

        offset += page_size

    verb = "[DRY RUN] would upsert" if dry_run else "Upserted"
    print(f"\n  {verb} {upserted} vectors  (skipped {skipped} empty chunks)")
    return upserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Migrate ChromaDB museum collections → Pinecone (384-dim, cosine)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts without writing to Pinecone",
    )
    parser.add_argument(
        "--collection",
        metavar="NAME",
        help="Migrate only this collection (e.g. hl_mencken_corpus)",
    )
    args = parser.parse_args()

    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX", "museum-corpus")

    if not api_key:
        print("✗  PINECONE_API_KEY not set in .env or environment")
        sys.exit(1)

    print(f"Pinecone index : {index_name}")
    print(f"ChromaDB source: {CHROMA_PATH}")
    if args.dry_run:
        print("Mode           : DRY RUN — nothing will be written\n")
    else:
        print()

    # Connect to Pinecone — prefer direct host URL if available
    pc = Pinecone(api_key=api_key)
    pinecone_host = os.getenv("PINECONE_HOST")
    if pinecone_host:
        pinecone_index = pc.Index(host=pinecone_host)
        print(f"Pinecone host   : {pinecone_host}")
    else:
        pinecone_index = pc.Index(index_name)

    # Verify index dimensions match
    stats = pinecone_index.describe_index_stats()
    print(f"Pinecone index stats: {stats.total_vector_count} vectors currently stored")

    # Connect to ChromaDB
    if not CHROMA_PATH.exists():
        print(f"✗  ChromaDB path not found: {CHROMA_PATH}")
        sys.exit(1)

    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    all_collections = chroma_client.list_collections()

    if args.collection:
        matching = [c for c in all_collections if c.name == args.collection]
        if not matching:
            print(f"✗  Collection '{args.collection}' not found.")
            print(f"   Available: {[c.name for c in all_collections]}")
            sys.exit(1)
        collections = matching
    else:
        collections = all_collections

    print(f"Collections to migrate ({len(collections)}):")
    for col in collections:
        c = chroma_client.get_collection(col.name)
        sample = c.get(limit=1, include=["metadatas"])
        pid = infer_persona_id(col.name, sample["metadatas"][0]) if sample["metadatas"] else "?"
        print(f"  {col.name:45s} persona_id={pid}  ({c.count()} chunks)")

    print()
    if not args.dry_run:
        try:
            confirm = input("Proceed with migration? [y/N] ").strip().lower()
        except EOFError:
            confirm = "n"
        if confirm != "y":
            print("Aborted.")
            sys.exit(0)

    total_upserted = 0
    for col in collections:
        c = chroma_client.get_collection(col.name)
        total_upserted += migrate_collection(c, pinecone_index, dry_run=args.dry_run)

    print(f"\n{'='*60}")
    action = "would be upserted" if args.dry_run else "upserted"
    print(f"Done. Total vectors {action}: {total_upserted}")
    if not args.dry_run:
        final_stats = pinecone_index.describe_index_stats()
        print(f"Pinecone index now contains: {final_stats.total_vector_count} vectors")


if __name__ == "__main__":
    main()
