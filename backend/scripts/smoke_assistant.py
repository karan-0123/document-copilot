from __future__ import annotations
import sys
import asyncio
from pathlib import Path

# Add backend directory to path so local modules under app/ can be found
script_dir = Path(__file__).resolve().parent
backend_dir = script_dir.parent
sys.path.append(str(backend_dir))

try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

from app.config import settings
from app.assistant.agent import agent
from app.assistant.deps import DocumentAgentDeps
from app.grounding.validator import validate_grounding, GroundingValidationError
from app.retrieval.retriever import DocumentRetriever
from app.database.session import SessionLocal
from app.chat.orchestrator import extract_metadata_filters

QUERIES = {
    "apple-mix": "Across Apple's 2021-2025 10-Ks, how did the revenue mix between iPhone, Services, Mac, iPad, and Wearables change?",
    "nvda-datacenter": "How did NVIDIA describe demand drivers for its Data Center business from fiscal 2021 through fiscal 2025?",
    "q10-refusal": "Do the filings prove that generative AI improved margins for any of these companies?",
    "underspecified": "What is the best stock to buy right now?",
}

QUERY_KEY = "apple-mix"

async def run_query(query_key: str) -> None:
    query = QUERIES.get(query_key)
    if not query:
        print(f"Query key '{query_key}' not found.")
        return

    print(f"Running assistant smoke query for key: {query_key}")
    print(f"Query: {query}")
    print("=" * 80)

    # Extract metadata filters
    tickers, years = extract_metadata_filters(query)
    print(f"Extracted metadata filters: tickers={tickers}, years={years}")

    # Initialize DB session and retriever
    db = SessionLocal()
    retriever = DocumentRetriever()

    deps = DocumentAgentDeps(
        db=db,
        retriever=retriever,
        tickers=tickers,
        fiscal_years=years,
    )

    try:
        print("Running agent model...")
        result = await agent.run(query, deps=deps)
        grounded_answer = result.output

        print("\n" + "-" * 80)
        print("AGENT ANSWER:")
        print(grounded_answer.answer)
        print("-" * 80)

        print("\nCitations:")
        for citation in grounded_answer.citations:
            print(f"  - [{citation.citation_index}] Chunk ID: {citation.chunk_id}")
            print(f"    Excerpt: \"{citation.excerpt}\"")

        print("\nRunning Grounding Validation...")
        try:
            validated = validate_grounding(grounded_answer, deps.retrieved_passages)
            print("Validation Status: PASSED")
            print(f"Generated {len(validated)} validated database citation records.")
        except GroundingValidationError as gve:
            print(f"Validation Status: FAILED - {gve}")

    except Exception as e:
        print(f"Error executing agent turn: {e}")
    finally:
        db.close()

def main() -> None:
    asyncio.run(run_query(QUERY_KEY))

if __name__ == "__main__":
    main()
