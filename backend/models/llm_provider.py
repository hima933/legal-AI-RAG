"""
LLM providers with automatic fallback priority:
1) Ollama
2) Groq
3) OpenAI
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from models.llm_config import config

logger = logging.getLogger(__name__)

_selected_models = {
    "ollama": None,
    "current_provider": "ollama",
}

PROVIDER_PRIORITY = ["ollama", "groq", "openai"]
MAX_PROVIDER_TIMEOUT = 90


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def check_connection(self) -> bool:
        pass


class OllamaProvider(LLMProvider):
    def __init__(self, model: Optional[str] = None):
        import requests

        self.requests = requests
        self.host = config.llm.MODELS["ollama"]["host"]
        self.model = model or _selected_models.get("ollama") or self._auto_select_model()

    def check_connection(self) -> bool:
        try:
            response = self.requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_available_models(self) -> List[Dict]:
        try:
            response = self.requests.get(f"{self.host}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            models = []
            for model_info in data.get("models", []):
                models.append(
                    {
                        "name": model_info.get("name", ""),
                        "size": model_info.get("size", 0),
                        "modified_at": model_info.get("modified_at", ""),
                        "digest": model_info.get("digest", ""),
                    }
                )
            return models
        except Exception as exc:
            logger.warning(f"Failed to fetch Ollama models: {exc}")
            return []

    def _auto_select_model(self) -> str:
        """
        Automatically select best available model
        based on VRAM and installed models.
        """

        available = [m["name"] for m in self.get_available_models()]
        if not available:
            raise RuntimeError("No Ollama models found. Run: ollama pull phi3:mini")

        # Preferred order for low-resource systems
        preference_order = [
            "phi3:latest",
            "phi3:mini",
            "phi3",
            "orca-mini",
            "neural-chat",
            "mistral",
            "llama3",
        ]

        for preferred in preference_order:
            if preferred in available:
                logger.info(f"Auto-selected Ollama model: {preferred}")
                _selected_models["ollama"] = preferred
                return preferred

        # fallback to first installed model
        fallback = available[0]
        logger.info(f"Auto-selected fallback Ollama model: {fallback}")
        _selected_models["ollama"] = fallback
        return fallback

    def generate(self, prompt: str, **kwargs) -> str:
        timeout = min(int(kwargs.get("timeout", MAX_PROVIDER_TIMEOUT)), MAX_PROVIDER_TIMEOUT)
        response = self.requests.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "temperature": kwargs.get("temperature", config.llm.GENERATION_CONFIG["temperature"]),
                "top_p": kwargs.get("top_p", config.llm.GENERATION_CONFIG["top_p"]),
                "num_predict": kwargs.get("max_tokens", config.llm.GENERATION_CONFIG["max_tokens"]),
                "stream": False,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("response", "").strip()
        if not text:
            raise ValueError("Empty response from Ollama")
        return text


class GroqProvider(LLMProvider):
    def __init__(self):
        from groq import Groq

        api_key = (
            os.getenv("GROQ_API_KEY")
            or config.llm.MODELS.get("groq", {}).get("api_key", "")
            or config.llm.MODELS.get("grok", {}).get("api_key", "")
        )
        if not api_key:
            raise ValueError("GROQ_API_KEY is not configured")

        self.client = Groq(api_key=api_key)
        self.model = (
            os.getenv("GROQ_MODEL")
            or config.llm.MODELS.get("groq", {}).get("model")
            or config.llm.MODELS.get("grok", {}).get("model")
            or "llama-3.3-70b-versatile"
        )

    def check_connection(self) -> bool:
        try:
            self.client.models.list()
            return True
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs) -> str:
        timeout = min(int(kwargs.get("timeout", MAX_PROVIDER_TIMEOUT)), MAX_PROVIDER_TIMEOUT)
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": config.llm.LEGAL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=kwargs.get("temperature", config.llm.GENERATION_CONFIG["temperature"]),
            top_p=kwargs.get("top_p", config.llm.GENERATION_CONFIG["top_p"]),
            max_tokens=kwargs.get("max_tokens", config.llm.GENERATION_CONFIG["max_tokens"]),
            timeout=timeout,
        )
        text = completion.choices[0].message.content if completion.choices else ""
        if not text:
            raise ValueError("Empty response from Groq")
        return text


class OpenAIProvider(LLMProvider):
    def __init__(self):
        import openai

        api_key = config.llm.MODELS["openai"]["api_key"]
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        self.client = openai.OpenAI(api_key=api_key)
        self.model = config.llm.MODELS["openai"]["model"]

    def check_connection(self) -> bool:
        try:
            self.client.models.list()
            return True
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs) -> str:
        timeout = min(int(kwargs.get("timeout", MAX_PROVIDER_TIMEOUT)), MAX_PROVIDER_TIMEOUT)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": config.llm.LEGAL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=kwargs.get("temperature", config.llm.GENERATION_CONFIG["temperature"]),
            max_tokens=kwargs.get("max_tokens", config.llm.GENERATION_CONFIG["max_tokens"]),
            timeout=timeout,
        )
        text = response.choices[0].message.content if response.choices else ""
        if not text:
            raise ValueError("Empty response from OpenAI")
        return text


class LLMFactory:
    _providers = {
        "ollama": OllamaProvider,
        "groq": GroqProvider,
        "grok": GroqProvider,
        "openai": OpenAIProvider,
    }

    @staticmethod
    def create_provider(provider_name: Optional[str] = None) -> LLMProvider:
        provider_name = (provider_name or "").lower().strip() or config.llm.PROVIDER
        if provider_name == "grok":
            provider_name = "groq"

        if provider_name not in LLMFactory._providers:
            raise ValueError(f"Unknown provider: {provider_name}")

        provider = LLMFactory._providers[provider_name]()
        return provider


class LLMCache:
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict] = {}
        self.max_size = max_size

    def get(self, key: str) -> Optional[Dict]:
        return self.cache.get(key)

    def set(self, key: str, value: Dict):
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value

    def clear(self):
        self.cache.clear()


_llm_provider: Optional[LLMProvider] = None
_llm_cache: LLMCache = LLMCache()


def _provider_attempt_order() -> List[str]:
    configured = (config.llm.PROVIDER or "ollama").lower().strip()
    if configured == "grok":
        configured = "groq"

    order = []
    if configured in PROVIDER_PRIORITY:
        order.append(configured)

    for p in PROVIDER_PRIORITY:
        if p not in order:
            order.append(p)

    return order


def get_llm_provider() -> LLMProvider:
    global _llm_provider

    if _llm_provider is not None:
        return _llm_provider

    for provider_name in _provider_attempt_order():
        try:
            provider = LLMFactory.create_provider(provider_name)
            if provider.check_connection():
                _llm_provider = provider
                _selected_models["current_provider"] = provider_name
                return _llm_provider
        except Exception as exc:
            logger.warning(f"Provider init failed ({provider_name}): {exc}")

    raise RuntimeError("No LLM provider available (Ollama/Groq/OpenAI)")


def _build_prompt(query: str, context_text: str) -> str:
    return f"""You are an expert legal assistant.

Use ONLY the provided legal context.
If information is missing, state that clearly.
No hallucinations. No repetitive lines.
Keep response between 6 and 10 sentences.

Question:
{query}

Legal Context:
{context_text}

Answer:"""


def generate_legal_answer(query: str, context_text: str, **kwargs) -> Dict:
    max_context_chars = 2400
    context_text = (context_text or "")[:max_context_chars]

    cache_key = f"{query}|{context_text[:180]}"
    cached = _llm_cache.get(cache_key)
    if cached:
        return cached

    prompt = _build_prompt(query, context_text)
    answer = None
    used_provider = None

    for provider_name in _provider_attempt_order():
        try:
            provider = LLMFactory.create_provider(provider_name)
            if not provider.check_connection():
                continue
            answer = provider.generate(prompt, timeout=MAX_PROVIDER_TIMEOUT, **kwargs)
            used_provider = provider_name
            break
        except Exception as exc:
            logger.warning(f"Provider failed ({provider_name}): {exc}")
            continue

    if not answer or len(str(answer).strip()) < 15:
        if context_text:
            answer = "The retrieved context is insufficient to produce a reliable legal answer."
        else:
            answer = "Unable to generate a legal answer because no usable context was found."

    confidence = calculate_confidence(str(answer), context_text, query)
    warning = check_safety(str(answer), query)

    result = {
        "answer": str(answer).strip(),
        "confidence": confidence,
        "has_warning": warning is not None,
        "warning": warning,
        "disclaimer": config.safety.LEGAL_DISCLAIMER if config.safety.ENABLE_DISCLAIMERS else "",
        "provider": used_provider or "none",
    }

    _llm_cache.set(cache_key, result)
    return result


def calculate_confidence(answer: str, context: str, query: str) -> float:
    confidence = 0.5
    if len(answer) < 100:
        confidence -= 0.2

    uncertainty_phrases = [
        "i'm not sure",
        "i don't know",
        "not enough information",
        "cannot determine",
        "unclear",
        "insufficient",
    ]
    if any(phrase in answer.lower() for phrase in uncertainty_phrases):
        confidence -= 0.25

    context_words = set((context or "").lower().split())
    answer_words = (answer or "").lower().split()
    if answer_words:
        matching_words = sum(1 for word in answer_words if word in context_words)
        confidence += (matching_words / len(answer_words)) * 0.3

    return min(1.0, max(0.0, confidence))


def check_safety(answer: str, query: str) -> Optional[str]:
    query_lower = (query or "").lower()
    answer_lower = (answer or "").lower()

    for keyword in config.safety.HARMFUL_QUERY_KEYWORDS:
        if keyword in query_lower:
            return "Warning: This query may involve potentially illegal activity."

    if any(keyword in answer_lower for keyword in ["commit crime", "evade law", "destroy evidence"]):
        return "Warning: This response may contain unsafe legal content."

    return None


def get_available_ollama_models() -> List[Dict]:
    try:
        provider = OllamaProvider()
        return provider.get_available_models()
    except Exception as exc:
        logger.warning(f"Unable to list Ollama models: {exc}")
        return []


def set_selected_model(model_name: str) -> Dict:
    try:
        _selected_models["ollama"] = model_name
        return {
            "status": "success",
            "selected_model": model_name,
            "message": f"Model '{model_name}' selected successfully",
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def get_selected_model() -> str:
    return _selected_models.get("ollama") or config.llm.MODELS["ollama"]["model"]


def get_model_recommendations() -> Dict[str, Dict]:
    return {
        "low_resource": {
            "model": "orca-mini",
            "description": "Small and fast for CPU and low VRAM",
            "vram_required_gb": 4,
            "speed": "Fast",
        },
        "balanced": {
            "model": "mistral",
            "description": "Balanced speed and quality",
            "vram_required_gb": 8,
            "speed": "Moderate",
        },
        "high_quality": {
            "model": "llama-3.3-70b-versatile",
            "description": "Higher quality via Groq/OpenAI when available",
            "vram_required_gb": 0,
            "speed": "Fast (cloud)",
        },
    }
