"""
Comprehensive tests for Embedding System

Tests cover:
- EmbeddingModel dataclass
- EmbeddingSystem class
  - Initialization and lazy loading
  - Local embedding generation
  - Caching (memory and disk)
  - Cosine similarity
  - Similarity search
  - Text clustering
  - Semantic index creation and search
- TrainingDataCollector class
  - Initialization
  - Training data collection
  - Statistics generation
  - Data export
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import json
import tempfile
import os
from pathlib import Path
from dataclasses import fields


class TestEmbeddingModel:
    """Tests for EmbeddingModel dataclass"""

    def test_creation_minimal(self):
        """Test minimal EmbeddingModel creation"""
        from api.embedding_system import EmbeddingModel

        model = EmbeddingModel(
            name="test_model",
            dimension=384,
            model_type="local"
        )

        assert model.name == "test_model"
        assert model.dimension == 384
        assert model.model_type == "local"
        assert model.local_path is None

    def test_creation_with_path(self):
        """Test EmbeddingModel with local path"""
        from api.embedding_system import EmbeddingModel

        model = EmbeddingModel(
            name="custom_model",
            dimension=768,
            model_type="custom",
            local_path="/path/to/model"
        )

        assert model.name == "custom_model"
        assert model.local_path == "/path/to/model"

    def test_dataclass_fields(self):
        """Test EmbeddingModel has expected fields"""
        from api.embedding_system import EmbeddingModel

        field_names = [f.name for f in fields(EmbeddingModel)]

        assert "name" in field_names
        assert "dimension" in field_names
        assert "model_type" in field_names
        assert "local_path" in field_names


class TestEmbeddingSystemInit:
    """Tests for EmbeddingSystem initialization"""

    def test_init_default_config(self, tmp_path):
        """Test initialization with default config"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()

            assert system.model_config.name == "local_semantic"
            assert system.model_config.dimension == 384
            assert system.model_config.model_type == "local"
            assert system.embedding_cache == {}

    def test_init_custom_config(self, tmp_path):
        """Test initialization with custom config"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem, EmbeddingModel

            custom_config = EmbeddingModel(
                name="custom",
                dimension=512,
                model_type="sentence-transformers"
            )
            system = EmbeddingSystem(model_config=custom_config)

            assert system.model_config.name == "custom"
            assert system.model_config.dimension == 512

    def test_creates_cache_dir(self, tmp_path):
        """Test cache directory is created"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()

            cache_dir = tmp_path / ".agent" / "embeddings"
            assert cache_dir.exists()

    def test_sentence_transformers_detection(self, tmp_path):
        """Test sentence transformers detection"""
        with patch.object(Path, 'home', return_value=tmp_path):
            with patch.dict('sys.modules', {'sentence_transformers': Mock()}):
                from api.embedding_system import EmbeddingSystem

                system = EmbeddingSystem()
                # With sentence_transformers available, use_transformer should be True
                # But model not loaded yet (lazy loading)
                assert system._model_loaded is False


class TestLocalEmbedding:
    """Tests for local embedding generation"""

    def test_generates_embedding(self, tmp_path):
        """Test local embedding generates correct dimension"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False  # Force local

            embedding = system._local_embedding("test text")

            assert isinstance(embedding, np.ndarray)
            assert len(embedding) == 384

    def test_embedding_is_normalized(self, tmp_path):
        """Test embedding is L2 normalized"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            embedding = system._local_embedding("test text for normalization")
            norm = np.linalg.norm(embedding)

            # Should be close to 1.0 (L2 normalized)
            assert 0.99 < norm < 1.01

    def test_similar_texts_have_similar_embeddings(self, tmp_path):
        """Test similar texts produce similar embeddings"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            emb1 = system._local_embedding("create a function")
            emb2 = system._local_embedding("create a method")
            emb3 = system._local_embedding("deploy to production")

            # Similar texts should have higher similarity
            sim_similar = system.cosine_similarity(emb1, emb2)
            sim_different = system.cosine_similarity(emb1, emb3)

            assert sim_similar > sim_different

    def test_empty_text_handling(self, tmp_path):
        """Test handling of empty text"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            embedding = system._local_embedding("")

            assert isinstance(embedding, np.ndarray)
            assert len(embedding) == 384

    def test_unicode_text_handling(self, tmp_path):
        """Test handling of unicode text"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            embedding = system._local_embedding("create a function for caf\u00e9 日本語")

            assert isinstance(embedding, np.ndarray)
            assert len(embedding) == 384

    def test_semantic_keywords_influence(self, tmp_path):
        """Test semantic keywords affect embedding"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            # Keywords like 'fix', 'bug', 'error' should create distinct embeddings
            emb_bug = system._local_embedding("fix the bug")
            emb_create = system._local_embedding("create new feature")

            # These should be different due to semantic features
            similarity = system.cosine_similarity(emb_bug, emb_create)
            assert similarity < 0.9


class TestGetEmbedding:
    """Tests for get_embedding method"""

    def test_returns_embedding(self, tmp_path):
        """Test get_embedding returns array"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            embedding = system.get_embedding("test text")

            assert isinstance(embedding, np.ndarray)

    def test_caching_works(self, tmp_path):
        """Test embedding caching"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            # First call
            emb1 = system.get_embedding("test text")

            # Second call should use cache
            emb2 = system.get_embedding("test text")

            np.testing.assert_array_equal(emb1, emb2)
            assert len(system.embedding_cache) == 1

    def test_cache_bypass(self, tmp_path):
        """Test cache can be bypassed"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            # First call
            emb1 = system.get_embedding("test text", use_cache=True)

            # Clear cache
            system.embedding_cache = {}

            # With cache bypass, should recalculate
            emb2 = system.get_embedding("test text", use_cache=False)

            # Should be same result (deterministic)
            np.testing.assert_array_almost_equal(emb1, emb2)

    def test_truncates_long_text(self, tmp_path):
        """Test long text is truncated"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            # Create very long text
            long_text = "word " * 5000  # Way over 10000 chars

            # Should not raise
            embedding = system.get_embedding(long_text)

            assert isinstance(embedding, np.ndarray)


class TestGetEmbeddingsBatch:
    """Tests for batch embedding"""

    def test_batch_embedding(self, tmp_path):
        """Test batch embedding returns correct shape"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            texts = ["text one", "text two", "text three"]
            embeddings = system.get_embeddings_batch(texts)

            assert isinstance(embeddings, np.ndarray)
            assert embeddings.shape == (3, 384)

    def test_empty_batch(self, tmp_path):
        """Test empty batch handling"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            embeddings = system.get_embeddings_batch([])

            assert len(embeddings) == 0


class TestCosineSimilarity:
    """Tests for cosine similarity calculation"""

    def test_identical_vectors(self, tmp_path):
        """Test identical vectors have similarity 1.0"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()

            vec = np.array([1.0, 2.0, 3.0])
            similarity = system.cosine_similarity(vec, vec)

            assert abs(similarity - 1.0) < 0.001

    def test_orthogonal_vectors(self, tmp_path):
        """Test orthogonal vectors have similarity 0.0"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()

            vec1 = np.array([1.0, 0.0, 0.0])
            vec2 = np.array([0.0, 1.0, 0.0])
            similarity = system.cosine_similarity(vec1, vec2)

            assert abs(similarity) < 0.001

    def test_zero_vector_handling(self, tmp_path):
        """Test zero vector returns 0.0"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()

            vec1 = np.array([1.0, 2.0, 3.0])
            vec2 = np.array([0.0, 0.0, 0.0])
            similarity = system.cosine_similarity(vec1, vec2)

            assert similarity == 0.0


class TestFindSimilar:
    """Tests for find_similar method"""

    def test_finds_similar_texts(self, tmp_path):
        """Test finds similar texts"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            candidates = [
                "create a function",
                "create a method",
                "deploy to production",
                "push to server"
            ]

            results = system.find_similar("create a class", candidates, top_k=2)

            assert len(results) == 2
            # Results should be tuples of (text, similarity)
            assert isinstance(results[0], tuple)
            assert isinstance(results[0][1], float)

    def test_respects_top_k(self, tmp_path):
        """Test respects top_k limit"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            candidates = ["text1", "text2", "text3", "text4", "text5"]

            results = system.find_similar("query", candidates, top_k=3)

            assert len(results) == 3

    def test_sorted_by_similarity(self, tmp_path):
        """Test results are sorted by similarity (descending)"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            candidates = ["a", "b", "c", "d"]
            results = system.find_similar("query", candidates, top_k=4)

            # Check sorted descending
            similarities = [r[1] for r in results]
            assert similarities == sorted(similarities, reverse=True)


class TestClusterTexts:
    """Tests for text clustering"""

    def test_clusters_texts(self, tmp_path):
        """Test clustering creates expected number of clusters"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            texts = ["create function", "create method", "deploy app", "deploy server", "fix bug", "fix error"]

            clusters = system.cluster_texts(texts, n_clusters=3)

            assert isinstance(clusters, dict)
            assert len(clusters) == 3

    def test_empty_texts(self, tmp_path):
        """Test clustering with empty list"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            clusters = system.cluster_texts([], n_clusters=3)

            assert clusters == {}

    def test_fewer_texts_than_clusters(self, tmp_path):
        """Test with fewer texts than clusters"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            texts = ["text1", "text2"]
            clusters = system.cluster_texts(texts, n_clusters=5)

            # Should only create as many clusters as there are texts
            assert len(clusters) <= 2


class TestCachePersistence:
    """Tests for cache save/load"""

    def test_save_cache(self, tmp_path):
        """Test saving cache to disk"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            # Add something to cache
            system.get_embedding("test text")

            # Save cache
            system.save_cache()

            # Check file exists
            cache_file = tmp_path / ".agent" / "embeddings" / "embedding_cache.json"
            assert cache_file.exists()

    def test_load_cache(self, tmp_path):
        """Test loading cache from disk"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system1 = EmbeddingSystem()
            system1.use_transformer = False

            # Add and save
            system1.get_embedding("test text")
            system1.save_cache()

            # Create new system - should load cache
            system2 = EmbeddingSystem()
            system2.load_cache()

            assert len(system2.embedding_cache) == 1

    def test_load_empty_cache(self, tmp_path):
        """Test loading when no cache exists"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.load_cache()

            assert system.embedding_cache == {}

    def test_load_corrupted_cache(self, tmp_path):
        """Test loading corrupted cache file"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            # Create corrupted cache file
            cache_dir = tmp_path / ".agent" / "embeddings"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / "embedding_cache.json"
            cache_file.write_text("not valid json {{{")

            system = EmbeddingSystem()

            # Should handle gracefully
            assert system.embedding_cache == {}


class TestSemanticIndex:
    """Tests for semantic index creation and search"""

    def test_create_index(self, tmp_path):
        """Test creating semantic index"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            texts = ["text one", "text two", "text three"]
            index = system.create_semantic_index(texts)

            assert index["size"] == 3
            assert index["dimension"] == 384
            assert len(index["texts"]) == 3

    def test_search_index(self, tmp_path):
        """Test searching semantic index"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            texts = ["create function", "deploy app", "fix bug"]
            system.create_semantic_index(texts)

            results = system.search_semantic_index("create method", top_k=2)

            assert len(results) == 2
            assert isinstance(results[0], tuple)

    def test_search_empty_index(self, tmp_path):
        """Test searching when no index exists"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()

            results = system.search_semantic_index("query")

            assert results == []


class TestTrainingDataCollector:
    """Tests for TrainingDataCollector class"""

    def test_init(self, tmp_path):
        """Test initialization"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            collector = TrainingDataCollector()

            assert collector.training_data["commands"] == []
            assert collector.training_data["patterns"] == []

    def test_init_with_learning_system(self, tmp_path):
        """Test initialization with learning system"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            mock_system = Mock()
            collector = TrainingDataCollector(learning_system=mock_system)

            assert collector.learning_system is mock_system

    def test_creates_data_dir(self, tmp_path):
        """Test data directory is created"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            collector = TrainingDataCollector()

            data_dir = tmp_path / ".agent" / "training_data"
            assert data_dir.exists()

    def test_add_training_example(self, tmp_path):
        """Test adding training example"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            collector = TrainingDataCollector()

            collector.add_training_example(
                input_text="create a REST API",
                task_type="code_generation",
                tool="aider",
                success=True,
                output="API created"
            )

            assert len(collector.training_data["commands"]) == 1
            assert collector.training_data["commands"][0]["command"] == "create a REST API"

    def test_collect_from_history_no_system(self, tmp_path):
        """Test collecting with no learning system"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            collector = TrainingDataCollector()

            data = collector.collect_from_history()

            assert data == collector.training_data

    def test_collect_from_history_with_system(self, tmp_path):
        """Test collecting from learning system"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            # Mock learning system with database
            mock_system = Mock()
            mock_conn = Mock()
            mock_system.conn = mock_conn

            # Mock two database calls: commands then patterns
            # Each execute().fetchall() returns different data
            command_result = Mock()
            command_result.fetchall.return_value = [
                {
                    "command": "test command",
                    "task_type": "test",
                    "tool_used": "aider",
                    "success": True,
                    "execution_time": 1.0
                }
            ]

            pattern_result = Mock()
            pattern_result.fetchall.return_value = [
                {
                    "pattern_text": "test pattern",
                    "confidence": 0.8,
                    "success_count": 10,
                    "failure_count": 2
                }
            ]

            # Return different results for each execute() call
            mock_conn.execute.side_effect = [command_result, pattern_result]

            collector = TrainingDataCollector(learning_system=mock_system)
            data = collector.collect_from_history()

            assert len(data["commands"]) == 1
            assert len(data["patterns"]) == 1
            assert data["commands"][0]["command"] == "test command"
            assert data["patterns"][0]["pattern"] == "test pattern"

    def test_prepare_for_training(self, tmp_path):
        """Test preparing data for training"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            collector = TrainingDataCollector()

            # Add some examples
            collector.training_data["commands"] = [
                {"command": "cmd1", "task_type": "type1", "tool": "tool1", "success": True},
                {"command": "cmd2", "task_type": "type2", "tool": "tool2", "success": False}
            ]

            X, y = collector.prepare_for_training()

            assert len(X) == 2
            assert len(y) == 2
            assert X[0] == "cmd1"
            assert y[0]["task_type"] == "type1"

    def test_get_statistics(self, tmp_path):
        """Test getting statistics"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            collector = TrainingDataCollector()

            collector.training_data["commands"] = [
                {"command": "cmd1", "task_type": "type1", "tool": "tool1", "success": True},
                {"command": "cmd2", "task_type": "type2", "tool": "tool2", "success": False}
            ]
            collector.training_data["patterns"] = [
                {"confidence": 0.9},
                {"confidence": 0.5}
            ]

            stats = collector.get_statistics()

            assert stats["total_examples"] == 2
            assert stats["successful_examples"] == 1
            assert stats["unique_task_types"] == 2
            assert stats["patterns_learned"] == 2
            assert stats["high_confidence_patterns"] == 1

    def test_save_training_data(self, tmp_path):
        """Test saving training data"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            collector = TrainingDataCollector()
            collector.add_training_example("test", "type", "tool", True)

            collector.save_training_data()

            data_file = tmp_path / ".agent" / "training_data" / "training_data.json"
            assert data_file.exists()

    def test_load_training_data(self, tmp_path):
        """Test loading training data"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            # Save data
            collector1 = TrainingDataCollector()
            collector1.add_training_example("test", "type", "tool", True)
            collector1.save_training_data()

            # Load in new collector
            collector2 = TrainingDataCollector()
            collector2.load_training_data()

            assert len(collector2.training_data["commands"]) == 1

    def test_export_for_fine_tuning(self, tmp_path):
        """Test exporting for fine-tuning"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            collector = TrainingDataCollector()
            collector.training_data["commands"] = [
                {"command": "cmd1", "task_type": "type1", "tool": "tool1", "success": True},
                {"command": "cmd2", "task_type": "type2", "tool": "tool2", "success": False}
            ]

            output_path = tmp_path / "fine_tune.jsonl"
            collector.export_for_fine_tuning(str(output_path))

            assert output_path.exists()

            # Check format - JSONL with only successful examples
            with open(output_path) as f:
                lines = f.readlines()
            assert len(lines) == 1  # Only successful examples

    def test_generate_synthetic_data(self, tmp_path):
        """Test generating synthetic data from templates"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            collector = TrainingDataCollector()

            # Mock template library
            mock_template = Mock()
            mock_template.examples = ["example1", "example2"]
            mock_template.category.value = "test_category"
            mock_template.name = "test_template"
            mock_template.tool_suggestions = ["tool1"]
            mock_template.confidence_threshold = 0.8

            mock_library = Mock()
            mock_library.templates = [mock_template]

            synthetic = collector.generate_synthetic_data(mock_library)

            assert len(synthetic) == 2
            assert synthetic[0]["input"] == "example1"
            assert synthetic[0]["task_type"] == "test_category"


class TestEdgeCases:
    """Tests for edge cases"""

    def test_very_long_text(self, tmp_path):
        """Test handling very long text"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            # 20000 character text
            long_text = "word " * 4000
            embedding = system.get_embedding(long_text)

            assert isinstance(embedding, np.ndarray)
            assert len(embedding) == 384

    def test_special_characters(self, tmp_path):
        """Test handling special characters"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            text = "function() { return x + y; } // comment"
            embedding = system.get_embedding(text)

            assert isinstance(embedding, np.ndarray)

    def test_whitespace_only(self, tmp_path):
        """Test handling whitespace-only text"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            embedding = system.get_embedding("   \t\n   ")

            assert isinstance(embedding, np.ndarray)

    def test_numeric_text(self, tmp_path):
        """Test handling numeric text"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            embedding = system.get_embedding("12345 67890")

            assert isinstance(embedding, np.ndarray)


class TestIntegration:
    """Integration tests"""

    def test_full_embedding_workflow(self, tmp_path):
        """Test complete embedding workflow"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import EmbeddingSystem

            system = EmbeddingSystem()
            system.use_transformer = False

            # Create embeddings
            texts = ["create function", "create method", "deploy app"]

            # Get embeddings
            embeddings = system.get_embeddings_batch(texts)

            # Find similar
            results = system.find_similar("create class", texts, top_k=2)

            # Results should favor "create" texts
            assert any("create" in r[0] for r in results)

            # Create and search index
            system.create_semantic_index(texts)
            search_results = system.search_semantic_index("create something", top_k=2)

            assert len(search_results) > 0

            # Save and reload cache
            system.save_cache()
            system.load_cache()

            assert len(system.embedding_cache) > 0

    def test_training_collector_workflow(self, tmp_path):
        """Test complete training data collector workflow"""
        with patch.object(Path, 'home', return_value=tmp_path):
            from api.embedding_system import TrainingDataCollector

            collector = TrainingDataCollector()

            # Add examples
            for i in range(5):
                collector.add_training_example(
                    f"command {i}",
                    f"type_{i % 2}",
                    f"tool_{i % 3}",
                    i % 2 == 0
                )

            # Get statistics
            stats = collector.get_statistics()
            assert stats["total_examples"] == 5

            # Prepare for training
            X, y = collector.prepare_for_training()
            assert len(X) == 5

            # Save and load
            collector.save_training_data()

            new_collector = TrainingDataCollector()
            new_collector.load_training_data()
            assert len(new_collector.training_data["commands"]) == 5
