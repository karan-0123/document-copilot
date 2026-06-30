import openai
from app.config import settings

_openai_client = None

def _get_client() -> openai.OpenAI:
    global _openai_client
    if _openai_client is None:
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is not configured in settings.")
        _openai_client = openai.OpenAI(api_key=settings.openai_api_key)
    return _openai_client

def embed_query(query: str) -> list[float]:
    """Generates OpenAI vector embeddings for a query string using the configured model.
    
    Uses a singleton-like client reference to minimize initialization overhead.
    """
    client = _get_client()
    response = client.embeddings.create(
        input=[query],
        model=settings.openai_embedding_model
    )
    return response.data[0].embedding
