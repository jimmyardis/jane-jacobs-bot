#!/usr/bin/env python3
"""
Chunker & Embedder for Historical Figure Chatbot Template
Chunks cleaned corpus text, generates embeddings, and loads into ChromaDB.
"""

import os
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

import chromadb
from chromadb.config import Settings
from openai import OpenAI

from persona_manager import PersonaManager


def load_cleaned_texts(cleaned_dir: Path) -> List[Dict]:
    """Load all cleaned text files with their metadata."""
    texts = []

    for txt_file in sorted(cleaned_dir.glob('*.txt')):
        # Skip report files
        if txt_file.name.startswith('_'):
            continue

        print(f"Loading: {txt_file.name}")

        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try to load associated metadata
        json_file = txt_file.with_suffix('.json')
        metadata = {}

        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    metadata = json.load(f)
            except:
                pass

        # Also check raw directory for metadata
        if not metadata:
            raw_json = txt_file.parent.parent / "raw" / txt_file.with_suffix('.json').name
            if raw_json.exists():
                try:
                    with open(raw_json, 'r') as f:
                        metadata = json.load(f)
                except:
                    pass

        texts.append({
            'filename': txt_file.name,
            'content': content,
            'metadata': metadata
        })

    return texts


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Chunk text into overlapping segments.
    Uses approximate token count (words * 1.3) for estimation.
    """
    words = text.split()
    chunks = []

    # Approximate tokens to words ratio
    words_per_chunk = int(chunk_size / 1.3)
    words_overlap = int(overlap / 1.3)

    start = 0
    while start < len(words):
        end = start + words_per_chunk
        chunk_words = words[start:end]
        chunk_text = ' '.join(chunk_words).strip()

        if chunk_text:
            chunks.append(chunk_text)

        start += (words_per_chunk - words_overlap)

    return chunks


def chunk_by_paragraphs(text: str, target_chunk_size: int = 500) -> List[str]:
    """
    Chunk text by paragraphs, trying to preserve paragraph integrity.
    """
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = []
    current_size = 0

    words_per_chunk = int(target_chunk_size / 1.3)

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_words = len(para.split())

        # If single paragraph is too large, split it
        if para_words > words_per_chunk * 1.5:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_size = 0

            # Split large paragraph
            para_chunks = chunk_text(para, chunk_size=target_chunk_size, overlap=50)
            chunks.extend(para_chunks)

        # If adding this paragraph would exceed chunk size
        elif current_size + para_words > words_per_chunk:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            current_chunk = [para]
            current_size = para_words

        # Add to current chunk
        else:
            current_chunk.append(para)
            current_size += para_words

    # Add final chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks


def create_embeddings_batch(texts: List[str], client: OpenAI, model: str = "text-embedding-3-small") -> List[List[float]]:
    """Generate embeddings for a batch of texts using OpenAI API."""
    try:
        response = client.embeddings.create(
            model=model,
            input=texts
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        print(f"  ✗ Error generating embeddings: {e}")
        return []


def main(persona_id: str = "jane-jacobs"):
    """
    Main execution function.

    Args:
        persona_id: Persona identifier (e.g., 'jane-jacobs')
    """
    # Load environment variables
    load_dotenv()

    # Load persona configuration
    print(f"Loading persona: {persona_id}")
    try:
        persona_config = PersonaManager.load_persona(persona_id)
        print(f"✓ Loaded persona: {persona_config['metadata']['name']}\n")
    except Exception as e:
        print(f"✗ Error loading persona config: {e}")
        sys.exit(1)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("✗ Error: OPENAI_API_KEY not found in environment")
        print("  Please set it in your .env file")
        sys.exit(1)

    # Initialize OpenAI client
    openai_client = OpenAI(api_key=openai_api_key)

    # Set up directories from persona config
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    corpus_paths = PersonaManager.get_corpus_paths(persona_config)
    corpus_cleaned = corpus_paths['cleaned']
    chroma_db_dir = project_root / "chroma_db"

    chroma_db_dir.mkdir(parents=True, exist_ok=True)

    print(f"{persona_config['metadata']['name']} Chunker & Embedder")
    print("=" * 60)
    print(f"Source directory: {corpus_cleaned}")
    print(f"ChromaDB directory: {chroma_db_dir}")
    print()

    # Load cleaned texts
    print("Loading cleaned texts...")
    texts = load_cleaned_texts(corpus_cleaned)

    if not texts:
        print("✗ No cleaned texts found")
        print(f"  Run corpus_cleaner.py --persona {persona_id} first")
        sys.exit(1)

    print(f"✓ Loaded {len(texts)} text file(s)\n")

    # Initialize ChromaDB
    print("Initializing ChromaDB...")
    chroma_client = chromadb.PersistentClient(
        path=str(chroma_db_dir),
        settings=Settings(anonymized_telemetry=False)
    )

    # Get or create collection
    collection_name = PersonaManager.get_collection_name(persona_config)

    try:
        # Try to delete existing collection
        chroma_client.delete_collection(collection_name)
        print(f"  ✓ Deleted existing collection")
    except:
        pass

    collection = chroma_client.create_collection(
        name=collection_name,
        metadata={"description": f"{persona_config['metadata']['name']} writings corpus"}
    )
    print(f"✓ Created collection: {collection_name}\n")

    # Process each text file
    total_chunks = 0
    batch_size = 100  # Process embeddings in batches

    for text_info in texts:
        filename = text_info['filename']
        content = text_info['content']
        metadata = text_info['metadata']

        print(f"{'='*60}")
        print(f"Processing: {filename}")
        print(f"{'='*60}")

        # Extract metadata
        title = metadata.get('title', filename.replace('.txt', ''))
        author = metadata.get('author', persona_config['corpus']['author'])
        year = metadata.get('year', 'Unknown')

        print(f"  Title: {title}")
        print(f"  Length: {len(content):,} characters")

        # Chunk the text
        print(f"  Chunking text (preserving paragraphs)...")
        chunks = chunk_by_paragraphs(content, target_chunk_size=500)
        print(f"  ✓ Created {len(chunks)} chunks")

        # Process chunks in batches
        print(f"  Generating embeddings...")

        for batch_start in range(0, len(chunks), batch_size):
            batch_end = min(batch_start + batch_size, len(chunks))
            batch_chunks = chunks[batch_start:batch_end]

            print(f"    Batch {batch_start//batch_size + 1}/{(len(chunks)-1)//batch_size + 1} " +
                  f"({batch_start+1}-{batch_end}/{len(chunks)})")

            # Generate embeddings
            embeddings = create_embeddings_batch(batch_chunks, openai_client)

            if not embeddings:
                print(f"    ✗ Failed to generate embeddings for batch")
                continue

            # Prepare documents for ChromaDB
            ids = [f"{filename}_{batch_start + i}" for i in range(len(batch_chunks))]
            metadatas = [
                {
                    'source': filename,
                    'title': title,
                    'author': author,
                    'year': str(year),
                    'chunk_index': batch_start + i,
                    'total_chunks': len(chunks)
                }
                for i in range(len(batch_chunks))
            ]

            # Add to ChromaDB
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=batch_chunks,
                metadatas=metadatas
            )

            total_chunks += len(batch_chunks)

        print(f"  ✓ Added {len(chunks)} chunks to database\n")

    # Summary
    print(f"{'='*60}")
    print(f"Embedding Summary:")
    print(f"  Files processed: {len(texts)}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Embeddings stored in: {chroma_db_dir}")
    print(f"{'='*60}")

    # Test query
    print(f"\nTesting database with sample query...")
    try:
        # Generate query embedding with OpenAI (matching the collection's embedding model)
        test_query = "What makes a city safe?"
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=test_query
        )
        query_embedding = response.data[0].embedding

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )
    except Exception as e:
        print(f"⚠ Test query failed: {e}")
        results = None

    if results and results['documents'] and len(results['documents'][0]) > 0:
        print(f"✓ Database working - found {len(results['documents'][0])} relevant chunks")
        print(f"\nTop result preview:")
        print(f"  Source: {results['metadatas'][0][0].get('title', 'Unknown')}")
        print(f"  Text: {results['documents'][0][0][:200]}...")
    else:
        print(f"⚠ Warning: Test query returned no results")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Chunk and embed corpus for historical figure chatbot"
    )
    parser.add_argument(
        "--persona",
        default="jane-jacobs",
        help="Persona ID to process (default: jane-jacobs)"
    )
    args = parser.parse_args()

    main(persona_id=args.persona)
