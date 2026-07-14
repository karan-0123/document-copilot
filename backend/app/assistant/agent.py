"""Thin Groq LLM wrapper for the document assistant.

Uses the Groq Python SDK directly with JSON mode (json_object) instead of
pydantic-ai's structured output, which causes 400 errors with Llama models
on Groq's json_schema mode.

Passages are pre-retrieved by the orchestrator and injected into the user prompt.
The model returns a JSON object with 'answer' and 'citations' fields.
"""
from pathlib import Path
import json
import logging
from uuid import UUID

import httpx
from pydantic import ValidationError

from app.config import settings
from app.assistant.outputs import GroundedAnswer

# Load prompt instructions from markdown file
INSTRUCTIONS_PATH = Path(__file__).resolve().parent / "instructions.md"
system_instruction = INSTRUCTIONS_PATH.read_text(encoding="utf-8")

logger = logging.getLogger("app.assistant.agent")

# Append JSON format instructions to system prompt
SYSTEM_PROMPT = system_instruction + """

### 5. Output Format
You MUST respond with a valid JSON object matching this exact schema:
```json
{
  "answer": "Your response text with inline [1], [2] citation markers...",
  "citations": [
    {
      "chunk_id": "the-exact-uuid-from-the-passage-header",
      "citation_index": 1,
      "excerpt": "exact verbatim quote from the passage text"
    }
  ]
}
```

Rules for the JSON output:
- The `answer` field contains your full narrative response with inline citation markers like [1], [2].
- The `citations` array contains one object per citation used in the answer.
- `chunk_id` MUST be the exact UUID shown in the passage header as "Chunk ID: <uuid>".
- `citation_index` is the 1-based number matching the [N] marker in the answer text.
- `excerpt` MUST be a verbatim substring copied from the passage text. Do not paraphrase.
- When refusing (insufficient evidence), return: {"answer": "I cannot answer this question because the loaded filings do not contain sufficient evidence.", "citations": []}
- Do NOT wrap the JSON in markdown code fences. Return raw JSON only.
"""

_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    """Lazily initialize a shared async HTTP client for Groq API calls."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=60.0)
    return _http_client


async def run_agent(
    augmented_prompt: str,
    message_history: list[dict] | None = None,
) -> GroundedAnswer:
    """Call the Groq API with JSON mode and return a validated GroundedAnswer.

    Args:
        augmented_prompt: The user query with pre-retrieved passages injected.
        message_history: Optional prior conversation messages for multi-turn context.

    Returns:
        A validated GroundedAnswer Pydantic model.

    Raises:
        Exception: On API errors, JSON parse failures, or validation errors.
    """
    client = _get_http_client()

    # Build messages array
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history if present
    if message_history:
        for msg in message_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

    # Add the current augmented prompt
    messages.append({"role": "user", "content": augmented_prompt})

    resp = await client.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openai_llm_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        },
    )

    if resp.status_code == 429:
        raise Exception("429 - Groq rate limit exceeded")
    if resp.status_code == 503:
        raise Exception("503 - Groq service unavailable")
    if resp.status_code != 200:
        raise Exception(f"Groq API error: HTTP {resp.status_code} - {resp.text[:500]}")

    data = resp.json()
    raw_content = data["choices"][0]["message"]["content"]

    # Parse JSON response
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Groq JSON response: {e}\nRaw: {raw_content[:500]}")
        raise Exception(f"Model returned invalid JSON: {e}")

    # Validate with Pydantic — handle flexible citation formats from the model
    answer_text = parsed.get("answer", "")
    raw_citations = parsed.get("citations", [])

    # Normalize citations: the model sometimes returns just indices instead of full objects
    normalized_citations = []
    for c in raw_citations:
        if isinstance(c, dict) and "chunk_id" in c:
            normalized_citations.append(c)
        # Skip malformed citations rather than crash

    try:
        grounded = GroundedAnswer(
            answer=answer_text,
            citations=[
                {
                    "chunk_id": UUID(c["chunk_id"]),
                    "citation_index": c.get("citation_index", i + 1),
                    "excerpt": c.get("excerpt", ""),
                }
                for i, c in enumerate(normalized_citations)
            ]
        )
    except (ValidationError, ValueError) as e:
        logger.warning(f"Citation validation issue (falling back to answer-only): {e}")
        # Fall back to answer without citations rather than failing entirely
        grounded = GroundedAnswer(answer=answer_text, citations=[])

    return grounded
