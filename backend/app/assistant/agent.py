from uuid import UUID
from pathlib import Path
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from app.config import settings
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.retrieval import RetrievalFilter

# Load prompt instructions from markdown file
INSTRUCTIONS_PATH = Path(__file__).resolve().parent / "instructions.md"
system_instruction = INSTRUCTIONS_PATH.read_text(encoding="utf-8")

import os

# Ensure OpenAI API key is in environment for pydantic_ai
os.environ["OPENAI_API_KEY"] = settings.openai_api_key

# Initialize OpenAI model with configured model name
openai_model = OpenAIModel(settings.openai_llm_model)

# Instantiate Pydantic AI agent
agent = Agent(
    model=openai_model,
    deps_type=DocumentAgentDeps,
    output_type=GroundedAnswer,
    system_prompt=system_instruction,
)

@agent.tool
def search_filings(ctx: RunContext[DocumentAgentDeps], query: str) -> str:
    """Search the SEC filings database for relevant excerpts/passages.
    
    Applies current ticker and year constraints automatically.
    """
    filters = None
    if ctx.deps.tickers or ctx.deps.fiscal_years:
        filters = RetrievalFilter(
            tickers=ctx.deps.tickers,
            fiscal_years=ctx.deps.fiscal_years
        )
        
    passages = ctx.deps.retriever.search_filings(
        db=ctx.deps.db,
        query=query,
        filters=filters
    )
    
    # Register all retrieved passages in deps for grounding verification
    for p in passages:
        ctx.deps.retrieved_passages[str(p.chunk_id)] = p
        
    if not passages:
        return "No matching filings found."
        
    formatted = []
    for p in passages:
        formatted.append(
            f"[Document: {p.company_name} ({p.ticker}) | Filing: {p.filing_type} {p.fiscal_year} | Section: {p.section} | Page: {p.page}]\n"
            f"Chunk ID: {p.chunk_id}\n"
            f"Text Content:\n{p.text}\n"
            f"--------------------------------------------------"
        )
    return "\n".join(formatted)

@agent.tool
def read_passage_context(ctx: RunContext[DocumentAgentDeps], chunk_id: UUID) -> str:
    """Read a target chunk and its immediate sequential before/after neighbor chunks to see surrounding context.
    
    Use this to read contiguous document context if the original chunk was split.
    """
    from app.database import get_chunk_with_neighbors
    from app.retrieval.retriever import map_chunk_to_passage
    
    chunks = get_chunk_with_neighbors(
        db=ctx.deps.db,
        chunk_id=chunk_id,
        before=1,
        after=1
    )
    
    if not chunks:
        return "Chunk not found."
        
    formatted = []
    for c in chunks:
        p = map_chunk_to_passage(c)
        # Register neighbor chunk in deps as well so it's a valid grounding source
        ctx.deps.retrieved_passages[str(p.chunk_id)] = p
        
        is_target = c.id == chunk_id
        tag = " [TARGET CHUNK]" if is_target else ""
        formatted.append(
            f"[Chunk ID: {p.chunk_id} | Index: {c.chunk_index}{tag}]\n"
            f"Text Content:\n{c.text}\n"
            f"--------------------------------------------------"
        )
    return "\n".join(formatted)
