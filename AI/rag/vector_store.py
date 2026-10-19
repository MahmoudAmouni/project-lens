"""ChromaDB vector store: add document pieces, search them. Unchanged files are never embedded twice."""

import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path

import chromadb
import numpy as np
from chromadb.config import Settings

from AI.rag.chunker import Chunk, chunk_document
from AI.rag.keywords import keyword_bonus, keywords

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # Arabic + English, runs locally
ADD_BATCH = 1000
SEMANTIC_CANDIDATES = 40
KEYWORD_CANDIDATES = 20  # per keyword


def file_hash(path: str) -> str:
    digest = hashlib.sha1()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class VectorStore:
    """One Chroma collection per folder. A small manifest file remembers which file versions are indexed."""

    def __init__(self, persist_dir: str):
        self.persist_dir = Path(persist_dir)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir), settings=Settings(anonymized_telemetry=False)
        )
        self.collection = None
        self.manifest_path: Path | None = None
        self._model = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
            os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
            from sentence_transformers import SentenceTransformer  # slow import, only when needed

            try:
                self._model = SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)  # no internet needed
            except OSError:
                self._model = SentenceTransformer(EMBEDDING_MODEL)  # first run: download (~470 MB)
        vectors = self._model.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()

    def open_folder(self, folder: str) -> None:
        key = hashlib.sha1(str(Path(folder).resolve()).lower().encode()).hexdigest()[:16]
        name = f"folder_{key}"
        self.collection = self.client.get_or_create_collection(
            name=name, metadata={"hnsw:space": "cosine"}, embedding_function=None
        )
        self.manifest_path = self.persist_dir / f"{name}.json"

    def read_manifest(self) -> dict[str, str]:
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def index(self, folder: str, documents, on_file: Callable[[str], None] | None = None) -> dict:
        """Make the folder's collection match the readable documents. Returns counts of what was done."""
        self.open_folder(folder)
        manifest, new_manifest = self.read_manifest(), {}
        stats = {"embedded": 0, "reused": 0, "chunks": 0}
        for document in documents:
            if document.status != "ok":
                continue
            current_hash = file_hash(document.path)
            new_manifest[document.name] = current_hash
            if manifest.get(document.name) == current_hash:
                stats["reused"] += 1
                continue
            if on_file:
                on_file(document.name)
            self.collection.delete(where={"document": document.name})
            stats["chunks"] += self.add_chunks(chunk_document(document), current_hash)
            stats["embedded"] += 1
        for removed in set(manifest) - set(new_manifest):
            self.collection.delete(where={"document": removed})
        self.manifest_path.write_text(json.dumps(new_manifest, indent=1), encoding="utf-8")
        return stats

    def add_chunks(self, chunks: list[Chunk], hash_text: str) -> int:
        for start in range(0, len(chunks), ADD_BATCH):
            batch = chunks[start : start + ADD_BATCH]
            self.collection.add(
                ids=[f"{hash_text}-{start + i}" for i in range(len(batch))],
                documents=[chunk.text for chunk in batch],
                embeddings=self.embed([chunk.text for chunk in batch]),
                metadatas=[
                    {"document": c.document, "location": c.location, "page": c.page, "table_id": c.table_id}
                    for c in batch
                ],
            )
        return len(chunks)

    def search(self, query: str, document: str | None = None, top_k: int = 8) -> list[dict]:
        """Hybrid search: the closest pieces by meaning plus pieces with the query's words, best first."""
        if self.collection is None or self.collection.count() == 0:
            return []
        query_vector = self.embed([query])[0]
        where = {"document": document} if document else None
        found = self.collection.query(
            query_embeddings=[query_vector],
            n_results=min(SEMANTIC_CANDIDATES, self.collection.count()),
            where=where,
            include=["documents", "metadatas", "embeddings"],
        )
        candidates = {
            pid: (text, meta, vector)
            for pid, text, meta, vector in zip(
                found["ids"][0], found["documents"][0], found["metadatas"][0], found["embeddings"][0], strict=True
            )
        }
        words = keywords(query)
        for word in words[:3]:
            hits = self.collection.get(
                where=where, where_document={"$contains": word}, limit=KEYWORD_CANDIDATES,
                include=["documents", "metadatas", "embeddings"],
            )  # fmt: skip
            for pid, text, meta, vector in zip(
                hits["ids"], hits["documents"], hits["metadatas"], hits["embeddings"], strict=True
            ):
                candidates[pid] = (text, meta, vector)

        scored = [
            (float(np.dot(query_vector, vector)) + keyword_bonus(text, words), text, meta)
            for text, meta, vector in candidates.values()
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {"document": meta["document"], "location": meta["location"], "text": text, "score": round(score, 3)}
            for score, text, meta in scored[:top_k]
        ]
