"""
Demo script showing LLM-powered code review agent in action.

This demonstrates the difference between:
1. Static analysis (pattern matching)
2. LLM-powered analysis (intelligent reasoning)
"""

from agents.llm_reviewer_agent import LLMReviewerAgent
from agents.analyzer_agent import AnalyzerAgent
from models.data_models import FileAnalysis, CodeMetrics
from tools.code_parser import CodeParserTool

# Sample vulnerable code
VULNERABLE_CODE = '''
import sqlite3
import os

# Configuration
DATABASE = "users.db"
API_KEY = "PLACEHOLDER_API_KEY_HERE"  # Hardcoded secret! (DEMO ONLY - DO NOT USE REAL KEYS)

def get_user(user_id):
    """Get user by ID - VULNERABLE TO SQL INJECTION"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # BAD: String formatting in SQL query
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    
    return cursor.fetchone()

def authenticate_user(username, password):
    """Authenticate user - MISSING ERROR HANDLING"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # No try-catch for database operations!
    query = "SELECT * FROM users WHERE username = ? AND password = ?"
    cursor.execute(query, (username, password))
    
    return cursor.fetchone() is not None
'''

def main():
    print("=" * 80)
    print("🤖 LLM-POWERED CODE REVIEW AGENT DEMO")
    print("=" * 80)
    print()
    
    # Step 1: Static Analysis
    print("📊 STEP 1: Static Analysis (Pattern Matching)")
    print("-" * 80)
    
    analyzer = AnalyzerAgent()
    code_parser = CodeParserTool()
    
    # Analyze the code
    file_analysis = analyzer.analyze_file("demo_vulnerable.py", VULNERABLE_CODE)
    
    if file_analysis:
        print(f"✓ Found {len(file_analysis.issues)} issues using static analysis:")
        for i, issue in enumerate(file_analysis.issues, 1):
            print(f"  {i}. [{issue.severity.upper()}] {issue.description}")
            print(f"     Line {issue.line_number}: {issue.code_snippet[:50]}...")
        print()
    
    # Step 2: LLM-Powered Review
    print("🧠 STEP 2: LLM-Powered Analysis (AI Reasoning)")
    print("-" * 80)
    
    try:
        llm_reviewer = LLMReviewerAgent(enable_llm=True)
        
        if llm_reviewer.enable_llm:
            print(f"✓ Using {llm_reviewer.llm_client.provider}/{llm_reviewer.llm_client.model}")
            print()
            
            # Get LLM review
            print("🔍 Analyzing code with AI...")
            llm_review = llm_reviewer.review_code_with_llm(
                file_analysis=file_analysis,
                source_code=VULNERABLE_CODE,
                project_context="User authentication system for a web application"
            )
            
            if llm_review.get("status") == "success":
                llm_analysis = llm_review.get("llm_analysis", {})
                
                print("\n✨ AI INSIGHTS:")
                print("-" * 80)
                
                # Code purpose
                purpose = llm_analysis.get("purpose", "N/A")
                print(f"\n📝 Code Purpose:\n{purpose}\n")
                
                # Critical issues
                critical = llm_analysis.get("critical_issues", [])
                if critical:
                    print(f"🚨 Critical Issues in Context:")
                    for issue in critical:
                        print(f"  • {issue}")
                    print()
                
                # Recommendations
                recommendations = llm_analysis.get("recommendations", [])
                if recommendations:
                    print(f"💡 AI Recommendations:")
                    if isinstance(recommendations, list):
                        for i, rec in enumerate(recommendations, 1):
                            print(f"  {i}. {rec}")
                    else:
                        print(f"  {recommendations}")
                    print()
                
                # Additional concerns
                additional = llm_analysis.get("additional_concerns", "")
                if additional:
                    print(f"⚠️  Additional Concerns:\n{additional}\n")
                
                # Priority
                priority = llm_analysis.get("priority", [])
                if priority:
                    print(f"📋 Suggested Fix Priority:")
                    for item in priority:
                        print(f"  • {item}")
                    print()
            
            else:
                print(f"❌ LLM review failed: {llm_review.get('message')}")
            
            # Generate intelligent suggestions
            print("\n💬 STEP 3: Generating AI-Powered Suggestions")
            print("-" * 80)
            
            suggestions = llm_reviewer.generate_intelligent_suggestions(
                analysis_results=[file_analysis],
                source_codes={"demo_vulnerable.py": VULNERABLE_CODE},
                project_context="User authentication system"
            )
            
            if suggestions:
                print(f"✓ Generated {len(suggestions)} intelligent suggestions:\n")
                for i, suggestion in enumerate(suggestions[:3], 1):
                    print(f"{i}. {suggestion.title}")
                    print(f"   Priority: {suggestion.priority} | Impact: {suggestion.impact} | Effort: {suggestion.estimated_effort}")
                    print(f"   {suggestion.description[:200]}...")
                    print()
        
        else:
            print("⚠️  LLM is disabled. Using rule-based analysis only.")
            print("   To enable LLM, set environment variables:")
            print("   - For OpenAI: export OPENAI_API_KEY=your-key")
            print("   - For Bedrock: configure AWS credentials")
            print("   - For Ollama: install ollama and run 'ollama pull llama3.1'")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 To use LLM features, you need to:")
        print("   1. Install LLM dependencies: pip install openai anthropic boto3 ollama")
        print("   2. Set up API keys or run local model (Ollama)")
        print("   3. Configure environment variables")
    
    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETE")
    print("=" * 80)
    print("\n📚 Key Differences:")
    print("   • Static Analysis: Fast, rule-based, finds known patterns")
    print("   • LLM Analysis: Intelligent, context-aware, provides reasoning")
    print("   • Combined: Best of both worlds - speed + intelligence")
    print()

if __name__ == "__main__":
    main()
