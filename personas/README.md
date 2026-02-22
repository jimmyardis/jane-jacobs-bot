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
   cp personas/jane-jacobs/sources.json personas/your-figure-id/sources.json
   # Edit to list your figure's works
   ```

4. **Add corpus files** to `personas/your-figure-id/corpus/raw/`
   - PDFs, DOCX, or TXT files of their writings
   - Transcripts of speeches or interviews
   - Letters, essays, or compiled works

5. **Run the corpus pipeline**
   ```bash
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

## Corpus Sourcing Strategies

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

### Option 2: Manual Files

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

### Option 3: Mixed Sources

Combine both approaches:
- Use archive_downloader for public domain works
- Add additional manual files for recent or hard-to-find texts

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
