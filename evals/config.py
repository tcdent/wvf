"""
LLM Configuration for WSL Evaluations

Defines supported models and their configurations.
Expects API keys in environment variables:
- ANTHROPIC_API_KEY
- OPENAI_API_KEY
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Provider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class ModelConfig:
    """Configuration for a specific LLM model."""

    provider: Provider
    model_id: str
    display_name: str
    max_tokens: int = 1024
    temperature: float = 0.0  # Deterministic for evals

    @property
    def env_key(self) -> str:
        """Environment variable name for API key."""
        return f"{self.provider.value.upper()}_API_KEY"


# Anthropic Models
CLAUDE_SONNET = ModelConfig(
    provider=Provider.ANTHROPIC,
    model_id="claude-sonnet-4-20250514",
    display_name="Claude Sonnet 4",
)

CLAUDE_OPUS = ModelConfig(
    provider=Provider.ANTHROPIC,
    model_id="claude-opus-4-5-20251101",
    display_name="Claude Opus 4.5",
)

CLAUDE_HAIKU = ModelConfig(
    provider=Provider.ANTHROPIC,
    model_id="claude-haiku-4-5-20251001",
    display_name="Claude Haiku 4.5",
)

# OpenAI Models
# Note: GPT-5 family only supports temperature=1
GPT_5_2 = ModelConfig(
    provider=Provider.OPENAI,
    model_id="gpt-5.2",
    display_name="GPT-5.2",
    temperature=1.0,
)

GPT_5_MINI = ModelConfig(
    provider=Provider.OPENAI,
    model_id="gpt-5-mini",
    display_name="GPT-5 Mini",
    temperature=1.0,
)


# All models available for evaluation
ALL_MODELS = [
    CLAUDE_SONNET,
    CLAUDE_OPUS,
    CLAUDE_HAIKU,
    GPT_5_2,
    GPT_5_MINI,
]

# Default models for quick runs
DEFAULT_MODELS = [
    CLAUDE_SONNET,
    GPT_5_2,
]

# Model lookup by name
MODEL_REGISTRY = {
    "claude-sonnet": CLAUDE_SONNET,
    "claude-opus": CLAUDE_OPUS,
    "claude-haiku": CLAUDE_HAIKU,
    "gpt-5.2": GPT_5_2,
    "gpt-5-mini": GPT_5_MINI,
}


def get_model(name: str) -> Optional[ModelConfig]:
    """Get model config by name."""
    return MODEL_REGISTRY.get(name.lower())


def get_models_by_provider(provider: Provider) -> list[ModelConfig]:
    """Get all models for a given provider."""
    return [m for m in ALL_MODELS if m.provider == provider]
