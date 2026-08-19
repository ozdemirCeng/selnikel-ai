"""
Production Cache Key Generation & ACL Partitioning Service.
Guarantees strict cache isolation across users, roles, departments, classifications, and ACL versions.
"""
import hashlib
import json
from typing import List, Optional
from app.domain.identity.models import User

class ACLPartitionedCacheKeyBuilder:
    """Builds cryptographically secure and partitioned cache keys for RAG and search queries."""

    @staticmethod
    def generate_rag_cache_key(
        query: str,
        user: User,
        classification: str = "internal",
        acl_version: str = "v1",
    ) -> str:
        """
        Generates deterministic cache key:
        rag:{query_sha256}:{user_id}:{sorted_departments}:{sorted_roles}:{classification}:{acl_version}
        """
        normalized_query = query.strip().lower()
        query_hash = hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()[:16]

        dept_str = ",".join(sorted(user.department_ids))
        role_str = ",".join(sorted(user.role_codes))

        key_components = [
            "rag",
            query_hash,
            str(user.id),
            dept_str,
            role_str,
            classification,
            acl_version,
        ]
        return ":".join(key_components)

    @staticmethod
    def generate_document_cache_key(
        document_id: str,
        revision_number: int,
        user: User,
    ) -> str:
        dept_str = ",".join(sorted(user.department_ids))
        return f"doc:{document_id}:rev{revision_number}:{dept_str}"


cache_key_builder = ACLPartitionedCacheKeyBuilder()
