# Context Sources — Adam Smith

Place biographical and characterological source files here in `raw/`.

## Sources to acquire

### Priority 1 (manual — copyrighted, place PDFs/TXT here)
- **"Adam Smith: An Enlightened Life"** — Nicholas Phillipson (2010, Yale University Press)
  - The authoritative modern biography. Reconstructs his intellectual formation from Hutcheson through Hume, his European travels as tutor to the Duke of Buccleuch, and the long composition of both major works. Essential for characterological detail: his absent-mindedness, his friendship with Hume, his habit of dictating while pacing.

- **"The Authentic Adam Smith: His Life and Ideas"** — James R. Otteson (2006, Worth Publishers)
  - Focused on what Smith actually argued versus what he is attributed. Directly addresses the misappropriation problem. Useful for the context_synthesizer to extract notes on how Smith understood his own project.

### Secondary (if available)
- **"Adam Smith and His World"** — D.D. Raphael (2004)
  - Short, accessible intellectual biography. Good supplement.

- **"Adam Smith's Marketplace of Life"** — James Otteson (2002, Cambridge)
  - Detailed study of the unity of TMS and WoN. Useful for the 'two Smiths' problem.

## After placing files

Run:
```bash
python execution/context_synthesizer.py --persona adam-smith
```

This will generate `context_notes.md` injected into the system prompt.
