"""
LLM Client for AI-powered code analysis.

Supports multiple LLM providers:
- Amazon Bedrock (Nova models)
- OpenAI (GPT-4)
- Anthropic (Claude)
- Ollama (local models)
"""

import os
from typing import Optional, Dict, Any, List
from enum import Enum
import json


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    BEDROCK = "bedrock"
    NOVA_INTERNAL = "nova_internal"  # Internal Amazon Nova API
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class LLMClient:
    """Client for interacting with various LLM providers."""
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        region: Optional[str] = None,
        api_url: Optional[str] = None
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: LLM provider (bedrock, nova_internal, openai, anthropic, ollama)
            model: Model name/ID
            api_key: API key for the provider
            region: AWS region (for Bedrock)
            api_url: API URL (for internal Nova)
        """
        self.provider = provider or os.getenv("LLM_PROVIDER", "bedrock")
        self.model = model or self._get_default_model()
        self.api_key = api_key or os.getenv("NOVA_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.api_url = api_url or os.getenv("NOVA_API_URL", "https://internal.nova.amazon.com/api")
        
        # Initialize the appropriate client
        self.client = self._initialize_client()
    
    def _get_default_model(self) -> str:
        """Get default model for the provider."""
        defaults = {
            "bedrock": os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"),
            "nova_internal": os.getenv("NOVA_MODEL", "nova-pro"),
            "openai": "gpt-4",
            "anthropic": "claude-3-5-sonnet-20241022",
            "ollama": "llama3.1"
        }
        return defaults.get(self.provider, "gpt-4")
    
    def _initialize_client(self):
        """Initialize the LLM client based on provider."""
        if self.provider == "bedrock":
            return self._init_bedrock()
        elif self.provider == "nova_internal":
            return self._init_nova_internal()
        elif self.provider == "openai":
            return self._init_openai()
        elif self.provider == "anthropic":
            return self._init_anthropic()
        elif self.provider == "ollama":
            return self._init_ollama()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def _init_bedrock(self):
        """Initialize Amazon Bedrock client."""
        try:
            import boto3
            return boto3.client(
                service_name='bedrock-runtime',
                region_name=self.region
            )
        except ImportError:
            raise ImportError("boto3 is required for Bedrock. Install with: pip install boto3")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Bedrock client: {e}")
    
    def _init_nova_internal(self):
        """Initialize Internal Amazon Nova API client."""
        try:
            import httpx
            # Return httpx client configured for internal Nova API
            return httpx.Client(
                base_url=self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                    "Content-Type": "application/json"
                },
                timeout=60.0
            )
        except ImportError:
            raise ImportError("httpx is required for Nova Internal API. Install with: pip install httpx")
    
    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            return OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai is required. Install with: pip install openai")
    
    def _init_anthropic(self):
        """Initialize Anthropic client."""
        try:
            from anthropic import Anthropic
            return Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic is required. Install with: pip install anthropic")
    
    def _init_ollama(self):
        """Initialize Ollama client."""
        try:
            import ollama
            return ollama
        except ImportError:
            raise ImportError("ollama is required. Install with: pip install ollama")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate text using the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated text
        """
        if self.provider == "bedrock":
            return self._generate_bedrock(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "nova_internal":
            return self._generate_nova_internal(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "openai":
            return self._generate_openai(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "anthropic":
            return self._generate_anthropic(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "ollama":
            return self._generate_ollama(prompt, system_prompt, temperature, max_tokens)
    
    def _generate_bedrock(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Amazon Bedrock."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        body = json.dumps({
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        
        response = self.client.invoke_model(
            modelId=self.model,
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    def _generate_nova_internal(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Internal Amazon Nova API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        try:
            response = self.client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Handle different response formats
            if "choices" in result:
                return result["choices"][0]["message"]["content"]
            elif "content" in result:
                return result["content"][0]["text"]
            elif "response" in result:
                return result["response"]
            else:
                return str(result)
        
        except Exception as e:
            raise RuntimeError(f"Nova Internal API error: {e}")
    
    def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using OpenAI."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Anthropic."""
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        response = self.client.messages.create(**kwargs)
        return response.content[0].text
    
    def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Ollama."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": temperature,
                "num_predict": max_tokens
            }
        )
        
        return response['message']['content']
    
    def analyze_code(
        self,
        code: str,
        file_path: str,
        issues: List[Dict[str, Any]],
        language: str
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze code and provide intelligent insights.
        
        Args:
            code: Source code to analyze
            file_path: Path to the file
            issues: List of issues found by static analysis
            language: Programming language
        
        Returns:
            Dictionary with LLM analysis results
        """
        system_prompt = """You are an expert code reviewer and security analyst. 
Analyze the provided code and issues, then provide:
1. Contextual understanding of the code's purpose
2. Severity assessment of issues in context
3. Detailed fix recommendations with code examples
4. Potential side effects of fixes
5. Best practices suggestions

Be concise but thorough. Focus on actionable insights."""
        
        # Prepare the prompt
        issues_summary = "\n".join([
            f"- Line {issue['line_number']}: {issue['description']} (Severity: {issue['severity']})"
            for issue in issues[:5]  # Limit to top 5 issues
        ])
        
        prompt = f"""Analyze this {language} code:

File: {file_path}

Code:
```{language}
{code[:2000]}  # Limit code length
```

Static Analysis Found These Issues:
{issues_summary}

Provide:
1. Code purpose and context
2. Are these issues critical in this context?
3. Detailed fix recommendations with code examples
4. Priority order for fixes
5. Any additional concerns not caught by static analysis

Format your response as JSON with keys: purpose, critical_issues, recommendations, priority, additional_concerns"""
        
        try:
            response = self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more focused analysis
                max_tokens=2000
            )
            
            # Try to parse as JSON
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # If not valid JSON, return as text
                return {
                    "analysis": response,
                    "format": "text"
                }
        
        except Exception as e:
            return {
                "error": str(e),
                "fallback": "LLM analysis unavailable, using static analysis only"
            }
    
    def generate_fix(
        self,
        code: str,
        issue: Dict[str, Any],
        language: str
    ) -> str:
        """
        Generate a code fix using LLM.
        
        Args:
            code: Original code
            issue: Issue to fix
            language: Programming language
        
        Returns:
            Fixed code with explanation
        """
        system_prompt = f"""You are an expert {language} developer. 
Generate a fixed version of the code that addresses the issue.
Provide the complete fixed code and a brief explanation of changes."""
        
        prompt = f"""Fix this {language} code:

Original Code:
```{language}
{code}
```

Issue: {issue['description']}
Line: {issue['line_number']}
Severity: {issue['severity']}

Provide:
1. Fixed code (complete, ready to use)
2. Explanation of changes
3. Why this fix is better

Format as:
FIXED CODE:
```{language}
[fixed code here]
```

EXPLANATION:
[explanation here]"""
        
        try:
            return self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,  # Very low temperature for code generation
                max_tokens=1500
            )
        except Exception as e:
            return f"Error generating fix: {e}"
    
    def prioritize_issues(
        self,
        issues: List[Dict[str, Any]],
        project_context: str
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to intelligently prioritize issues based on project context.
        
        Args:
            issues: List of issues
            project_context: Description of the project
        
        Returns:
            Prioritized list of issues with reasoning
        """
        system_prompt = """You are a senior software architect. 
Prioritize code issues based on project context, business impact, and technical debt.
Consider: security risks, user impact, maintainability, and urgency."""
        
        issues_text = "\n".join([
            f"{i+1}. {issue['description']} (Severity: {issue['severity']}, File: {issue['file_path']})"
            for i, issue in enumerate(issues[:20])  # Limit to 20 issues
        ])
        
        prompt = f"""Project Context: {project_context}

Issues Found:
{issues_text}

Prioritize these issues considering:
1. Security impact
2. User-facing impact
3. Code maintainability
4. Effort to fix

Return a JSON array with prioritized issues, each with:
- issue_number (from the list above)
- priority_score (1-10, 10 being highest)
- reasoning (brief explanation)

Example format:
[
  {{"issue_number": 1, "priority_score": 9, "reasoning": "Critical security vulnerability"}},
  {{"issue_number": 3, "priority_score": 7, "reasoning": "High user impact"}}
]"""
        
        try:
            response = self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=1500
            )
            
            # Parse JSON response
            try:
                priorities = json.loads(response)
                return priorities
            except json.JSONDecodeError:
                return []
        
        except Exception as e:
            return []
