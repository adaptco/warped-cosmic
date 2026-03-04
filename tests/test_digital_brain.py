"""Tests for Digital Brain and Digital Thread."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from digital_brain.brain import DigitalBrain
from digital_brain.thread import DigitalThread


# =====================================================================
# DigitalBrain tests
# =====================================================================

class TestDigitalBrain:
    def test_create_repo(self):
        brain = DigitalBrain()
        repo = brain.create_repo("ml-ops", "machine-learning", "ML operations")
        assert repo.name == "ml-ops"
        assert repo.domain == "machine-learning"
        assert brain.repo_count == 1
        assert len(repo.embedding) == 32  # default dimensions

    def test_file_knowledge(self):
        brain = DigitalBrain()
        repo = brain.create_repo("physics", "science")
        entry = brain.file_knowledge(
            repo.repo_id, "Wave equation: ∂²u/∂t² = c²∂²u/∂x²", source="textbook"
        )
        assert entry.repo_id == repo.repo_id
        assert brain.entry_count == 1
        assert entry.entry_id in repo.artifacts

    def test_file_knowledge_missing_repo(self):
        brain = DigitalBrain()
        try:
            brain.file_knowledge("nonexistent", "content")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass

    def test_retrieve_returns_ranked_results(self):
        brain = DigitalBrain()
        repo = brain.create_repo("vectors", "ml")
        brain.file_knowledge(repo.repo_id, "cosine similarity for embeddings")
        brain.file_knowledge(repo.repo_id, "euclidean distance in vector spaces")
        brain.file_knowledge(repo.repo_id, "unrelated cooking recipe for pasta")

        results = brain.retrieve("vector similarity search", top_k=3)
        assert len(results) <= 3
        assert all(r.score >= 0.0 for r in results)
        # Results should be sorted by score descending
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_retrieve_with_repo_filter(self):
        brain = DigitalBrain()
        r1 = brain.create_repo("alpha", "domain-a")
        r2 = brain.create_repo("beta", "domain-b")
        brain.file_knowledge(r1.repo_id, "content in alpha")
        brain.file_knowledge(r2.repo_id, "content in beta")

        results = brain.retrieve("content", repo_filter=r1.repo_id)
        assert all(r.repo_id == r1.repo_id for r in results)

    def test_get_thread(self):
        brain = DigitalBrain()
        repo = brain.create_repo("test-repo", "testing")
        brain.file_knowledge(repo.repo_id, "entry one")
        e2 = brain.file_knowledge(repo.repo_id, "entry two")

        thread = brain.get_thread(e2.entry_id)
        assert len(thread) == 2

    def test_list_repos(self):
        brain = DigitalBrain()
        brain.create_repo("a", "da")
        brain.create_repo("b", "db")
        assert len(brain.list_repos()) == 2


# =====================================================================
# DigitalThread tests
# =====================================================================

class TestDigitalThread:
    def test_stitch_creates_node(self):
        dt = DigitalThread()
        node = dt.stitch("repo-a", "repo-b", content_summary="cross-link")
        assert node.source_repo == "repo-a"
        assert node.target_repo == "repo-b"
        assert dt.node_count == 1

    def test_get_connections(self):
        dt = DigitalThread()
        dt.stitch("repo-a", "repo-b")
        dt.stitch("repo-a", "repo-c")

        conns = dt.get_connections("repo-a")
        assert len(conns) == 2

    def test_propagate_decays_amplitude(self):
        dt = DigitalThread()
        node = dt.stitch("r1", "r2", amplitude=1.0)
        initial_amp = node.amplitude

        dt.propagate(time_step=1.0)
        assert node.amplitude <= initial_amp

    def test_collapse_state_ranks_by_strength(self):
        dt = DigitalThread()
        dt.stitch("origin", "target-a", amplitude=0.9)
        dt.stitch("origin", "target-b", amplitude=0.5)
        dt.stitch("origin", "target-c", amplitude=0.2)

        ranked = dt.collapse_state("origin")
        assert len(ranked) == 3
        # First should be strongest
        assert ranked[0][1] >= ranked[1][1]
        assert ranked[1][1] >= ranked[2][1]

    def test_propagate_kills_low_amplitude(self):
        dt = DigitalThread(decay=0.001)
        node = dt.stitch("r1", "r2", amplitude=0.01)
        dt.propagate(time_step=1.0)
        assert node.coherence == 0.0
