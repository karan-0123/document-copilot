from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from app.retrieval import DocumentRetriever
from app.retrieval.types import SourcePassage

@dataclass
class DocumentAgentDeps:
    """Dependencies passed to the Pydantic AI agent run context."""
    db: Session
    retriever: DocumentRetriever
    tickers: list[str] | None = None
    fiscal_years: list[int] | None = None
    
    # tracks all passages retrieved during tool runs so the grounding validator can check them
    retrieved_passages: dict[str, SourcePassage] = field(
        default_factory=dict, 
        compare=False, 
        hash=False
    )
