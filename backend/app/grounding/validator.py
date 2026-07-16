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

def _normalize_alphanumeric(text: str) -> str:
    """Helper to strip punctuation and normalize spacing for robust comparison."""
    # Replace non-alphanumeric characters with spaces
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', cleaned).strip().lower()

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
        
        # Check if the cited chunk is in retrieved passages, and if the excerpt is a substring
        found = False
        passage = None
        
        if chunk_key in retrieved_passages:
            passage = retrieved_passages[chunk_key]
            norm_excerpt = _normalize_text(citation.excerpt)
            norm_chunk_text = _normalize_text(passage.text)
            
            if norm_excerpt in norm_chunk_text:
                found = True
            else:
                # Try alphanumeric fallback
                alpha_excerpt = _normalize_alphanumeric(citation.excerpt)
                alpha_chunk_text = _normalize_alphanumeric(passage.text)
                if alpha_excerpt in alpha_chunk_text:
                    found = True
        
        # Auto-healing logic: if not found, scan other retrieved passages
        if not found:
            norm_excerpt = _normalize_text(citation.excerpt)
            for other_key, other_passage in retrieved_passages.items():
                if other_key == chunk_key:
                    continue
                norm_other = _normalize_text(other_passage.text)
                if norm_excerpt in norm_other:
                    chunk_key = other_key
                    passage = other_passage
                    found = True
                    break
            
            if not found:
                # Alphanumeric fallback on other passages
                alpha_excerpt = _normalize_alphanumeric(citation.excerpt)
                for other_key, other_passage in retrieved_passages.items():
                    if other_key == chunk_key:
                        continue
                    alpha_other = _normalize_alphanumeric(other_passage.text)
                    if alpha_excerpt in alpha_other:
                        chunk_key = other_key
                        passage = other_passage
                        found = True
                        break
        
        if not found:
            raise GroundingValidationError(
                f"Citation index {citation.citation_index} cites excerpt '{citation.excerpt}' "
                f"which does not exist verbatim inside the text of any retrieved chunks."
            )
            
        # Format database insertion payload with the corrected/validated chunk ID
        validated_citations.append({
            "chunk_id": UUID(chunk_key),
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
