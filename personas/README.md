# Historical Figure Personas

This directory contains persona configurations for the historical figure chatbot template. Each persona lives in its own subdirectory with a complete configuration file and corpus.

## Quick Start

To create a new historical figure chatbot:

1. **Copy the template**
   ```bash
   cp personas/template.json personas/your-figure-id/persona.json
   ```

2. **Fill in the persona.json fields** (see Structure Reference below)

3. **Create sources.json** for corpus acquisition
   ```bash
   cp personas/template_sources.json personas/your-figure-id/sources.json
   # Edit to list your figure's works (supports archive, gutenberg, and manual sources)
   ```

4. **Add corpus files** to `personas/your-figure-id/corpus/raw/`
   - PDFs, DOCX, or TXT files of their writings
   - Transcripts of speeches or interviews
   - Letters, essays, or compiled works

5. **Download and process the corpus**
   ```bash
   # Download from all sources (Archive.org + Gutenberg) in one command
   python execution/download_corpus.py --persona your-figure-id
   # Then clean and embed
   python execution/corpus_cleaner.py --persona your-figure-id
   python execution/chunker_embedder.py --persona your-figure-id
   ```

6. **Test locally**
   ```bash
   PERSONA_ID=your-figure-id python execution/api_server.py
   ```

7. **Test the widget**
   - Open `widget/demo.html` in a browser
   - Update the script tag: `data-persona-id="your-figure-id"`

## persona.json Structure Reference

### Required Fields

**metadata**
- `name`: Full name (used in system prompt and UI)
- `birth_year`: Birth year (integer)
- `death_year`: Death year (integer, or null if still living)
- `current_age`: How old they'd be now (auto-calculated from birth_year)
- `famous_work`: Their most well-known work (referenced in system prompt)

**corpus**
- `collection_name`: ChromaDB collection name (format: `{persona_id}_corpus`)
- `author`: Author name for corpus metadata

**persona**
- `system_prompt_template`: Full system prompt with placeholders like `{name}`, `{current_year}`, `{birth_year}`, `{death_year}`, `{current_age}`, `{famous_work}`
- `domain`: Field of expertise (e.g., "urban planning", "computer science", "physics")

**widget.conversation_starters**
- Array of 4 engaging questions that showcase the persona's expertise

**widget.ui**
- `header_title`: Widget header text (usually just their name)
- `header_subtitle`: Birth/death years in parentheses
- `header_tagline`: Call-to-action text below the header
- `input_placeholder`: Placeholder for the input field

**widget.theme**
- `primary_color`: Main accent color (hex code)
- Other colors: cream, charcoal, warm_gray, dark_cream, text_gray
- Fonts: font_primary, font_secondary

**model**
- `llm`: Claude model name
- `max_tokens`: Max response length
- `embedding_model`: OpenAI embedding model
- `retrieval_chunks`: Number of RAG chunks to retrieve

### Optional Fields

- `metadata.tagline`: Short descriptive phrase
- `metadata.description`: Longer bio
- `persona.frameworks`: Array of key concepts/theories they're known for
- `widget.ui.error_message`: Custom error message
- `widget.ui.demo_*`: Demo page content (hero title, description, etc.)

## System Prompt Guidelines

The system prompt is the most important part of persona configuration. It defines the chatbot's voice, knowledge, and behavior.

### Best Practices

1. **Voice & Tone Section**
   - Describe their speaking style (formal/casual, academic/plain-spoken)
   - Key personality traits (curious, sharp, warm, skeptical)
   - How they interact (ask questions, push back, validate)
   - What language patterns they avoid

2. **Knowledge Section**
   - Always include: "Everything in your corpus (provided in context below)"
   - Add relevant current events they'd have opinions on
   - List their key frameworks/theories/concepts
   - Mention how they apply old ideas to new situations

3. **Constraints Section**
   - Things they wouldn't do (speak in jargon, be neutral when they have strong views)
   - Always include: "Say 'As an AI' or reference being an AI"
   - Behavioral guardrails specific to their personality

4. **Template Variables**
   - Use `{name}`, `{birth_year}`, `{death_year}`, `{current_age}`, `{current_year}`, `{famous_work}`
   - These get auto-substituted when the system prompt is built

### Example System Prompt Structure

```
You are {name} ({birth_year}–{death_year}), but you're alive in {current_year} at age {current_age}. You're [their significance].

**Voice and tone:**
- [Speaking style]
- [Personality traits]
- [Interaction patterns]

**What you know:**
- Everything in your corpus (provided in context below).
- Current events up to {current_year} — [relevant topics].
- [Key frameworks and how they apply them].

**What you won't do:**
- [Behavioral constraints]
- Say "As an AI" or reference being an AI.

You are {name}. Respond as [him/her/them].
```

## Knowledge Layers

Each persona has three knowledge layers that work together at runtime:

| Layer | Directory | Tool | Output | How it's used |
|-------|-----------|------|--------|---------------|
| **Own writings** | `corpus/` | `chunker_embedder.py` | `{persona}_corpus` ChromaDB collection | Retrieved per-query, injected as "excerpts from your writings" |
| **Biographical context** | `context/raw/` | `context_synthesizer.py` | `context_notes.md` | Injected statically into system prompt as "Characterological Notes" |
| **Critical discourse** | `discourse/` | `chunker_embedder.py --discourse` | `{persona}_discourse` ChromaDB collection | Retrieved per-query, injected as "critical discourse about your ideas" |

### Layer 1: Own Writings (corpus/)

The figure's own books, essays, interviews, and speeches. See **Corpus Sourcing Strategies** below.

### Layer 2: Biographical Context (context/)

Biographies, memoirs, oral histories, and characterological studies *about* the figure — not their own words, but what others observed about how they lived, thought, and behaved.

**What belongs here:**
- Biographies and biographical essays
- Memoirs by people who knew them
- Oral history transcripts
- Letters and correspondence collections
- Psychological or characterological studies

**Workflow:**
1. Place `.txt` or `.md` files in `context/raw/`
2. Run the synthesizer (uses Anthropic API — you will be prompted to confirm):
   ```bash
   python execution/context_synthesizer.py --persona your-figure-id
   ```
3. Review the generated `personas/your-figure-id/context_notes.md`
4. Restart `api_server.py` — it automatically injects context_notes into the system prompt

### Layer 3: Critical Discourse (discourse/)

Works that analyzed, critiqued, responded to, or debated the figure's ideas. Embedded separately so the persona can distinguish between their own words and how others engaged with them.

**What belongs here:**
- Academic critiques and reviews
- Intellectual responses and rebuttals
- Letters from correspondents (Freud writing to Jung, etc.)
- Interviews where others discuss the figure's impact
- Polemics, celebrations, retrospectives

**Workflow:**
1. Place raw files in `discourse/raw/`
2. Clean them:
   ```bash
   python execution/corpus_cleaner.py --persona your-figure-id
   ```
   *(Note: corpus_cleaner reads from corpus/raw/ by default — move cleaned files manually to discourse/cleaned/ for now)*
3. Embed into the discourse collection:
   ```bash
   python execution/chunker_embedder.py --persona your-figure-id --discourse
   ```
4. Restart `api_server.py` — it automatically loads the discourse collection if present

---

## Corpus Sourcing Strategies

### The `source` Field

Each entry in `sources.json` has an optional `source` field that controls which downloader processes it:

| Value | Downloader | When to use |
|-------|-----------|-------------|
| `"archive"` (default) | `archive_downloader.py` | 20th century works, uses search query |
| `"gutenberg"` | `gutenberg_downloader.py` | Pre-1928 US works, requires `gutenberg_id` |
| `"manual"` | (none) | Copyrighted/hard-to-find texts you place yourself |

Entries without a `source` field default to `"archive"` for backwards compatibility.

Use `python execution/download_corpus.py --persona your-id` to run both downloaders at once.

---

### Option 1: Internet Archive (Public Domain)

For figures whose works are in the public domain:

1. Create `sources.json`:
   ```json
   {
     "downloader": "internet_archive",
     "priority_1": [
       {
         "title": "Famous Book Title",
         "author": "Author Name",
         "year": 1950,
         "search_terms": "famous book title author name"
       }
     ]
   }
   ```

2. Run downloader:
   ```bash
   python execution/archive_downloader.py --persona your-figure-id
   ```

### Option 2: Project Gutenberg (Public Domain)

Project Gutenberg has clean, plain-text versions of 70,000+ public domain works — ideal for pre-1928 figures because there's no OCR noise.

**Finding a Gutenberg ID:**
1. Go to [gutenberg.org](https://www.gutenberg.org) and search for the book
2. The ID is the number in the URL: `gutenberg.org/ebooks/23` → ID is `23`

1. Add entries with `"source": "gutenberg"` and `"gutenberg_id"` to `sources.json`:
   ```json
   {
     "downloader": "auto",
     "priority_1": [
       {
         "title": "Narrative of the Life of Frederick Douglass",
         "author": "Frederick Douglass",
         "year": 1845,
         "source": "gutenberg",
         "gutenberg_id": 23
       }
     ]
   }
   ```

2. Run the Gutenberg downloader (or the master script):
   ```bash
   python execution/gutenberg_downloader.py --persona your-figure-id
   # or download everything at once:
   python execution/download_corpus.py --persona your-figure-id
   ```

**Note:** The downloader tries three URL patterns automatically and falls back gracefully if one fails.

### Option 3: Manual Files

For copyrighted works or hard-to-find texts:

1. Manually add PDFs/DOCX/TXT to `personas/your-figure-id/corpus/raw/`
2. Create minimal `sources.json`:
   ```json
   {
     "downloader": "manual",
     "files": [
       {
         "path": "personas/your-figure-id/corpus/raw/book.pdf",
         "title": "Book Title",
         "year": 1980
       }
     ]
   }
   ```
3. Run corpus cleaner directly (skip downloader)

### Option 4: Mixed Sources

Combine all three — just set the `source` field per entry and run `download_corpus.py`:
- `"source": "gutenberg"` for clean pre-1928 plain text
- `"source": "archive"` for 20th century works via search
- `"source": "manual"` for anything you place yourself

### Corpus Size Guidelines

- **Minimum**: 3-5 documents, ~50,000 words → 100-200 chunks
- **Recommended**: 10-15 documents, ~200,000 words → 400-600 chunks
- **Maximum**: 30+ documents, ~500,000 words → 1000+ chunks

More corpus = better responses, but also higher embedding costs (~$0.002 per 10,000 words).

## Widget Theme Customization

The widget theme defines colors, fonts, and visual identity.

### Color Palette

Choose colors that reflect the persona's era, field, or personality:

- **Academic/Scholarly**: Blues, grays (#3498db, #34495e)
- **Creative/Artistic**: Warm tones, purples (#e74c3c, #9b59b6)
- **Scientific/Technical**: Greens, teals (#27ae60, #16a085)
- **Historical/Classic**: Earth tones, sepia (#8b4513, #d2691e)

Example:
```json
"theme": {
  "primary_color": "#3498db",   // Main accent (buttons, borders)
  "cream": "#f7f3e9",           // Light background
  "charcoal": "#2a2a2a",        // Dark text
  "warm_gray": "#95a5a6",       // Secondary elements
  "dark_cream": "#ecf0f1",      // Hover states
  "text_gray": "#7f8c8d"        // Secondary text
}
```

### Font Choices

- **Monospace fonts** (Courier, Consolas): Technical, direct, typewriter feel
- **Serif fonts** (Georgia, Garamond): Classic, literary, academic
- **Sans-serif fonts** (Helvetica, Arial): Modern, clean, accessible

## Testing Checklist

Before deploying a new persona:

- [ ] persona.json validates (no JSON syntax errors)
- [ ] All required fields are filled
- [ ] System prompt template includes all placeholders
- [ ] Conversation starters are engaging and persona-relevant
- [ ] Corpus has at least 100 chunks
- [ ] `corpus_cleaner.py` runs without errors
- [ ] `chunker_embedder.py` generates embeddings successfully
- [ ] ChromaDB collection created with correct name
- [ ] API server starts without errors
- [ ] `/health` endpoint shows correct chunk count
- [ ] `/persona/{id}/config` endpoint returns widget config
- [ ] Widget loads with correct theme colors
- [ ] Conversation starters appear correctly
- [ ] Chat responses match persona voice
- [ ] Follow-up questions stay in character

## Troubleshooting

### "FileNotFoundError: Persona config not found"
- Check that `personas/{persona-id}/persona.json` exists
- Verify PERSONA_ID environment variable matches directory name
- Ensure persona-id uses hyphens (not underscores) for directory name

### "Collection not found in ChromaDB"
- Run `chunker_embedder.py --persona {persona-id}` first
- Check that `collection_name` in persona.json matches `{persona_id}_corpus` format
- Verify corpus/cleaned/ directory has text files

### "Widget shows default Jane Jacobs theme"
- Check browser console for API fetch errors
- Verify `/persona/{id}/config` endpoint returns data
- Ensure `data-persona-id` attribute matches persona id

### "Chat responses don't match persona voice"
- Review system_prompt_template for clarity
- Add more specific voice/tone descriptions
- Increase corpus size for better RAG context
- Adjust max_tokens if responses are cut off

### "Embedding costs too high"
- Reduce corpus size (fewer/shorter documents)
- Use shorter chunks (edit chunker_embedder.py chunk_size)
- Pre-build ChromaDB locally and commit to git (skip Railway rebuild)

## Examples

### Jane Jacobs (Urban Planning)
- **Voice**: Plain-spoken, direct, occasionally sharp
- **Domain**: Cities, neighborhoods, urban planning
- **Theme**: 1960s Greenwich Village (brick red, cream, typewriter font)
- **Corpus**: 5 books + transcripts = 580 chunks

### Potential Personas

**Ada Lovelace** (Computer Science Pioneer)
- Voice: Poetic, visionary, mathematical
- Domain: Computing, mathematics, creative analysis
- Theme: Victorian era meets computational (deep purple, gold)

**Richard Feynman** (Physics)
- Voice: Curious, playful, relentlessly questioning
- Domain: Physics, teaching, problem-solving
- Theme: Chalkboard aesthetic (black, white, yellow)

**Rachel Carson** (Environmentalism)
- Voice: Lyrical, scientific, urgent about ecology
- Domain: Marine biology, environmental science, nature writing
- Theme: Natural greens and blues (ocean/forest)

**Hannah Arendt** (Political Philosophy)
- Voice: Rigorous, conceptual, historically grounded
- Domain: Political theory, totalitarianism, human condition
- Theme: Philosophical grays and earth tones

## Contributing

When creating personas for public use:

1. Ensure corpus sources are properly licensed (public domain or fair use)
2. Test thoroughly before submitting
3. Document any special considerations in a persona-specific README
4. Include attribution for corpus sources
5. Provide example conversations demonstrating voice accuracy

## Resources

- **Public Domain Texts**: Internet Archive, Project Gutenberg, Google Books
- **Voice Analysis**: Read published interviews, watch recordings
- **Era Research**: Understand historical context for authentic voice
- **Domain Knowledge**: Research key concepts to include in system prompt
