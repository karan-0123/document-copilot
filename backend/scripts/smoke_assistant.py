from __future__ import annotations
import sys
import asyncio
import logging
import argparse
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
from app.assistant.agent import run_agent
from app.assistant.deps import DocumentAgentDeps
from app.grounding.validator import validate_grounding, GroundingValidationError
from app.retrieval.retriever import DocumentRetriever
from app.database.session import SessionLocal
from app.chat.orchestrator import extract_metadata_filters

# Setup standard logging. force=True ensures the configuration is applied in Jupyter.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
    force=True
)
# Enable Pydantic AI logs so user can see agent actions/tool runs
logging.getLogger("pydantic_ai").setLevel(logging.INFO)

logger = logging.getLogger("smoke_assistant")

class QueryLoggerAdapter(logging.LoggerAdapter):
    """Prefixes logs with the query key for clean output during parallel runs."""
    def process(self, msg, kwargs):
        return f"[{self.extra['query_key']}] {msg}", kwargs

QUERIES = {
    "apple-mix": "Across Apple's 2021-2025 10-Ks, how did the revenue mix between iPhone, Services, Mac, iPad, and Wearables change?",
    "nvda-datacenter": "How did NVIDIA describe demand drivers for its Data Center business from fiscal 2021 through fiscal 2025?",
    "q10-refusal": "Do the filings prove that generative AI improved margins for any of these companies?",
    "underspecified": "What is the best stock to buy right now?",
}

async def run_query(query_key: str) -> None:
    query = QUERIES.get(query_key)
    if not query:
        logger.error(f"Query key '{query_key}' not found.")
        return

    q_logger = QueryLoggerAdapter(logger, {"query_key": query_key})
    q_logger.info(f"Starting query: {query}")

    # Extract metadata filters
    tickers, years = extract_metadata_filters(query)
    q_logger.info(f"Extracted metadata filters: tickers={tickers}, years={years}")

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
        q_logger.info("Pre-retrieving passages...")
        from app.retrieval import RetrievalFilter, format_passages_for_agent
        filters = None
        if tickers or years:
            filters = RetrievalFilter(tickers=tickers, fiscal_years=years)
        passages = retriever.search_filings(db=db, query=query, filters=filters)
        q_logger.info(f"Retrieved {len(passages)} passages.")

        # Register passages for grounding validation
        for p in passages:
            deps.retrieved_passages[str(p.chunk_id)] = p

        # Build augmented prompt with context
        if passages:
            augmented_prompt = (
                f"## RETRIEVED CONTEXT PASSAGES\n\n"
                + "\n".join(
                    f"**Passage {i+1}** — Chunk ID: {p.chunk_id}\n"
                    f"[{p.company_name} ({p.ticker}) | {p.filing_type} FY{p.fiscal_year} | "
                    f"Section: {p.section or 'N/A'} | Page: {p.page or 'N/A'}]\n"
                    f"{p.text.strip()}\n"
                    for i, p in enumerate(passages)
                )
                + f"\n---\n\n## USER QUESTION\n\n{query}"
            )
        else:
            augmented_prompt = (
                f"## RETRIEVED CONTEXT PASSAGES\n\n"
                f"No relevant filings were found for this query.\n\n"
                f"---\n\n## USER QUESTION\n\n{query}"
            )

        q_logger.info("Running agent model...")
        grounded_answer = await run_agent(augmented_prompt=augmented_prompt)

        q_logger.info("--- AGENT ANSWER ---")
        q_logger.info(grounded_answer.answer)
        q_logger.info("-" * 40)

        q_logger.info("Citations:")
        for citation in grounded_answer.citations:
            q_logger.info(f"  - [{citation.citation_index}] Chunk ID: {citation.chunk_id}")
            q_logger.info(f"    Excerpt: \"{citation.excerpt}\"")

        q_logger.info("Running Grounding Validation...")
        try:
            validated = validate_grounding(grounded_answer, deps.retrieved_passages)
            q_logger.info("Validation Status: PASSED")
            q_logger.info(f"Generated {len(validated)} validated database citation records.")
        except GroundingValidationError as gve:
            q_logger.warning(f"Validation Status: FAILED - {gve}")

    except Exception as e:
        q_logger.exception(f"Error executing agent turn: {e}")
    finally:
        db.close()

async def main_async() -> None:
    parser = argparse.ArgumentParser(description="Run smoke test assistant queries in parallel or individually.")
    parser.add_argument(
        "--query",
        choices=list(QUERIES.keys()) + ["all"],
        default="all",
        help="Specific query key to run, or 'all' to run all queries concurrently. Default is 'all'."
    )
    # Parse arguments. Note: we slice sys.argv to avoid collision if running within another runner/Jupyter.
    args, unknown = parser.parse_known_args()

    if args.query == "all":
        logger.info(f"Running all {len(QUERIES)} queries in parallel...")
        tasks = [run_query(key) for key in QUERIES.keys()]
        await asyncio.gather(*tasks)
        logger.info("All queries execution complete.")
    else:
        logger.info(f"Running single query: {args.query}")
        await run_query(args.query)

def main() -> None:
    asyncio.run(main_async())

if __name__ == "__main__":
    main()

