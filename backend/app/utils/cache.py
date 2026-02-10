"""
Cache em memória com TTL para consultas pesadas.
"""
from typing import Any, Callable, Optional, TypeVar

from cachetools import TTLCache

from app.config import get_settings

T = TypeVar("T")
_ttl_cache: Optional[TTLCache] = None


def get_cache() -> TTLCache:
    global _ttl_cache
    if _ttl_cache is None:
        settings = get_settings()
        _ttl_cache = TTLCache(maxsize=500, ttl=settings.cache_ttl_seconds)
    return _ttl_cache


def cache_key(*parts: Any) -> str:
    """Gera chave de cache a partir de partes (filtros, etc.)."""
    return ":".join(str(p) for p in parts)


def cached(key_prefix: str):
    """Decorator para cachear resultado de função com TTL."""

    def decorator(func: Callable[..., T]):
        def wrapper(*args: Any, **kwargs: Any) -> T:
            c = get_cache()
            key = cache_key(key_prefix, args, tuple(sorted(kwargs.items())))
            if key in c:
                return c[key]
            result = func(*args, **kwargs)
            c[key] = result
            return result

        return wrapper

    return decorator
