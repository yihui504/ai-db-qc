"""Embedding utilities for AI-DB-QC semantic testing.

Priority chain (first available wins):
  1. sentence-transformers  — local GPU/CPU, real semantic embeddings
  2. OpenAI API             — cloud-based embeddings via text-embedding-3-small
  3. Deterministic hash     — offline fallback (no semantic meaning; for infra testing only)

Usage:
    from ai_db_qa.embedding import get_embed_fn, EmbedBackend

    embed = get_embed_fn()               # auto-selects best available
    vectors = embed(["hello", "world"])  # returns List[List[float]]

    # Explicit backend selection
    embed = get_embed_fn(backend=EmbedBackend.SENTENCE_TRANSFORMERS, model="all-MiniLM-L6-v2")
    embed = get_embed_fn(backend=EmbedBackend.OPENAI, api_key="sk-...")
    embed = get_embed_fn(backend=EmbedBackend.HASH)
"""

from __future__ import annotations

import enum
import hashlib
import json
import logging
import os
import pathlib
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Early offline-mode injection
# If the HuggingFace model cache already contains the default
# model, switch to offline mode BEFORE any HF library imports
# so that no HEAD requests are sent to huggingface.co.
# This avoids proxy SSL failures in air-gapped / restricted
# corporate environments.
# ─────────────────────────────────────────────────────────────

def _hf_cache_has_model(model_slug: str) -> bool:
    """Return True if *model_slug* has a cached snapshot on disk."""
    hf_home = os.environ.get("HF_HOME", "").strip()
    if hf_home:
        cache_root = pathlib.Path(hf_home).expanduser() / "hub"
    else:
        cache_root = pathlib.Path.home() / ".cache" / "huggingface" / "hub"
    safe_slug = model_slug.replace("/", "--").replace("\\", "--")
    candidates = [
        cache_root / f"models--sentence-transformers--{safe_slug}",
        cache_root / f"models--{safe_slug}",
    ]
    return any(c.exists() for c in candidates)


_DEFAULT_ST_MODEL = "all-MiniLM-L6-v2"
if (
    not os.environ.get("HF_HUB_OFFLINE")
    and _hf_cache_has_model(_DEFAULT_ST_MODEL)
):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    logger.debug(
        "Local HF cache detected (%s); set HF_HUB_OFFLINE=1 to skip network checks.",
        _DEFAULT_ST_MODEL,
    )


# ─────────────────────────────────────────────────────────────
# Backend enum
# ─────────────────────────────────────────────────────────────

class EmbedBackend(str, enum.Enum):
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OPENAI                = "openai"
    HASH                  = "hash"
    AUTO                  = "auto"


# ─────────────────────────────────────────────────────────────
# Backend implementations
# ─────────────────────────────────────────────────────────────

def _hash_embed(texts: List[str], dim: int = 128) -> List[List[float]]:
    """Deterministic pseudo-embedding via SHA-256.

    WARNING: No semantic meaning.  Results are reproducible across runs but
    semantically random.  Use ONLY for infrastructure / pipeline testing.
    """
    vectors = []
    for text in texts:
        h = hashlib.sha256(text.encode()).hexdigest()
        raw = [int(h[i:i+2], 16) for i in range(0, min(len(h), dim * 2), 2)]
        vec = [(x - 127.5) / 127.5 for x in raw[:dim]]
        while len(vec) < dim:
            vec.append(0.0)
        vectors.append(vec[:dim])
    return vectors


def _st_embed_factory(model_name: str = "all-MiniLM-L6-v2", batch_size: int = 64) -> Callable:
    """Build a sentence-transformers embedding function.

    Dimensions depend on model:
      all-MiniLM-L6-v2  → 384
      all-mpnet-base-v2  → 768
      paraphrase-multilingual-MiniLM-L12-v2 → 384

    Network note: the module-level initializer sets HF_HUB_OFFLINE=1 when a
    cached copy of the default model is present, so this function should not
    trigger any network requests in typical use.
    """
    # If the requested model is not the default but IS cached, enable offline for it too
    if model_name != _DEFAULT_ST_MODEL and _hf_cache_has_model(model_name):
        if not os.environ.get("HF_HUB_OFFLINE"):
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"

    from sentence_transformers import SentenceTransformer  # type: ignore
    _model = SentenceTransformer(model_name)

    def embed(texts: List[str], dim: Optional[int] = None) -> List[List[float]]:
        embeddings = _model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        result = [e.tolist() for e in embeddings]
        # Truncate/pad to requested dim if specified
        if dim and dim != len(result[0]):
            result = [v[:dim] + [0.0] * max(0, dim - len(v)) for v in result]
        return result

    return embed


def _openai_embed_factory(
    api_key: str,
    model: str = "text-embedding-3-small",
    base_url: str = "https://api.openai.com/v1",
    dim: Optional[int] = None,
) -> Callable:
    """Build an OpenAI-compatible embedding function.

    Supports any OpenAI-compatible embedding endpoint.
    """
    import urllib.request

    def embed(texts: List[str], requested_dim: Optional[int] = None) -> List[List[float]]:
        target_dim = requested_dim or dim
        payload: Dict[str, Any] = {"model": model, "input": texts}
        if target_dim:
            payload["dimensions"] = target_dim  # supported by text-embedding-3-* models

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/embeddings",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        # Sort by index to ensure ordering
        items = sorted(result["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]

    return embed


# ─────────────────────────────────────────────────────────────
# Auto-detection
# ─────────────────────────────────────────────────────────────

def _detect_sentence_transformers() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def get_embed_fn(
    backend: EmbedBackend = EmbedBackend.AUTO,
    model: str = "all-MiniLM-L6-v2",
    api_key: Optional[str] = None,
    base_url: str = "https://api.openai.com/v1",
    dim: Optional[int] = None,
    batch_size: int = 64,
) -> Callable:
    """Return an embedding function based on available backends.

    Args:
        backend:    Force a specific backend, or AUTO to detect best available.
        model:      Model name for ST (default: all-MiniLM-L6-v2) or OpenAI.
        api_key:    API key for OpenAI backend.
        base_url:   Base URL for OpenAI-compatible API.
        dim:        Optional output dimension (truncate/pad).
        batch_size: Batch size for ST inference.

    Returns:
        Callable[[List[str]], List[List[float]]] — embed function.
        The returned function accepts an optional 'dim' keyword argument.

    Backend selection in AUTO mode:
        1. sentence-transformers (if installed)
        2. OpenAI API (if api_key provided)
        3. Hash fallback
    """
    if backend == EmbedBackend.AUTO:
        if _detect_sentence_transformers():
            backend = EmbedBackend.SENTENCE_TRANSFORMERS
            logger.info("Auto-selected backend: sentence-transformers (%s)", model)
        elif api_key:
            backend = EmbedBackend.OPENAI
            logger.info("Auto-selected backend: OpenAI (%s)", model)
        else:
            backend = EmbedBackend.HASH
            logger.warning(
                "Auto-selected backend: hash (no semantic meaning). "
                "Install sentence-transformers for real embeddings: "
                "pip install sentence-transformers"
            )

    if backend == EmbedBackend.SENTENCE_TRANSFORMERS:
        if not _detect_sentence_transformers():
            raise ImportError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            )
        base_fn = _st_embed_factory(model_name=model, batch_size=batch_size)
        if dim:
            def fn(texts: List[str], dim: int = dim) -> List[List[float]]:  # type: ignore
                return base_fn(texts, dim=dim)
            return fn
        return base_fn

    if backend == EmbedBackend.OPENAI:
        if not api_key:
            raise ValueError("api_key is required for OpenAI backend")
        return _openai_embed_factory(api_key=api_key, model=model, base_url=base_url, dim=dim)

    if backend == EmbedBackend.HASH:
        def hash_fn(texts: List[str], dim: int = (dim or 128)) -> List[List[float]]:  # type: ignore
            return _hash_embed(texts, dim=dim)
        return hash_fn

    raise ValueError(f"Unknown backend: {backend}")


# ─────────────────────────────────────────────────────────────
# Backend info
# ─────────────────────────────────────────────────────────────

def get_backend_info() -> Dict[str, Any]:
    """Return information about available embedding backends."""
    st_available = _detect_sentence_transformers()

    info: Dict[str, Any] = {
        "sentence_transformers": {
            "available": st_available,
            "install": "pip install sentence-transformers",
            "recommended_models": [
                "all-MiniLM-L6-v2 (384D, fast, good quality)",
                "all-mpnet-base-v2 (768D, slower, high quality)",
                "paraphrase-multilingual-MiniLM-L12-v2 (384D, multilingual)",
            ],
            "dim": 384,   # default for all-MiniLM-L6-v2
        },
        "openai": {
            "available": "requires api_key",
            "models": [
                "text-embedding-3-small (1536D, cheap, good)",
                "text-embedding-3-large (3072D, expensive, best)",
            ],
        },
        "hash": {
            "available": True,
            "warning": "No semantic meaning. Use for infrastructure testing only.",
        },
        "selected_backend": (
            "sentence_transformers" if st_available else "hash"
        ),
    }

    if st_available:
        try:
            from sentence_transformers import __version__ as st_version  # type: ignore
            info["sentence_transformers"]["version"] = st_version
        except Exception:
            pass

    return info


def check_backends() -> None:
    """Print a summary of available embedding backends."""
    info = get_backend_info()
    print("Embedding Backend Availability:")
    print(f"  sentence-transformers: {'✓ installed' if info['sentence_transformers']['available'] else '✗ not installed'}")
    print(f"  openai API:           requires api_key")
    print(f"  hash fallback:        always available (no semantic meaning)")
    print(f"\nSelected: {info['selected_backend']}")
    if not info["sentence_transformers"]["available"]:
        print(f"\nTo enable real semantic embeddings:")
        print(f"  pip install sentence-transformers")
        print(f"  # Then the default 384D model 'all-MiniLM-L6-v2' will be used automatically")


if __name__ == "__main__":
    check_backends()
