import asyncio
import logging
from pathlib import Path

from app.rag.chunking import Chunker
from app.rag.embeddings import EmbeddingClient
from app.rag.extraction import TextExtractor
from app.infrastructure.vector.qdrant_client import QdrantVectorStore
from app.rag.ingestion import IngestionService

logging.basicConfig(level=logging.INFO)

async def main():
    extractor = TextExtractor()
    chunker = Chunker(chunk_size=500, chunk_overlap=50)
    # Ensure this matches the model used in the app
    embedding_client = EmbeddingClient()
    # Initialize Qdrant store
    vector_store = QdrantVectorStore(collection_name="ai_university")
    
    ingestion_service = IngestionService(
        extractor=extractor,
        chunker=chunker,
        embedding_client=embedding_client,
        vector_store=vector_store,
    )

    data_dir = Path("data/polity")
    
    files = [
        ("fundamental_rights.txt", "Fundamental Rights"),
        ("dpsp.txt", "Directive Principles of State Policy"),
        ("president.txt", "The President of India")
    ]
    
    for filename, title in files:
        file_path = data_dir / filename
        if file_path.exists():
            print(f"Ingesting {title}...")
            await ingestion_service.ingest_document(
                file_path=file_path,
                title=title,
            )
            print(f"Successfully ingested {title}.")
        else:
            print(f"File {file_path} not found.")

if __name__ == "__main__":
    asyncio.run(main())
