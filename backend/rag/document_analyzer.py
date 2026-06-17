import json
import logging
import re
from typing import Any, Dict, List

from models.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


def _split_sentences(text: str) -> List[str]:
    payload = re.sub(r"\s+", " ", text or "").strip()
    if not payload:
        return []
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", payload) if item.strip()]


def _extract_sections(full_text: str) -> List[str]:
    pattern = re.compile(r"\b(?:section|article|clause)\s+\d+[A-Za-z\-]*", re.IGNORECASE)
    seen = set()
    items = []
    for match in pattern.findall(full_text or ""):
        normalized = re.sub(r"\s+", " ", match).strip().title()
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(normalized)
    return items[:18]


def _extract_citations(full_text: str) -> List[str]:
    patterns = [
        r"\b(?:AIR|SCC|SCR|CriLJ)\s+\d{4}\s+[A-Za-z0-9()\-]+\b",
        r"\b\d{4}\s+\(\d+\)\s+[A-Z]{2,}\s+\d+\b",
        r"\b(?:section|article)\s+\d+[A-Za-z\-]*\b",
    ]
    citations: List[str] = []
    seen = set()
    for p in patterns:
        for m in re.findall(p, full_text or "", flags=re.IGNORECASE):
            norm = re.sub(r"\s+", " ", m).strip()
            key = norm.lower()
            if key in seen:
                continue
            seen.add(key)
            citations.append(norm)
    return citations[:25]


def _extract_case_title(full_text: str) -> str:
    patterns = [
        r"([A-Z][A-Za-z0-9.,&()\- ]{2,120}\s+v(?:s\.?|\.?)\s+[A-Z][A-Za-z0-9.,&()\- ]{2,120})",
        r"([A-Z][A-Za-z0-9.,&()\- ]{2,120}\s+versus\s+[A-Z][A-Za-z0-9.,&()\- ]{2,120})",
    ]
    for pattern in patterns:
        match = re.search(pattern, full_text or "")
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return ""


def _extract_parties(full_text: str, case_title: str) -> List[str]:
    if case_title:
        parts = re.split(r"\s+v(?:s\.?|\.?)\s+|\s+versus\s+", case_title, flags=re.IGNORECASE)
        cleaned = [re.sub(r"\s+", " ", p).strip(" ,.;:") for p in parts if p and p.strip()]
        if len(cleaned) >= 2:
            return cleaned[:2]

    between_match = re.search(r"\bbetween\s+(.{5,100}?)\s+and\s+(.{5,100}?)(?:[,.;\n]|$)", full_text or "", flags=re.IGNORECASE)
    if between_match:
        return [
            re.sub(r"\s+", " ", between_match.group(1)).strip(" ,.;:"),
            re.sub(r"\s+", " ", between_match.group(2)).strip(" ,.;:"),
        ]
    return []


def _extract_court(full_text: str) -> str:
    patterns = [
        r"(Supreme Court of India)",
        r"(High Court of [A-Za-z ]+)",
        r"(District Court of [A-Za-z ]+)",
        r"(Sessions Court of [A-Za-z ]+)",
        r"(Court of [A-Za-z ]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, full_text or "", flags=re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return ""


def _detect_case_type(full_text: str) -> str:
    text = (full_text or "").lower()
    if "criminal appeal" in text:
        return "Criminal Appeal"
    if "civil appeal" in text:
        return "Civil Appeal"
    if "writ petition" in text:
        return "Writ Petition"
    if "special leave petition" in text:
        return "Special Leave Petition"
    if "appeal" in text:
        return "Appeal"
    if "petition" in text:
        return "Petition"
    if "suit" in text:
        return "Suit"
    if "bail" in text:
        return "Bail Matter"
    return "General Legal Matter"


def _extract_judgement(full_text: str) -> str:
    sentences = _split_sentences(full_text)
    decision_markers = [
        "held",
        "found",
        "ordered",
        "directed",
        "allowed",
        "dismissed",
        "acquitted",
        "convicted",
        "sentenced",
        "set aside",
        "quashed",
    ]
    for sentence in sentences:
        lower = sentence.lower()
        if any(marker in lower for marker in decision_markers):
            return sentence
    return ""


def _extract_key_points(full_text: str) -> List[str]:
    sentences = _split_sentences(full_text)
    markers = [
        "section",
        "article",
        "issue",
        "argument",
        "evidence",
        "alleged",
        "dispute",
        "held",
        "found",
        "court",
    ]
    points = []
    seen = set()
    for sentence in sentences:
        lower = sentence.lower()
        if len(sentence.split()) < 6:
            continue
        if not any(marker in lower for marker in markers):
            continue
        key = lower[:140]
        if key in seen:
            continue
        seen.add(key)
        points.append(sentence)
        if len(points) >= 6:
            break

    if not points:
        points = sentences[:4]
    return points


def _extract_risks(full_text: str) -> List[str]:
    text = (full_text or "").lower()
    mapping = [
        ("forgery", "Potential forgery-related criminal liability"),
        ("fraud", "Potential fraud allegations and financial risk"),
        ("breach", "Possible breach-related civil liability"),
        ("penalty", "Exposure to statutory penalties"),
        ("imprisonment", "Risk of custodial punishment"),
        ("non-compliance", "Regulatory non-compliance risk"),
    ]
    risks = [label for keyword, label in mapping if keyword in text]
    return risks[:5]


def _extract_acts(full_text: str) -> List[str]:
    patterns = [
        r"Indian Penal Code",
        r"Code of Criminal Procedure",
        r"Constitution of India",
        r"Evidence Act",
        r"Contract Act",
        r"Companies Act",
    ]
    seen = set()
    acts = []
    for pattern in patterns:
        if re.search(pattern, full_text or "", flags=re.IGNORECASE):
            key = pattern.lower()
            if key not in seen:
                seen.add(key)
                acts.append(pattern)
    return acts[:8]


def _build_case_structure(full_text: str, key_points: List[str], judgement: str) -> Dict[str, List[str]]:
    sentences = _split_sentences(full_text)
    facts = sentences[:3]
    issues = [s for s in key_points if "issue" in s.lower() or "dispute" in s.lower()][:4]
    arguments = [s for s in key_points if "argument" in s.lower() or "contend" in s.lower()][:4]
    decision = [judgement] if judgement else [s for s in key_points if any(k in s.lower() for k in ["held", "ordered", "dismissed", "allowed"] )][:2]

    return {
        "facts": facts,
        "issues": issues,
        "arguments": arguments,
        "decision": decision,
    }


def _heuristic_summary(full_text: str, key_points: List[str], judgement: str) -> str:
    if judgement and key_points:
        return f"{key_points[0]} {judgement}".strip()

    sentences = _split_sentences(full_text)
    if not sentences:
        return "Document analyzed, but text content was limited."
    return " ".join(sentences[:3])[:650]


def _default_analysis(full_text: str) -> Dict[str, Any]:
    case_title = _extract_case_title(full_text)
    parties = _extract_parties(full_text, case_title)
    court = _extract_court(full_text)
    legal_sections = _extract_sections(full_text)
    key_points = _extract_key_points(full_text)
    judgement = _extract_judgement(full_text)
    risks = _extract_risks(full_text)
    acts = _extract_acts(full_text)
    summary = _heuristic_summary(full_text, key_points, judgement)
    case_type = _detect_case_type(full_text)
    case_structure = _build_case_structure(full_text, key_points, judgement)

    parties_output = parties
    if case_title and not parties_output:
        parties_output = [case_title]

    return {
        "summary": summary,
        "case_type": case_type,
        "parties": parties_output,
        "court": court,
        "legal_sections": legal_sections,
        "judgement": judgement,
        "risks": risks,
        "key_points": key_points,
        "key_clauses": legal_sections[:8],
        "citations": _extract_citations(full_text),
        "case_structure": case_structure,
        "extracted_legal_entities": {
            "parties": parties_output,
            "court": court,
            "acts": acts,
            "sections": legal_sections,
        },
    }


def _safe_parse_json(raw: str) -> Dict[str, Any]:
    payload = (raw or "").strip()
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except Exception:
        pass

    fenced = re.search(r"\{[\s\S]*\}", payload)
    if fenced:
        try:
            return json.loads(fenced.group(0))
        except Exception:
            return {}
    return {}


def _is_weak(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        raw = value.strip().lower()
        return raw in {"", "unknown", "not available", "analysis unavailable", "document analyzed, but structured extraction was limited."}
    if isinstance(value, list):
        return len([item for item in value if str(item).strip()]) == 0
    if isinstance(value, dict):
        return len(value) == 0
    return False


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", (value or "").lower())).strip()


def _overlap_ratio(candidate: str, full_text: str) -> float:
    candidate_tokens = {t for t in _normalize_text(candidate).split() if len(t) >= 4}
    if not candidate_tokens:
        return 0.0
    source_tokens = set(_normalize_text(full_text).split())
    return len(candidate_tokens.intersection(source_tokens)) / len(candidate_tokens)


def _is_grounded_phrase(phrase: str, full_text: str) -> bool:
    candidate = _normalize_text(phrase)
    source = _normalize_text(full_text)
    if len(candidate) < 5:
        return False
    if candidate in source:
        return True
    return _overlap_ratio(phrase, full_text) >= 0.72


def _ground_list_items(items: Any, full_text: str) -> List[str]:
    if not isinstance(items, list):
        return []
    grounded: List[str] = []
    seen = set()
    for item in items:
        payload = str(item).strip()
        if not payload:
            continue
        key = payload.lower()
        if key in seen:
            continue
        if _is_grounded_phrase(payload, full_text):
            grounded.append(payload)
            seen.add(key)
    return grounded[:20]


def _sanitize_case_type(parsed_case_type: Any, base_case_type: str, full_text: str) -> str:
    if not isinstance(parsed_case_type, str) or _is_weak(parsed_case_type):
        return base_case_type

    candidate = parsed_case_type.strip()
    lower = candidate.lower()

    if lower in {
        "criminal appeal",
        "civil appeal",
        "writ petition",
        "special leave petition",
        "appeal",
        "petition",
        "suit",
        "bail matter",
        "general legal matter",
    }:
        return candidate

    if any(token in lower for token in ["appeal", "petition", "suit", "bail", "application", "revision"]):
        if _overlap_ratio(candidate, full_text) >= 0.45:
            return candidate

    return base_case_type


def _grounded_summary(parsed_summary: Any, base_summary: str, full_text: str) -> str:
    if not isinstance(parsed_summary, str) or _is_weak(parsed_summary):
        return base_summary

    candidate = re.sub(r"\s+", " ", parsed_summary).strip()
    if _overlap_ratio(candidate, full_text) < 0.55:
        return base_summary
    return candidate[:900]


def _merge_analysis(base: Dict[str, Any], parsed: Dict[str, Any], full_text: str) -> Dict[str, Any]:
    merged = dict(base)

    # Keep extraction grounded in document text. LLM output can only refine known fields.
    merged["summary"] = _grounded_summary(parsed.get("summary"), base.get("summary", ""), full_text)
    merged["case_type"] = _sanitize_case_type(parsed.get("case_type"), base.get("case_type", "General Legal Matter"), full_text)

    for key in ["parties", "legal_sections", "risks", "key_points", "key_clauses", "citations"]:
        grounded_items = _ground_list_items(parsed.get(key), full_text)
        merged[key] = grounded_items if grounded_items else base.get(key, [])

    for key in ["court", "judgement"]:
        value = parsed.get(key)
        if isinstance(value, str) and value.strip() and _is_grounded_phrase(value, full_text):
            merged[key] = value.strip()
        else:
            merged[key] = base.get(key, "")

    # Rebuild structured entities from grounded fields so values stay consistent.
    acts = base.get("extracted_legal_entities", {}).get("acts", [])
    merged["case_structure"] = _build_case_structure(
        full_text,
        merged.get("key_points", []) or base.get("key_points", []),
        merged.get("judgement", "") or base.get("judgement", ""),
    )
    merged["extracted_legal_entities"] = {
        "parties": merged.get("parties", []),
        "court": merged.get("court", ""),
        "acts": acts,
        "sections": merged.get("legal_sections", []),
    }

    # Sanitize field types.
    for key in ["parties", "legal_sections", "risks", "key_points", "key_clauses", "citations"]:
        if not isinstance(merged.get(key), list):
            merged[key] = base.get(key, [])
        merged[key] = [str(item).strip() for item in merged[key] if str(item).strip()][:20]

    if not isinstance(merged.get("case_structure"), dict):
        merged["case_structure"] = base.get("case_structure", {})
    if not isinstance(merged.get("extracted_legal_entities"), dict):
        merged["extracted_legal_entities"] = base.get("extracted_legal_entities", {})

    for key in ["summary", "case_type", "court", "judgement"]:
        if _is_weak(merged.get(key)):
            merged[key] = base.get(key, "")
        merged[key] = str(merged.get(key, "")).strip()

    if _is_weak(merged.get("summary")):
        merged["summary"] = base.get("summary", "")

    if _is_weak(merged.get("case_type")):
        merged["case_type"] = base.get("case_type", "General Legal Matter")

    return merged


def analyze_document(full_text: str) -> Dict[str, Any]:
    """
    Analyze legal document with robust heuristic fallback and optional LLM refinement.
    """
    base = _default_analysis(full_text)
    preview = (full_text or "")[:14000]

    prompt = f"""Analyze the following legal document and return strict JSON only.
Use only facts present in the document text. Do not invent parties, court names, sections, or outcomes.
If a field is unclear, return an empty string or empty list for that field.

Required JSON schema:
{{
  "summary": "string",
  "case_type": "string",
  "parties": ["string"],
  "court": "string",
  "legal_sections": ["string"],
  "judgement": "string",
  "risks": ["string"],
  "key_points": ["string"],
  "key_clauses": ["string"],
  "citations": ["string"],
  "case_structure": {{
    "facts": ["string"],
    "issues": ["string"],
    "arguments": ["string"],
    "decision": ["string"]
  }},
  "extracted_legal_entities": {{
    "parties": ["string"],
    "court": "string",
    "acts": ["string"],
    "sections": ["string"]
  }}
}}

Document:
{preview}
"""

    try:
        provider = get_llm_provider()
        raw = provider.generate(prompt, max_tokens=950, temperature=0.0, timeout=90)
        parsed = _safe_parse_json(raw)
        if not parsed:
            return base
        return _merge_analysis(base, parsed, full_text)
    except Exception as exc:
        logger.warning(f"Document analysis fallback to heuristics: {exc}")
        return base
