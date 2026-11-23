"""Remote Brawl Stars game-data catalogue with a persistent offline cache.

BrawlAPI serves game-file metadata (brawlers, maps and modes). It does NOT
provide current map win-rate samples in its static map payload; this module
therefore never fabricates performance statistics.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

BASE_URL = os.getenv("BRAWLBOT_GAME_DATA_URL", "https://api.brawlapi.com").rstrip("/")
CACHE_PATH = Path(os.getenv("BRAWLBOT_KNOWLEDGE_FILE", "data/knowledge.json"))
CACHE_TTL_SECONDS = max(300, int(os.getenv("BRAWLBOT_KNOWLEDGE_TTL", "21600")))
ENDPOINTS = {
    "brawlers": "/v1/brawlers",
    "maps": "/v1/maps",
    "gamemodes": "/v1/gamemodes",
}


class KnowledgeService:
    def __init__(self, cache_path: Path | str = CACHE_PATH, base_url: str = BASE_URL,
                 transport: httpx.AsyncBaseTransport | None = None):
        self.cache_path = Path(cache_path)
        self.base_url = base_url.rstrip("/")
        self.transport = transport
        self.data: dict[str, list[dict[str, Any]]] = {k: [] for k in ENDPOINTS}
        self.updated_at: float | None = None
        self.last_error: str | None = None
        self.source = "BrawlAPI"
        self._lock = asyncio.Lock()
        self.load_cache()

    def load_cache(self) -> None:
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            for key in ENDPOINTS:
                values = payload.get(key, [])
                if isinstance(values, list):
                    self.data[key] = values
            self.updated_at = payload.get("updated_at")
        except (OSError, ValueError, TypeError):
            return

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {**self.data, "updated_at": self.updated_at, "source": self.source}
        temp = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.cache_path)

    async def refresh(self, force: bool = False) -> dict[str, Any]:
        async with self._lock:
            age = time.time() - self.updated_at if self.updated_at else None
            if not force and age is not None and age < CACHE_TTL_SECONDS:
                return self.status()
            errors: dict[str, str] = {}
            async with httpx.AsyncClient(timeout=httpx.Timeout(8.0), transport=self.transport,
                                         headers={"User-Agent": "BrawlBotAI/0.7.0"}) as client:
                async def fetch(key: str, path: str):
                    try:
                        response = await client.get(self.base_url + path)
                        response.raise_for_status()
                        payload = response.json()
                        items = payload.get("list") if isinstance(payload, dict) else None
                        if not isinstance(items, list):
                            raise ValueError("La respuesta no contiene una lista válida.")
                        return key, items, None
                    except (httpx.HTTPError, ValueError) as exc:
                        return key, None, str(exc)
                results = await asyncio.gather(*(fetch(k, p) for k, p in ENDPOINTS.items()))
            updated = []
            for key, items, error in results:
                if error:
                    errors[key] = error
                elif items is not None:
                    self.data[key] = items
                    updated.append(key)
            if updated:
                self.updated_at = time.time()
                self.last_error = None if not errors else "; ".join(f"{k}: {v}" for k, v in errors.items())
                self._save_cache()
            else:
                self.last_error = "; ".join(f"{k}: {v}" for k, v in errors.items()) or "No se recibieron datos."
            result = self.status()
            result["updated_sections"] = updated
            result["errors"] = errors
            return result

    def status(self) -> dict[str, Any]:
        age = max(0, int(time.time() - self.updated_at)) if self.updated_at else None
        return {
            "source": self.source,
            "source_url": self.base_url,
            "counts": {key: len(value) for key, value in self.data.items()},
            "updated_at": self.updated_at,
            "cache_age_seconds": age,
            "cache_ttl_seconds": CACHE_TTL_SECONDS,
            "cache_available": any(self.data.values()),
            "last_error": self.last_error,
            "performance_stats_available": False,
            "performance_stats_note": (
                "BrawlAPI entrega catálogo y metadatos del juego; sus listas estáticas de mapas "
                "no incluyen muestras de win rate/picks. BrawlBot no inventa esas estadísticas."
            ),
        }

    def search(self, category: str, query: str, limit: int = 25) -> dict[str, Any]:
        if category not in ENDPOINTS:
            raise ValueError("Categoría válida: brawlers, maps o gamemodes.")
        needle = query.casefold().strip()
        items = self.data[category]
        matches = [item for item in items if needle in str(item.get("name", "")).casefold()
                   or needle in str(item.get("hash", "")).casefold()]
        return {"category": category, "query": query, "total_matches": len(matches),
                "results": matches[:max(1, min(limit, 100))], "source": self.source,
                "data_updated_at": self.updated_at}


knowledge = KnowledgeService()
