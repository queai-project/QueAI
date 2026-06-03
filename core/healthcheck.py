"""
Probe del healthcheck declarado por cada plugin en su manifest.

Usado tanto por el endpoint REST /api/v1/plugins/<id>/healthcheck como por
la versión UI (sesión Django). Cache en LocMemCache, TTL configurable.
"""

from __future__ import annotations

import time

import requests
from django.conf import settings
from django.core.cache import cache

CACHE_PREFIX = "queai:hc:"


def probe(folder_name: str, endpoint_path: str) -> dict:
    """Pega al healthcheck del plugin (vía Traefik interno) y devuelve dict."""
    url = settings.QUEAI_INTERNAL_TRAEFIK_URL + endpoint_path
    start = time.perf_counter()
    try:
        res = requests.get(url, timeout=settings.QUEAI_HEALTHCHECK_TIMEOUT)
    except requests.exceptions.Timeout:
        return {"healthy": False, "status_code": None, "latency_ms": None, "error": "timeout", "url": url}
    except requests.RequestException as e:
        return {"healthy": False, "status_code": None, "latency_ms": None, "error": str(e)[:200], "url": url}
    latency = int((time.perf_counter() - start) * 1000)
    healthy = 200 <= res.status_code < 300
    return {
        "healthy": healthy,
        "status_code": res.status_code,
        "latency_ms": latency,
        "error": None if healthy else f"HTTP {res.status_code}",
        "url": url,
    }


def cached_probe(folder_name: str, endpoint_path: str) -> dict:
    """probe() con cache de QUEAI_HEALTHCHECK_CACHE_TTL segundos."""
    key = f"{CACHE_PREFIX}{folder_name}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = probe(folder_name, endpoint_path)
    result["checked_at"] = int(time.time())
    cache.set(key, result, settings.QUEAI_HEALTHCHECK_CACHE_TTL)
    return result


def invalidate(folder_name: str | None = None):
    """Invalida la cache de un plugin o de todos."""
    if folder_name is None:
        cache.clear()
    else:
        cache.delete(f"{CACHE_PREFIX}{folder_name}")
