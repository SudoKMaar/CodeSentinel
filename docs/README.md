# 📚 Documentation Index

## 🚀 Getting Started

### Quick Start
- **[QUICK_START.md](QUICK_START.md)** - Get started in 5 minutes with LLM agent
- **[INSTALLATION.md](INSTALLATION.md)** - Detailed installation instructions
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick command reference

### LLM Setup (NEW!)
- **[../SETUP_AMAZON_NOVA.md](../SETUP_AMAZON_NOVA.md)** - Complete Amazon Nova setup guide
- **[../QUICK_START_NOVA.md](../QUICK_START_NOVA.md)** - 5-minute Nova quick start
- **[../demo_llm_agent.py](../demo_llm_agent.py)** - LLM demo script

---

## 📖 User Guides

### Core Features
- **[CLI_USAGE.md](CLI_USAGE.md)** - Command-line interface guide
- **[SESSION_MANAGEMENT.md](SESSION_MANAGEMENT.md)** - Pause/resume functionality
- **[../examples/README.md](../examples/README.md)** - Configuration examples and templates

### API Documentation
- **[api/README.md](api/README.md)** - REST API reference
- Interactive docs available at: `http://localhost:8000/docs`

---

## 🏗️ Architecture & Design

### Architecture
- **[../README.md](../README.md)** - Main README with architecture overview
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment architecture and options

---

## 🚀 Deployment

### Deployment Options
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
  - Docker deployment
  - Kubernetes deployment
  - Cloud deployments (AWS, GCP, Azure)
  - CI/CD integration

### Quick Deploy
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide with quick start section

---

## 🎓 Capstone Project

### Project Overview
- **[../README.md](../README.md)** - Complete project overview and features
- **[INSTALLATION.md](INSTALLATION.md)** - Installation and setup guide

---

## 🎯 Feature Highlights

### Multi-Agent System
The project implements a sophisticated multi-agent system:

1. **Coordinator Agent** - Orchestrates the entire workflow
2. **Analyzer Agent** - Performs static code analysis
3. **Documenter Agent** - Generates documentation
4. **Reviewer Agent** - Provides rule-based suggestions
5. **LLM Reviewer Agent** ⭐ NEW! - AI-powered intelligent review

### LLM Integration ⭐ NEW!
Real AI-powered code review using:
- Amazon Bedrock (Nova models)
- OpenAI (GPT-4)
- Anthropic (Claude)
- Ollama (local models)

### Key Capabilities
- ✅ Security vulnerability detection
- ✅ Code quality analysis
- ✅ Intelligent fix recommendations
- ✅ Context-aware suggestions
- ✅ Pause/resume for long operations
- ✅ Memory Bank for learning patterns
- ✅ REST API and CLI interfaces
- ✅ Docker and Kubernetes deployment

---

## 📊 Documentation by Topic

### For Developers
- [INSTALLATION.md](INSTALLATION.md) - Setup and installation
- [CLI_USAGE.md](CLI_USAGE.md) - Command-line usage
- [EXAMPLES.md](EXAMPLES.md) - Code examples
- [api/README.md](api/README.md) - API reference

### For DevOps
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [../docker-compose.yml](../docker-compose.yml) - Docker Compose config
- [../k8s-deployment.yaml](../k8s-deployment.yaml) - Kubernetes manifests

### For Project Evaluation
- [../PROJECT_STATUS.md](../PROJECT_STATUS.md) - Complete project overview
- [../CAPSTONE_REQUIREMENTS_ANALYSIS.md](../CAPSTONE_REQUIREMENTS_ANALYSIS.md) - Requirements compliance
- [../README.md](../README.md) - Main project README

---

## 🆘 Troubleshooting

### Common Issues

**LLM not working:**
- Check environment variables: `echo %LLM_PROVIDER%`
- Verify API keys are set
- Run `python demo_llm_agent.py` to test
- See [../SETUP_AMAZON_NOVA.md](../SETUP_AMAZON_NOVA.md) for detailed setup

**Installation issues:**
- See [INSTALLATION.md](INSTALLATION.md)
- Check Python version: `python --version` (requires 3.11+)
- Verify dependencies: `pip list`

**Analysis issues:**
- Check file patterns match your code
- Verify path exists
- See [CLI_USAGE.md](CLI_USAGE.md) for usage examples

---

## 🔗 External Resources

### LLM Providers
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [OpenAI API](https://platform.openai.com/)
- [Anthropic Claude](https://www.anthropic.com/)
- [Ollama](https://ollama.ai/)

### Technologies Used
- [FastAPI](https://fastapi.tiangolo.com/) - REST API framework
- [tree-sitter](https://tree-sitter.github.io/) - Code parsing
- [Hypothesis](https://hypothesis.readthedocs.io/) - Property-based testing
- [Docker](https://www.docker.com/) - Containerization
- [Kubernetes](https://kubernetes.io/) - Orchestration

---

## 📝 Contributing

For development setup and contribution guidelines, see:
- [../README.md](../README.md) - Main README with development section
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Codebase organization

---

## 📞 Support

For questions or issues:
1. Check relevant documentation above
2. Run demos: `python demo_llm_agent.py`
3. Review examples in [EXAMPLES.md](EXAMPLES.md)
4. Check [../PROJECT_STATUS.md](../PROJECT_STATUS.md) for project overview

---

**Last Updated:** 2024 - Includes LLM integration features
