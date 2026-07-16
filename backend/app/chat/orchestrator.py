import re
import json
import asyncio
from uuid import UUID
from typing import AsyncGenerator

from app.database import (
    get_service_role_client,
    get_messages,
    create_message,
    create_citations,
)
from app.database.session import SessionLocal
from app.retrieval import DocumentRetriever
from app.assistant.deps import DocumentAgentDeps
from app.assistant.agent import run_agent
from app.grounding.validator import validate_grounding, GroundingValidationError

def extract_metadata_filters(query: str) -> tuple[list[str] | None, list[int] | None]:
    """Helper to deterministically extract tickers and years from the query to seed filters."""
    query_lower = query.lower()
    tickers = []
    
    # Check for tickers or company names
    if "apple" in query_lower or "aapl" in query_lower:
        tickers.append("AAPL")
    if "microsoft" in query_lower or "msft" in query_lower:
        tickers.append("MSFT")
    if "nvidia" in query_lower or "nvda" in query_lower:
        tickers.append("NVDA")
    if "amazon" in query_lower or "amzn" in query_lower:
        tickers.append("AMZN")
    if "alphabet" in query_lower or "google" in query_lower or "googl" in query_lower:
        tickers.append("GOOGL")
        
    years = set()
    
    # 1. Match explicit ranges, e.g. 2021-2025, 2021 to 2025, 2021–2025 (dash/en-dash)
    range_pattern = r'\b(202[0-6])\s*(?:-|–|to|through)\s*(202[0-6])\b'
    for start, end in re.findall(range_pattern, query):
        for y in range(int(start), int(end) + 1):
            years.add(y)
            
    # 2. Match abbreviated ranges, e.g. 2021-25 or 2021–25
    abbr_range_pattern = r'\b(202[0-6])\s*(?:-|–)\s*(2[0-6])\b'
    for start, end_short in re.findall(abbr_range_pattern, query):
        end = 2000 + int(end_short)
        for y in range(int(start), end + 1):
            years.add(y)
            
    # 3. Match general two 4-digit years separated by words/spaces if range words are present in the query
    # E.g. "between 2021 and 2025" or "from 2021 to 2025"
    all_4digit_years = [int(y) for y in re.findall(r'\b(202[0-6])\b', query)]
    if len(all_4digit_years) == 2 and any(w in query_lower for w in ["to", "through", "and", "between"]):
        for y in range(min(all_4digit_years), max(all_4digit_years) + 1):
            years.add(y)
            
    # 4. Match single 4-digit years
    for y in all_4digit_years:
        years.add(y)
        
    # 5. Match single 2-digit years with 'FY' prefix, e.g. FY21, FY 25, or range FY21-FY25
    # First match expressions like FY21-FY25 or FY21 to FY25
    fy_range_pattern = r'\bfy\s*(202[0-6]|[2-6][0-9])\s*(?:-|–|to|through)\s*fy\s*(202[0-6]|[2-6][0-9])\b'
    for start_fy, end_fy in re.findall(fy_range_pattern, query_lower):
        start = int(start_fy) if len(start_fy) == 4 else 2000 + int(start_fy)
        end = int(end_fy) if len(end_fy) == 4 else 2000 + int(end_fy)
        for y in range(start, end + 1):
            years.add(y)
            
    # Then match single FY matches
    for m in re.findall(r'\bfy\s*(202[0-6]|[2-6][0-9])\b', query_lower):
        val = int(m) if len(m) == 4 else 2000 + int(m)
        years.add(val)
        
    return (tickers or None, sorted(list(years)) or None)

async def orchestrate_chat_turn(
    thread_id: UUID,
    user_id: str,
    client_messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Orchestrates a single chat turn: runs retrieval, Pydantic AI agent, validation, and saves to DB."""
    if not client_messages:
        yield f"3:{json.dumps('No messages provided')}\n"
        return

    last_user_message = client_messages[-1].get("content", "").strip()
    if not last_user_message:
        yield f"3:{json.dumps('User query cannot be empty')}\n"
        return

    # 1. Initialize DB Session and Retriever
    db = SessionLocal()
    retriever = DocumentRetriever()
    supabase_client = await get_service_role_client()

    # 2. Extract tickers/years and prepare Agent dependencies
    tickers, years = extract_metadata_filters(last_user_message)
    deps = DocumentAgentDeps(
        db=db,
        retriever=retriever,
        tickers=tickers,
        fiscal_years=years,
    )

    # 3. Convert client chat history to plain dicts for the Groq API (excluding last user message)
    message_history = []
    for msg in client_messages[:-1]:
        role = msg.get("role")
        content = msg.get("content", "").strip()
        if content and role in ("user", "assistant"):
            message_history.append({"role": role, "content": content})

    # 4. Persist User message to Supabase IMMEDIATELY before generation
    seq_user = 1
    seq_assistant = 2
    try:
        # Fetch current message count to get correct sequences
        existing = await get_messages(supabase_client, thread_id)
        seq_user = len(existing) + 1
        seq_assistant = len(existing) + 2

        # Save user message
        await create_message(
            supabase_client,
            thread_id=thread_id,
            role="user",
            content=last_user_message,
            sequence=seq_user,
        )
    except Exception as persist_error:
        yield f"3:{json.dumps(f'Failed to save user message: {str(persist_error)}')}\n"
        db.close()
        return

    # 5. Pre-retrieve passages and inject into prompt (instead of agent tool calling)
    from app.retrieval import RetrievalFilter

    filters = None
    if tickers or years:
        filters = RetrievalFilter(tickers=tickers, fiscal_years=years)

    # Dynamically scale retrieval limit for multi-entity/multi-year synthesis queries
    limit = settings.retrieval_limit
    if tickers and len(tickers) > 1:
        limit = max(limit, len(tickers) * 3)
    if years and len(years) > 2:
        limit = max(limit, len(years) * 2)
    limit = min(limit, 15)  # Cap at 15 to avoid token issues / rate limits

    try:
        passages = retriever.search_filings(db=db, query=last_user_message, filters=filters, limit=limit)
    except Exception as retrieval_err:
        yield f"3:{json.dumps(f'Retrieval failed: {str(retrieval_err)}')}\n"
        db.close()
        return

    # Register all retrieved passages in deps for grounding validation
    for p in passages:
        deps.retrieved_passages[str(p.chunk_id)] = p

    # Build the augmented prompt with context
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
            + f"\n---\n\n## USER QUESTION\n\n{last_user_message}"
        )
    else:
        # No passages found — agent should refuse per instructions
        augmented_prompt = (
            f"## RETRIEVED CONTEXT PASSAGES\n\n"
            f"No relevant filings were found for this query.\n\n"
            f"---\n\n## USER QUESTION\n\n{last_user_message}"
        )

    db.close()  # Close DB session after retrieval (before LLM call)

    grounded_answer = None

    # Retry up to 3 times with exponential backoff for transient Groq errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Call Groq API directly with JSON mode (no pydantic-ai streaming)
            # Groq responds in ~1-2s, so buffering is fine — no need for incremental streaming
            grounded_answer = await run_agent(
                augmented_prompt=augmented_prompt,
                message_history=message_history,
            )

            # Send the complete answer as stream text
            if grounded_answer and grounded_answer.answer:
                yield f"0:{json.dumps(grounded_answer.answer)}\n"
            break  # Success — exit the retry loop

        except Exception as e:
            err_str = str(e)
            is_429 = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
            is_503 = "503" in err_str or "UNAVAILABLE" in err_str or "overloaded" in err_str.lower()
            is_retryable = is_429 or is_503

            if is_retryable and attempt < max_retries - 1:
                wait_secs = (5 * (attempt + 1)) if is_429 else (2 ** attempt)
                await asyncio.sleep(wait_secs)
                continue  # Retry

            # Build a user-friendly message for quota exhaustion
            if is_429:
                friendly = "Groq free-tier quota exhausted. Please wait a minute and try again."
            else:
                friendly = f"Error during agent run: {err_str}"

            yield f"3:{json.dumps(friendly)}\n"
            return

    # 6. Perform Grounding and Citation validation
    try:
        citation_payloads = validate_grounding(grounded_answer, deps.retrieved_passages)
    except GroundingValidationError as gve:
        # Fallback error stream event (3: events require JSON-encoded strings)
        yield f"3:{json.dumps(f'Grounding validation failed: {str(gve)}')}\n"
        return

    # 6. Persist Assistant message to Supabase
    try:
        # Map citations to payload format for the client
        client_citations = []
        for index, item in enumerate(citation_payloads, 1):
            metadata = item["citation_metadata"]
            client_citations.append({
                "index": item["citation_index"],
                "company": metadata["company"],
                "filing_type": metadata["filing_type"],
                "year": metadata["year"],
                "section": metadata["section"],
                "page": metadata["page"],
                "excerpt": metadata["excerpt"],
            })

        # Save assistant message
        assistant_msg = await create_message(
            supabase_client,
            thread_id=thread_id,
            role="assistant",
            content=grounded_answer.answer,
            sequence=seq_assistant,
            payload={"citations": client_citations},
        )

        # Save message citations to message_citations table
        if citation_payloads and assistant_msg.get("id"):
            await create_citations(
                supabase_client,
                message_id=assistant_msg["id"],
                citations=citation_payloads,
            )

    except Exception as persist_error:
        yield f"3:{json.dumps(f'Persistence failed: {str(persist_error)}')}\n"
