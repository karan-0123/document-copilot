import re
from app.assistant.outputs import GroundedAnswer, Citation
from app.retrieval.types import SourcePassage

class GroundingValidationError(ValueError):
    """Exception raised when a generated citation violates grounding policies (hallucination or missing text)."""
    pass

def _normalize_text(text: str) -> str:
    """Helper to normalize whitespace and lowercase text for robust substring matching."""
    # Replace newlines, tabs, and duplicate spaces with a single space, then strip
    return re.sub(r'\s+', ' ', text).strip().lower()

def validate_grounding(
    answer: GroundedAnswer, 
    retrieved_passages: dict[str, SourcePassage]
) -> list[dict]:
    """Ensures every citation in the GroundedAnswer maps to a retrieved chunk and cites verbatim text.
    
    Raises:
        GroundingValidationError: If any citation is invalid or doesn't match verbatim.
        
    Returns:
        List of dicts formatted for the message_citations database table insertion.
    """
    # Refusal string is exempt from citation requirement
    if answer.answer.strip() == "I cannot answer this question because the loaded filings do not contain sufficient evidence.":
        return []
        
    validated_citations = []
    
    for citation in answer.citations:
        chunk_key = str(citation.chunk_id)
        
        # Invariant 1: Cited chunk must have been retrieved or read during the run context
        if chunk_key not in retrieved_passages:
            raise GroundingValidationError(
                f"Citation index {citation.citation_index} cites chunk ID {citation.chunk_id} "
                "which was not retrieved or read during this request."
            )
            
        passage = retrieved_passages[chunk_key]
        
        # Invariant 2: Excerpt must be verbatim present in the chunk text (case and whitespace normalized)
        norm_excerpt = _normalize_text(citation.excerpt)
        norm_chunk_text = _normalize_text(passage.text)
        
        if norm_excerpt not in norm_chunk_text:
            raise GroundingValidationError(
                f"Citation index {citation.citation_index} cites excerpt '{citation.excerpt}' "
                f"which does not exist verbatim inside the text of chunk {citation.chunk_id}."
            )
            
        # Format database insertion payload
        validated_citations.append({
            "chunk_id": citation.chunk_id,
            "citation_index": citation.citation_index,
            "citation_metadata": {
                "company": passage.company_name,
                "filing_type": passage.filing_type,
                "year": passage.fiscal_year,
                "section": passage.section,
                "page": passage.page,
                "excerpt": citation.excerpt,
            }
        })
        
    return validated_citations
