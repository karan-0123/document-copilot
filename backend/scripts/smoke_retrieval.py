from __future__ import annotations
import sys
from pathlib import Path

# Add backend directory to path so local modules under app/ can be found
script_dir = Path(__file__).resolve().parent
backend_dir = script_dir.parent
sys.path.append(str(backend_dir))

# Mock OpenAI embeddings since the API key might have no quota during local dry runs
import openai.resources.embeddings

class MockData:
    def __init__(self, embedding):
        self.embedding = embedding
        
class MockResponse:
    def __init__(self, data):
        self.data = data
        
def mock_create(*args, **kwargs):
    input_data = kwargs.get("input", [])
    if isinstance(input_data, str):
        input_data = [input_data]
    return MockResponse([MockData([0.1] * 1536) for _ in input_data])

openai.resources.embeddings.Embeddings.create = mock_create

# Local imports must happen AFTER sys.path is updated
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import SearchFilters, format_passages_for_agent

SMOKE_QUERIES: list[tuple[str, SearchFilters | None]] = [
    (
        "Across Apple's 10-Ks, how did the revenue mix between iPhone, Services, Mac, iPad, and Wearables change?",
        SearchFilters(ticker="AAPL", form="10-K"),
    ),
    (
        "How did NVIDIA describe demand drivers and customer concentration for its Data Center business?",
        SearchFilters(ticker="NVDA", form="10-K"),
    ),
    (
        "What changed in the way Microsoft describes Azure, AI infrastructure, and cloud capacity constraints?",
        SearchFilters(ticker="MSFT", form="10-K"),
    ),
]

def main() -> None:
    print("Initializing DocumentRetriever...")
    retriever = DocumentRetriever()
    
    for query, filters in SMOKE_QUERIES:
        print("\n" + "=" * 80)
        print(f"Query: {query}")
        if filters is not None:
            print(f"Filters: {filters.model_dump_json()}")
        
        print("-" * 80)
        passages = retriever.search(query, filters=filters)
        print(f"Retrieved {len(passages)} passages:")
        print(format_passages_for_agent(passages))

if __name__ == "__main__":
    main()
