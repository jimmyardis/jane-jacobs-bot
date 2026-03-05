# Discourse Sources — Adam Smith

Files here are works that analyzed, critiqued, responded to, or debated Smith's ideas. They are embedded separately from the corpus so the persona can distinguish his own words from how others engaged with them.

Place cleaned text files in `discourse/raw/` (or `discourse/cleaned/` if already clean).

## Sources (from sources.json)

| Title | Author | Year | Source | Notes |
|-------|--------|------|--------|-------|
| The Letters of David Hume | David Hume | 1932 | archive | Hume-Smith correspondence; Hume's comments on TMS and WoN drafts |
| Thoughts on the Cause of the Present Discontents | Edmund Burke | 1770 | archive | Burke's engagement with merchant political power |
| Capital, Vol. I | Karl Marx | 1867 | gutenberg (35993) | Extensive engagement with Smith's labor theory; critique and extension |
| Report on the Subject of Manufactures | Alexander Hamilton | 1791 | manual | Departure from Smith on industrial policy; already in Hamilton corpus |
| The General Theory | John Maynard Keynes | 1936 | archive | Classical economics legacy; Keynesian departure from Smithian equilibrium |
| The Affluent Society | J.K. Galbraith | 1958 | archive | Producer-created demand; updates Smith's merchant-capture concern |

## Download

Run the archive downloader for archive sources:
```bash
python execution/archive_downloader.py --persona adam-smith --discourse
```

Marx's Capital Vol I (Gutenberg 35993):
```bash
python execution/gutenberg_downloader.py --persona adam-smith --discourse
```

Or run both at once:
```bash
python execution/download_corpus.py --persona adam-smith --discourse
```

## Embed

After downloading and cleaning:
```bash
python execution/chunker_embedder.py --persona adam-smith --discourse
```

This creates the `adam_smith_discourse` ChromaDB collection.
