import json
import logging
import re
from typing import Any, Dict, List

from models.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


def _extract_json_block(raw_text: str) -> Dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Empty analyzer response")

    # Attempt 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Regex extraction of code block (Markdown)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Attempt 3: Regex extraction of outermost braces
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
            
    raise ValueError("No valid JSON object found in analyzer response")


def _sanitize_list(value: Any, max_items: int = 6) -> List[str]:
    if not isinstance(value, list):
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []
    clean = [str(item).strip() for item in value if item and isinstance(item, (str, int, float))]
    return clean[:max_items]


def _sanitize_analysis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    risk = str(analysis.get("risk_level", "")).upper().strip()
    
    # Fuzzy match risk level
    if "HIGH" in risk: risk = "HIGH"
    elif "MEDIUM" in risk: risk = "MEDIUM"
    elif "LOW" in risk: risk = "LOW"
    else:
        risk = "UNKNOWN"

    return {
        "case_type": str(analysis.get("case_type", "General Legal Query")).strip(),
        "legal_issues": _sanitize_list(analysis.get("legal_issues", [])),
        "key_arguments": _sanitize_list(analysis.get("key_arguments", [])),
        "risk_level": risk,
        "recommended_action": str(analysis.get("recommended_action", "Consult a qualified attorney.")).strip(),
    }


def generate_legal_analysis(question: str, answer: str, context_chunks: list) -> dict:
    context_text = " ".join(
        str(chunk.get("text", "")).strip()
        for chunk in (context_chunks or [])
        if isinstance(chunk, dict)
    )
    context_preview = context_text[:4000]

    prompt = f"""You are a legal analysis extraction engine.
Return ONLY valid JSON with this exact schema:
{{
  "case_type": "string",
  "legal_issues": ["string"],
  "key_arguments": ["string"],
  "risk_level": "LOW|MEDIUM|HIGH|UNKNOWN",
  "recommended_action": "string"
}}

Question:
{question}

Answer:
{answer}

Context:
{context_preview}
"""

    try:
        provider = get_llm_provider()
        raw = provider.generate(prompt, temperature=0.1, max_tokens=400)
        parsed = _extract_json_block(raw)
    except Exception as e:
        logger.warning(f"Legal analyzer failed: {e}")
        return {
            "files_processed": [
                {
                    "name": "query_context",
                    "analysis": {
                        "case_type": "Unknown",
                        "legal_issues": [],
                        "key_arguments": [],
                        "risk_level": "UNKNOWN",
                        "recommended_action": "Analysis unavailable",
                    },
                }
            ]
        }

    if not isinstance(parsed, dict):
        raise ValueError("Analyzer did not return an object")

    analysis = _sanitize_analysis(parsed)

    result = {
        "files_processed": [
            {
                "name": "query_context",
                "analysis": analysis,
            }
        ]
    }

    logger.debug("Structured legal analysis generated successfully")
    return result