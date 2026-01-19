"""
LLM Client using LiteLLM for WSL Evaluations

Provides unified interface for calling any LLM provider through LiteLLM.
Supports Anthropic, OpenAI, Google, Mistral, Cohere, and many more.

API keys should be set in environment variables:
- ANTHROPIC_API_KEY
- OPENAI_API_KEY
- etc.
"""

from dataclasses import dataclass
from typing import Optional

from .config import ModelConfig


@dataclass
class LLMResponse:
    """Standardized response from any LLM."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    error: Optional[str] = None


class LLMClient:
    """Unified LLM client using LiteLLM."""

    def __init__(self, config: ModelConfig):
        self.config = config
        try:
            import litellm

            self.litellm = litellm
            # Suppress litellm debug output
            litellm.set_verbose = False
        except ImportError:
            raise ImportError("litellm package required: pip install litellm")

    def _get_model_string(self) -> str:
        """
        Get the LiteLLM model string.

        LiteLLM uses provider prefixes for routing:
        - anthropic/claude-sonnet-4-20250514
        - openai/gpt-4o
        - etc.
        """
        provider = self.config.provider.value
        model_id = self.config.model_id

        # LiteLLM uses provider/ prefix for routing
        return f"{provider}/{model_id}"

    def complete(self, system: str, user: str) -> LLMResponse:
        """
        Send a completion request through LiteLLM.

        Args:
            system: System prompt with WSL context
            user: User question to answer

        Returns:
            LLMResponse with content and token usage
        """
        model_string = self._get_model_string()

        try:
            # Build messages based on model capabilities
            if self.config.model_id.startswith("o1"):
                # o1 models handle system prompts differently
                messages = [
                    {"role": "user", "content": f"{system}\n\n---\n\n{user}"}
                ]
            else:
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ]

            # Build completion kwargs
            kwargs = {
                "model": model_string,
                "messages": messages,
            }

            # Add temperature if model supports it
            if not self.config.model_id.startswith("o1"):
                kwargs["temperature"] = self.config.temperature

            # Add max tokens with correct parameter name
            if self.config.model_id.startswith("o1"):
                kwargs["max_completion_tokens"] = self.config.max_tokens
            else:
                kwargs["max_tokens"] = self.config.max_tokens

            response = self.litellm.completion(**kwargs)

            return LLMResponse(
                content=response.choices[0].message.content or "",
                model=response.model or model_string,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
            )

        except Exception as e:
            return LLMResponse(
                content="",
                model=model_string,
                input_tokens=0,
                output_tokens=0,
                error=str(e),
            )

    def complete_with_wsl(
        self,
        wsl_content: str,
        wsl_prompt: str,
        question: str,
    ) -> LLMResponse:
        """
        Complete a request with WSL context.

        Args:
            wsl_content: The WSL document content
            wsl_prompt: The WSL system prompt explaining the format
            question: The question to answer using WSL context

        Returns:
            LLMResponse with the model's answer
        """
        system = f"""{wsl_prompt}

## Your Worldview State

The following WSL document represents your current worldview. Use it to inform your responses.

```wsl
{wsl_content}
```

Answer questions based on the beliefs and understanding encoded in your worldview."""

        return self.complete(system, question)


def create_client(config: ModelConfig) -> LLMClient:
    """Factory function to create client for model."""
    return LLMClient(config)
