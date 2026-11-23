import json
import httpx
import pytest
from brawlbot.knowledge import KnowledgeService

@pytest.mark.asyncio
async def test_refresh_persists_remote_catalog(tmp_path):
    payloads = {
        "/v1/brawlers": {"list": [{"id": 1, "name": "Shelly", "released": True}]},
        "/v1/maps": {"list": [{"id": 2, "name": "Hard Rock Mine", "disabled": False}]},
        "/v1/gamemodes": {"list": [{"id": 3, "name": "Gem Grab"}]},
    }
    def handler(request):
        return httpx.Response(200, json=payloads[request.url.path])
    service = KnowledgeService(tmp_path / "knowledge.json", transport=httpx.MockTransport(handler))
    result = await service.refresh(force=True)
    assert result["counts"] == {"brawlers": 1, "maps": 1, "gamemodes": 1}
    assert result["updated_sections"] == ["brawlers", "maps", "gamemodes"]
    assert (tmp_path / "knowledge.json").exists()
    assert service.search("brawlers", "shel")["total_matches"] == 1

@pytest.mark.asyncio
async def test_refresh_failure_keeps_existing_cache(tmp_path):
    cache = tmp_path / "knowledge.json"
    cache.write_text(json.dumps({"brawlers": [{"name": "Shelly"}], "maps": [], "gamemodes": [], "updated_at": 1}))
    def handler(request):
        return httpx.Response(503)
    service = KnowledgeService(cache, transport=httpx.MockTransport(handler))
    result = await service.refresh(force=True)
    assert result["cache_available"] is True
    assert service.search("brawlers", "shel")["total_matches"] == 1
    assert result["errors"]

def test_search_rejects_unknown_category(tmp_path):
    service = KnowledgeService(tmp_path / "none.json")
    with pytest.raises(ValueError):
        service.search("players", "tag")
