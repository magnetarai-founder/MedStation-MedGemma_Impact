#!/usr/bin/env python3
"""
Embedding System for Jarvis
Handles semantic embeddings for memory and NLP understanding
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass
import pickle
import threading


@dataclass
class EmbeddingModel:
    """Configuration for embedding models"""
    name: str
    dimension: int
    model_type: str  # sentence-transformers, openai, custom
    local_path: Optional[str] = None
    
    
class EmbeddingSystem:
    """
    Lightweight embedding system that works with local models
    Can be extended to use sentence-transformers, OpenAI, or custom models
    """
    
    def __init__(self, model_config: Optional[EmbeddingModel] = None):
        self.cache_dir = Path.home() / ".agent" / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Default to lightweight local embeddings
        self.model_config = model_config or EmbeddingModel(
            name="local_semantic",
            dimension=384,  # Small but effective
            model_type="local"
        )
        
        self.embedding_cache = {}
        self.load_cache()
        
        # Lazy load sentence-transformers when needed
        self.transformer_model = None
        self._model_loaded = False
        self.use_transformer = False
        
        # Check if sentence-transformers is available but don't load yet
        try:
            import sentence_transformers
            self.use_transformer = True
            print("✓ Sentence transformers available (will load on first use)")
        except ImportError:
            print("ℹ Using local embedding fallback (install sentence-transformers for better embeddings)")
    
    def _load_model_if_needed(self):
        """Lazy load the model only when needed"""
        if self.use_transformer and not self._model_loaded:
            try:
                from sentence_transformers import SentenceTransformer
                self.transformer_model = SentenceTransformer('all-MiniLM-L6-v2')
                self._model_loaded = True
                print("✓ Loaded sentence transformer model")
            except Exception as e:
                print(f"⚠️ Failed to load transformer: {e}")
                self.use_transformer = False
    
    def _local_embedding(self, text: str) -> np.ndarray:
        """
        Generate local embeddings without external dependencies
        Uses semantic hashing and feature extraction
        """
        # Normalize text
        text_lower = text.lower().strip()
        
        # Feature extraction
        features = []
        
        # 1. Character n-grams (captures morphology)
        for n in [2, 3, 4]:
            ngrams = [text_lower[i:i+n] for i in range(len(text_lower)-n+1)]
            ngram_features = [0] * 50  # 50 dimensions per n-gram size
            for ng in ngrams[:50]:  # Limit to first 50
                hash_val = int(hashlib.md5(ng.encode()).hexdigest()[:8], 16)
                ngram_features[hash_val % 50] += 1
            features.extend(ngram_features)
        
        # 2. Word features
        words = text_lower.split()
        word_features = [0] * 100
        for word in words[:30]:  # Limit to first 30 words
            hash_val = int(hashlib.md5(word.encode()).hexdigest()[:8], 16)
            word_features[hash_val % 100] += 1
        features.extend(word_features)
        
        # 3. Semantic indicators (keywords for code/commands)
        semantic_keywords = {
            'function': 10, 'class': 10, 'def': 10, 'create': 8,
            'fix': 8, 'bug': 8, 'error': 8, 'debug': 8,
            'test': 7, 'deploy': 7, 'build': 7, 'run': 7,
            'search': 6, 'find': 6, 'analyze': 6, 'explain': 6,
            'refactor': 9, 'optimize': 9, 'improve': 9,
            'git': 5, 'commit': 5, 'push': 5, 'pull': 5
        }
        
        semantic_features = [0] * 50
        for word in words:
            if word in semantic_keywords:
                weight = semantic_keywords[word]
                idx = list(semantic_keywords.keys()).index(word)
                semantic_features[idx % 50] += weight
        features.extend(semantic_features)
        
        # 4. Length and structure features
        structure_features = [
            len(text) / 100,  # Normalized length
            len(words) / 20,  # Normalized word count
            text.count('(') + text.count(')'),  # Parentheses (functions)
            text.count('[') + text.count(']'),  # Brackets
            text.count('{') + text.count('}'),  # Braces
            text.count('.'),  # Dots (methods, files)
            text.count('/'),  # Paths
            text.count('_'),  # Underscores
            text.count('-'),  # Dashes
            1 if '?' in text else 0,  # Question
            1 if '!' in text else 0,  # Exclamation
            1 if any(word in text_lower for word in ['create', 'make', 'build']) else 0,
            1 if any(word in text_lower for word in ['fix', 'debug', 'solve']) else 0,
            1 if any(word in text_lower for word in ['find', 'search', 'where']) else 0,
        ]
        features.extend(structure_features)
        
        # 5. Position-sensitive features (beginning/end of text)
        if words:
            first_word_hash = int(hashlib.md5(words[0].encode()).hexdigest()[:8], 16)
            last_word_hash = int(hashlib.md5(words[-1].encode()).hexdigest()[:8], 16)
            position_features = [
                first_word_hash % 100 / 100,
                last_word_hash % 100 / 100
            ]
        else:
            position_features = [0, 0]
        features.extend(position_features)
        
        # Pad or truncate to target dimension
        embedding = np.array(features[:self.model_config.dimension])
        if len(embedding) < self.model_config.dimension:
            embedding = np.pad(embedding, (0, self.model_config.dimension - len(embedding)))
        
        # L2 normalization
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def get_embedding(self, text: str, use_cache: bool = True) -> np.ndarray:
        """Get embedding for text"""
        # Truncate very large texts to prevent timeouts
        max_text_length = 10000  # ~10KB max
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."
        
        # Check cache
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if use_cache and text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]
        
        # Generate embedding
        self._load_model_if_needed()
        if self.transformer_model:
            # Use sentence-transformers if available
            # For very large texts, use batching
            if len(text) > 5000:
                # Split into chunks and average embeddings
                chunk_size = 2000
                chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
                embeddings = []
                for chunk in chunks[:5]:  # Max 5 chunks
                    try:
                        emb = self.transformer_model.encode(chunk, convert_to_numpy=True)
                        embeddings.append(emb)
                    except:
                        # If encoding fails, use local fallback
                        emb = self._local_embedding(chunk)
                        embeddings.append(emb)
                # Average the embeddings
                embedding = np.mean(embeddings, axis=0)
            else:
                embedding = self.transformer_model.encode(text, convert_to_numpy=True)
        else:
            # Use local embedding
            embedding = self._local_embedding(text)
        
        # Cache it
        self.embedding_cache[text_hash] = embedding
        
        return embedding
    
    def get_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for multiple texts"""
        self._load_model_if_needed()
        if self.transformer_model:
            # Batch processing with transformer
            return self.transformer_model.encode(texts, convert_to_numpy=True)
        else:
            # Process individually with local method
            return np.array([self.get_embedding(text, use_cache=True) for text in texts])
    
    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings"""
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_similar(self, query: str, candidates: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        """Find most similar texts from candidates"""
        query_emb = self.get_embedding(query)
        
        similarities = []
        for candidate in candidates:
            candidate_emb = self.get_embedding(candidate)
            sim = self.cosine_similarity(query_emb, candidate_emb)
            similarities.append((candidate, sim))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def cluster_texts(self, texts: List[str], n_clusters: int = 5) -> Dict[int, List[str]]:
        """Simple clustering of texts based on embeddings"""
        if not texts:
            return {}
        
        embeddings = self.get_embeddings_batch(texts)
        
        # Simple k-means style clustering
        # Initialize cluster centers randomly
        indices = np.random.choice(len(texts), min(n_clusters, len(texts)), replace=False)
        centers = embeddings[indices]
        
        # Iterate to refine clusters
        for _ in range(10):
            # Assign texts to nearest center
            clusters = {i: [] for i in range(len(centers))}
            for idx, emb in enumerate(embeddings):
                distances = [np.linalg.norm(emb - center) for center in centers]
                nearest = np.argmin(distances)
                clusters[nearest].append(texts[idx])
            
            # Update centers
            new_centers = []
            for i in range(len(centers)):
                if clusters[i]:
                    cluster_embeddings = [embeddings[texts.index(t)] for t in clusters[i]]
                    new_centers.append(np.mean(cluster_embeddings, axis=0))
                else:
                    new_centers.append(centers[i])
            centers = np.array(new_centers)
        
        return clusters
    
    def save_cache(self):
        """Save embedding cache to disk"""
        cache_file = self.cache_dir / "embedding_cache.pkl"
        with open(cache_file, 'wb') as f:
            pickle.dump(self.embedding_cache, f)
    
    def load_cache(self):
        """Load embedding cache from disk"""
        cache_file = self.cache_dir / "embedding_cache.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    self.embedding_cache = pickle.load(f)
            except:
                self.embedding_cache = {}
    
    def create_semantic_index(self, texts: List[str]) -> Dict[str, Any]:
        """Create a semantic index for fast similarity search"""
        embeddings = self.get_embeddings_batch(texts)
        
        # Create index structure
        index = {
            "texts": texts,
            "embeddings": embeddings,
            "dimension": self.model_config.dimension,
            "size": len(texts)
        }
        
        # Save to disk
        index_file = self.cache_dir / "semantic_index.pkl"
        with open(index_file, 'wb') as f:
            pickle.dump(index, f)
        
        return index
    
    def search_semantic_index(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search the semantic index"""
        index_file = self.cache_dir / "semantic_index.pkl"
        if not index_file.exists():
            return []
        
        with open(index_file, 'rb') as f:
            index = pickle.load(f)
        
        query_emb = self.get_embedding(query)
        
        # Calculate similarities
        similarities = []
        for idx, emb in enumerate(index["embeddings"]):
            sim = self.cosine_similarity(query_emb, emb)
            similarities.append((index["texts"][idx], sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


class TrainingDataCollector:
    """Collect and prepare training data for the learning system"""
    
    def __init__(self, learning_system=None):
        self.learning_system = learning_system
        self.data_dir = Path.home() / ".agent" / "training_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.training_data = {
            "commands": [],
            "patterns": [],
            "feedback": [],
            "preferences": []
        }
    
    def collect_from_history(self) -> Dict[str, List]:
        """Collect training data from command history"""
        if not self.learning_system:
            return self.training_data
        
        # Get command history
        history = self.learning_system.conn.execute("""
            SELECT command, task_type, tool_used, success, execution_time
            FROM command_history
            ORDER BY timestamp DESC
            LIMIT 1000
        """).fetchall()
        
        for row in history:
            self.training_data["commands"].append({
                "command": row["command"],
                "task_type": row["task_type"],
                "tool": row["tool_used"],
                "success": row["success"],
                "execution_time": row["execution_time"]
            })
        
        # Get patterns
        patterns = self.learning_system.conn.execute("""
            SELECT pattern_text, confidence, success_count, failure_count
            FROM patterns
            WHERE confidence > 0.6
        """).fetchall()
        
        for row in patterns:
            self.training_data["patterns"].append({
                "pattern": row["pattern_text"],
                "confidence": row["confidence"],
                "success_rate": row["success_count"] / (row["success_count"] + row["failure_count"])
                if (row["success_count"] + row["failure_count"]) > 0 else 0
            })
        
        return self.training_data
    
    def add_training_example(self, input_text: str, task_type: str, 
                            tool: str, success: bool, output: str = ""):
        """Add a training example"""
        example = {
            "input": input_text,
            "task_type": task_type,
            "tool": tool,
            "success": success,
            "output": output,
            "timestamp": Path.cwd().stat().st_mtime
        }
        
        self.training_data["commands"].append(example)
        
        # Save periodically
        if len(self.training_data["commands"]) % 10 == 0:
            self.save_training_data()
    
    def generate_synthetic_data(self, template_library) -> List[Dict]:
        """Generate synthetic training data from NLP templates"""
        synthetic_data = []
        
        for template in template_library.templates:
            if template.examples:
                for example in template.examples:
                    synthetic_data.append({
                        "input": example,
                        "task_type": template.category.value,
                        "intent": template.name,
                        "tools": template.tool_suggestions,
                        "confidence": template.confidence_threshold
                    })
        
        return synthetic_data
    
    def prepare_for_training(self) -> Tuple[List, List]:
        """Prepare data for training (X, y format)"""
        X = []  # Input texts
        y = []  # Labels (task_type, tool, success)
        
        for cmd in self.training_data["commands"]:
            X.append(cmd["command"])
            y.append({
                "task_type": cmd["task_type"],
                "tool": cmd["tool"],
                "success": cmd["success"]
            })
        
        return X, y
    
    def save_training_data(self):
        """Save training data to disk"""
        data_file = self.data_dir / "training_data.json"
        with open(data_file, 'w') as f:
            json.dump(self.training_data, f, indent=2)
    
    def load_training_data(self):
        """Load training data from disk"""
        data_file = self.data_dir / "training_data.json"
        if data_file.exists():
            with open(data_file, 'r') as f:
                self.training_data = json.load(f)
    
    def export_for_fine_tuning(self, output_path: str):
        """Export data in format suitable for fine-tuning LLMs"""
        fine_tune_data = []
        
        for cmd in self.training_data["commands"]:
            if cmd["success"]:
                fine_tune_data.append({
                    "prompt": f"Task: {cmd['task_type']}\nCommand: {cmd['command']}",
                    "completion": f"Tool: {cmd['tool']}"
                })
        
        with open(output_path, 'w') as f:
            for item in fine_tune_data:
                f.write(json.dumps(item) + "\n")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about training data"""
        stats = {
            "total_examples": len(self.training_data["commands"]),
            "successful_examples": sum(1 for c in self.training_data["commands"] if c.get("success")),
            "unique_task_types": len(set(c["task_type"] for c in self.training_data["commands"])),
            "unique_tools": len(set(c["tool"] for c in self.training_data["commands"])),
            "patterns_learned": len(self.training_data["patterns"]),
            "high_confidence_patterns": sum(1 for p in self.training_data["patterns"] 
                                           if p.get("confidence", 0) > 0.8)
        }
        
        return stats


if __name__ == "__main__":
    # Test embedding system
    print("Testing Embedding System\n" + "="*50)
    
    embedder = EmbeddingSystem()
    
    # Test texts
    test_texts = [
        "create a function to sort a list",
        "write a function that sorts arrays",
        "fix the bug in authentication",
        "debug the login issue",
        "deploy to production",
        "push to prod environment"
    ]
    
    print("\nSimilarity Tests:")
    for i in range(0, len(test_texts), 2):
        text1 = test_texts[i]
        text2 = test_texts[i+1]
        
        emb1 = embedder.get_embedding(text1)
        emb2 = embedder.get_embedding(text2)
        
        similarity = embedder.cosine_similarity(emb1, emb2)
        print(f"'{text1[:30]}...' vs '{text2[:30]}...'")
        print(f"  Similarity: {similarity:.3f}")
    
    # Test clustering
    print("\nClustering Test:")
    clusters = embedder.cluster_texts(test_texts, n_clusters=3)
    for cluster_id, texts in clusters.items():
        print(f"Cluster {cluster_id}:")
        for text in texts:
            print(f"  - {text}")
    
    # Test training data collector
    print("\nTraining Data Collector Test:")
    collector = TrainingDataCollector()
    
    # Add some examples
    collector.add_training_example(
        "create a REST API", 
        "code_generation",
        "aider",
        True,
        "API created successfully"
    )
    
    stats = collector.get_statistics()
    print(f"Training data statistics: {stats}")