# Quick Reference Guide

A quick reference for common tasks and commands with the Code Review & Documentation Agent.

## Table of Contents

- [Installation](#installation)
- [Basic Commands](#basic-commands)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [CI/CD Integration](#cicd-integration)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Installation

```bash
# Install
pip install code-review-documentation-agent

# Verify
code-review --help
```

## Basic Commands

### Analyze Code

```bash
# Basic analysis
code-review analyze --path ./src

# With config file
code-review analyze --path ./src --config config.yaml

# Quick analysis
code-review analyze --path ./src --depth quick

# Deep analysis
code-review analyze --path ./src --depth deep

# Custom output directory
code-review analyze --path ./src --output ./reports
```

### Session Management

```bash
# Check status
code-review status <session-id>

# Pause analysis
code-review pause <session-id>

# Resume analysis
code-review resume <session-id>

# View history
code-review history

# Filter history
code-review history --status-filter completed
```

### File Filtering

```bash
# Include specific patterns
code-review analyze --path ./src \
  --file-patterns "*.py" \
  --file-patterns "*.js"

# Exclude patterns
code-review analyze --path ./src \
  --exclude-patterns "tests/**" \
  --exclude-patterns "node_modules/**"
```

### Project Tracking

```bash
# Track project patterns
code-review analyze --path ./src --project-id my-project
```

## Configuration

### Minimal Config (YAML)

```yaml
target_path: ./src
analysis_depth: standard
```

### Standard Config (YAML)

```yaml
target_path: ./src
file_patterns:
  - "*.py"
  - "*.js"
exclude_patterns:
  - "node_modules/**"
  - "venv/**"
analysis_depth: standard
coding_standards:
  max_complexity: 10
  max_line_length: 100
```

### Minimal Config (JSON)

```json
{
  "target_path": "./src",
  "analysis_depth": "standard"
}
```

### Environment Variables

```bash
# AWS Bedrock
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=amazon.nova-pro-v1:0

# OpenAI
export OPENAI_API_KEY=your-key
export LLM_PROVIDER=openai

# Ollama (local)
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3.1

# General
export LOG_LEVEL=INFO
export MAX_PARALLEL_FILES=4
```

## API Endpoints

### Start Server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Trigger Analysis

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"codebase_path": "./src"}'
```

### Check Status

```bash
curl http://localhost:8000/status/<session-id>
```

### Get Results

```bash
curl http://localhost:8000/results/<session-id>
```

### Pause/Resume

```bash
# Pause
curl -X POST http://localhost:8000/pause/<session-id>

# Resume
curl -X POST http://localhost:8000/resume/<session-id>
```

### Get History

```bash
curl http://localhost:8000/history
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Code Review
  run: |
    pip install code-review-documentation-agent
    code-review analyze --path ./src --output ./reports
```

### GitLab CI

```yaml
code-review:
  script:
    - pip install code-review-documentation-agent
    - code-review analyze --path ./src --output ./reports
  artifacts:
    paths:
      - reports/
```

### Jenkins

```groovy
sh 'pip install code-review-documentation-agent'
sh 'code-review analyze --path ./src --output ./reports'
```

### PR Mode

```bash
code-review analyze \
  --path . \
  --pr-mode \
  --base-ref origin/main \
  --head-ref HEAD \
  --fail-on-critical
```

## Common Patterns

### Pattern 1: Quick Development Check

```bash
code-review analyze \
  --path ./src \
  --depth quick \
  --file-patterns "*.py"
```

### Pattern 2: Pre-Commit Analysis

```bash
code-review analyze \
  --path ./src \
  --depth standard \
  --project-id my-project \
  --fail-on-critical
```

### Pattern 3: Release Quality Check

```bash
code-review analyze \
  --path ./src \
  --depth deep \
  --config release-config.yaml \
  --output ./release-reports
```

### Pattern 4: Continuous Monitoring

```bash
# Run periodically with project tracking
code-review analyze \
  --path ./src \
  --project-id my-project \
  --output ./reports/$(date +%Y%m%d)
```

### Pattern 5: API Integration

```python
import requests

# Start analysis
response = requests.post(
    "http://localhost:8000/analyze",
    json={"codebase_path": "./src"}
)
session_id = response.json()["session_id"]

# Poll for completion
import time
while True:
    status = requests.get(f"http://localhost:8000/status/{session_id}")
    if status.json()["status"] == "completed":
        break
    time.sleep(5)

# Get results
results = requests.get(f"http://localhost:8000/results/{session_id}")
print(results.json())
```

## Troubleshooting

### Command Not Found

```bash
# Reinstall
pip install -e .

# Or use module syntax
python -m api.cli --help
```

### AWS Authentication

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_REGION=us-east-1
```

### No Files Found

```bash
# Check patterns with verbose output
code-review analyze --path ./src --verbose
```

### Memory Issues

```bash
# Reduce parallelism
export MAX_PARALLEL_FILES=2
code-review analyze --path ./src --no-parallel
```

### Session Not Found

```bash
# List available sessions
code-review history
```

## Keyboard Shortcuts

When using interactive mode:

- `Ctrl+C`: Cancel current operation
- `Ctrl+D`: Exit CLI

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Critical issues found (with --fail-on-critical)
- `3`: High severity issues found (with --fail-on-high)

## File Locations

- **Config**: `.code-review-config.yaml` or `analysis_config.yaml`
- **Sessions**: `.sessions/`
- **Memory Bank**: `memory_bank.db`
- **Logs**: `logs/` (if configured)
- **Reports**: `./code-review-reports/` (default)

## Useful Links

- [Full Documentation](README.md)
- [CLI Guide](CLI_USAGE.md)
- [API Reference](api/README.md)
- [Examples](EXAMPLES.md)
- [Configuration Templates](../examples/)

## Tips

1. **Use project IDs** for consistent pattern tracking
2. **Enable PR mode** in CI/CD to analyze only changed files
3. **Configure webhooks** for async notifications
4. **Use appropriate depth** (quick for dev, deep for releases)
5. **Track quality trends** with regular analyses
6. **Customize standards** with config files
7. **Cache results** for faster re-analysis
8. **Monitor sessions** with status command
9. **Review history** to track improvements
10. **Read logs** for debugging issues

## Quick Wins

### Improve Code Quality

```bash
# 1. Run analysis
code-review analyze --path ./src --project-id my-project

# 2. Review suggestions in report
cat ./code-review-reports/suggestions.md

# 3. Implement high-priority fixes

# 4. Re-run to verify improvements
code-review analyze --path ./src --project-id my-project
```

### Set Up CI/CD

```bash
# 1. Add config file to repo
cp examples/analysis_config.yaml .code-review-config.yaml

# 2. Add CI/CD workflow
cp examples/github_actions_workflow.yml .github/workflows/code-review.yml

# 3. Configure secrets (AWS keys, etc.)

# 4. Push and watch it run!
```

### Track Progress

```bash
# Run weekly analysis
code-review analyze --path ./src --project-id my-project

# View trends
code-review history --status-filter completed --verbose

# Compare quality scores over time
```

---

**Need more help?** Check the [full documentation](README.md) or run `code-review --help`.
