from abc import ABC, abstractmethod
import google.generativeai as genai
import anthropic
import os
from typing import Optional

class LLMProvider(ABC):
    @abstractmethod
    def generate_content(self, prompt: str) -> str:
        """Generate content using the LLM provider."""
        pass

class GeminiProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

    def generate_content(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text

class ClaudeProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv('CLAUDE_API_KEY')
        if not api_key:
            raise ValueError("CLAUDE_API_KEY environment variable is not set")
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_content(self, prompt: str) -> str:
        response = self.client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text

def get_llm_provider() -> LLMProvider:
    """Factory function to get the appropriate LLM provider based on environment variable."""
    provider_choice = os.getenv('LLM_CHOICE', 'gemini').lower()
    
    if provider_choice == 'gemini':
        return GeminiProvider()
    elif provider_choice == 'claude':
        return ClaudeProvider()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_choice}") 