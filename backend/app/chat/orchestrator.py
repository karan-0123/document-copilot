import re
import json
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
from app.assistant.agent import agent
from app.grounding.validator import validate_grounding, GroundingValidationError
from app.chat.messages import convert_to_agent_history

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
        
    # Find any years between 2020 and 2026
    years = [int(y) for y in re.findall(r'\b(202[0-6])\b', query)]
    
    return (tickers or None, years or None)

async def orchestrate_chat_turn(
    thread_id: UUID,
    user_id: str,
    client_messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Orchestrates a single chat turn: runs retrieval, Pydantic AI agent, validation, and saves to DB."""
    if not client_messages:
        yield "3:No messages provided\n"
        return

    last_user_message = client_messages[-1].get("content", "").strip()
    if not last_user_message:
        yield "3:User query cannot be empty\n"
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

    # 3. Convert client chat history (excluding last user message)
    agent_history = convert_to_agent_history(client_messages[:-1])

    last_len = 0
    grounded_answer = None

    try:
        # 4. Execute Pydantic AI Agent structured stream
        async with agent.run_stream(
            last_user_message,
            deps=deps,
            message_history=agent_history
        ) as result:
            async for model in result.stream_structured():
                # Extract incremental answer text delta to stream to frontend
                if model.answer:
                    new_text = model.answer
                    delta = new_text[last_len:]
                    if delta:
                        yield f"0:{json.dumps(delta)}\n"
                        last_len = len(new_text)
            
            # Fetch final fully-parsed GroundedAnswer Pydantic model
            grounded_answer = await result.get_output()

    except Exception as e:
        yield f"3:Error during agent run: {str(e)}\n"
        db.close()
        return

    db.close()  # Close DB session after LLM generation completes

    # 5. Perform Grounding and Citation validation
    try:
        citation_payloads = validate_grounding(grounded_answer, deps.retrieved_passages)
    except GroundingValidationError as gve:
        # Fallback error stream event
        yield f"3:Grounding validation failed: {str(gve)}\n"
        return

    # 6. Persist User and Assistant messages to Supabase
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
        yield f"3:Persistence failed: {str(persist_error)}\n"
