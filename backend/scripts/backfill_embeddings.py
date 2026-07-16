"""Backfill missing embeddings for all document chunks using Gemini API.

Processes chunks in batches with rate-limit handling.
"""
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from google import genai
from app.config import settings
from app.database.models import SourceDocument, DocumentChunk

BATCH_SIZE = 100  # Gemini supports up to 100 texts per embed_content call

def main():
    engine = create_engine(settings.sqlalchemy_database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    client = genai.Client(api_key=settings.gemini_api_key)

    # Count chunks needing embeddings
    total_missing = db.scalar(
        select(func.count(DocumentChunk.id))
        .where(DocumentChunk.embedding.is_(None))
    )
    print(f"Chunks missing embeddings: {total_missing}")

    if total_missing == 0:
        print("All chunks already have embeddings. Nothing to do.")
        return

    processed = 0
    failed = 0

    while True:
        # Fetch a batch of chunks without embeddings
        chunks = db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.embedding.is_(None))
            .order_by(DocumentChunk.id)
            .limit(BATCH_SIZE)
        ).scalars().all()

        if not chunks:
            break

        texts = [c.text for c in chunks]

        for attempt in range(5):
            try:
                response = client.models.embed_content(
                    model=settings.openai_embedding_model,
                    contents=texts,
                    config=genai.types.EmbedContentConfig(
                        output_dimensionality=settings.openai_embedding_dimensions
                    ),
                )
                embeddings = [e.values for e in response.embeddings]

                for chunk, emb in zip(chunks, embeddings):
                    chunk.embedding = emb

                db.commit()
                processed += len(chunks)
                print(f"  Embedded {processed}/{total_missing} chunks...")
                break  # success

            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    wait = 15 * (attempt + 1)
                    print(f"  Rate limited. Waiting {wait}s (attempt {attempt+1}/5)...")
                    time.sleep(wait)
                else:
                    print(f"  ERROR: {e}")
                    failed += len(chunks)
                    # Mark these as processed to avoid infinite loop
                    # by moving past them with a different approach
                    break
        else:
            print(f"  Failed after 5 retries for batch. Skipping {len(chunks)} chunks.")
            failed += len(chunks)
            # Skip these chunks by just moving on
            break

    print(f"\nDone! Processed: {processed}, Failed: {failed}")
    db.close()


if __name__ == "__main__":
    main()
