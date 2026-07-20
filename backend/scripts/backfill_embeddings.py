"""Backfill missing embeddings for all document chunks using Gemini API.

Processes chunks in batches with rate-limit handling.
"""
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database.models import SourceDocument, DocumentChunk

BATCH_SIZE = 50  # Balanced batch size for stable local CPU/GPU embedding processing

def main():
    engine = create_engine(settings.sqlalchemy_database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Count chunks needing embeddings
    total_missing = db.scalar(
        select(func.count(DocumentChunk.id))
        .where(DocumentChunk.embedding.is_(None))
    )
    db.close()
    print(f"Chunks missing embeddings: {total_missing}", flush=True)

    if total_missing == 0:
        print("All chunks already have embeddings. Nothing to do.", flush=True)
        return

    processed = 0
    
    url = "http://localhost:11434/api/embed"

    while True:
        db = Session()
        try:
            # Fetch only ID and text, prioritizing AAPL first alphabetically
            chunks = db.execute(
                select(DocumentChunk.id, DocumentChunk.text)
                .join(SourceDocument)
                .where(DocumentChunk.embedding.is_(None))
                .order_by(SourceDocument.ticker.asc(), DocumentChunk.id)
                .limit(BATCH_SIZE)
            ).all()
        except Exception as db_read_err:
            print(f"  Database read error (retrying in 5s): {db_read_err}", flush=True)
            try:
                db.rollback()
            except Exception:
                pass
            try:
                db.close()
            except Exception:
                pass
            time.sleep(5.0)
            continue

        try:
            db.close()  # Close session immediately to avoid idle transaction timeouts during HTTP calls
        except Exception as db_close_err:
            print(f"  Warning closing session after read: {db_close_err}", flush=True)

        if not chunks:
            break

        chunk_ids = [c[0] for c in chunks]
        texts = [c[1] for c in chunks]
        
        # Prepare batch payload for Ollama REST API
        payload = {
            "model": "nomic-embed-text",
            "input": texts
        }

        success = False
        embeddings = None
        for attempt in range(3):
            try:
                # Direct HTTP call to Ollama (without holding any DB connection open!)
                resp = httpx.post(url, json=payload, timeout=300.0)
                resp.raise_for_status()
                data = resp.json()
                embeddings = data.get("embeddings", [])
                
                if len(embeddings) != len(chunks):
                    raise ValueError(f"Returned embeddings count {len(embeddings)} mismatch input count {len(chunks)}")
                success = True
                break  # success

            except Exception as e:
                print(f"  Ollama attempt {attempt+1} failed: {e}", flush=True)
                time.sleep(5.0)
                
        if not success or not embeddings:
            print("Failed to embed batch from Ollama. Exiting loop.", flush=True)
            break

        # Save embeddings in a fresh, quick database transaction
        db = Session()
        try:
            for c_id, emb in zip(chunk_ids, embeddings):
                chunk = db.get(DocumentChunk, c_id)
                if chunk:
                    chunk.embedding = emb
            db.commit()
            processed += len(chunks)
            print(f"  Embedded {processed}/{total_missing} chunks...", flush=True)
        except Exception as db_err:
            print(f"  Database save error (retrying in 5s): {db_err}", flush=True)
            try:
                db.rollback()
            except Exception:
                pass
            try:
                db.close()
            except Exception:
                pass
            time.sleep(5.0)
            continue
            
        try:
            db.close()
        except Exception as db_close_err:
            print(f"  Warning closing session after write: {db_close_err}", flush=True)
        
        time.sleep(0.1)  # Minimal sleep to keep CPU/event loop responsive


if __name__ == "__main__":
    main()
