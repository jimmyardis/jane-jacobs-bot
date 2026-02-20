#!/usr/bin/env python3
"""
Startup script for Railway deployment
Checks if ChromaDB exists, builds it if needed, then starts API server
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def check_chromadb():
    """Check if ChromaDB database exists"""
    chroma_db_path = Path(__file__).parent.parent / "chroma_db" / "chroma.sqlite3"
    return chroma_db_path.exists()

def build_chromadb():
    """Build ChromaDB from cleaned corpus"""
    print("=" * 60)
    print("ChromaDB not found - building from corpus...")
    print("This will take a few minutes on first deployment")
    print("=" * 60)

    # Import and run chunker_embedder
    import chunker_embedder
    chunker_embedder.main()

    print("=" * 60)
    print("ChromaDB build complete!")
    print("=" * 60)

def start_server():
    """Start the API server"""
    import api_server
    # Server will be started by uvicorn in railway.json

if __name__ == "__main__":
    # Check if we need to build ChromaDB
    if not check_chromadb():
        print("First-time setup: Building ChromaDB...")
        try:
            build_chromadb()
        except Exception as e:
            print(f"Error building ChromaDB: {e}")
            print("Continuing anyway - server may fail if ChromaDB is missing")
    else:
        print("ChromaDB found - skipping build")

    print("Starting API server...")
