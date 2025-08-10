#!/usr/bin/env python3
"""
Verifier module for generator outputs using the Mistral 7B verifier.

Minimal integration of Constitution v5.4 JSON gate:
- Calls coordinator model (Mistral) to evaluate generated text
- Expects strict JSON response with fields per v5.4
- Provides parsed result and simple safety-floor helpers
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional, Dict, Any

import structlog

from config.models import COORDINATOR_MODEL

logger = structlog.get_logger("verifier")


@dataclass
class VerifierResult:
    confidence: float
    semantic_entropy: float
    action: str  # "pass" | "flag" | "suggest" | "block"
    concern: Optional[str]
    category: str  # "legal" | "financial" | "factual" | "context" | "bias"
    bias_type: Optional[str]
    raw_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence": self.confidence,
            "semantic_entropy": self.semantic_entropy,
            "action": self.action,
            "concern": self.concern,
            "category": self.category,
            "bias_type": self.bias_type,
            "raw_text": self.raw_text,
        }


BUSINESS_VERIFIER_PROMPT = (
    """
You are a safety advisor for a trusted user's personal business AI.
Check the following generated answer for these five essentials:
1. Fabrication (semantic entropy <0.7)
2. Legal risk (actions that could be prosecuted)
3. Financial risk (spend >$500 or irreversible commitments)
4. Missing critical context for decisions
5. Systematic bias (confirmation, financial sector, anchoring)

Return ONLY a strict JSON object (no prose):
{
  "confidence": 0.0-1.0,
  "semantic_entropy": 0.0-1.0,
  "action": "pass|flag|suggest|block",
  "concern": null or "brief issue",
  "category": "legal|financial|factual|context|bias",
  "bias_type": null or "confirmation|financial|anchoring"
}

Safety floors (never adapt): legal ≥0.85, financial ≥0.75.
If unsure, set action to "pass" with confidence ≤0.3.
    """
).strip()


def _build_verifier_input(generated_text: str) -> str:
    return (
        f"{BUSINESS_VERIFIER_PROMPT}\n\n=== GENERATED ANSWER TO REVIEW ===\n{generated_text}\n\nJSON:"
    )


def _parse_verifier_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Best-effort: try to find first JSON object in the text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                return None
        return None


def _coerce_result(raw_text: str, data: Optional[Dict[str, Any]]) -> VerifierResult:
    default = VerifierResult(
        confidence=0.3,
        semantic_entropy=0.7,
        action="pass",
        concern=None,
        category="factual",
        bias_type=None,
        raw_text=raw_text,
    )
    if not data:
        return default
    try:
        return VerifierResult(
            confidence=float(data.get("confidence", 0.3)),
            semantic_entropy=float(data.get("semantic_entropy", 0.7)),
            action=str(data.get("action", "pass")),
            concern=(data.get("concern") if data.get("concern") not in ("", None) else None),
            category=str(data.get("category", "factual")),
            bias_type=(data.get("bias_type") if data.get("bias_type") not in ("", None) else None),
            raw_text=raw_text,
        )
    except Exception:
        return default


def violates_safety_floor(result: VerifierResult) -> bool:
    if result.category == "legal" and result.confidence >= 0.85:
        return True
    if result.category == "financial" and result.confidence >= 0.75:
        return True
    return False


async def run_verifier(ollama_client, generated_text: str, timeout_seconds: float = 20.0) -> VerifierResult:
    """Run verifier using the coordinator (Mistral) and return parsed result."""
    prompt = _build_verifier_input(generated_text)
    try:
        response = await ollama_client.generate_response(
            prompt=prompt,
            model_alias=COORDINATOR_MODEL,
            system_prompt="Return JSON only. No prose.",
            max_tokens=200,
            temperature=0.0,
            timeout=timeout_seconds,
        )
        data = _parse_verifier_json(response.text)
        result = _coerce_result(response.text, data)
        logger.info(
            "verifier_completed",
            action=result.action,
            category=result.category,
            confidence=result.confidence,
        )
        return result
    except Exception as e:
        logger.warning("verifier_failed", error=str(e))
        return _coerce_result("", None)


