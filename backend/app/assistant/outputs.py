from uuid import UUID
from pydantic import BaseModel, Field

class Citation(BaseModel):
    """Factual citation representing a quote from a specific retrieved passage."""
    chunk_id: UUID = Field(
        description="The unique ID of the document chunk containing the cited quote"
    )
    citation_index: int = Field(
        description="The 1-based numeric index of this citation in the generated response (e.g. 1, 2, 3)"
    )
    excerpt: str = Field(
        description="The exact quote/verbatim excerpt from the document chunk text that supports the statement"
    )

class GroundedAnswer(BaseModel):
    """The structured answer output containing the narrative response and supporting citations."""
    answer: str = Field(
        description=(
            "The natural language response to the user query. Factual statements must be citable "
            "and end with inline citation markers like [1], [2], or [3] pointing to the citations list."
        )
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="The list of supporting citations. Every claim must map to a citation in this list."
    )
