import os
from google import genai
from app.config import settings

_gemini_client = None

def _get_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        if not settings.gemini_api_key:
            raise ValueError("Gemini API key is not configured in settings.")
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client

import time
import logging

logger = logging.getLogger("app.retrieval.embeddings")

def embed_query(query: str) -> list[float]:
    """Generates Gemini vector embeddings for a query string using the configured model.
    
    Uses a singleton-like client reference to minimize initialization overhead.
    """
    client = _get_client()
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.models.embed_content(
                model=settings.openai_embedding_model,
                contents=query,
                config=genai.types.EmbedContentConfig(output_dimensionality=settings.openai_embedding_dimensions)
            )
            return response.embeddings[0].values
        except Exception as e:
            err_str = str(e)
            is_429 = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
            if is_429 and attempt < max_retries - 1:
                sleep_secs = 2 ** attempt + 2
                logger.warning(
                    f"Gemini embedding API rate limited (HTTP 429). "
                    f"Retrying in {sleep_secs}s (attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(sleep_secs)
                continue
            raise e
