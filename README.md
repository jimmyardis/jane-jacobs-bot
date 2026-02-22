# Historical Figure Chatbot Template

A reusable RAG-powered chatbot template for embodying historical figures through their writings. Configured entirely through JSON - no code changes needed to create new personas.

**Example Personas:**
- **Jane Jacobs** (1916-2006) - Urbanist and author of *The Death and Life of Great American Cities*
- **Frederick Law Olmsted** (coming soon) - Landscape architect and designer of Central Park

## ✨ Features

- **Configuration-driven**: All persona-specific content in `persona.json`
- **RAG architecture**: Grounded responses from actual writings
- **Embeddable widget**: Single script tag, works anywhere
- **Themeable**: Custom colors, fonts, and conversation starters per persona
- **Production-ready**: Deploys to Railway with ChromaDB persistence

---

## 🚀 Quick Start

### For Existing Personas (Jane Jacobs)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys:
   # - ANTHROPIC_API_KEY (for Claude)
   # - OPENAI_API_KEY (for embeddings)
   ```

3. **Run server:**
   ```bash
   PERSONA_ID=jane-jacobs python execution/api_server.py
   ```

4. **Open widget demo:**
   ```bash
   cd widget
   python -m http.server 8080
   # Visit http://localhost:8080/demo.html
   ```

### For Creating New Personas

See **Creating a New Persona** section below.

---

## 📚 Creating a New Persona

**Step-by-step guide:**

1. **Copy the template:**
   ```bash
   cp personas/template.json personas/your-persona-id/persona.json
   ```

2. **Fill in the persona.json fields:**
   - `metadata`: Name, birth/death years, famous work
   - `persona.system_prompt_template`: Voice, tone, knowledge, constraints
   - `widget.conversation_starters`: 4 engaging questions
   - `widget.ui`: Header text, tagline, placeholder
   - `widget.theme`: Colors and fonts
   - `model`: LLM and embedding model configs

3. **Create sources.json for corpus:**
   ```bash
   cp personas/jane-jacobs/sources.json personas/your-persona-id/sources.json
   # Edit to list their books/writings
   ```

4. **Add corpus files to `personas/your-persona-id/corpus/raw/`:**
   - PDFs, DOCX, or TXT files
   - Public domain works (via Archive.org) or manually sourced

5. **Run the corpus pipeline:**
   ```bash
   python execution/corpus_cleaner.py --persona your-persona-id
   python execution/chunker_embedder.py --persona your-persona-id
   ```

6. **Test locally:**
   ```bash
   PERSONA_ID=your-persona-id python execution/api_server.py
   ```

7. **Deploy:**
   - Set `PERSONA_ID=your-persona-id` in Railway environment variables
   - Push to GitHub, Railway auto-deploys

**Full guide:** See `personas/README.md` for comprehensive documentation including:
- System prompt best practices
- Corpus sourcing strategies
- Widget theme customization
- Testing checklist
- Troubleshooting

---

## 🎨 Widget Integration

**Embed on any website with a single script tag:**

```html
<link rel="stylesheet" href="https://yourusername.github.io/historical-figures/widget/jacobs-widget.css">
<script src="https://yourusername.github.io/historical-figures/widget/jacobs-widget.js"
        data-api-url="https://your-api.up.railway.app"
        data-persona-id="jane-jacobs"></script>
```

The widget automatically:
- Loads persona configuration from `/persona/{id}/config`
- Applies custom theme colors via CSS variables
- Displays persona-specific conversation starters
- Uses correct header text, tagline, and placeholder

---

## 📂 Project Structure

```
historical-figures-chatbot/
├── personas/                       # Persona configurations
│   ├── jane-jacobs/
│   │   ├── persona.json           # All persona-specific config
│   │   ├── sources.json           # Corpus source list
│   │   └── corpus/
│   │       ├── raw/               # Original files
│   │       └── cleaned/           # Processed text
│   ├── template.json              # Blank template for new personas
│   └── README.md                  # Persona creation guide
├── execution/
│   ├── persona_manager.py         # Config loader
│   ├── api_server.py              # FastAPI backend
│   ├── chunker_embedder.py        # RAG pipeline
│   ├── corpus_cleaner.py          # Text extraction
│   └── archive_downloader.py      # Internet Archive scraper
├── chroma_db/                      # Vector database (multi-collection)
├── widget/
│   ├── jacobs-widget.js           # Embeddable widget
│   ├── jacobs-widget.css          # Themeable styles
│   └── demo.html                  # Demo page
├── .env                            # API keys (not in git)
├── requirements.txt                # Python dependencies
└── railway.json                    # Railway deployment config
```

---

## 🛠 Tech Stack

**Backend:**
- Python 3.12
- FastAPI (API server)
- ChromaDB (vector database)
- OpenAI (text-embedding-3-small for embeddings)
- Anthropic (Claude Sonnet 4 for responses)

**Frontend:**
- Vanilla JavaScript (no framework)
- CSS variables for runtime theming
- Single-file embeddable widget

**Deployment:**
- Railway (with Nixpacks builder)
- GitHub Pages (for widget hosting)

---

## 🧪 API Endpoints

**Chat:**
```bash
POST /chat
{
  "message": "What makes a city safe?",
  "conversation_id": "optional-id"
}
```

**Health Check:**
```bash
GET /health
# Returns: {"status": "healthy", "chromadb": {"chunks": 580}}
```

**Persona Configuration:**
```bash
GET /persona/{persona_id}/config
# Returns widget UI strings, theme, and conversation starters
```

**List Personas:**
```bash
GET /personas
# Returns: {"personas": ["jane-jacobs", "frederick-law-olmsted"]}
```

---

## 📊 Persona Configuration Reference

**Minimal persona.json:**

```json
{
  "id": "your-persona-id",
  "metadata": {
    "name": "Full Name",
    "birth_year": 1900,
    "death_year": 2000,
    "famous_work": "Their Most Famous Work"
  },
  "corpus": {
    "collection_name": "your_persona_id_corpus",
    "author": "Full Name"
  },
  "persona": {
    "system_prompt_template": "You are {name} ({birth_year}–{death_year})...",
    "domain": "field of expertise"
  },
  "widget": {
    "conversation_starters": [
      "Question 1?",
      "Question 2?",
      "Question 3?",
      "Question 4?"
    ],
    "ui": {
      "header_title": "Full Name",
      "header_subtitle": "(birth_year – death_year)",
      "header_tagline": "Tagline for the widget",
      "input_placeholder": "Ask them a question..."
    },
    "theme": {
      "primary_color": "#3498db",
      "cream": "#f7f3e9",
      "charcoal": "#2a2a2a"
    }
  },
  "model": {
    "llm": "claude-sonnet-4-20250514",
    "max_tokens": 1024,
    "embedding_model": "text-embedding-3-small",
    "retrieval_chunks": 5
  }
}
```

**Template variables in system_prompt_template:**
- `{name}` - Persona's full name
- `{birth_year}` - Birth year
- `{death_year}` - Death year (empty if still living)
- `{current_year}` - Auto-injected current year (2026)
- `{current_age}` - Auto-calculated age
- `{famous_work}` - Their most famous work

---

## 🚂 Railway Deployment

**Deploy to Railway:**

1. Connect Railway to your GitHub repo
2. Set environment variables:
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`
   - `PERSONA_ID=jane-jacobs` (or your persona)
   - `HOST=0.0.0.0`
   - `PORT=8000`

3. Railway auto-deploys using `railway.json` config

4. Generate public domain in Railway → Settings → Networking

**Multi-persona deployment:**
- Default: Single persona per deployment (set via `PERSONA_ID`)
- Advanced: One deployment can serve multiple personas (ChromaDB supports multiple collections)

See `RAILWAY_DEPLOY.md` for detailed deployment guide.

---

## 💡 Example Personas

**Jane Jacobs** (Urbanist)
- **Voice**: Plain-spoken, direct, occasionally sharp
- **Domain**: Cities, neighborhoods, urban planning
- **Theme**: 1960s Greenwich Village (brick red, cream, typewriter font)
- **Corpus**: 5 books + transcripts = 580 chunks

**Potential Personas:**
- **Ada Lovelace** - Computing pioneer, poetic and mathematical
- **Richard Feynman** - Physicist, playful and relentlessly curious
- **Rachel Carson** - Environmental scientist, lyrical and urgent
- **Frederick Law Olmsted** - Landscape architect, formal and visionary

---

## 📖 Documentation

- **`personas/README.md`** - Comprehensive persona creation guide (200+ lines)
- **`RAILWAY_DEPLOY.md`** - Railway deployment instructions
- **`directives/jane_jacobs_chatbot.md`** - Original Jane Jacobs specifications

---

## 🧑‍💻 Development

**Run locally:**
```bash
# Install dependencies
pip install -r requirements.txt

# Set up .env file
cp .env.example .env

# Run API server
PERSONA_ID=jane-jacobs python execution/api_server.py

# In another terminal, serve widget
cd widget && python -m http.server 8080
```

**Test persona config loading:**
```bash
python execution/persona_manager.py jane-jacobs
```

**Create embeddings for new persona:**
```bash
python execution/chunker_embedder.py --persona your-persona-id
```

---

## 🤝 Contributing

**To add a new historical figure:**

1. Fork this repo
2. Create a new persona in `personas/your-figure-id/`
3. Follow the guide in `personas/README.md`
4. Test locally
5. Submit a PR with:
   - persona.json
   - sources.json
   - Attribution for corpus sources
   - Example conversations demonstrating voice accuracy

**Ensure:**
- Corpus sources are properly licensed (public domain or fair use)
- System prompt accurately reflects their documented voice/style
- Conversation starters showcase their expertise

---

## 📜 License

MIT License - See LICENSE file for details.

**Corpus Attribution:**
- Jane Jacobs texts: Public domain and fair use excerpts
- See individual persona directories for source attribution

---

## 🙏 Acknowledgments

Built for those who want to hear the voices of thinkers, writers, and visionaries through their own words.

**Powered by:**
- [Anthropic Claude](https://www.anthropic.com/) - LLM responses
- [OpenAI](https://openai.com/) - Text embeddings
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Internet Archive](https://archive.org/) - Public domain texts
