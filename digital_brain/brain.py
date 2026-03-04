"""Digital Brain — filing system for cross-functional knowledge as repos.

Models knowledge domains as virtual GitHub repositories with semantic
embeddings, enabling cross-domain retrieval and thread stitching.
"""

from __future__ import annotations

import hashlib
import math
from typing import Dict, List, Optional, Sequence, Tuple

from config import VECTOR_DIMENSIONS
from schemas import KnowledgeEntry, KnowledgeRepo, SearchResult


class DigitalBrain:
    """Filing system that models cross-functional knowledge as repositories.

    Each knowledge domain is stored as a ``KnowledgeRepo`` with entries
    that carry deterministic embeddings for cosine-similarity retrieval.
    """

    def __init__(self, dimensions: int = VECTOR_DIMENSIONS) -> None:
        self._repos: Dict[str, KnowledgeRepo] = {}
        self._entries: Dict[str, KnowledgeEntry] = {}
        self._dimensions = dimensions

    # ------------------------------------------------------------------
    # Embedding helpers
    # ------------------------------------------------------------------

    def _deterministic_embedding(self, text: str) -> List[float]:
        """Hash-based deterministic embedding (no GPU required)."""
        digest = hashlib.sha256(text.encode()).hexdigest()
        raw = [
            int(digest[i : i + 2], 16) / 255.0
            for i in range(0, min(len(digest), self._dimensions * 2), 2)
        ]
        # Pad or truncate to target dimensions
        while len(raw) < self._dimensions:
            raw.append(0.0)
        # L2-normalize
        norm = math.sqrt(sum(v * v for v in raw)) or 1.0
        return [v / norm for v in raw[: self._dimensions]]

    @staticmethod
    def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
        return dot / (norm_a * norm_b)

    # ------------------------------------------------------------------
    # Repository management
    # ------------------------------------------------------------------

    def create_repo(
        self,
        name: str,
        domain: str,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> KnowledgeRepo:
        """Create a new knowledge repository."""
        repo = KnowledgeRepo(
            name=name,
            domain=domain,
            description=description,
            embedding=self._deterministic_embedding(f"{domain} {name} {description}"),
            tags=tags or [],
        )
        self._repos[repo.repo_id] = repo
        return repo

    def list_repos(self) -> List[KnowledgeRepo]:
        """List all knowledge repositories."""
        return list(self._repos.values())

    def get_repo(self, repo_id: str) -> Optional[KnowledgeRepo]:
        """Get a repo by ID."""
        return self._repos.get(repo_id)

    # ------------------------------------------------------------------
    # Knowledge filing
    # ------------------------------------------------------------------

    def file_knowledge(
        self,
        repo_id: str,
        content: str,
        source: str = "",
        tags: Optional[List[str]] = None,
    ) -> KnowledgeEntry:
        """File a piece of knowledge into a repository."""
        repo = self._repos.get(repo_id)
        if repo is None:
            raise KeyError(f"Repository {repo_id} not found")

        entry = KnowledgeEntry(
            repo_id=repo_id,
            content=content,
            embedding=self._deterministic_embedding(content),
            source=source,
            tags=tags or [],
        )
        self._entries[entry.entry_id] = entry
        repo.artifacts.append(entry.entry_id)
        return entry

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        repo_filter: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Retrieve knowledge entries ranked by cosine similarity."""
        q_emb = self._deterministic_embedding(query)
        scored: List[Tuple[float, KnowledgeEntry]] = []

        for entry in self._entries.values():
            if repo_filter and entry.repo_id != repo_filter:
                continue
            sim = self._cosine_similarity(q_emb, entry.embedding)
            if sim >= min_score:
                scored.append((sim, entry))

        scored.sort(key=lambda t: t[0], reverse=True)

        results: List[SearchResult] = []
        for score, entry in scored[:top_k]:
            results.append(
                SearchResult(
                    entry_id=entry.entry_id,
                    repo_id=entry.repo_id,
                    content=entry.content,
                    score=score,
                    source=entry.source,
                )
            )
        return results

    def get_thread(self, entry_id: str) -> List[KnowledgeEntry]:
        """Get all entries in the same repo as the given entry (the thread)."""
        entry = self._entries.get(entry_id)
        if entry is None:
            return []
        return [
            e for e in self._entries.values() if e.repo_id == entry.repo_id
        ]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def repo_count(self) -> int:
        return len(self._repos)

    @property
    def entry_count(self) -> int:
        return len(self._entries)
