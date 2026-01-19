"""
Local Feature Extraction: Fuzzy Signature (STEP-4)

Use MinHash (datasketch) for fuzzy file matching.
Graceful degradation if datasketch unavailable.
Non-blocking, best-effort.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import datasketch; graceful skip if unavailable
try:
    from datasketch import MinHash
    DATASKETCH_AVAILABLE = True
except ImportError:
    DATASKETCH_AVAILABLE = False
    logger.warning("datasketch not available; fuzzy hashing disabled")


def extract_fuzzy(
    file_path: str,
    num_perm: int = 128,  # Number of hash functions (MinHash)
    chunk_size: int = 65536  # 64 KB chunks
) -> Optional[dict]:
    """
    Extract fuzzy signature from file using MinHash.
    
    MinHash is fast and memory-efficient for large files.
    Gracefully returns None if datasketch unavailable.
    
    Args:
        file_path: Path to file on disk
        num_perm: Number of MinHash permutations (default 128)
        chunk_size: Chunk size for reading (default 64 KB)
    
    Returns:
        dict with keys:
        - algorithm: "minhash"
        - value: MinHash digest (hex string)
        - num_perm: number of permutations used
        
        OR None if extraction fails or datasketch unavailable
    """
    if not DATASKETCH_AVAILABLE:
        logger.debug("Fuzzy extraction skipped: datasketch unavailable")
        return None
    
    try:
        # Initialize MinHash
        mh = MinHash(num_perm=num_perm)
        
        # Read file in chunks and update MinHash
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                mh.update(chunk)
        
        # Serialize MinHash to hex
        # datasketch uses a format: num_perm:value1:value2:...
        result = {
            "algorithm": "minhash",
            "value": mh.hashvalues,  # List of hash values
            "num_perm": num_perm
        }
        
        logger.debug(
            f"Fuzzy signature computed: {file_path[:50]} "
            f"(num_perm={num_perm})"
        )
        
        return result
    
    except FileNotFoundError:
        logger.warning(f"Fuzzy hash: file not found {file_path}")
        return None
    
    except PermissionError:
        logger.warning(f"Fuzzy hash: permission denied {file_path}")
        return None
    
    except Exception as e:
        logger.warning(f"Fuzzy hash extraction failed: {e}")
        return None

