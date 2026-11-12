"""NALAM AI RAG (Retrieval-Augmented Generation) Knowledge Engine.

Indexes project architectural documentation, algorithm specifications, API contracts,
and IVR workflows to answer queries about NALAM AI design, implementation, and loss calculations.
"""
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple


class DocumentChunk:
    def __init__(self, doc_name: str, section: str, content: str, file_path: str):
        self.doc_name = doc_name
        self.section = section
        self.content = content.strip()
        self.file_path = file_path
        self.tokens = self._tokenize(f"{doc_name} {section} {content}")

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
        stopwords = {
            "the", "and", "for", "with", "that", "this", "from", "are", "have", "has",
            "was", "were", "been", "will", "would", "should", "could", "all", "any",
            "about", "into", "through", "during", "before", "after", "above", "below",
        }
        return [w for w in words if w not in stopwords]


class RAGKnowledgeEngine:
    """In-memory semantic document chunker and BM25 retriever for NALAM AI documentation."""

    DOC_FILES = [
        "STOCK_ALGORITHM.md",
        "README.md",
        "API.md",
        "IVR_ARCHITECTURE.md",
        "IVR_API.md",
        "IVR_CALL_FLOWS.md",
        "DEMO_GUIDE.md",
        "DEMO_TEST_DATA.md",
        "FINAL_SECURITY_AUDIT.md",
        "FINAL_SMOKE_TEST_REPORT.md",
    ]

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.getcwd()
        self.chunks: List[DocumentChunk] = []
        self._doc_count = 0
        self._avg_dl = 0.0
        self._idf: Dict[str, float] = {}
        self.build_index()

    def build_index(self) -> int:
        """Scans workspace docs, splits into semantic sections, and indexes them."""
        self.chunks.clear()

        for filename in self.DOC_FILES:
            full_path = os.path.join(self.workspace_root, filename)
            if not os.path.exists(full_path):
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    text = f.read()
                self._parse_and_chunk_markdown(filename, full_path, text)
            except Exception as e:
                # Log or ignore unreadable files safely
                continue

        self._doc_count = len(self.chunks)
        if self._doc_count > 0:
            total_tokens = sum(len(c.tokens) for c in self.chunks)
            self._avg_dl = total_tokens / self._doc_count

            # Calculate document frequencies
            df: Dict[str, int] = {}
            for chunk in self.chunks:
                unique_tokens = set(chunk.tokens)
                for t in unique_tokens:
                    df[t] = df.get(t, 0) + 1

            # Calculate IDF with smoothing
            for t, count in df.items():
                self._idf[t] = math.log(1.0 + (self._doc_count - count + 0.5) / (count + 0.5))

        return len(self.chunks)

    def _parse_and_chunk_markdown(self, filename: str, file_path: str, content: str):
        """Splits markdown by headers (H1, H2, H3)."""
        sections = re.split(r"\n(?=#{1,3}\s+)", content)
        for sec in sections:
            sec = sec.strip()
            if not sec:
                continue

            lines = sec.split("\n", 1)
            first_line = lines[0].strip()
            header = re.sub(r"^#{1,3}\s*", "", first_line) if first_line.startswith("#") else "General"
            body = lines[1].strip() if len(lines) > 1 else first_line

            # If section is very long, chunk further by paragraphs
            if len(body) > 1800:
                paragraphs = body.split("\n\n")
                current_chunk = []
                current_len = 0
                part_idx = 1
                for p in paragraphs:
                    current_chunk.append(p)
                    current_len += len(p)
                    if current_len >= 1200:
                        chunk_text = "\n\n".join(current_chunk)
                        self.chunks.append(DocumentChunk(
                            doc_name=filename,
                            section=f"{header} (Part {part_idx})",
                            content=chunk_text,
                            file_path=file_path,
                        ))
                        current_chunk = []
                        current_len = 0
                        part_idx += 1
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    self.chunks.append(DocumentChunk(
                        doc_name=filename,
                        section=f"{header} (Part {part_idx})",
                        content=chunk_text,
                        file_path=file_path,
                    ))
            else:
                self.chunks.append(DocumentChunk(
                    doc_name=filename,
                    section=header,
                    content=body,
                    file_path=file_path,
                ))

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """BM25 scoring retrieval over indexed NALAM AI documentation."""
        if not self.chunks:
            self.build_index()

        query_tokens = DocumentChunk._tokenize(query)
        if not query_tokens:
            return []

        k1 = 1.5
        b = 0.75
        scored_chunks: List[Tuple[float, DocumentChunk]] = []

        for chunk in self.chunks:
            score = 0.0
            doc_len = len(chunk.tokens)
            if doc_len == 0:
                continue

            # Frequency map of tokens in this chunk
            tf: Dict[str, int] = {}
            for t in chunk.tokens:
                tf[t] = tf.get(t, 0) + 1

            for qt in query_tokens:
                if qt in tf:
                    term_freq = tf[qt]
                    idf = self._idf.get(qt, 1.0)
                    numerator = term_freq * (k1 + 1.0)
                    denominator = term_freq + k1 * (1.0 - b + b * (doc_len / (self._avg_dl or 1.0)))
                    score += idf * (numerator / denominator)

                    # Boost for section header match
                    if qt in chunk.section.lower():
                        score += 2.0

            if score > 0.1:
                scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, chunk in scored_chunks[:top_k]:
            results.append({
                "document": chunk.doc_name,
                "section": chunk.section,
                "content": chunk.content[:800],
                "score": round(score, 3),
                "file_path": chunk.file_path,
            })

        return results


# Global singleton instance
rag_engine = RAGKnowledgeEngine()
