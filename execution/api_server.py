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
from openai import OpenAI

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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not ANTHROPIC_API_KEY:
    print("✗ Error: ANTHROPIC_API_KEY not found in environment")
    sys.exit(1)

if not OPENAI_API_KEY:
    print("✗ Error: OPENAI_API_KEY not found in environment")
    sys.exit(1)

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize ChromaDB
script_dir = Path(__file__).parent
project_root = script_dir.parent
chroma_db_dir = project_root / "chroma_db"

if not chroma_db_dir.exists():
    print(f"✗ Error: ChromaDB directory not found: {chroma_db_dir}")
    print(f"  Run chunker_embedder.py first")
    sys.exit(1)

chroma_client = chromadb.PersistentClient(
    path=str(chroma_db_dir),
    settings=Settings(anonymized_telemetry=False)
)

try:
    collection_name = PersonaManager.get_collection_name(persona_config)
    collection = chroma_client.get_collection(collection_name)
    print(f"✓ Loaded ChromaDB collection '{collection_name}' with {collection.count()} chunks")
except Exception as e:
    print(f"✗ Error loading ChromaDB collection: {e}")
    sys.exit(1)

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
    """Retrieve relevant chunks from ChromaDB."""
    # Generate query embedding using OpenAI
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    query_embedding = response.data[0].embedding

    # Query ChromaDB with the embedding
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    chunks = []
    if results and results['documents']:
        for i in range(len(results['documents'][0])):
            chunks.append({
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i]
            })

    return chunks


def build_context(chunks: List[Dict]) -> str:
    """Build context string from retrieved chunks."""
    if not chunks:
        return ""

    context_parts = ["Here are relevant excerpts from your writings:\n"]

    for i, chunk in enumerate(chunks, 1):
        metadata = chunk['metadata']
        title = metadata.get('title', 'Unknown')
        year = metadata.get('year', 'Unknown')

        context_parts.append(f"\n--- Excerpt {i} ({title}, {year}) ---")
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
        max_tokens=1024,
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
        "service": "Jane Jacobs Chatbot API",
        "corpus_chunks": collection.count()
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
    return {
        "status": "healthy",
        "chromadb": {
            "connected": True,
            "chunks": collection.count()
        },
        "active_conversations": len(conversations)
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

    print(f"\nStarting Jane Jacobs Chatbot API server...")
    print(f"  Corpus chunks: {collection.count()}")
    print(f"  Server: http://{host}:{port}")
    print(f"  Docs: http://{host}:{port}/docs")
    print()

    uvicorn.run(app, host=host, port=port)
