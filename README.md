# comms-ai-datagen

Synthetic data generator for Central Bank Communications AI — built for the Federal Reserve System / FRBSF hackathon.

Generates realistic synthetic data across 5 categories using multiple LLM backends. Designed to train and evaluate NLP models for text classification, sentiment analysis, topic modeling, and LLM-based draft generation.

Two ways to run it:
- **Streamlit UI** (`app.py`) — web interface with auto-detection across Ollama → OpenAI → AWS Bedrock
- **CLI** (`python -m datagen`) — terminal-based, AWS Bedrock only

## Quick Start

**Requirements:** Python 3.10+

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
# .venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### Streamlit UI (recommended)

```bash
cp .env.example .env           # then edit with your credentials
streamlit run app.py           # opens at http://localhost:8501
```

The UI auto-detects your LLM backend in priority order: local Ollama → OpenAI → AWS Bedrock. Configure connection details in the sidebar or via `.env`.

### CLI (Bedrock only)

```bash
python -m datagen validate --config config.yaml        # validate config
python -m datagen test-connection --config config.yaml  # test AWS connection
python -m datagen generate --config config.yaml         # generate all enabled categories
python -m datagen generate --config config.yaml --dry-run                          # preview only
python -m datagen generate --config config.yaml --category inquiries -v            # specific category, verbose
```

## LLM Backends

| Backend | Used by | Setup |
|---|---|---|
| **Ollama** (local) | UI | Install Ollama, pull a model. Set `OLLAMA_HOST` and `OLLAMA_MODEL` in `.env` |
| **OpenAI** | UI | Set `OPENAI_API_KEY` in `.env` |
| **AWS Bedrock** | UI + CLI | Configure AWS CLI credentials, enable Claude models in Bedrock console |

The Streamlit UI tries each backend in order and uses the first one that responds. The CLI only supports Bedrock.

## Configuration

### `.env` — LLM credentials (Streamlit UI)

Copy `.env.example` to `.env` and fill in whichever backend(s) you want:

```bash
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma4:e4b
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
AWS_PROFILE=your-sso-profile
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-6
```

### `config.yaml` — data generation settings

Controls what gets generated, how many records, and output format. Key settings:

```yaml
bedrock:
  model_id: "global.anthropic.claude-sonnet-4-6"
  region: "us-east-1"
  batch_size: 5          # records per API call

categories:
  inquiries:
    enabled: true
    count: 5
  social_media:
    enabled: true
    count: 5
  # ... same pattern for news_articles, response_templates, insight_reports

output:
  directory: "./output"
  add_timestamp: true    # prevents overwriting previous runs
```

See `config.yaml` for the full set of options (topics, sources, platforms, sentiments, etc.).

## Data Categories

| Category | ID Prefix | Description |
|---|---|---|
| `inquiries` | INQ | Incoming comms from media, public, and stakeholders |
| `social_media` | SM | Posts about Fed policy from Twitter, Reddit, LinkedIn |
| `news_articles` | NEWS | Financial journalism covering Fed decisions |
| `response_templates` | RT | Pre-drafted responses for common inquiry types |
| `insight_reports` | RPT | Monitoring reports with sentiment, trends, and risk alerts |

## Output

JSON files are saved to `output/`. With `add_timestamp: true` (default), each run creates timestamped files like `inquiries_20260409_102930.json`.

The Streamlit UI includes a built-in file viewer with preview and download.

## Cost Estimates

| Backend | Cost | Speed |
|---|---|---|
| Ollama (local) | Free | ~5–60 min depending on model/hardware |
| OpenAI (GPT-4o) | ~$0.50–2 | ~10–20 min |
| AWS Bedrock (Claude Sonnet) | ~$5–15 | ~15–30 min |

Estimates based on ~1,780 records at batch_size=10.

## Troubleshooting

| Issue | Fix |
|---|---|
| `AccessDeniedException` | Enable Bedrock model access in AWS Console |
| `ExpiredTokenException` | Refresh AWS credentials or SSO session |
| `ThrottlingException` | Lower `batch_size` |
| `ValidationException` | Check `model_id` is valid for your region |
| JSON parse errors | Lower `batch_size` for more reliable responses |
| Ollama 405 error | Use base URL only (`http://host:11434`), not `/api/chat` |
| Ollama malformed JSON | Use larger models (27B+); smaller models may struggle with structured output |
| "No LLM backend connected" in UI | Click Detect in sidebar, verify `.env` values |
