import pytest
from uuid import uuid4
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

from app.assistant.outputs import GroundedAnswer, Citation
from app.retrieval.types import SourcePassage
from app.grounding.validator import validate_grounding, GroundingValidationError
from app.chat.messages import convert_to_agent_history

def test_convert_to_agent_history():
    """Test that client message format converts correctly to Pydantic AI message history."""
    client_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there! How can I help?"},
        {"role": "user", "content": "What is the capital of France?"}
    ]
    
    history = convert_to_agent_history(client_messages)
    
    assert len(history) == 3
    assert isinstance(history[0], ModelRequest)
    assert isinstance(history[0].parts[0], UserPromptPart)
    assert history[0].parts[0].content == "Hello"
    
    assert isinstance(history[1], ModelResponse)
    assert isinstance(history[1].parts[0], TextPart)
    assert history[1].parts[0].content == "Hi there! How can I help?"
    
    assert isinstance(history[2], ModelRequest)
    assert history[2].parts[0].content == "What is the capital of France?"

def test_grounding_validator_success():
    """Test grounding validation passes when citations exist in retrieved passages with verbatim excerpts."""
    chunk_id = uuid4()
    passage = SourcePassage(
        chunk_id=chunk_id,
        document_id=uuid4(),
        text="Apple's revenue grew by 10% in fiscal year 2024.",
        ticker="AAPL",
        company_name="Apple Inc.",
        filing_type="10-K",
        fiscal_year=2024,
        source_url="https://sec.gov"
    )
    
    answer = GroundedAnswer(
        answer="Apple's revenue grew by 10% in 2024 [1].",
        citations=[
            Citation(chunk_id=chunk_id, citation_index=1, excerpt="revenue grew by 10%")
        ]
    )
    
    retrieved_passages = {str(chunk_id): passage}
    
    payloads = validate_grounding(answer, retrieved_passages)
    assert len(payloads) == 1
    assert payloads[0]["chunk_id"] == chunk_id
    assert payloads[0]["citation_index"] == 1
    assert payloads[0]["citation_metadata"]["excerpt"] == "revenue grew by 10%"
    assert payloads[0]["citation_metadata"]["company"] == "Apple Inc."

def test_grounding_validator_missing_chunk():
    """Test validation fails when a cited chunk was not actually retrieved."""
    chunk_id_cited = uuid4()
    chunk_id_retrieved = uuid4()
    
    passage = SourcePassage(
        chunk_id=chunk_id_retrieved,
        document_id=uuid4(),
        text="Apple's revenue grew by 10% in fiscal year 2024.",
        ticker="AAPL",
        company_name="Apple Inc.",
        filing_type="10-K",
        fiscal_year=2024,
        source_url="https://sec.gov"
    )
    
    answer = GroundedAnswer(
        answer="Apple's revenue grew by 10% in 2024 [1].",
        citations=[
            Citation(chunk_id=chunk_id_cited, citation_index=1, excerpt="revenue grew by 99%")
        ]
    )
    
    retrieved_passages = {str(chunk_id_retrieved): passage}
    
    with pytest.raises(GroundingValidationError) as excinfo:
        validate_grounding(answer, retrieved_passages)
    assert "does not exist verbatim" in str(excinfo.value)

def test_grounding_validator_excerpt_mismatch():
    """Test validation fails when the cited excerpt is not verbatim inside the chunk text."""
    chunk_id = uuid4()
    passage = SourcePassage(
        chunk_id=chunk_id,
        document_id=uuid4(),
        text="Apple's revenue grew by 10% in fiscal year 2024.",
        ticker="AAPL",
        company_name="Apple Inc.",
        filing_type="10-K",
        fiscal_year=2024,
        source_url="https://sec.gov"
    )
    
    # Excerpt says 15% instead of 10%
    answer = GroundedAnswer(
        answer="Apple's revenue grew by 15% in 2024 [1].",
        citations=[
            Citation(chunk_id=chunk_id, citation_index=1, excerpt="revenue grew by 15%")
        ]
    )
    
    retrieved_passages = {str(chunk_id): passage}
    
    with pytest.raises(GroundingValidationError) as excinfo:
        validate_grounding(answer, retrieved_passages)
    assert "does not exist verbatim" in str(excinfo.value)

def test_grounding_validator_refusal_exempt():
    """Test that the refusal message is exempt from grounding checks and does not fail."""
    answer = GroundedAnswer(
        answer="I cannot answer this question because the loaded filings do not contain sufficient evidence.",
        citations=[]
    )
    payloads = validate_grounding(answer, {})
    assert payloads == []
