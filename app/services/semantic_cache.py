from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.config import settings
from app.models import SemanticCacheEntry


_model = None
_model_lock = threading.Lock()


@dataclass
class CacheMatch:
    response_text: str
    provider_name: str
    score: float


class SemanticCacheService:
    def __init__(self):
        self.threshold = settings.semantic_cache_threshold
        self.top_k = settings.semantic_cache_top_k

    def _get_model(self) -> SentenceTransformer:
        global _model
        if _model is None:
            with _model_lock:
                if _model is None:
                    _model = SentenceTransformer("all-MiniLM-L6-v2")
        return _model

    def embed_text(self, text: str) -> list[float]:
        model = self._get_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def find_match(self, db: Session, prompt: str) -> tuple[CacheMatch | None, list[float]]:
        query_embedding = self.embed_text(prompt)
        entries = (
            db.query(SemanticCacheEntry)
            .order_by(SemanticCacheEntry.created_at.desc())
            .limit(self.top_k)
            .all()
        )

        best_match = None
        best_score = -1.0
        query_vec = np.array(query_embedding, dtype=np.float32)

        for entry in entries:
            candidate = np.array(entry.prompt_embedding, dtype=np.float32)
            score = float(np.dot(query_vec, candidate))
            if score > best_score:
                best_score = score
                best_match = entry

        if best_match is not None and best_score >= self.threshold:
            return (
                CacheMatch(
                    response_text=best_match.response_text,
                    provider_name=best_match.provider_name,
                    score=best_score,
                ),
                query_embedding,
            )

        return None, query_embedding

    def store(self, db: Session, prompt: str, embedding: list[float], response_text: str, provider_name: str) -> SemanticCacheEntry:
        entry = SemanticCacheEntry(
            prompt_text=prompt,
            prompt_embedding=embedding,
            response_text=response_text,
            provider_name=provider_name,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
