"""Backward-compatible entry point for SEC document ingestion.

This script delegates to the new modular orchestrator in chunk_and_embed.py,
which uses Docling for structure-aware chunking and OpenAI for embeddings.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path to allow importing app modules
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_DIR.parent))

from ingest.chunk_and_embed import main

if __name__ == "__main__":
    main()
