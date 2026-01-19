"""
Local Feature Extraction: Exact Hash (STEP-4)

Compute partial SHA-256 hash from first N bytes of file.
Non-blocking, graceful error handling.
"""

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_exact(
    file_path: str,
    partial_hash_bytes: int = 4194304,  # 4 MB default
    timeout: Optional[float] = None
) -> Optional[dict]:
    """
    Extract exact hash features from file.
    
    Computes SHA-256 hash from first N bytes (partial hash).
    This is fast and collision-resistant for practical use.
    
    Args:
        file_path: Path to file on disk
        partial_hash_bytes: Number of bytes to read (default 4 MB)
        timeout: Optional timeout (not implemented in v1)
    
    Returns:
        dict with keys:
        - algorithm: "sha256"
        - value: hex digest of first N bytes
        - bytes_read: actual bytes read
        
        OR None if extraction fails
    """
    try:
        # Open file in binary mode
        with open(file_path, 'rb') as f:
            # Read first N bytes
            chunk = f.read(partial_hash_bytes)
            
            if not chunk:
                logger.warning(f"Exact hash: empty file {file_path}")
                return None
            
            # Compute SHA-256
            hash_obj = hashlib.sha256()
            hash_obj.update(chunk)
            
            result = {
                "algorithm": "sha256",
                "value": hash_obj.hexdigest(),
                "bytes_read": len(chunk)
            }
            
            logger.debug(
                f"Exact hash computed: {file_path[:50]} "
                f"({len(chunk)} bytes, hash={result['value'][:8]}...)"
            )
            
            return result
    
    except FileNotFoundError:
        logger.warning(f"Exact hash: file not found {file_path}")
        return None
    
    except PermissionError:
        logger.warning(f"Exact hash: permission denied {file_path}")
        return None
    
    except Exception as e:
        logger.warning(f"Exact hash extraction failed: {e}")
        return None

