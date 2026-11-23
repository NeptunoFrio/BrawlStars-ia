from fastapi.testclient import TestClient
from brawlbot.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "0.7.0"
    assert data["status"] == "ok"
    assert "contract_version" in data


def test_draft():
    r = client.post(
        "/api/v1/draft",
        json={
            "mode": "gem_grab",
            "map_name": "hard_rock_mine",
            "owned_brawlers": ["Poco", "Jessie", "Colt", "Shelly"],
            "enemy_picks": ["Bull"],
            "team_size": 3,
        },
    )
    assert r.status_code == 200
    assert len(r.json()["recommendations"]) == 3


def test_team_analyze():
    r = client.post(
        "/api/v1/team/analyze",
        json={
            "mode": "gem_grab",
            "map_name": "hard_rock_mine",
            "team": ["Poco", "Colt", "Jessie"],
        },
    )
    assert r.status_code == 200
    assert "score" in r.json()


def test_agent_decide_heuristic():
    r = client.post(
        "/api/v1/agent/decide",
        json={"health": 0.2, "under_pressure": True},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["action"] == "retreat"
    assert data["brain_type"] == "heuristic"
    assert "inference_ms" in data


def test_simulator():
    r = client.post("/api/v1/simulator/episode")
    assert r.status_code == 200
    data = r.json()
    assert data["episode_steps"] > 0
    assert "total_reward" in data


def test_brains_status():
    r = client.get("/api/v1/brains/status")
    assert r.status_code == 200
    data = r.json()
    assert "active_brain" in data
    assert "contract_version" in data


def test_models_list():
    r = client.get("/api/v1/models")
    assert r.status_code == 200
    data = r.json()
    assert "models" in data
    assert "active_model" in data


def test_metrics():
    r = client.get("/api/v1/metrics")
    assert r.status_code == 200
    assert "counters" in r.json()


def test_catalog():
    r = client.get("/api/v1/catalog")
    assert r.status_code == 200
    data = r.json()
    assert "brawlers" in data
    assert "maps" in data


def test_knowledge_status_endpoint():
    r = client.get("/api/v1/knowledge/status")
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "BrawlAPI"
    assert "performance_stats_available" in data


def test_knowledge_search_endpoint():
    from brawlbot.knowledge import knowledge
    knowledge.data["brawlers"] = [{"id": 1, "name": "Shelly"}]
    r = client.get("/api/v1/knowledge/search", params={"category": "brawlers", "q": "shel"})
    assert r.status_code == 200
    assert r.json()["total_matches"] == 1


def test_draft_uses_dynamic_catalogue_when_available(monkeypatch):
    from brawlbot.knowledge import knowledge
    monkeypatch.setattr(knowledge, "data", {
        "brawlers": [
            {"id": 1, "name": "Poco", "released": True, "class": {"name": "Support"}},
            {"id": 2, "name": "Piper", "released": True, "class": {"name": "Marksman"}},
            {"id": 3, "name": "Shelly", "released": True, "class": {"name": "Damage Dealer"}},
        ],
        "maps": [{"id": 10, "name": "Hard Rock Mine", "gameMode": {"name": "Gem Grab"}}],
        "gamemodes": [{"id": 20, "name": "Gem Grab", "hash": "Gem-Grab"}],
    })
    monkeypatch.setattr(knowledge, "updated_at", 123.0)
    response = client.post("/api/v1/draft", json={
        "mode": "gem_grab", "map_name": "Hard Rock Mine",
        "owned_brawlers": ["Poco", "Piper", "Shelly"], "enemy_picks": [], "team_size": 2,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["catalogue"]["source"] == "BrawlAPI"
    assert len(data["recommendations"]) == 2
    assert data["statistics"]["win_rate_available"] is False
