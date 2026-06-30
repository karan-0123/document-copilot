import uuid
from app.database.models import DocumentChunk
from app.retrieval.fusion import reciprocal_rank_fusion

def test_reciprocal_rank_fusion_basic():
    # Create mock DocumentChunks with unique IDs
    c1 = DocumentChunk(id=uuid.uuid4(), text="Chunk 1")
    c2 = DocumentChunk(id=uuid.uuid4(), text="Chunk 2")
    c3 = DocumentChunk(id=uuid.uuid4(), text="Chunk 3")
    
    # Rankings lists (list of chunks in ranked order)
    vector_results = [c1, c2]
    lexical_results = [c2, c3]
    
    # Execute RRF (k = 60)
    # RRF Score formula: sum(1.0 / (60 + rank))
    # Rank positions:
    # c1: vector rank 1, lexical rank None -> score = 1/(60+1) = 1/61 = 0.016393
    # c2: vector rank 2, lexical rank 1 -> score = 1/(60+2) + 1/(60+1) = 1/62 + 1/61 = 0.016129 + 0.016393 = 0.032522
    # c3: vector rank None, lexical rank 2 -> score = 1/(60+2) = 1/62 = 0.016129
    fused = reciprocal_rank_fusion(vector_results, lexical_results, k=60)
    
    assert len(fused) == 3
    # c2 should have the highest score since it appears in both lists
    assert fused[0][0].id == c2.id
    assert fused[0][1] > fused[1][1]
    
    # c1 should be second (rank 1 in vector vs c3's rank 2 in lexical)
    assert fused[1][0].id == c1.id
    
    # c3 should be last
    assert fused[2][0].id == c3.id

def test_reciprocal_rank_fusion_empty():
    fused = reciprocal_rank_fusion([], [])
    assert fused == []
