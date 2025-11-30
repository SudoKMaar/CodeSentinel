# 📁 Examples Directory

This directory contains example configurations, demo scripts, and CI/CD integration examples.

---

## 📝 Configuration Examples

### Analysis Configuration
- **`analysis_config.yaml`** - Basic analysis configuration
- **`analysis_config_example.yaml`** - Detailed configuration example
- **`comprehensive_config.yaml`** - Complete configuration with all options

### CLI Configuration
- **`cli_config_example.json`** - JSON format CLI config
- **`cli_config_example.yaml`** - YAML format CLI config

### Coding Standards Templates
- **`coding_standards_pep8.yaml`** - Python PEP 8 standards
- **`coding_standards_google.yaml`** - Google Python style guide
- **`coding_standards_airbnb.yaml`** - Airbnb JavaScript style guide

**Usage:**
```bash
python -m api.cli analyze --path ./src --config examples/coding_standards_pep8.yaml
```

---

## 🎬 Demo Scripts

### Agent Demos
- **`analyzer_agent_demo.py`** - Analyzer agent demonstration
- **`coordinator_agent_demo.py`** - Coordinator agent demonstration
- **`documenter_agent_demo.py`** - Documenter agent demonstration
- **`reviewer_agent_demo.py`** - Reviewer agent demonstration

### Feature Demos
- **`memory_bank_demo.py`** - Memory Bank usage example
- **`session_manager_demo.py`** - Session management example

**Usage:**
```bash
python examples/analyzer_agent_demo.py
```

---

## 🔄 CI/CD Integration Examples

### GitHub Actions
- **`github_actions_workflow.yml`** - Complete GitHub Actions workflow
  - Runs on pull requests
  - Analyzes changed files
  - Uploads reports as artifacts
  - Fails on critical issues

**Setup:**
```bash
# Copy to your repo
cp examples/github_actions_workflow.yml .github/workflows/code-review.yml

# Add secrets in GitHub:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - OPENAI_API_KEY (if using OpenAI)
```

### GitLab CI
- **`gitlab_ci_workflow.yml`** - Complete GitLab CI configuration
  - Runs on merge requests
  - PR mode analysis
  - Webhook notifications
  - SARIF output

**Setup:**
```bash
# Copy to your repo
cp examples/gitlab_ci_workflow.yml .gitlab-ci.yml

# Add variables in GitLab:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
```

---

## 🚀 Quick Start Examples

### 1. Basic Analysis
```bash
python -m api.cli analyze \
  --path ./src \
  --config examples/analysis_config.yaml
```

### 2. With Coding Standards
```bash
python -m api.cli analyze \
  --path ./src \
  --config examples/coding_standards_pep8.yaml \
  --depth deep
```

### 3. PR Mode (CI/CD)
```bash
python -m api.cli analyze \
  --path . \
  --pr-mode \
  --base-ref origin/main \
  --head-ref HEAD \
  --fail-on-critical
```

---

## 📚 Related Documentation

- [../docs/CLI_USAGE.md](../docs/CLI_USAGE.md) - Complete CLI guide
- [../docs/EXAMPLES.md](../docs/EXAMPLES.md) - More usage examples
- [../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) - Deployment guide
- [../README.md](../README.md) - Main project README

---

## 💡 Tips

### Customize Configurations
1. Copy an example config
2. Modify for your project
3. Save as `my-config.yaml`
4. Use with `--config my-config.yaml`

### Test Configurations
```bash
# Test with demo code
python -m api.cli analyze \
  --path ./demo_vulnerable_code.py \
  --config examples/coding_standards_pep8.yaml
```

### CI/CD Integration
1. Choose your CI platform (GitHub Actions or GitLab CI)
2. Copy the example workflow
3. Add required secrets/variables
4. Customize for your needs
5. Commit and push

---

**All examples are ready to use!** 🚀
