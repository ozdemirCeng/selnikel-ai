import pytest
from app.services.embedding.fallback import DeterministicHashEmbeddingProvider
from app.services.embedding.factory import EmbeddingProviderFactory


@pytest.mark.asyncio
async def test_deterministic_hash_embeddings():
    provider = DeterministicHashEmbeddingProvider(dimension=1024)
    assert provider.dimension == 1024

    texts = [
        "Selnikel Endüstriyel Kazan Buhar Kapasitesi 5000 kg/h",
        "Brülör nozül bakım periyodu 500 çalışma saati",
    ]

    # Test embed_documents
    doc_vectors = await provider.embed_documents(texts)
    assert len(doc_vectors) == 2
    assert len(doc_vectors[0]) == 1024
    assert len(doc_vectors[1]) == 1024

    # Verify unit normalization (length = 1.0)
    norm0 = sum(x * x for x in doc_vectors[0]) ** 0.5
    norm1 = sum(x * x for x in doc_vectors[1]) ** 0.5
    assert abs(norm0 - 1.0) < 1e-4
    assert abs(norm1 - 1.0) < 1e-4

    # Test embed_query
    query_vec = await provider.embed_query("buhar kazanı kapasitesi")
    assert len(query_vec) == 1024

    # Test embed_sparse
    sparse_res = await provider.embed_sparse(texts)
    assert len(sparse_res) == 2
    assert isinstance(sparse_res[0], dict)
    assert len(sparse_res[0]) > 0


@pytest.mark.asyncio
async def test_embedding_factory_resolution():
    mock_prov = EmbeddingProviderFactory.get_provider(force_provider="mock")
    assert mock_prov.dimension == 1024

    bge_prov = EmbeddingProviderFactory.get_provider(force_provider="bge-m3")
    assert bge_prov.dimension == 1024
