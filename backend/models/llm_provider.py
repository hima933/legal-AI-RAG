"""
LLM Provider - Ollama (phi3)
"""

import logging
from typing import Dict, Optional
from models.llm_config import config

logger = logging.getLogger(__name__)


class OllamaProvider:
    """Ollama local LLM provider using phi3 model"""

    def __init__(self):
        import requests
        self.requests = requests
        self.host = config.llm.OLLAMA_HOST
        self.model = config.llm.OLLAMA_MODEL

    def check_connection(self) -> bool:
        try:
            response = self.requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 256) -> str:
        response = self.requests.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "temperature": temperature,
                "num_predict": max_tokens,
                "stream": False,
            },
            timeout=90,
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("response", "").strip()
        if not text:
            raise ValueError("Empty response from Ollama")
        return text


# Single global provider instance
_provider: Optional[OllamaProvider] = None


def get_llm_provider() -> OllamaProvider:
    global _provider
    if _provider is None:
        _provider = OllamaProvider()
    return _provider


def _build_prompt(query: str, context_text: str) -> str:
    return f"""You are an expert legal assistant.

Use ONLY the provided legal context to answer.
If information is missing, say so clearly.
Keep response between 6 and 10 sentences.

Question:
{query}

Legal Context:
{context_text}

Answer:"""


# Simple response cache
_cache: Dict[str, Dict] = {}


def generate_legal_answer(query: str, context_text: str) -> Dict:
    context_text = (context_text or "")[:2400]
    cache_key = f"{query}|{context_text[:180]}"

    if cache_key in _cache:
        return _cache[cache_key]

    prompt = _build_prompt(query, context_text)

    try:
        provider = get_llm_provider()
        answer = provider.generate(prompt)
    except Exception as exc:
        logger.error(f"LLM generation failed: {exc}")
        answer = "Unable to generate a legal answer at this time."

    # Basic confidence calculation
    confidence = 0.5
    uncertainty_phrases = ["i don't know", "not enough information", "unclear", "insufficient"]
    if any(p in answer.lower() for p in uncertainty_phrases):
        confidence -= 0.2
    if len(answer) > 100:
        confidence += 0.2

    result = {
        "answer": answer.strip(),
        "confidence": round(min(1.0, max(0.0, confidence)), 2),
        "disclaimer": config.safety.LEGAL_DISCLAIMER,
    }

    _cache[cache_key] = result
    return result


def check_safety(query: str) -> Optional[str]:
    for keyword in config.safety.HARMFUL_QUERY_KEYWORDS:
        if keyword in query.lower():
            return "Warning: This query may involve potentially illegal activity."
    return None