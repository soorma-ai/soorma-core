"""
LLM Utilities - Dynamic model selection based on available API keys.

Supports multiple LLM providers via LiteLLM:
- OpenAI (OPENAI_API_KEY)
- Anthropic (ANTHROPIC_API_KEY) 
- Google/Gemini (GOOGLE_API_KEY or GEMINI_API_KEY)
- Azure OpenAI (AZURE_API_KEY)
- Together AI (TOGETHER_API_KEY)
- Groq (GROQ_API_KEY)
"""
import os
from typing import Optional


# Default models for each provider (cost-effective options for demos)
PROVIDER_MODELS = {
    "openai": "gpt-4.1-nano",
    "anthropic": "anthropic/claude-3-haiku-20240307",
    "google": "gemini/gemini-2.0-flash",
    "azure": "azure/gpt-4o-mini",
    "together": "together_ai/meta-llama/Llama-3-8b-chat-hf",
    "groq": "groq/llama3-8b-8192",
}


def get_llm_model(preferred_provider: Optional[str] = None) -> str:
    """
    Get the LLM model based on available API keys.
    
    Args:
        preferred_provider: Optional provider to prefer if multiple keys are available.
                          Options: "openai", "anthropic", "google", "azure", "together", "groq"
    
    Returns:
        Model string compatible with LiteLLM.
    
    Raises:
        ValueError: If no API key is found for any supported provider.
    
    Examples:
        >>> model = get_llm_model()
        >>> model = get_llm_model(preferred_provider="anthropic")
    """
    # Check if user has a preferred provider
    if preferred_provider:
        key_found = _check_provider_key(preferred_provider)
        if key_found:
            return PROVIDER_MODELS.get(preferred_provider, PROVIDER_MODELS["openai"])
    
    # Check providers in order of preference
    providers_to_check = [
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("google", ["GOOGLE_API_KEY", "GEMINI_API_KEY"]),
        ("azure", "AZURE_API_KEY"),
        ("together", "TOGETHER_API_KEY"),
        ("groq", "GROQ_API_KEY"),
    ]
    
    for provider, key_names in providers_to_check:
        if isinstance(key_names, list):
            for key_name in key_names:
                if os.environ.get(key_name):
                    return PROVIDER_MODELS[provider]
        else:
            if os.environ.get(key_names):
                return PROVIDER_MODELS[provider]
    
    raise ValueError(
        "No LLM API key found. Please set one of: "
        "OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, GEMINI_API_KEY, "
        "AZURE_API_KEY, TOGETHER_API_KEY, or GROQ_API_KEY"
    )


def _check_provider_key(provider: str) -> bool:
    """Check if the API key for a provider is available."""
    key_map = {
        "openai": ["OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
        "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
        "azure": ["AZURE_API_KEY"],
        "together": ["TOGETHER_API_KEY"],
        "groq": ["GROQ_API_KEY"],
    }
    
    keys = key_map.get(provider, [])
    return any(os.environ.get(k) for k in keys)


def has_any_llm_key() -> bool:
    """Check if any LLM API key is available."""
    try:
        get_llm_model()
        return True
    except ValueError:
        return False
