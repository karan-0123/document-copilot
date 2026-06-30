import sys
from pathlib import Path
import openai
from app.config import settings

def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Gets OpenAI embeddings for a list of texts using the synchronous client.
    
    Raises:
        Exception: If the OpenAI API call fails.
    """
    if not settings.openai_api_key:
        raise ValueError("OpenAI API key is not configured in settings.")
        
    client = openai.OpenAI(api_key=settings.openai_api_key)
    
    response = client.embeddings.create(
        input=texts,
        model=settings.openai_embedding_model
    )
    
    # Return the embeddings in the same order as texts
    return [data.embedding for data in response.data]


def verify_dimensions(embedding: list[float]) -> bool:
    """Verifies that the embedding has the correct dimension."""
    if not embedding:
        return False
    return len(embedding) == settings.openai_embedding_dimensions
