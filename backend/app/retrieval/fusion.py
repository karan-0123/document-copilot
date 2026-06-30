from collections import defaultdict
from app.database.models import DocumentChunk

def reciprocal_rank_fusion(
    vector_results: list[DocumentChunk],
    lexical_results: list[DocumentChunk],
    k: int = 60,
) -> list[tuple[DocumentChunk, float]]:
    """Combine vector similarity rankings and full-text keyword search rankings using RRF.
    
    The RRF score for document d is calculated as:
        RRF_Score(d) = sum(1.0 / (k + rank)) for each rank in the results.
        
    Arguments:
        vector_results: list of similarity search results ordered by rank ascending.
        lexical_results: list of FTS results ordered by rank ascending.
        k: smoothing constant (default: 60).
        
    Returns:
        List of tuples (DocumentChunk, score) ordered by score descending.
    """
    scores = defaultdict(float)
    chunk_map = {}
    
    # Process vector results
    for rank, chunk in enumerate(vector_results, start=1):
        chunk_map[chunk.id] = chunk
        scores[chunk.id] += 1.0 / (k + rank)
        
    # Process lexical results
    for rank, chunk in enumerate(lexical_results, start=1):
        chunk_map[chunk.id] = chunk
        scores[chunk.id] += 1.0 / (k + rank)
        
    # Sort by RRF score descending
    sorted_scores = sorted(scores.items(), key=lambda item: -item[1])
    
    # Return fused list of chunks and their score
    return [(chunk_map[chunk_id], score) for chunk_id, score in sorted_scores]
