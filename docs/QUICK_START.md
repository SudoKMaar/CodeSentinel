# Quick Start Guide

## 🚀 5-Minute Setup with LLM Agent

### 1. Install Dependencies
```bash
pip install -r requirements.txt

# Install LLM provider (choose one):
pip install openai      # For OpenAI GPT-4
pip install anthropic   # For Anthropic Claude
pip install ollama      # For local Ollama
# boto3 already included for Amazon Bedrock
```

### 2. Configure LLM Provider

**Option A: Amazon Bedrock (Recommended)**
```bash
# Configure AWS credentials
aws configure

# Set environment variables
set LLM_PROVIDER=bedrock
set BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
set AWS_REGION=us-east-1

# Or run automated setup
setup_nova.bat
```

**Option B: OpenAI**
```bash
set OPENAI_API_KEY=your-api-key
set LLM_PROVIDER=openai
```

**Option C: Ollama (Free, Local)**
```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.1
set LLM_PROVIDER=ollama
```

### 3. Test LLM Integration
```bash
# Run LLM demo
python demo_llm_agent.py
```

### 3. Verify Setup
```bash
python scripts/verify_setup.py
```

### 4. Test Installation
```bash
pytest tests/test_setup.py -v
```

## Usage Examples

### CLI Usage

**Analyze a codebase:**
```bash
python -m api.cli analyze --path ./src --config examples/analysis_config.yaml
```

**Check status:**
```bash
python -m api.cli status <session-id>
```

**Pause/Resume:**
```bash
python -m api.cli pause <session-id>
python -m api.cli resume <session-id>
```

### API Usage

**Start the server:**
```bash
python -m uvicorn api.main:app --reload
```

**Test the API:**
```bash
# Health check
curl http://localhost:8000/health

# Trigger analysis
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"codebase_path": "./src"}'
```

## Configuration

### Minimal .env
```env
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
LOG_LEVEL=INFO
```

### Analysis Config
See `examples/analysis_config.yaml` for a complete example.

## What's Next?

The project structure is now set up. Subsequent tasks will implement:
- Task 2: Core data models
- Task 3: MCP tools for file system and parsing
- Task 4: Memory Bank for long-term storage
- Task 5: Session state management
- Tasks 6-8: The three specialized agents
- Task 9: Coordinator agent
- Tasks 10-19: Additional features and testing

## Current Status

✅ **Task 1 Complete**: Project structure and dependencies set up
- Directory structure created
- Dependencies configured
- CLI and API scaffolding in place
- Configuration management ready
- Docker support added
- Documentation created

🔄 **Next Task**: Implement core data models (Task 2)
