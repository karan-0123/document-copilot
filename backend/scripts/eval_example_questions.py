import sys
import asyncio
import time
from pathlib import Path
from uuid import UUID

# Ensure backend folder is in PYTHONPATH
script_dir = Path(__file__).resolve().parent
backend_dir = script_dir.parent
sys.path.append(str(backend_dir))

from app.config import settings
from app.database.session import SessionLocal
from app.retrieval.retriever import DocumentRetriever
from app.retrieval import RetrievalFilter
from app.chat.orchestrator import extract_metadata_filters
from app.assistant.agent import run_agent
from app.assistant.deps import DocumentAgentDeps
from app.grounding.validator import validate_grounding, GroundingValidationError

# The 10 representative analyst questions from the brief, plus 2 out-of-corpus refusal controls
QUESTIONS = [
    (
        "Q1",
        "Across Apple's 2021–2025 10-Ks, how did the revenue mix between iPhone, Services, Mac, iPad, and Wearables change, and which category appears to have contributed most to any mix shift?"
    ),
    (
        "Q2",
        "For Amazon, compare AWS operating income and margin against North America and International from 2021–2025. In which years did AWS appear to fund losses or weaker profitability elsewhere?"
    ),
    (
        "Q3",
        "How did NVIDIA describe demand drivers, customer concentration, and supply constraints for its Data Center business from fiscal 2021 through fiscal 2025?"
    ),
    (
        "Q4",
        "Across Microsoft's 2021–2025 filings, what changed in the way the company describes Azure, AI infrastructure, and cloud capacity constraints?"
    ),
    (
        "Q5",
        "For Alphabet, how did Google Search, YouTube ads, Google Network, subscriptions/platforms/devices, and Google Cloud revenue trends differ across the available 10-Ks?"
    ),
    (
        "Q6",
        "Which of the five companies added, removed, or materially changed risk-factor language related to AI, cloud infrastructure, export controls, supply chain concentration, or regulation between 2021 and 2025?"
    ),
    (
        "Q7",
        "For Apple and NVIDIA, what do the filings say about supplier concentration or dependence on third-party manufacturing, and did the wording become more or less urgent over time?"
    ),
    (
        "Q8",
        "Compare capital expenditures and purchase commitments for Microsoft, Alphabet, Amazon, and NVIDIA. What do the filings imply about the scale and timing of AI/cloud infrastructure investment?"
    ),
    (
        "Q9",
        "For each company, summarize the most important geographic revenue exposures disclosed in the latest 10-K, then identify any year-over-year changes that could matter to an analyst."
    ),
    (
        "Q10",
        "If an analyst asks whether the filings prove that generative AI improved margins for any of these companies, what evidence exists in the corpus, and where should the bot refuse to infer beyond the filings?"
    ),
    (
        "Q11 (Out-of-Corpus Ticker)",
        "What is Tesla's total revenue in 2023?"
    ),
    (
        "Q12 (Out-of-Corpus Year)",
        "Across Apple's 2012 filings, what was the gross margin?"
    ),
]

async def eval_query(q_id: str, query: str, retriever: DocumentRetriever):
    print(f"\n[{q_id}] Processing: {query[:80]}...")
    
    db = SessionLocal()
    tickers, years = extract_metadata_filters(query)
    
    # Setup dynamic retrieval limit matching orchestrator
    limit = settings.retrieval_limit
    if tickers and len(tickers) > 1:
        limit = max(limit, len(tickers) * 3)
    if years and len(years) > 2:
        limit = max(limit, len(years) * 2)
    limit = min(limit, 15)

    filters = None
    if tickers or years:
        filters = RetrievalFilter(tickers=tickers, fiscal_years=years)

    # 1. Retrieve Passages
    try:
        passages = retriever.search_filings(db=db, query=query, filters=filters, limit=limit)
    except Exception as e:
        print(f"[{q_id}] Retrieval failed: {e}")
        db.close()
        return {
            "q_id": q_id,
            "query": query,
            "filters": f"tickers={tickers}, years={years}",
            "passages_count": 0,
            "answer": f"Retrieval Error: {e}",
            "citations": [],
            "grounding_status": "FAILED",
            "validation_error": str(e),
        }

    # 2. Build Augmented Prompt
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

    # 3. Call Agent Model with retries
    grounded_answer = None
    retry_count = 5
    for attempt in range(retry_count):
        try:
            grounded_answer = await run_agent(augmented_prompt=augmented_prompt)
            break
        except Exception as e:
            if attempt < retry_count - 1:
                # Use longer wait times for 429 rate limit backoff (15s, 30s, 45s, 60s)
                wait_time = (attempt + 1) * 15
                print(f"[{q_id}] API Error. Retrying in {wait_time}s... Error: {e}")
                await asyncio.sleep(wait_time)
            else:
                grounded_answer = None
                print(f"[{q_id}] Failed after {retry_count} attempts: {e}")

    db.close()

    if not grounded_answer:
        return {
            "q_id": q_id,
            "query": query,
            "filters": f"tickers={tickers}, years={years}, retrieval_limit={limit}",
            "passages_count": len(passages),
            "answer": "Agent execution failed / API unavailable.",
            "citations": [],
            "grounding_status": "FAILED",
            "validation_error": "Agent execution failed / API rate limit exceeded.",
        }

    # 4. Grounding and Citations Validation
    retrieved_map = {str(p.chunk_id): p for p in passages}
    grounding_status = "PASSED"
    validation_error = None
    try:
        validate_grounding(grounded_answer, retrieved_map)
    except GroundingValidationError as gve:
        grounding_status = "FAILED"
        validation_error = str(gve)

    return {
        "q_id": q_id,
        "query": query,
        "filters": f"tickers={tickers}, years={years}, retrieval_limit={limit}",
        "passages_count": len(passages),
        "answer": grounded_answer.answer,
        "citations": [
            {
                "index": c.citation_index,
                "chunk_id": str(c.chunk_id),
                "excerpt": c.excerpt,
                "source": f"{retrieved_map[str(c.chunk_id)].company_name} ({retrieved_map[str(c.chunk_id)].ticker}) FY{retrieved_map[str(c.chunk_id)].fiscal_year} p.{retrieved_map[str(c.chunk_id)].page or 'N/A'}" if str(c.chunk_id) in retrieved_map else "Unknown Source"
            }
            for c in grounded_answer.citations
        ],
        "grounding_status": grounding_status,
        "validation_error": validation_error,
        "raw_passages": [
            {
                "header": f"{p.company_name} ({p.ticker}) {p.filing_type} FY{p.fiscal_year} p.{p.page or 'N/A'}",
                "text": p.text
            } for p in passages
        ]
    }

async def main():
    print("Starting evaluation of Phase 9 analyst questions...")
    start_time = time.time()
    
    retriever = DocumentRetriever()
    results = []
    
    # Process sequentially to avoid aggressive rate limiting on free tiers
    for q_id, query in QUESTIONS:
        res = await eval_query(q_id, query, retriever)
        results.append(res)
        await asyncio.sleep(12)  # Cooldown between queries to prevent 429
        
    duration = time.time() - start_time
    print(f"\nEvaluation complete in {duration:.1f}s.")

    # Write Markdown results to docs/eval_results.md
    output_path = Path(backend_dir).parent / "docs" / "eval_results.md"
    
    md_content = []
    md_content.append("# Phase 9 — Evaluation Results Against Analyst Questions\n")
    md_content.append(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    md_content.append(f"Total Questions Evaluated: {len(QUESTIONS)}")
    passed_count = sum(1 for r in results if r["grounding_status"] == "PASSED")
    md_content.append(f"Grounding Validation Passes: {passed_count} / {len(QUESTIONS)}\n")
    md_content.append("## Summary Table\n")
    md_content.append("| QID | Query | Pass/Fail | Passages Retrieved | Citations |")
    md_content.append("| --- | --- | --- | --- | --- |")
    for r in results:
        status_emoji = "✅ PASS" if r["grounding_status"] == "PASSED" else "❌ FAIL"
        cit_count = len(r["citations"])
        md_content.append(f"| {r['q_id']} | {r['query'][:50]}... | {status_emoji} | {r['passages_count']} | {cit_count} |")
    
    md_content.append("\n---\n")
    md_content.append("## Detailed Results\n")
    
    for r in results:
        md_content.append(f"### {r['q_id']}: {r['query']}\n")
        md_content.append(f"**Extracted Filters:** `{r['filters']}`  ")
        md_content.append(f"**Passages Retrieved:** `{r['passages_count']}`  ")
        status_str = "✅ Grounding Check: PASSED" if r["grounding_status"] == "PASSED" else f"❌ Grounding Check: FAILED ({r['validation_error']})"
        md_content.append(f"**Status:** {status_str}\n")
        md_content.append("#### LLM Response:\n")
        md_content.append(r["answer"])
        md_content.append("\n")
        
        if r["citations"]:
            md_content.append("#### Cited Excerpts:\n")
            for c in r["citations"]:
                md_content.append(f"- **[{c['index']}]** *{c['source']}*  ")
                md_content.append(f"  Excerpt: `\"{c['excerpt']}\"`")
            md_content.append("\n")
            
        md_content.append("#### Retrieved Passages Context:\n")
        for i, p in enumerate(r.get("raw_passages", [])):
            md_content.append(f"<details><summary>Passage {i+1} — {p['header']}</summary>\n\n```\n{p['text']}\n```\n\n</details>")
        
        md_content.append("\n---\n")

    output_path.write_text("\n".join(md_content), encoding="utf-8")
    print(f"Results successfully written to: {output_path.absolute()}")

if __name__ == "__main__":
    asyncio.run(main())
