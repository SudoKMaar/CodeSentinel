# Installation Guide

## Prerequisites

### Required
- Python 3.11 or higher
- pip (Python package manager)
- Git

### Optional (for LLM access)
- AWS account with Bedrock access (for Amazon Nova models) - **Recommended for Amazon employees**
- OpenAI API key (alternative)
- Anthropic API key (alternative)
- Ollama installed locally (for free local LLM execution)

## Step-by-Step Installation

### 1. Clone or Download the Project

```bash
git clone <repository-url>
cd code-review-documentation-agent
```

Or if you received the project as a zip file, extract it and navigate to the directory.

### 2. Create a Virtual Environment (Recommended)

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

**Option A: Install from requirements.txt (Recommended for quick start)**
```bash
pip install -r requirements.txt
```

**Option B: Install as editable package**
```bash
pip install -e .
```

**Option C: Install with development dependencies**
```bash
pip install -e ".[dev]"
```

### 4. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:

**For Amazon Bedrock (Recommended for Amazon employees):**
```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
```

**For OpenAI:**
```env
OPENAI_API_KEY=your_openai_key_here
```

**For Anthropic:**
```env
ANTHROPIC_API_KEY=your_anthropic_key_here
```

**For Ollama (Local, Free):**
```env
# No API keys needed - runs locally
# Install Ollama from https://ollama.ai
# Then run: ollama pull llama3.1
```

### 5. Verify Installation

Run the verification script:
```bash
python scripts/verify_setup.py
```

You should see all checks passing with ✓ marks.

### 6. Run Tests

Verify everything is working:
```bash
pytest tests/test_setup.py -v
```

All tests should pass.

## AWS Bedrock Setup (For Amazon Employees)

### Why Amazon Bedrock with Nova?

- **Free tier available** for Amazon employees
- **Amazon Nova Pro**: Excellent for complex code analysis and reasoning
- **Amazon Nova Lite**: Faster, cost-effective for simpler tasks
- **No data retention**: Your code stays private
- **High performance**: Low latency, high throughput

### Setting Up Bedrock Access

1. **Request Bedrock Access:**
   - Go to AWS Console → Amazon Bedrock
   - Request access to Nova models (usually instant approval)

2. **Create IAM Credentials:**
   ```bash
   # Option 1: Use AWS CLI to configure
   aws configure
   
   # Option 2: Create access keys in IAM Console
   # IAM → Users → Your User → Security Credentials → Create Access Key
   ```

3. **Test Bedrock Connection:**
   ```bash
   python -c "import boto3; client = boto3.client('bedrock-runtime', region_name='us-east-1'); print('✓ Bedrock connection successful')"
   ```

4. **Configure Model ID:**
   
   Available Nova models:
   - `amazon.nova-pro-v1:0` - Best for complex analysis (recommended)
   - `amazon.nova-lite-v1:0` - Faster, for simpler tasks
   - `amazon.nova-micro-v1:0` - Fastest, for basic tasks

## Alternative LLM Setup

### OpenAI Setup

1. Get API key from https://platform.openai.com/api-keys
2. Add to `.env`: `OPENAI_API_KEY=sk-...`
3. Cost: ~$0.01-0.03 per 1K tokens

### Anthropic Setup

1. Get API key from https://console.anthropic.com/
2. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
3. Cost: Similar to OpenAI

### Ollama Setup (Free, Local)

1. Install Ollama: https://ollama.ai
2. Pull a model:
   ```bash
   ollama pull llama3.1
   # or
   ollama pull codellama
   # or
   ollama pull mistral
   ```
3. No API keys needed - runs entirely on your machine

## Verification

### Test CLI

```bash
python -m api.cli --help
```

You should see the CLI help menu.

### Test API Import

```bash
python -c "from api.main import app; print('✓ API imports successfully')"
```

### Test Configuration

```bash
python -c "from config.settings import settings; print(f'✓ Using model: {settings.bedrock_model_id}')"
```

## Troubleshooting

### Issue: "ModuleNotFoundError"

**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "AWS credentials not found"

**Solution:** Configure AWS credentials
```bash
aws configure
# Or set environment variables in .env
```

### Issue: "Bedrock access denied"

**Solution:** Request model access
1. Go to AWS Console → Amazon Bedrock
2. Click "Model access" in left sidebar
3. Request access to Nova models

### Issue: "Import errors with tree-sitter"

**Solution:** Tree-sitter language parsers will be installed in task 3
```bash
# This will be handled in the next task
```

### Issue: "Port 8000 already in use"

**Solution:** Change port in `.env`
```env
API_PORT=8001
```

## Next Steps

After successful installation:

1. **Configure analysis settings**: Edit `examples/analysis_config.yaml`
2. **Set up coding standards**: Review `examples/coding_standards_pep8.yaml`
3. **Run your first analysis**: See README.md for usage examples
4. **Explore the API**: Start the server with `uvicorn api.main:app --reload`

## Docker Installation (Alternative)

If you prefer Docker:

```bash
# Build the image
docker-compose build

# Start the service
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## Getting Help

- Check the README.md for usage examples
- Review the examples/ directory for configuration templates
- Run `python scripts/verify_setup.py` to diagnose issues
- Check logs in the logs/ directory (after first run)

## Summary

You should now have:
- ✓ Python environment set up
- ✓ All dependencies installed
- ✓ Environment variables configured
- ✓ LLM access configured (Bedrock/OpenAI/Anthropic/Ollama)
- ✓ Tests passing
- ✓ CLI and API working

Ready to proceed to the next task!
