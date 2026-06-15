from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from pypdf import PdfReader


@dataclass(frozen=True, slots=True)
class ExtractedChunk:
    content: str
    page_number: int
    metadata: dict[str, object]


class DocumentExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: Path) -> Iterator[ExtractedChunk]:
        ...


class PdfExtractor(DocumentExtractor):
    def extract(self, file_path: Path) -> Iterator[ExtractedChunk]:
        reader = PdfReader(file_path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                yield ExtractedChunk(
                    content=text.strip(),
                    page_number=i + 1,
                    metadata={},
                )
