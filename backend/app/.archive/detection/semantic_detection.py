"""Semantic similarity detection using embeddings and FAISS."""

from typing import Optional, List, Dict, Any
import logging
import numpy as np

logger = logging.getLogger(__name__)


class SemanticDetection:
    """Semantic similarity detection using embeddings.
    
    Uses sentence transformers to embed text and FAISS for similarity search.
    Detects semantically similar content even if text is different.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        threshold: float = 0.80,
        use_faiss: bool = True,
    ):
        """Initialize semantic detection.
        
        Args:
            model_name: HuggingFace model for embeddings
            threshold: Similarity threshold (0-1). Default 0.80
            use_faiss: Whether to use FAISS for indexing
        """
        self.threshold = threshold
        self.model_name = model_name
        self.use_faiss = use_faiss
        self.index = None
        self.embeddings_cache = {}
        self.samples = []
        
        logger.info(f"SemanticDetection initialized with model={model_name}, threshold={threshold}")
        
        # Try to load sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")
            self.model = None
    
    def build_index(self, reference_samples: List[str]) -> None:
        """Build FAISS index from reference samples.
        
        Args:
            reference_samples: List of reference strings to index
        """
        logger.info(f"Building FAISS index for {len(reference_samples)} samples")
        
        if not self.model:
            logger.error("Model not loaded, cannot build index")
            return
        
        self.samples = reference_samples
        
        try:
            # Generate embeddings for all samples
            embeddings = self.model.encode(reference_samples, convert_to_numpy=True)
            
            if self.use_faiss:
                import faiss
                
                # Create FAISS index
                dimension = embeddings.shape[1]
                self.index = faiss.IndexFlatL2(dimension)
                self.index.add(embeddings.astype(np.float32))
                
                logger.info(f"Built FAISS index: dimension={dimension}, samples={len(reference_samples)}")
            else:
                # Store embeddings for manual search
                self.embeddings_cache = {
                    sample: embedding for sample, embedding in zip(reference_samples, embeddings)
                }
                logger.info(f"Stored embeddings for {len(reference_samples)} samples")
        
        except ImportError:
            logger.warning("FAISS not installed. Install with: pip install faiss-cpu")
            self.use_faiss = False
            self.embeddings_cache = {
                sample: embedding for sample, embedding in zip(
                    reference_samples,
                    self.model.encode(reference_samples, convert_to_numpy=True)
                )
            }
    
    def detect(self, input_text: str, reference_samples: Optional[List[str]] = None) -> Dict[str, Any]:
        """Detect semantically similar samples.
        
        Args:
            input_text: Text to search for
            reference_samples: Optional list of samples (builds index if provided)
        
        Returns:
            Detection result with matches and confidence
        """
        logger.debug(f"Semantic detection: '{input_text[:50]}'")
        
        if not self.model:
            logger.error("Model not loaded")
            return {
                "detected": False,
                "confidence": 0.0,
                "matches": [],
                "error": "Model not loaded",
            }
        
        if reference_samples:
            self.build_index(reference_samples)
        
        if not self.samples:
            logger.warning("No samples indexed")
            return {
                "detected": False,
                "confidence": 0.0,
                "matches": [],
                "reason": "No samples indexed",
            }
        
        # Generate embedding for input
        input_embedding = self.model.encode(input_text, convert_to_numpy=True)
        
        matches = []
        
        if self.use_faiss and self.index:
            # Use FAISS for fast similarity search
            distances, indices = self.index.search(
                np.array([input_embedding], dtype=np.float32),
                min(5, len(self.samples))  # Top 5 matches
            )
            
            for idx, distance in zip(indices[0], distances[0]):
                if idx < len(self.samples):
                    # L2 distance to similarity
                    similarity = 1.0 / (1.0 + distance)
                    
                    if similarity >= self.threshold:
                        matches.append({
                            "matched_sample": self.samples[idx],
                            "confidence": round(float(similarity), 4),
                        })
        else:
            # Manual cosine similarity search
            matches = self._cosine_similarity_search(input_embedding, self.samples)
        
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        
        detected = len(matches) > 0
        max_confidence = matches[0]["confidence"] if matches else 0.0
        
        logger.info(f"Semantic detection: detected={detected}, matches={len(matches)}")
        
        return {
            "detected": detected,
            "confidence": round(max_confidence, 4),
            "matches": matches,
            "threshold_used": self.threshold,
            "algorithm": "semantic_similarity",
            "model": self.model_name,
        }
    
    def batch_detect(
        self,
        input_texts: List[str],
        reference_samples: List[str],
    ) -> List[Dict[str, Any]]:
        """Detect multiple input texts.
        
        Args:
            input_texts: List of texts to search for
            reference_samples: List of reference samples
        
        Returns:
            List of detection results
        """
        logger.info(f"Batch semantic detection: {len(input_texts)} inputs vs {len(reference_samples)} samples")
        
        # Build index once
        self.build_index(reference_samples)
        
        results = []
        for text in input_texts:
            result = self.detect(text)
            results.append({
                "input": text,
                **result
            })
        
        return results
    
    def _cosine_similarity_search(
        self,
        input_embedding: np.ndarray,
        samples: List[str],
    ) -> List[Dict[str, Any]]:
        """Search using cosine similarity."""
        matches = []
        
        # Normalize input embedding
        input_norm = input_embedding / (np.linalg.norm(input_embedding) + 1e-10)
        
        for sample, sample_embedding in self.embeddings_cache.items():
            # Normalize sample embedding
            sample_norm = sample_embedding / (np.linalg.norm(sample_embedding) + 1e-10)
            
            # Cosine similarity
            similarity = float(np.dot(input_norm, sample_norm))
            
            if similarity >= self.threshold:
                matches.append({
                    "matched_sample": sample,
                    "confidence": round(similarity, 4),
                })
        
        return matches
    
    def update_threshold(self, threshold: float) -> None:
        """Update detection threshold."""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0 and 1, got {threshold}")
        self.threshold = threshold
        logger.info(f"Semantic detection threshold updated to {threshold}")
    
    def clear_cache(self) -> None:
        """Clear embeddings cache and index."""
        self.embeddings_cache.clear()
        self.index = None
        self.samples.clear()
        logger.info("Semantic detection cache cleared")
