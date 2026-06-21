import asyncio
import argparse
from pathlib import Path
from uuid import UUID

from app.core.config import get_settings
from app.rag.extraction import PdfExtractor
from app.rag.chunking import Chunker
from app.rag.embeddings import GeminiEmbeddingClient
from app.rag.ingestion import IngestionService
from app.infrastructure.vector.qdrant_client import QdrantVectorStore


async def main():
    parser = argparse.ArgumentParser(description="Ingest documents into the RAG system.")
    parser.add_argument("file_path", type=str, help="Path to the PDF file to ingest.")
    parser.add_argument("--title", type=str, help="Title of the document.")
    parser.add_argument("--subject_id", type=str, help="Optional subject UUID.")
    
    args = parser.parse_args()
    
    settings = get_settings()
    file_path = Path(args.file_path)
    title = args.title or file_path.stem
    subject_id = UUID(args.subject_id) if args.subject_id else None
    
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist.")
        return

    # Initialize components
    extractor = PdfExtractor()
    chunker = Chunker()
    embedding_client = GeminiEmbeddingClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_embedding_model,
        output_dimensionality=settings.gemini_embedding_dimensions,
    )
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        vector_size=settings.gemini_embedding_dimensions,
    )
    
    service = IngestionService(
        extractor=extractor,
        chunker=chunker,
        embedding_client=embedding_client,
        vector_store=vector_store,
    )
    
    print(f"Ingesting {file_path}...")
    document = await service.ingest_document(file_path, title, subject_id)
    print(f"Successfully ingested document: {document.title} (ID: {document.id})")


if __name__ == "__main__":
    asyncio.run(main())
