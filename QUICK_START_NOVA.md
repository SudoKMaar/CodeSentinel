# ⚡ Quick Start: Amazon Nova in 5 Minutes

## 🎯 Goal
Get Amazon Nova agent working in 5 minutes!

---

## Step 1: Install (30 seconds)
```bash

```

## Step 2: Configure AWS (2 minutes)
```bash
aws configure
```
Enter:
- AWS Access Key ID: `[your-key]`
- AWS Secret Access Key: `[your-secret]`
- Region: `us-east-1`
- Output format: `json`

## Step 3: Enable Model Access (1 minute)
1. Go to: https://console.aws.amazon.com/bedrock/
2. Click "Model access" (left menu)
3. Click "Manage model access"
4. Enable "Amazon Nova Pro"
5. Click "Save changes"

## Step 4: Set Environment (30 seconds)
```bash
set LLM_PROVIDER=bedrock
set BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
set AWS_REGION=us-east-1
```

## Step 5: Test (1 minute)
```bash
python demo_llm_agent.py
```

---

## ✅ Expected Output

```
🤖 LLM-POWERED CODE REVIEW AGENT DEMO
================================================================================

📊 STEP 1: Static Analysis (Pattern Matching)
--------------------------------------------------------------------------------
✓ Found 3 issues using static analysis:
  1. [HIGH] Potential hardcoded secret detected
  2. [MEDIUM] Missing error handling for file operations
  3. [MEDIUM] Function 'get_user' has moderate cyclomatic complexity

🧠 STEP 2: LLM-Powered Analysis (AI Reasoning)
--------------------------------------------------------------------------------
✓ Using bedrock/amazon.nova-pro-v1:0

🔍 Analyzing code with AI...

✨ AI INSIGHTS:
--------------------------------------------------------------------------------

📝 Code Purpose:
This code implements user authentication for a database-backed application...

🚨 Critical Issues in Context:
  • Hardcoded API key exposes credentials
  • SQL injection vulnerability in get_user function
  • Missing error handling could crash application

💡 AI Recommendations:
  1. Immediately rotate the exposed API key
  2. Use parameterized queries to prevent SQL injection
  3. Add try-except blocks for database operations

✅ DEMO COMPLETE
```

---

## 🚨 Troubleshooting

### Error: "Unable to locate credentials"
```bash
# Run AWS configure
aws configure
```

### Error: "Access denied to model"
```bash
# Enable model access in AWS Console
# Go to: Bedrock → Model access → Enable Nova Pro
```

### Error: "Region not supported"
```bash
# Use supported region
set AWS_REGION=us-east-1
```

### Error: "boto3 not found"
```bash
# Install boto3
pip install boto3
```

---

## 🎯 One-Line Setup (Windows)

```bash
setup_nova.bat
```

This script does everything automatically!

---

## 📝 Manual .env Setup

Create `.env` file:
```
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
AWS_REGION=us-east-1
```

---

## 🚀 Now Use It!

### Analyze Your Code
```bash
python -m api.cli analyze --path "C:\QAL\Week 48\Optimus Agent Evaluation Workflow"
```

### Run Demo
```bash
python demo_llm_agent.py
```

### Test LLM Client
```bash
python -c "from tools.llm_client import LLMClient; c = LLMClient(); print(c.generate('Hello'))"
```

---

## 💰 Cost

**Very cheap!**
- Small file: ~$0.001
- Medium file: ~$0.005
- Large project: ~$0.10

---

## ✅ Done!

You now have Amazon Nova agent working! 🎉

**Next:** Run `python demo_llm_agent.py`
