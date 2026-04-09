# comms-ai-datagen

Synthetic data generator for Central Bank Communications AI — built for the Federal Reserve System / FRBSF hackathon use case.

Generates realistic synthetic data across 5 categories using AWS Bedrock (Claude Sonnet/Opus), designed to train and evaluate NLP models for text classification, sentiment analysis, topic modeling, and LLM-based draft generation.

## Data Categories

| Category | Description | Default Count |
|---|---|---|
| **Inquiries** | Incoming communications from media, public, and stakeholders | 500 |
| **Social Media** | Posts about Fed monetary policy from Twitter, Reddit, LinkedIn | 1,000 |
| **News Articles** | Financial journalism covering Fed decisions and economic policy | 200 |
| **Response Templates** | Pre-drafted responses for common inquiry types | 50 |
| **Insight Reports** | Communication monitoring reports with sentiment, trends, and risks | 30 |

## Prerequisites

- **Python 3.10+**
- **AWS CLI** configured with credentials that have Bedrock access
- **Bedrock model access** enabled for Claude Sonnet 4.6 (or other Claude models) in your AWS account

### AWS Setup

1. **Configure AWS credentials** (choose one method):

   **Option A: AWS SSO (Recommended for organizations)**
   ```bash
   aws configure sso
   ```
   Follow the prompts to authenticate. Note the profile name created (e.g., `AWSAdministratorAccess-051570254217`).

   **Option B: Standard AWS credentials**
   ```bash
   aws configure
   ```

2. **Set AWS Profile** (required if using SSO):
   
   **PowerShell (Windows):**
   ```powershell
   # For current session
   $env:AWS_PROFILE = "AWSAdministratorAccess-051570254217"
   
   # Or add to your PowerShell profile for persistence
   notepad $PROFILE
   # Add this line: $env:AWS_PROFILE = "AWSAdministratorAccess-051570254217"
   ```
   
   **Bash (Linux/Mac):**
   ```bash
   # For current session
   export AWS_PROFILE=AWSAdministratorAccess-051570254217
   
   # Or add to ~/.bashrc or ~/.zshrc for persistence
   echo 'export AWS_PROFILE=AWSAdministratorAccess-051570254217' >> ~/.bashrc
   ```

3. **Ensure you have access to Bedrock models** in your AWS console:
   - Go to **Amazon Bedrock** → **Model access**
   - Enable **Anthropic Claude** models (Claude Sonnet 4.6, Claude Opus 4.6, etc.)
   - Model access is granted at the account level and may take a few minutes to activate

## Installation

```bash
# Clone or unzip the package
cd comms-ai-datagen

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

## Usage

### 1. Validate Configuration

Check that your `config.yaml` is valid before generating:

```bash
python -m datagen validate --config config.yaml
```

### 2. Test AWS Bedrock Connection

Verify your AWS credentials and model access:

```bash
python -m datagen test-connection --config config.yaml
```

### 3. Dry Run

See what would be generated without making API calls:

```bash
python -m datagen generate --config config.yaml --dry-run
```

### 4. Generate All Data

```bash
python -m datagen generate --config config.yaml
```

### 5. Generate Specific Categories

```bash
# Generate only social media and news articles
python -m datagen generate --config config.yaml --category social_media --category news_articles

# Generate only inquiries
python -m datagen generate --config config.yaml --category inquiries
```

### 6. Verbose Output

```bash
python -m datagen generate --config config.yaml -v
```

## Configuration

All settings are controlled via `config.yaml`:

```yaml
bedrock:
  # Use inference profile IDs for cross-region routing
  model_id: "global.anthropic.claude-sonnet-4-6"  # recommended
  # Other options:
  # - global.anthropic.claude-opus-4-6-v1
  # - global.anthropic.claude-sonnet-4-5-20250929-v1:0
  region: "us-east-1"
  max_tokens: 4096
  batch_size: 10  # records per API call

data:
  date_range:
    start: "2022-01-01"
    end: "2025-12-31"
  context: "Federal Reserve System / FRBSF"

categories:
  inquiries:
    enabled: true
    count: 500      # adjust as needed
  social_media:
    enabled: true
    count: 1000
  # ... see config.yaml for all options

output:
  format: json
  directory: "./output"
  pretty: true
  add_timestamp: true  # Adds timestamp to filenames for versioning
```

### Key Configuration Options

| Setting | Description |
|---|---|
| `bedrock.model_id` | Bedrock inference profile ID (e.g., global.anthropic.claude-sonnet-4-6) |
| `bedrock.region` | AWS region for Bedrock |
| `bedrock.batch_size` | Number of records to generate per API call (lower = more diverse, higher = faster) |
| `categories.*.enabled` | Enable/disable individual categories |
| `categories.*.count` | Number of records to generate per category |
| `data.date_range` | Date range for generated timestamps (2022-2025) |
| `output.add_timestamp` | Add timestamp to filenames (true = versioned files, false = overwrite) |

## Output

Generated data is saved as JSON files in the `output/` directory.

**With timestamps enabled (default):**
```
output/
├── inquiries_20260409_102930.json
├── social_media_20260409_102930.json
├── news_articles_20260409_102930.json
├── response_templates_20260409_102930.json
└── insight_reports_20260409_102930.json
```

**With timestamps disabled (`add_timestamp: false`):**
```
output/
├── inquiries.json
├── social_media.json
├── news_articles.json
├── response_templates.json
└── insight_reports.json
```

> **Note:** Timestamp versioning prevents accidental data loss by creating a new file for each generation run.

### Sample Record: Inquiry

```json
{
  "id": "INQ-00001",
  "source": "media",
  "channel": "email",
  "subject": "Request for Comment on FOMC Rate Decision",
  "body": "I am writing from Reuters to request an official comment...",
  "category": "monetary_policy",
  "priority": "high",
  "timestamp": "2023-06-15T14:30:00Z",
  "sender_name": "Jane Smith",
  "sender_organization": "Reuters"
}
```

### Sample Record: Social Media Post

```json
{
  "id": "SM-00001",
  "platform": "twitter",
  "author_type": "financial_analyst",
  "author_handle": "@fed_watcher",
  "text": "Fed holds rates steady at 5.25-5.50%. Markets expected this. #FOMC #FedRate",
  "sentiment": "neutral",
  "sentiment_score": 0.1,
  "topic": "fed_rate_decision",
  "engagement_score": 245,
  "reply_count": 18,
  "repost_count": 67,
  "timestamp": "2023-09-20T18:05:00Z",
  "hashtags": ["#FOMC", "#FedRate", "#MonetaryPolicy"]
}
```

## Project Structure

```
comms-ai-datagen/
├── pyproject.toml          # Package configuration
├── requirements.txt        # Python dependencies
├── config.yaml             # Generation configuration
├── README.md               # This file
├── src/
│   └── datagen/
│       ├── __init__.py
│       ├── main.py             # CLI entrypoint
│       ├── config.py           # Config loading & validation
│       ├── bedrock_client.py   # AWS Bedrock integration
│       ├── utils.py            # Utility functions
│       └── generators/
│           ├── __init__.py
│           ├── base.py               # Abstract base generator
│           ├── inquiries.py          # Incoming communications
│           ├── social_media.py       # Social media posts
│           ├── news_articles.py      # News articles
│           ├── response_templates.py # Response templates
│           └── insight_reports.py    # Insight reports
└── output/                 # Generated JSON files
```

## Estimated Costs

With default settings (1,780 total records, batch_size=10):
- ~178 Bedrock API calls
- Estimated cost: ~$5-15 depending on model (Sonnet is cheaper than Opus)
- Generation time: ~15-30 minutes

## Troubleshooting

| Issue | Solution |
|---|---|
| `AccessDeniedException` | Enable Bedrock model access in AWS Console |
| `ExpiredTokenException` | Re-run `aws configure` or refresh SSO session |
| `ThrottlingException` | Reduce `batch_size` in config or add retry delays |
| `ValidationException` | Check `model_id` is correct and available in your region |
| JSON parse errors | Reduce `batch_size` to get more reliable responses |
