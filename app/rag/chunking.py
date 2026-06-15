from __future__ import annotations

import hashlib
from typing import Iterator

from app.domain.documents import DocumentChunk
from app.rag.extraction import ExtractedChunk
from uuid import UUID


class Chunker:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def create_chunks(
        self,
        document_id: UUID,
        extracted_chunks: Iterator[ExtractedChunk],
    ) -> Iterator[DocumentChunk]:
        chunk_index = 0
        for extracted in extracted_chunks:
            text = extracted.content
            # For now, we do simple splitting by character count.
            # In a real scenario, we might want more sophisticated recursive splitting.
            start = 0
            while start < len(text):
                end = start + self._chunk_size
                chunk_text = text[start:end]
                
                content_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
                
                yield DocumentChunk(
                    document_id=document_id,
                    content=chunk_text,
                    content_hash=content_hash,
                    chunk_index=chunk_index,
                    page_start=extracted.page_number,
                    page_end=extracted.page_number,
                    metadata=extracted.metadata,
                )
                
                chunk_index += 1
                if end >= len(text):
                    break
                start += self._chunk_size - self._chunk_overlap
