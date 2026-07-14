import sys
from pathlib import Path
from google import genai
from app.config import settings

def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Gets Gemini embeddings for a list of texts using the synchronous client."""
    if not settings.gemini_api_key:
        raise ValueError("Gemini API key is not configured in settings.")
        
    client = genai.Client(api_key=settings.gemini_api_key)
    
    import time
    for attempt in range(5):
        try:
            response = client.models.embed_content(
                model=settings.openai_embedding_model,
                contents=texts,
                config=genai.types.EmbedContentConfig(output_dimensionality=settings.openai_embedding_dimensions)
            )
            return [e.values for e in response.embeddings]
        except Exception as e:
            if attempt < 4:
                print(f"Rate limited or error: {e}. Waiting 15 seconds before retry...")
                time.sleep(15)
            else:
                raise e


def verify_dimensions(embedding: list[float]) -> bool:
    """Verifies that the embedding has the correct dimension."""
    if not embedding:
        return False
    return len(embedding) == settings.openai_embedding_dimensions
