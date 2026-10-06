from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "data" / "documents"

@dataclass
class Chunk:
    chunk_id: str
    text: str
    source: str
    topic: str


def rewrite_query(question: str) -> str:
    """Lightweight deterministic query expansion; an LLM can replace this in production."""
    q = re.sub(r"\s+", " ", question.strip())
    expansions = {
        "pre auth": "preauthorization",
        "pre-auth": "preauthorization",
        "claim": "claim submission reimbursement adjudication",
        "bp": "blood pressure hypertension",
        "meds": "medication safety prescribed dose schedule",
    }
    for short, expanded in expansions.items():
        if short in q.lower():
            q = f"{q} {expanded}"
    return q


def load_documents(doc_dir: Path = DOCS_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(doc_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        sections = [s.strip() for s in re.split(r"(?=^## )", raw, flags=re.MULTILINE) if s.strip()]
        for i, section in enumerate(sections):
            heading = section.splitlines()[0].lstrip("# ").strip()
            topic = heading.lower().replace(" ", "-")
            chunks.append(Chunk(f"{path.stem}-{i}", section, path.name, topic))
    return chunks


class HealthcareRAG:
    def __init__(self) -> None:
        self.model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.collection_name = os.getenv("CHROMA_COLLECTION", "healthcare_knowledge")
        self.chroma_path = os.getenv("CHROMA_PATH", str(ROOT / "chroma_db"))
        self.top_k = int(os.getenv("TOP_K", "5"))
        self.min_relevance = float(os.getenv("MIN_RELEVANCE", "0.25"))
        self.embedder = SentenceTransformer(self.model_name)
        self.client = chromadb.PersistentClient(path=self.chroma_path)
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def index_documents(self, chunks: Iterable[Chunk] | None = None) -> int:
        chunks = list(chunks or load_documents())
        if not chunks:
            return 0
        embeddings = self.embedder.encode([c.text for c in chunks], normalize_embeddings=True).tolist()
        self.collection.upsert(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[{"source": c.source, "topic": c.topic} for c in chunks],
            embeddings=embeddings,
        )
        return len(chunks)

    def retrieve(self, question: str, topic: str | None = None) -> list[dict]:
        if self.collection.count() == 0:
            self.index_documents()
        rewritten = rewrite_query(question)
        embedding = self.embedder.encode([rewritten], normalize_embeddings=True).tolist()
        kwargs = {"query_embeddings": embedding, "n_results": self.top_k,
                  "include": ["documents", "metadatas", "distances"]}
        if topic:
            kwargs["where"] = {"topic": topic.lower().replace(" ", "-")}
        result = self.collection.query(**kwargs)
        rows = []
        for doc, metadata, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
            relevance = max(0.0, 1.0 - float(distance))
            if relevance >= self.min_relevance:
                rows.append({"text": doc, "source": metadata["source"], "topic": metadata["topic"], "relevance": relevance})
        return rows

    def answer(self, question: str, topic: str | None = None) -> str:
        contexts = self.retrieve(question, topic)
        if not contexts:
            return "I could not find sufficiently relevant information in the healthcare knowledge base."
        context = "\n\n".join(f"[{i+1}] {r['text']} (source: {r['source']})" for i, r in enumerate(contexts))
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or OpenAI is None:
            return "LLM mode is not configured. Retrieved evidence:\n\n" + context
        kwargs = {"api_key": api_key}
        if os.getenv("OPENAI_BASE_URL"):
            kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")
        client = OpenAI(**kwargs)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a healthcare document assistant. Answer only from supplied evidence. Do not diagnose, prescribe, or invent policy. If evidence is insufficient, say so. Cite evidence as [1], [2]."},
                {"role": "user", "content": f"Evidence:\n{context}\n\nQuestion: {question}"},
            ],
        )
        return response.choices[0].message.content or "No answer generated."
