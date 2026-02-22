# Railway Deployment Guide

Deploy your Historical Figure Chatbot to Railway for public API access.

## Persona Configuration

This template supports deploying any historical figure persona. The active persona is controlled by the `PERSONA_ID` environment variable.

## Prerequisites

1. Railway account (sign up at https://railway.app)
2. GitHub repo pushed (already done ✓)
3. API keys ready (Anthropic + OpenAI)

## Deployment Steps

### 1. Include Cleaned Corpus in Git

The cleaned corpus (1.3MB) needs to be in your repo for Railway to build ChromaDB:

```bash
cd /mnt/c/Users/Owner/Documents/jane-jacobs-bot

# Add cleaned corpus files
git add corpus/cleaned/

# Commit
git commit -m "Add cleaned corpus for Railway deployment

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push to GitHub
git push origin main
```

### 2. Create Railway Project

1. Go to https://railway.app
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Choose `jane-jacobs-bot`
5. Railway will detect it as a Python project

### 3. Configure Environment Variables

In Railway project settings, add these variables:

```
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
PERSONA_ID=jane-jacobs
HOST=0.0.0.0
PORT=8000
```

**Persona Selection:**
- `PERSONA_ID` determines which persona to deploy (default: `jane-jacobs`)
- Must match a directory name in `personas/`
- Examples: `jane-jacobs`, `frederick-law-olmsted`, `ada-lovelace`
- One deployment = one persona (see Multi-Persona section for advanced setup)

### 4. Add Build Command

In Railway project settings → Deploy:

**Build Command:**
```bash
pip install -r requirements.txt && python execution/chunker_embedder.py
```

This will:
- Install dependencies
- Generate embeddings from cleaned corpus (~$0.0064 cost)
- Build ChromaDB

**Start Command:**
```bash
python execution/api_server.py
```

### 5. Deploy

Railway will automatically deploy. First deployment takes 3-5 minutes:
- Installing dependencies (~1 min)
- Building ChromaDB (~2-3 min)
- Starting server

### 6. Get Your Public URL

Once deployed:
1. Go to Settings → Networking
2. Click "Generate Domain"
3. Your API will be at: `https://your-app.up.railway.app`

### 7. Test Your Deployment

```bash
curl https://your-app.up.railway.app/health
```

Should return:
```json
{"status":"healthy","chromadb":{"connected":true,"chunks":580},"active_conversations":0}
```

### 8. Update Widget

Update your widget to use the public API:

```html
<script src="jacobs-widget.js" data-api-url="https://your-app.up.railway.app"></script>
```

## Important Notes

### ChromaDB Persistence

**Issue:** Railway's filesystem is ephemeral - ChromaDB rebuilds on each deploy.

**Solutions:**

**Option A: Accept Rebuild (Simplest)**
- Costs ~$0.0064 per deployment
- Automatic, no extra setup
- Good for development/demos

**Option B: Use Railway Volumes (Production)**
1. In Railway: Add → Volume
2. Mount path: `/app/chroma_db`
3. ChromaDB persists across deploys
4. One-time embedding cost

**Option C: Pre-build ChromaDB**
- Build ChromaDB locally
- Commit `chroma_db/` to git (16MB)
- Remove from `.gitignore`
- No rebuild needed (but larger repo)

### Cost Estimates

**Per Deployment:**
- OpenAI embeddings: ~$0.0064
- Railway: ~$5/month for 500GB egress
- Anthropic: Pay per API call

**Monthly (estimate):**
- 1000 conversations: ~$2-5 (Claude API)
- Railway hosting: $5-10
- Total: ~$7-15/month

### CORS Configuration

The API server has CORS enabled for all origins. For production, update `api_server.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

### Build Fails
- Check Railway logs for errors
- Verify API keys are set correctly
- Ensure cleaned corpus is in git

### ChromaDB Empty
- Check build command ran successfully
- Verify `corpus/cleaned/` has files
- Check Railway logs for embedding errors

### API Returns 500
- Check environment variables are set
- Verify Anthropic API key has credits
- Check model name is correct

### Widget Won't Connect
- Verify API URL in widget
- Check CORS settings
- Test health endpoint

## Alternative: Railway Template

For one-click deploy, create a `railway.toml`:

```toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt && python execution/chunker_embedder.py"

[deploy]
startCommand = "python execution/api_server.py"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
```

Then share your repo as a Railway template.

## Deploying a Custom Persona

To deploy your own historical figure:

### 1. Create Persona Configuration

```bash
# Locally, create your persona
cp personas/template.json personas/your-figure-id/persona.json
# Edit persona.json with all config
# Add corpus files to personas/your-figure-id/corpus/raw/
```

### 2. Build Corpus Locally (Recommended)

```bash
# Process corpus locally first
python execution/corpus_cleaner.py --persona your-figure-id
python execution/chunker_embedder.py --persona your-figure-id
```

This avoids embedding costs on each Railway deployment.

### 3. Commit to Git

```bash
git add personas/your-figure-id/
git commit -m "Add [Name] persona"
git push origin main
```

### 4. Update Railway Environment

In Railway Variables:
- Change `PERSONA_ID` to `your-figure-id`
- Railway auto-redeploys with new persona

### 5. Update Widget

```html
<script src="widget.js"
        data-api-url="https://your-app.up.railway.app"
        data-persona-id="your-figure-id"></script>
```

## Multi-Persona Deployment (Advanced)

To serve multiple personas from one deployment:

1. **Include all persona directories** in git
2. **Build all ChromaDB collections** locally:
   ```bash
   python execution/chunker_embedder.py --persona jane-jacobs
   python execution/chunker_embedder.py --persona frederick-law-olmsted
   ```
3. **Commit chroma_db/** to git (skip .gitignore)
4. **Remove PERSONA_ID** from Railway (API will error if set)
5. **Use persona-specific endpoints:**
   - Widget: `data-persona-id="jane-jacobs"`
   - API: Uses persona from widget, looks up correct collection

**Note:** Multi-persona requires more memory (~500MB per persona). Ensure Railway plan supports it.

## Next Steps

After deployment:
1. Test widget on your website
2. Monitor Railway usage/costs
3. Set up custom domain (optional)
4. Add analytics (optional)
5. Create additional personas (see `personas/README.md`)

Your historical figure chatbot is now live! 🚂
