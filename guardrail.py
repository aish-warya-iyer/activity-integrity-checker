import logging
import os
import re

from enkryptai_sdk import GuardrailsClient

ADHERENCE_THRESHOLD = float(os.environ.get("ADHERENCE_THRESHOLD", "1.0"))

# Enkrypt's `adherence` detector reliably catches numeric/factual contradictions against
# the supplied context, but does not reliably catch speculative narrative layered onto
# otherwise-correct numbers (tested: fabricated intent/cause scored 1.0 even when clearly
# unsupported). This denylist catches the specific failure mode the Lyzr system prompt is
# meant to prevent ("do not speculate about cause or intent") as a second, deterministic layer.
SPECULATIVE_PATTERNS = [
    r"\bdeliberat\w*\b",
    r"\bintenti\w*\b",
    r"\bprobably\b",
    r"\blikely\b",
    r"\bappears? to\b",
    r"\bseems? to\b",
    r"\bcheat\w*\b",
    r"\bshortcut\w*\b",
    r"\bon purpose\b",
    r"\bto (?:skip|avoid|save time|save distance)\b",
    r"\bsuggest\w* (?:that|he|she|they)\b",
    r"\bmay have\b",
    r"\bmight have\b",
]
_SPECULATIVE_RE = re.compile("|".join(SPECULATIVE_PATTERNS), re.IGNORECASE)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = GuardrailsClient(api_key=os.environ["ENKRYPT_API_KEY"])
    return _client


def _template_message(deviation_results):
    lines = []
    for r in deviation_results:
        status = "FLAGGED" if r.get("flagged") else "clean"
        lines.append(
            f"Segment '{r.get('segment_name')}': max deviation {r.get('max_deviation_m')}m "
            f"(threshold {r.get('threshold_m')}m) — {status}."
        )
    return " ".join(lines)


def guard_explanation(explanation_text, deviation_results):
    context = str(deviation_results)
    result = _get_client().adherence(llm_answer=explanation_text, context=context)
    score = result.summary.adherence_score

    speculative_match = _SPECULATIVE_RE.search(explanation_text)

    if score >= ADHERENCE_THRESHOLD and not speculative_match:
        return {"text": explanation_text, "blocked": False, "adherence_score": score}

    reason = "speculative_language" if speculative_match else "low_adherence_score"
    logging.warning(
        "Enkrypt guardrail blocked Lyzr explanation (reason=%s, adherence_score=%s, "
        "matched=%r); falling back to template.",
        reason,
        score,
        speculative_match.group(0) if speculative_match else None,
    )
    return {
        "text": _template_message(deviation_results),
        "blocked": True,
        "adherence_score": score,
        "block_reason": reason,
    }
