"""
Local Feature Extraction: Semantic Embedding (STEP-4)

Use sentence-transformers (SBERT) for semantic embeddings.
Lazy-loading of pretrained model.
Graceful degradation if library unavailable.
Non-blocking, best-effort.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global model cache (lazy-loaded on first use)
_semantic_model = None
SBERT_AVAILABLE = False

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SBERT_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not available; semantic extraction disabled")


def _get_model():
    """
    Lazy-load semantic model on first use.
    
    Returns:
        Model instance or None if unavailable/failed
    """
    global _semantic_model
    
    if not SBERT_AVAILABLE:
        return None
    
    if _semantic_model is not None:
        return _semantic_model
    
    try:
        # Use lightweight model for speed
        logger.info("Loading semantic model: all-MiniLM-L6-v2")
        _semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Semantic model loaded successfully")
        return _semantic_model
    
    except Exception as e:
        logger.warning(f"Failed to load semantic model: {e}")
        return None


def extract_semantic(
    file_path: str,
    metadata: Optional[dict] = None
) -> Optional[dict]:
    """
    Extract semantic embedding from file metadata.
    
    This extracts text/metadata about the file and generates
    a semantic embedding vector. Does NOT read full file content.
    
    Args:
        file_path: Path to file on disk
        metadata: Optional metadata dict with keys like:
                  - filename (str)
                  - mimetype (str)
                  - url (str)
                  - description (str)
    
    Returns:
        dict with keys:
        - model_name: name of the model used
        - vector: list[float] embedding vector
        - dimension: int, dimension of embedding
        
        OR None if extraction fails or model unavailable
    """
    model = _get_model()
    if model is None:
        logger.debug("Semantic extraction skipped: model unavailable")
        return None
    
    try:
        # Build text to embed from metadata + filename
        text_parts = []
        
        if metadata:
            if 'filename' in metadata:
                text_parts.append(metadata['filename'])
            if 'mimetype' in metadata:
                text_parts.append(f"type: {metadata['mimetype']}")
            if 'url' in metadata:
                text_parts.append(f"url: {metadata['url']}")
            if 'description' in metadata:
                text_parts.append(metadata['description'])
        
        # Add filename from path
        import os
        text_parts.append(os.path.basename(file_path))
        
        # Combine all text
        text_to_embed = " ".join(text_parts)
        
        if not text_to_embed.strip():
            logger.debug("Semantic: no metadata to embed")
            return None
        
        # Generate embedding
        embedding = model.encode(text_to_embed, convert_to_numpy=True)
        
        result = {
            "model_name": "all-MiniLM-L6-v2",
            "vector": embedding.tolist(),  # Convert numpy to list
            "dimension": len(embedding)
        }
        
        logger.debug(
            f"Semantic embedding computed: {file_path[:50]} "
            f"(dimension={result['dimension']})"
        )
        
        return result
    
    except Exception as e:
        logger.warning(f"Semantic extraction failed: {e}")
        return None

