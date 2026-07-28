from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


WORD_RE = re.compile(r"[a-zA-Z0-9._/-]+")
STOP_WORDS = {
    "a",
    "ai",
    "al",
    "ale",
    "am",
    "an",
    "and",
    "as",
    "at",
    "au",
    "ca",
    "care",
    "ce",
    "conform",
    "cu",
    "de",
    "din",
    "do",
    "este",
    "for",
    "i",
    "in",
    "is",
    "la",
    "mai",
    "nu",
    "or",
    "pe",
    "si",
    "sunt",
    "the",
    "to",
    "un",
    "una",
    "une",
}


@dataclass
class Chunk:
    source: str
    text: str
    token_counts: dict[str, int]


class KnowledgeBaseRetriever:
    def __init__(
        self,
        roots: list[Path],
        max_chunk_chars: int = 1200,
        chunk_overlap_chars: int = 150,
    ) -> None:
        self.roots = roots
        self.max_chunk_chars = max_chunk_chars
        self.chunk_overlap_chars = chunk_overlap_chars
        self._chunks: list[Chunk] = []
        self._doc_freq: dict[str, int] = {}
        self._last_indexed_files: dict[str, float] = {}

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens = [token.lower() for token in WORD_RE.findall(text)]
        return [token for token in tokens if len(token) > 1 and token not in STOP_WORDS]

    @staticmethod
    def _safe_read_text(path: Path) -> str:
        for encoding in ("utf-8", "cp1250", "cp1252", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return ""

    @staticmethod
    def _read_pdf(path: Path) -> str:
        try:
            from pypdf import PdfReader
        except Exception:
            return ""

        import logging
        import warnings

        pypdf_logger = logging.getLogger("pypdf")
        original_level = pypdf_logger.level
        pypdf_logger.setLevel(logging.ERROR)

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                reader = PdfReader(str(path), strict=False)
                pages: list[str] = []
                for page in reader.pages:
                    try:
                        text = page.extract_text() or ""
                    except Exception:
                        continue
                    if text.strip():
                        pages.append(text)
                return "\n\n".join(pages)
        except Exception:
            return ""
        finally:
            pypdf_logger.setLevel(original_level)

    def _read_document(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".md", ".txt", ".json", ".csv", ".log"}:
            return self._safe_read_text(path)
        if suffix == ".pdf":
            return self._read_pdf(path)
        return ""

    def _chunk_text(self, text: str) -> list[str]:
        normalized = text.replace("\r\n", "\n")
        paragraphs = [line.strip() for line in normalized.split("\n") if line.strip()]
        if not paragraphs:
            return []

        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            candidate = paragraph if not current else f"{current}\n{paragraph}"
            if len(candidate) <= self.max_chunk_chars:
                current = candidate
                continue

            if current:
                chunks.append(current)

            if len(paragraph) <= self.max_chunk_chars:
                current = paragraph
            else:
                start = 0
                while start < len(paragraph):
                    end = min(start + self.max_chunk_chars, len(paragraph))
                    chunks.append(paragraph[start:end])
                    if end >= len(paragraph):
                        break
                    start = max(0, end - self.chunk_overlap_chars)
                current = ""

        if current:
            chunks.append(current)

        return chunks

    def _discover_files(self) -> list[Path]:
        files: list[Path] = []
        for root in self.roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.lower() in {".md", ".txt", ".json", ".csv", ".log", ".pdf"}:
                    files.append(path)
        return sorted(files)

    def index(self, force: bool = False) -> dict[str, Any]:
        files = self._discover_files()
        file_mtimes = {str(path): path.stat().st_mtime for path in files}

        if not force and file_mtimes == self._last_indexed_files:
            return {
                "reindexed": False,
                "files": len(files),
                "chunks": len(self._chunks),
            }

        chunks: list[Chunk] = []
        doc_freq_counter: Counter[str] = Counter()

        for path in files:
            raw_text = self._read_document(path)
            if not raw_text.strip():
                continue
            relative_path = str(path)
            for part in self._chunk_text(raw_text):
                tokens = self._tokenize(part)
                if not tokens:
                    continue
                token_counts = Counter(tokens)
                chunks.append(
                    Chunk(
                        source=relative_path,
                        text=part,
                        token_counts=dict(token_counts),
                    )
                )
                doc_freq_counter.update(set(token_counts.keys()))

        self._chunks = chunks
        self._doc_freq = dict(doc_freq_counter)
        self._last_indexed_files = file_mtimes

        return {
            "reindexed": True,
            "files": len(files),
            "chunks": len(chunks),
        }

    def search(self, query: str, top_k: int = 4, min_score: float = 0.2) -> list[dict[str, Any]]:
        query_tokens = self._tokenize(query)
        if not query_tokens or not self._chunks:
            return []

        query_counts = Counter(query_tokens)
        total_chunks = max(len(self._chunks), 1)
        scored: list[tuple[float, Chunk]] = []

        for chunk in self._chunks:
            score = 0.0
            for token, q_count in query_counts.items():
                tf = chunk.token_counts.get(token, 0)
                if tf <= 0:
                    continue
                df = self._doc_freq.get(token, 0)
                idf = 1.0 + (total_chunks / (1 + df))
                score += min(tf, q_count) * idf

            if score > min_score:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, chunk in scored[: max(top_k, 1)]:
            results.append(
                {
                    "source": chunk.source,
                    "score": round(score, 3),
                    "text": chunk.text,
                }
            )
        return results

    def build_context(self, query: str, top_k: int = 4, max_chars: int = 3200) -> tuple[str, list[dict[str, Any]]]:
        results = self.search(query=query, top_k=top_k)
        if not results:
            return "", []

        lines: list[str] = []
        total = 0
        trimmed_results: list[dict[str, Any]] = []
        for index, item in enumerate(results, start=1):
            header = f"[{index}] source={item['source']} score={item['score']}"
            block = f"{header}\n{item['text']}"
            if total + len(block) > max_chars:
                break
            lines.append(block)
            total += len(block)
            trimmed_results.append(
                {
                    "source": item["source"],
                    "score": item["score"],
                }
            )

        return "\n\n".join(lines), trimmed_results

    def status(self) -> dict[str, Any]:
        return {
            "roots": [str(root) for root in self.roots],
            "files": len(self._last_indexed_files),
            "chunks": len(self._chunks),
        }
