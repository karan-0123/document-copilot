import httpx
import logging

logger = logging.getLogger("app.retrieval.embeddings")

def embed_query(query: str) -> list[float]:
    """Generates local Ollama vector embeddings for a query string using nomic-embed-text."""
    url = "http://localhost:11434/api/embeddings"
    payload = {
        "model": "nomic-embed-text",
        "prompt": query
    }
    
    resp = httpx.post(url, json=payload, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    return data["embedding"]
