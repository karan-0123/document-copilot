import sys
import uuid
import argparse
import json
from datetime import date
from pathlib import Path
import tiktoken

# Add backend directory to sys.path to allow importing app modules
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_DIR.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from app.database.models import SourceDocument, DocumentChunk

from ingest.chunking import parse_markdown_to_docling, get_chunker, chunk_document
from ingest.embeddings import get_embeddings_batch

MARKDOWN_DIR = Path(__file__).resolve().parents[2] / "data" / "markdown"

COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}

# Database engine and session local configuration
engine = create_engine(settings.sqlalchemy_database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def fiscal_year_from_report_date(report_date: str | None) -> int | None:
    if not report_date:
        return None
    return int(report_date[:4])


def ingest_document_with_docling(
    entry: dict,
    chunker_type: str,
    max_tokens: int,
    skip_embeddings: bool,
    force: bool,
    test_run: bool,
    db: Session,
    encoding
) -> bool:
    """Ingests a single SEC 10-K document using Docling chunking and OpenAI embeddings.
    
    Returns:
        bool: True if test_run was triggered and completed, False otherwise.
    """
    report_date = entry.get("report_date")
    filing_date = entry.get("filing_date")
    year = (report_date or filing_date or "0000")[:4]
    
    html_name = Path(entry["local_path"]).name
    md_name = Path(html_name).with_suffix(".md").name
    md_file_path = MARKDOWN_DIR / year / md_name
    
    if not md_file_path.exists():
        print(f"Warning: Markdown file not found at {md_file_path}. Skipping.")
        return False
        
    print(f"Reading markdown for {entry['ticker']} ({year}) from {md_file_path}...")
    markdown_content = md_file_path.read_text(encoding="utf-8")
    accession_number = entry["accession_number"]
    
    existing = db.query(SourceDocument).filter(SourceDocument.accession_number == accession_number).first()
    if existing:
        if not force:
            print(f"Document {accession_number} already exists in DB. Skipping (use --force to overwrite).")
            return False
        else:
            print(f"Document {accession_number} already exists. Overwriting (deleting existing row and chunks)...")
            db.query(DocumentChunk).filter(DocumentChunk.document_id == existing.id).delete()
            db.delete(existing)
            db.commit()
            
    print(f"Parsing {entry['ticker']} ({year}) with Docling structure parser...")
    doc = parse_markdown_to_docling(md_file_path)
    
    print(f"Chunking with {chunker_type} chunker (max_tokens={max_tokens})...")
    chunker = get_chunker(chunker_type, max_tokens)
    chunks = chunk_document(doc, chunker)
    
    if not chunks:
        print(f"Warning: No chunks generated for {entry['ticker']} ({year}). Skipping.")
        return False
        
    # Populate token count using tiktoken
    for idx, c in enumerate(chunks):
        c["token_count"] = len(encoding.encode(c["text"]))
        
    print(f"Total chunks generated: {len(chunks)}")
    
    if test_run:
        print("\n--- TEST RUN MODE ACTIVE ---")
        print("Limiting execution to exactly ONE chunk.")
        chunks = chunks[:1]
        
    # Compute embeddings
    embeddings = [None] * len(chunks)
    if not skip_embeddings:
        print("Generating embeddings via OpenAI...")
        texts = [c["text"] for c in chunks]
        
        # Batch size for embeddings API
        batch_size = 100
        embeddings_failed = False
        for i in range(0, len(chunks), batch_size):
            batch_texts = texts[i:i+batch_size]
            try:
                batch_embeddings = get_embeddings_batch(batch_texts)
                for j, emb in enumerate(batch_embeddings):
                    embeddings[i + j] = emb
            except Exception as e:
                print(f"Warning: OpenAI Embeddings API failed: {e}")
                print("Proceeding with NULL embeddings for the rest of the chunks...")
                embeddings_failed = True
                break
                
        if embeddings_failed:
            # Keep what we succeeded with, set rest to None
            pass
            
    # Insert SourceDocument
    doc_id = uuid.uuid4()
    source_doc = SourceDocument(
        id=doc_id,
        ticker=entry["ticker"],
        company_name=COMPANY_NAMES.get(entry["ticker"], entry["ticker"]),
        filing_type=entry["form"],
        fiscal_year=fiscal_year_from_report_date(report_date) or int(year),
        filing_date=parse_date(entry["filing_date"]),
        accession_number=entry["accession_number"],
        source_url=entry["source_url"],
        markdown_content=markdown_content,
        doc_metadata={},
    )
    
    db.add(source_doc)
    db.commit()
    print(f"Inserted source_document: {entry['ticker']} ({year}) (ID: {doc_id})")
    
    # Save chunks in database
    chunk_objects = []
    for c_idx, c in enumerate(chunks):
        chunk_objects.append(DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_index=c["chunk_index"],
            text=c["text"],
            page=c["page"],
            section=c["section"],
            token_count=c["token_count"],
            chunk_metadata={},
            embedding=embeddings[c_idx],
        ))
        
    db.bulk_save_objects(chunk_objects)
    db.commit()
    print(f"Successfully ingested {len(chunks)} chunks for {entry['ticker']} ({year}).")
    
    if test_run:
        print("\n--- TEST RUN VERIFICATION INFO ---")
        print(f"Filing: {entry['ticker']} ({year})")
        print(f"Document ID: {doc_id}")
        print(f"Chunk text sample (first 100 chars): {chunks[0]['text'][:100]}...")
        print(f"Chunk page: {chunks[0]['page']}")
        print(f"Chunk section: {chunks[0]['section']}")
        print(f"Chunk tokens: {chunks[0]['token_count']}")
        print(f"Embedding generated: {'Yes (Length: ' + str(len(embeddings[0])) + ')' if embeddings[0] else 'No (NULL)'}")
        print("----------------------------------\n")
        return True
        
    return False


def main():
    parser = argparse.ArgumentParser(description="Ingest SEC 10-K filings using Docling Chunker and OpenAI embeddings.")
    parser.add_argument("--chunker", choices=["hybrid", "hierarchical"], default="hybrid", help="Docling chunker type.")
    parser.add_argument("--max-tokens", type=int, default=500, help="Max tokens per chunk (only used with hybrid chunker).")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip generating OpenAI vector embeddings.")
    parser.add_argument("--force", action="store_true", help="Overwrite documents if they already exist in database.")
    parser.add_argument("--test-run", action="store_true", help="Limit ingestion to a single document and exactly one chunk, then exit.")
    args = parser.parse_args()
    
    manifest_path = MARKDOWN_DIR / "manifest.json"
    if not manifest_path.exists():
        print(f"Error: Manifest not found at {manifest_path}. Please convert files to markdown first.")
        sys.exit(1)
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    db = SessionLocal()
    encoding = tiktoken.get_encoding("cl100k_base")
    
    filings = manifest.get("filings", [])
    print(f"Starting ingestion using Docling {args.chunker} chunker...")
    
    try:
        for idx, filing in enumerate(filings, 1):
            print(f"\n--- Ingesting filing [{idx}/{len(filings)}]: {filing['ticker']} ---")
            is_test_done = ingest_document_with_docling(
                filing,
                chunker_type=args.chunker,
                max_tokens=args.max_tokens,
                skip_embeddings=args.skip_embeddings,
                force=args.force,
                test_run=args.test_run,
                db=db,
                encoding=encoding
            )
            if is_test_done:
                print("Test run completed successfully. Exiting.")
                break
        else:
            print("\nIngestion pipeline complete!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
