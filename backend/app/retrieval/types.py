from uuid import UUID
from pydantic import BaseModel, Field

class RetrievalFilter(BaseModel):
    """Filter parameters to restrict retrieval queries to specific document subsets."""
    tickers: list[str] | None = Field(
        default=None, 
        description="Filter by filing tickers (e.g. ['AAPL', 'NVDA'])"
    )
    fiscal_years: list[int] | None = Field(
        default=None, 
        description="Filter by filing fiscal years (e.g. [2024, 2025])"
    )
    filing_types: list[str] | None = Field(
        default=None,
        description="Filter by filing types (e.g. ['10-K', '10-Q'])"
    )


class SearchFilters(BaseModel):
    """Simple filter parameters to restrict search (as used by agent and smoke scripts)."""
    ticker: str | None = Field(default=None, description="Filter by ticker (e.g. 'AAPL')")
    form: str | None = Field(default=None, description="Filter by form type (e.g. '10-K')")

class SourcePassage(BaseModel):
    """Structured representation of a retrieved document chunk for downstream LLM consumption and citation rendering."""
    chunk_id: UUID = Field(description="Unique identifier for the document chunk")
    document_id: UUID = Field(description="Unique identifier for the parent source document")
    text: str = Field(description="The narrative text content of the chunk")
    ticker: str = Field(description="Ticker symbol of the company (e.g., AAPL)")
    company_name: str = Field(description="Full legal name of the company")
    filing_type: str = Field(description="SEC form type (e.g., 10-K)")
    fiscal_year: int = Field(description="Fiscal year of the report")
    page: str | None = Field(default=None, description="Page number details if present")
    section: str | None = Field(default=None, description="Report section details if present")
    score: float | None = Field(default=None, description="Hybrid retrieval ranking score (e.g., RRF score)")
    source_url: str = Field(description="Access URL or filing reference link")

def format_passages_for_agent(passages: list[SourcePassage]) -> str:
    """Formats retrieved passages into a structured string block for agent consumption."""
    formatted = []
    for passage in passages:
        formatted.append(
            f"[{passage.ticker} {passage.filing_type} FY{passage.fiscal_year} (p. {passage.page or 'N/A'}, sec. {passage.section or 'N/A'})] (Score: {passage.score or 0:.4f})\n"
            f"Link: {passage.source_url}\n"
            f"Excerpt:\n{passage.text.strip()}"
        )
    return "\n\n==================================================\n\n".join(formatted)

