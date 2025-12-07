# cache.py
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, Any, Union

# Set up logging
logger = logging.getLogger(__name__)

CACHE_PATH = Path(".ai_doc_cache.json")


def _hash(prompt: str, extra: Optional[dict] = None) -> str:
    """Generate a hash key for the cache entry."""
    s = prompt + (json.dumps(extra, sort_keys=True) if extra else "")
    return hashlib.sha256(s.encode()).hexdigest()


def load_from_cache(prompt: str, extra: Optional[dict] = None) -> Optional[Any]:
    """
    Load a cached response.
    
    Args:
        prompt: The prompt/key to look up.
        extra: Additional context for the cache key.
        
    Returns:
        The cached value (str or dict) or None if not found.
    """
    if not CACHE_PATH.exists():
        return None
    try:
        data = json.loads(CACHE_PATH.read_text("utf-8"))
        return data.get(_hash(prompt, extra), None)
    except json.JSONDecodeError as e:
        logger.warning(f"Cache file is corrupted and will be ignored: {e}")
        return None
    except (OSError, IOError) as e:
        logger.warning(f"Failed to read cache file: {e}")
        return None


def save_to_cache(prompt: str, response: Union[str, dict], extra: Optional[dict] = None) -> None:
    """
    Save a response to cache.
    
    Args:
        prompt: The prompt/key to store under.
        response: The response to cache (can be str or dict).
        extra: Additional context for the cache key.
    """
    try:
        if CACHE_PATH.exists():
            data = json.loads(CACHE_PATH.read_text("utf-8"))
        else:
            data = {}

        data[_hash(prompt, extra)] = response
        CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except json.JSONDecodeError as e:
        logger.warning(f"Cache file corrupted, starting fresh: {e}")
        # If cache is corrupted, start fresh
        data = {_hash(prompt, extra): response}
        try:
            CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except (OSError, IOError) as write_error:
            logger.error(f"Failed to write cache file: {write_error}")
    except (OSError, IOError) as e:
        logger.error(f"Failed to save to cache: {e}")


def clear_cache() -> None:
    """Clear the entire cache."""
    if CACHE_PATH.exists():
        CACHE_PATH.unlink()

