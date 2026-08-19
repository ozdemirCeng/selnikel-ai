from typing import Dict, List, Optional
from app.core.logging import logger
from app.services.embedding.base import BaseEmbeddingProvider
from app.services.embedding.fallback import DeterministicHashEmbeddingProvider


class BGEM3EmbeddingProvider(BaseEmbeddingProvider):
    """Local embedding provider powered by BAAI/bge-m3.
    Produces 1024-dimensional dense vectors and sparse lexical weights.
    """

    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._fallback = DeterministicHashEmbeddingProvider(dimension=1024)
        self._init_model()

    def _init_model(self) -> None:
        try:
            from FlagEmbedding import BGEM3FlagModel

            logger.info(f"Loading local BGE-M3 model '{self.model_name}' on {self.device}...")
            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=(self.device != "cpu"),
                device=self.device,
            )
            logger.info("Local BGE-M3 model loaded successfully.")
        except ImportError:
            logger.warning(
                "FlagEmbedding package not installed. Running BGEM3 in deterministic fallback mode."
            )
            self._model = None
        except Exception as e:
            logger.warning(
                f"Failed to load local BGE-M3 weights ({e}). Running in deterministic fallback mode."
            )
            self._model = None

    @property
    def dimension(self) -> int:
        return 1024

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if self._model is not None:
            try:
                output = self._model.encode(
                    texts,
                    batch_size=16,
                    max_length=8192,
                    return_dense=True,
                    return_sparse=False,
                    return_colbert_vecs=False,
                )
                return [v.tolist() for v in output["dense_vecs"]]
            except Exception as e:
                logger.error(f"BGE-M3 encode failed: {e}. Falling back.")

        return await self._fallback.embed_documents(texts)

    async def embed_query(self, text: str) -> List[float]:
        res = await self.embed_documents([text])
        return res[0]

    async def embed_sparse(self, texts: List[str]) -> List[Dict[int, float]]:
        if self._model is not None:
            try:
                output = self._model.encode(
                    texts,
                    batch_size=16,
                    max_length=8192,
                    return_dense=False,
                    return_sparse=True,
                )
                return [
                    {int(k): float(v) for k, v in item.items()}
                    for item in output["lexical_weights"]
                ]
            except Exception as e:
                logger.error(f"BGE-M3 sparse encode failed: {e}. Falling back.")

        return await self._fallback.embed_sparse(texts)
