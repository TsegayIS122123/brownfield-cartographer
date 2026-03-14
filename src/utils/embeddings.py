"""Embedding utilities for semantic clustering."""

import numpy as np
from typing import List, Dict, Any, Optional
import logging
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import json

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings for text using various models."""
    
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.embeddings = {}
        
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (mock implementation for now)."""
        # TODO: Replace with actual embedding API call
        # For now, return a mock embedding (random vector)
        import hashlib
        
        # Create deterministic embedding based on text hash
        hash_obj = hashlib.md5(text.encode())
        seed = int(hash_obj.hexdigest()[:8], 16)
        np.random.seed(seed)
        
        # Generate 384-dim embedding (all-MiniLM-L6-v2 size)
        embedding = np.random.randn(384)
        embedding = embedding / np.linalg.norm(embedding)  # Normalize
        
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str], ids: List[str]) -> Dict[str, List[float]]:
        """Generate embeddings for multiple texts."""
        for text_id, text in zip(ids, texts):
            if text_id not in self.embeddings:
                self.embeddings[text_id] = self.generate_embedding(text)
                logger.debug(f"Generated embedding for {text_id}")
        
        return {tid: self.embeddings[tid] for tid in ids if tid in self.embeddings}
    
    def save_embeddings(self, filepath: str):
        """Save embeddings to file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.embeddings, f, indent=2)
    
    def load_embeddings(self, filepath: str):
        """Load embeddings from file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.embeddings = json.load(f)


class DomainClusterer:
    """Clusters modules into business domains using embeddings."""
    
    def __init__(self, n_clusters: int = 5, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.kmeans = None
        self.labels = {}
        self.cluster_names = {}
        
    def find_optimal_clusters(self, embeddings: np.ndarray, max_k: int = 10) -> int:
        """Find optimal number of clusters using silhouette score."""
        if len(embeddings) < 3:
            return min(2, len(embeddings))
        
        best_k = 2
        best_score = -1
        
        for k in range(2, min(max_k, len(embeddings))):
            kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
            labels = kmeans.fit_predict(embeddings)
            
            if len(set(labels)) > 1:
                score = silhouette_score(embeddings, labels)
                if score > best_score:
                    best_score = score
                    best_k = k
        
        logger.info(f"Optimal clusters: {best_k} (silhouette score: {best_score:.3f})")
        return best_k
    
    def cluster(self, embeddings_dict: Dict[str, List[float]], 
                purpose_statements: Dict[str, str]) -> Dict[str, int]:
        """Cluster embeddings into domains."""
        if not embeddings_dict:
            logger.warning("No embeddings to cluster")
            return {}
        
        # Convert to numpy array
        ids = list(embeddings_dict.keys())
        X = np.array([embeddings_dict[i] for i in ids])
        
        # Find optimal number of clusters
        if self.n_clusters == 'auto':
            k = self.find_optimal_clusters(X)
        else:
            k = min(self.n_clusters, len(ids))
        
        # Perform clustering
        self.kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
        labels = self.kmeans.fit_predict(X)
        
        # Store labels
        self.labels = {ids[i]: int(labels[i]) for i in range(len(ids))}
        
        # Generate cluster names
        self._name_clusters(purpose_statements)
        
        return self.labels
    
    def _name_clusters(self, purpose_statements: Dict[str, str]):
        """Generate human-readable names for clusters."""
        # Group statements by cluster
        cluster_texts = {}
        for module_id, label in self.labels.items():
            if label not in cluster_texts:
                cluster_texts[label] = []
            if module_id in purpose_statements:
                cluster_texts[label].append(purpose_statements[module_id])
        
        # Generate names (simple heuristic for now)
        for label, texts in cluster_texts.items():
            # Find common words
            all_words = ' '.join(texts).lower().split()
            word_freq = {}
            for word in all_words:
                if len(word) > 4:  # Ignore short words
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Most frequent word as cluster name
            if word_freq:
                cluster_name = max(word_freq.items(), key=lambda x: x[1])[0]
            else:
                cluster_name = f"Domain_{label}"
            
            self.cluster_names[label] = cluster_name.title()
        
        logger.info(f"Cluster names: {self.cluster_names}")
    
    def get_cluster_summary(self) -> Dict:
        """Get summary of clusters."""
        summary = {}
        for label, name in self.cluster_names.items():
            modules = [m for m, l in self.labels.items() if l == label]
            summary[name] = {
                "cluster_id": label,
                "module_count": len(modules),
                "modules": modules[:10],  # First 10 only
                "sample_purposes": []  # Would need purpose statements
            }
        return summary