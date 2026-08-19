import hashlib
import math
from typing import Dict, List
from app.services.embedding.base import BaseEmbeddingProvider


class DeterministicHashEmbeddingProvider(BaseEmbeddingProvider):
    """Zero-dependency, instantaneous deterministic embedding provider.
    Generates unit-normalized 1024-dimensional vectors based on cryptographic token hashing.
    Used for rapid unit testing, CI pipelines, and offline environments.
    """

    def __init__(self, dimension: int = 1024):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]

    async def embed_query(self, text: str) -> List[float]:
        return self._embed_single(text)

    async def embed_sparse(self, texts: List[str]) -> List[Dict[int, float]]:
        """Generate pseudo-sparse token weights based on word hash indices."""
        results = []
        for t in texts:
            words = t.lower().split()
            sparse_dict: Dict[int, float] = {}
            for w in set(words):
                if len(w) > 2:
                    h = int(hashlib.md5(w.encode("utf-8")).hexdigest()[:4], 16) % 30000
                    sparse_dict[h] = float(min(5.0, words.count(w) * 0.5 + 1.0))
            results.append(sparse_dict)
        return results

    def _embed_single(self, text: str) -> List[float]:
        vec = [0.0] * self._dimension
        cleaned = text.strip().lower()
        if not cleaned:
            return vec

        # Use sliding character n-grams and hashing to populate vector dimensions
        words = cleaned.split()
        for idx, word in enumerate(words):
            word_hash = hashlib.sha256(f"{word}_{idx % 8}".encode("utf-8")).digest()
            for b_idx, byte_val in enumerate(word_hash):
                dim_idx = (int(byte_val) * (b_idx + 1) * 31) % self._dimension
                val = math.sin((byte_val / 255.0) * math.pi * 2 + idx)
                vec[dim_idx] += val

        # Normalize to unit sphere (L2 norm)
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            return [x / norm for x in vec]
        return vec
