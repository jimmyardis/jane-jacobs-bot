#!/usr/bin/env python3
"""
FastAPI Server for Historical Figure Chatbot Template
RAG-powered API with Claude Sonnet for persona responses.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings
from anthropic import Anthropic
from sentence_transformers import SentenceTransformer

from persona_manager import PersonaManager


# Load environment variables
load_dotenv()

# Load persona configuration
PERSONA_ID = os.getenv("PERSONA_ID", "jane-jacobs")
print(f"Loading persona: {PERSONA_ID}")
try:
    persona_config = PersonaManager.load_persona(PERSONA_ID)
    print(f"✓ Loaded persona: {persona_config['metadata']['name']}")
except Exception as e:
    print(f"✗ Error loading persona config: {e}")
    sys.exit(1)

# Initialize clients
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_HOST = os.getenv("PINECONE_HOST")
USE_PINECONE = bool(PINECONE_API_KEY)

if not ANTHROPIC_API_KEY:
    print("✗ Error: ANTHROPIC_API_KEY not found in environment")
    sys.exit(1)

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Shared 384-dim embedding model — used for Pinecone query vectors and ChromaDB fallback
print("Loading embedding model: all-MiniLM-L6-v2")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
print("✓ Embedding model loaded")

# Vector store: Pinecone when PINECONE_API_KEY is set, else ChromaDB at ~/.chroma/museum/
pinecone_index = None
collection = None
discourse_collection = None

if USE_PINECONE:
    from pinecone import Pinecone as _PineconeClient
    _pc = _PineconeClient(api_key=PINECONE_API_KEY)
    if PINECONE_HOST:
        pinecone_index = _pc.Index(host=PINECONE_HOST)
    else:
        pinecone_index = _pc.Index(os.getenv("PINECONE_INDEX", "museum-corpus"))
    print(f"✓ Connected to Pinecone (persona filter: {PERSONA_ID})")
else:
    print("PINECONE_API_KEY not set — using ChromaDB fallback")
    _chroma_path = Path.home() / ".chroma" / "museum"
    _chroma_client = chromadb.PersistentClient(
        path=str(_chroma_path),
        settings=Settings(anonymized_telemetry=False),
    )
    try:
        _col_name = PersonaManager.get_collection_name(persona_config)
        collection = _chroma_client.get_collection(_col_name)
        print(f"✓ ChromaDB collection '{_col_name}' ({collection.count()} chunks)")
    except Exception as e:
        print(f"✗ Error loading ChromaDB collection: {e}")
        sys.exit(1)
    try:
        _disc_name = PersonaManager.get_discourse_collection_name(persona_config)
        discourse_collection = _chroma_client.get_collection(_disc_name)
        print(f"✓ Discourse collection '{_disc_name}' loaded")
    except Exception:
        print("  No discourse collection found (optional)")

# Initialize FastAPI app
app = FastAPI(
    title=f"{persona_config['metadata']['name']} Chatbot API",
    description=f"RAG-powered chatbot embodying {persona_config['metadata']['name']}",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conversation history storage (in-memory, replace with Redis/DB for production)
conversations: Dict[str, List[Dict]] = {}

# Build system prompt from persona configuration
SYSTEM_PROMPT = PersonaManager.build_system_prompt(persona_config)

# Inject characterological notes if available
context_notes = PersonaManager.load_context_notes(PERSONA_ID)
if context_notes:
    SYSTEM_PROMPT += f"\n\n## Characterological Notes\n{context_notes}"
    print(f"✓ Characterological notes injected into system prompt")
else:
    print(f"  No context_notes.md found (optional — run context_synthesizer.py to generate)")

print(f"✓ System prompt built for {persona_config['metadata']['name']}")


# Request/Response models
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[Dict[str, str]]


# Helper functions
def retrieve_relevant_chunks(query: str, n_results: int = 5) -> List[Dict]:
    """Retrieve relevant chunks using Pinecone (primary) or ChromaDB (fallback)."""
    query_vector = embed_model.encode(query, convert_to_numpy=True).tolist()
    chunks = []

    if USE_PINECONE:
        results = pinecone_index.query(
            vector=query_vector,
            top_k=n_results,
            filter={"persona_id": {"$eq": PERSONA_ID}},
            include_metadata=True,
            namespace="",
        )
        for match in results.matches:
            m = match.metadata or {}
            chunks.append({
                "text": m.get("text", ""),
                "metadata": {
                    "title": m.get("title", ""),
                    "source": m.get("source", ""),
                    "year": m.get("year", ""),
                },
                "knowledge_type": "own words",
            })
        return chunks

    # ChromaDB fallback
    corpus_results = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results,
    )
    if corpus_results and corpus_results["documents"]:
        for i in range(len(corpus_results["documents"][0])):
            chunks.append({
                "text": corpus_results["documents"][0][i],
                "metadata": corpus_results["metadatas"][0][i],
                "knowledge_type": "own words",
            })

    if discourse_collection:
        disc_results = discourse_collection.query(
            query_embeddings=[query_vector],
            n_results=3,
        )
        if disc_results and disc_results["documents"]:
            for i in range(len(disc_results["documents"][0])):
                chunks.append({
                    "text": disc_results["documents"][0][i],
                    "metadata": disc_results["metadatas"][0][i],
                    "knowledge_type": "critical discourse",
                })

    return chunks


def build_context(chunks: List[Dict]) -> str:
    """Build context string from retrieved chunks, labelled by knowledge type."""
    if not chunks:
        return ""

    own_words = [c for c in chunks if c.get('knowledge_type') == 'own words']
    discourse = [c for c in chunks if c.get('knowledge_type') == 'critical discourse']

    context_parts = []

    if own_words:
        context_parts.append("Here are relevant excerpts from your own writings:\n")
        for i, chunk in enumerate(own_words, 1):
            metadata = chunk['metadata']
            title = metadata.get('title', 'Unknown')
            year = metadata.get('year', 'Unknown')
            context_parts.append(f"\n--- Excerpt {i} ({title}, {year}) ---")
            context_parts.append(chunk['text'])

    if discourse:
        context_parts.append("\n\nHere are relevant excerpts from critical discourse about your ideas:\n")
        for i, chunk in enumerate(discourse, 1):
            metadata = chunk['metadata']
            title = metadata.get('title', 'Unknown')
            year = metadata.get('year', 'Unknown')
            context_parts.append(f"\n--- Discourse {i} ({title}, {year}) ---")
            context_parts.append(chunk['text'])

    return '\n'.join(context_parts)


def generate_response(user_message: str, conversation_history: List[Dict], context: str) -> str:
    """Generate response using Claude with RAG context."""

    # Build messages for Claude
    messages = []

    # Add conversation history (last 10 exchanges)
    for msg in conversation_history[-20:]:  # Last 10 exchanges = 20 messages
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Add current user message with context
    user_content = f"{context}\n\n---\n\nUser question: {user_message}"
    messages.append({
        "role": "user",
        "content": user_content
    })

    # Call Claude API
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=messages
    )

    return response.content[0].text


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": f"{persona_config['metadata']['name']} Chatbot API",
        "vector_store": "pinecone" if USE_PINECONE else "chromadb",
        "persona": PERSONA_ID,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint."""

    # Get or create conversation
    conversation_id = request.conversation_id or f"conv_{os.urandom(8).hex()}"

    if conversation_id not in conversations:
        conversations[conversation_id] = []

    conversation_history = conversations[conversation_id]

    try:
        # Retrieve relevant context from corpus
        chunks = retrieve_relevant_chunks(request.message, n_results=5)
        context = build_context(chunks)

        # Generate response
        response_text = generate_response(
            request.message,
            conversation_history,
            context
        )

        # Update conversation history
        conversation_history.append({
            "role": "user",
            "content": request.message
        })
        conversation_history.append({
            "role": "assistant",
            "content": response_text
        })

        # Prepare sources for response
        sources = []
        for chunk in chunks[:3]:  # Top 3 sources
            metadata = chunk['metadata']
            sources.append({
                "title": metadata.get('title', 'Unknown'),
                "year": metadata.get('year', 'Unknown'),
                "knowledge_type": chunk.get('knowledge_type', 'own words'),
                "preview": chunk['text'][:150] + "..."
            })

        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            sources=sources
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear a conversation history."""
    if conversation_id in conversations:
        del conversations[conversation_id]
        return {"status": "ok", "message": "Conversation cleared"}
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")


@app.get("/health")
async def health():
    """Detailed health check."""
    store_info = {"type": "pinecone"} if USE_PINECONE else {
        "type": "chromadb",
        "chunks": collection.count() if collection else 0,
    }
    return {
        "status": "healthy",
        "vector_store": store_info,
        "persona": PERSONA_ID,
        "active_conversations": len(conversations),
    }


@app.get("/persona/{persona_id}/config")
async def get_persona_config(persona_id: str):
    """
    Return widget-safe persona configuration.
    This endpoint provides the UI strings, theme colors, and conversation starters
    needed for the widget to display correctly.
    """
    try:
        config = PersonaManager.load_persona(persona_id)
        # Return only widget-relevant fields (no system prompt or sensitive data)
        return {
            "id": config['id'],
            "metadata": config['metadata'],
            "widget": config['widget']
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Persona not found: {persona_id}")


@app.get("/personas")
async def list_personas():
    """List all available personas."""
    return {
        "personas": PersonaManager.list_available_personas()
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    print(f"\nStarting {persona_config['metadata']['name']} Chatbot API server...")
    print(f"  Vector store: {'Pinecone' if USE_PINECONE else 'ChromaDB'}")
    print(f"  Server: http://{host}:{port}")
    print(f"  Docs: http://{host}:{port}/docs")
    print()

    uvicorn.run(app, host=host, port=port)
