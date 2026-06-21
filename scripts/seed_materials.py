import asyncio
import logging
import time
from pathlib import Path

from app.core.config import get_settings
from app.rag.chunking import Chunker
from app.rag.embeddings import GeminiEmbeddingClient
from app.rag.extraction import PdfExtractor
from app.infrastructure.vector.qdrant_client import QdrantVectorStore
from app.rag.ingestion import IngestionService

logging.basicConfig(level=logging.INFO)

async def main():
    settings = get_settings()
    
    extractor = PdfExtractor()
    chunker = Chunker(chunk_size=500, chunk_overlap=50)
    
    embedding_client = GeminiEmbeddingClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_embedding_model,
        output_dimensionality=settings.gemini_embedding_dimensions,
    )
    
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        vector_size=settings.gemini_embedding_dimensions,
    )
    
    ingestion_service = IngestionService(
        extractor=extractor,
        chunker=chunker,
        embedding_client=embedding_client,
        vector_store=vector_store,
    )

    data_dir = Path("data/polity")
    
    if not data_dir.exists():
        print(f"Data directory {data_dir} not found.")
        return

    pdf_files = list(data_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {data_dir}.")
        return

    # Recreate collection to ensure clean state
    print("Recreating Qdrant collection (clearing old data)...")
    await vector_store.recreate_collection()
    print("Collection recreated.")

    succeeded = 0
    failed = 0
    for i, file_path in enumerate(pdf_files):
        title = file_path.stem
        print(f"\n[{i+1}/{len(pdf_files)}] Ingesting {title} ({file_path.stat().st_size // 1024} KB)...")
        
        # Retry each document up to 3 times
        max_retries = 3
        for attempt in range(max_retries):
            try:
                start = time.perf_counter()
                await ingestion_service.ingest_document(
                    file_path=file_path,
                    title=title,
                    subject="Polity",
                )
                elapsed = time.perf_counter() - start
                print(f"  [OK] Successfully ingested {title} in {elapsed:.1f}s")
                succeeded += 1
                break
            except Exception as e:
                error_str = str(e)
                is_retryable = "429" in error_str or "504" in error_str or "Deadline" in error_str
                if is_retryable and attempt < max_retries - 1:
                    wait = 2 ** attempt * 30  # 30s, 60s
                    print(f"  [RETRY] Attempt {attempt+1} failed (rate limit/timeout), retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    print(f"  [FAIL] Failed to ingest {title}: {e}")
                    failed += 1
                    break
        
        # Delay between documents to respect rate limits
        if i < len(pdf_files) - 1:
            print("  Waiting 5s before next document...")
            await asyncio.sleep(5)

    print(f"\n{'='*50}")
    print(f"Ingestion complete: {succeeded} succeeded, {failed} failed out of {len(pdf_files)} total.")

if __name__ == "__main__":
    asyncio.run(main())

