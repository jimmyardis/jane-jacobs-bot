# Jane Jacobs Chatbot

A RAG-powered persona chatbot embodying Jane Jacobs (1916–2006), built as if she is alive in 2026 at age 109.

## Setup

1. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn chromadb openai anthropic internetarchive requests beautifulsoup4 pypdf
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Download corpus:**
   ```bash
   python execution/archive_downloader.py
   ```

4. **Process corpus:**
   ```bash
   python execution/corpus_cleaner.py
   python execution/chunker_embedder.py
   ```

5. **Run server:**
   ```bash
   python execution/api_server.py
   ```

## Tech Stack

- **Backend:** Python / FastAPI
- **Vector Database:** ChromaDB
- **Embeddings:** OpenAI text-embedding-3-small
- **LLM:** Claude Sonnet 4.6 (Anthropic API)
- **Hosting:** Railway

## Project Structure

```
jane-jacobs-bot/
├── directives/              # Build specifications
├── execution/               # Scripts and API server
├── corpus/                  # Source texts
│   ├── raw/                # Downloaded files
│   └── cleaned/            # Processed text
├── chroma_db/              # Vector database
└── widget/                 # Embeddable frontend
```

See `directives/jane_jacobs_chatbot.md` for full specifications.
