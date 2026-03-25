from cachetools import TTLCache
from threading import Lock

_store: dict[str, TTLCache] = {}
_lock = Lock()

DEFAULT_TTL = 60  # segundos


def get_cache(namespace: str, maxsize: int = 512, ttl: int = DEFAULT_TTL) -> TTLCache:
    if namespace not in _store:
        with _lock:
            if namespace not in _store:
                _store[namespace] = TTLCache(maxsize=maxsize, ttl=ttl)
    return _store[namespace]


def cache_get(namespace: str, key: str):
    return get_cache(namespace).get(key)


def cache_set(namespace: str, key: str, value, ttl: int = DEFAULT_TTL):
    get_cache(namespace, ttl=ttl)[key] = value


def cache_invalidate(namespace: str, key: str = None):
    """Invalida chave específica ou todo o namespace."""
    c = get_cache(namespace)
    if key:
        c.pop(key, None)
    else:
        c.clear()
