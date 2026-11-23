from brawlbot.intelligence import recommend_from_catalog


def sample_catalogue():
    return {
        "brawlers": [
            {"id": 1, "name": "Shelly", "hash": "Shelly", "released": True, "class": {"name": "Damage Dealer"}},
            {"id": 2, "name": "Poco", "hash": "Poco", "released": True, "class": {"name": "Support"}},
            {"id": 3, "name": "Piper", "hash": "Piper", "released": True, "class": {"name": "Marksman"}},
            {"id": 4, "name": "Barley", "hash": "Barley", "released": True, "class": {"name": "Artillery"}},
        ],
        "maps": [{"id": 10, "name": "Hard Rock Mine", "hash": "Hard-Rock-Mine",
                  "gameMode": {"name": "Gem Grab"}, "disabled": False}],
        "gamemodes": [{"id": 20, "name": "Gem Grab", "hash": "Gem-Grab", "scHash": "gemGrab"}],
    }


def test_dynamic_draft_uses_catalogue_and_owned_filter():
    result = recommend_from_catalog(
        mode="gem_grab", map_name="Hard Rock Mine", owned_brawlers=["Poco", "Piper", "Barley"],
        enemy_picks=["Shelly"], team_size=2, catalogue=sample_catalogue(), updated_at=123.0,
    )
    names = [x["brawler"] for x in result["recommendations"]]
    assert len(names) == 2
    assert set(names).issubset({"Poco", "Piper", "Barley"})
    assert result["input_validation"]["map_found"] is True
    assert result["input_validation"]["mode_found"] is True
    assert result["input_validation"]["map_mode_matches"] is True
    assert result["statistics"]["win_rate_available"] is False


def test_dynamic_draft_excludes_enemy_picks_and_reports_unknown_owned():
    result = recommend_from_catalog(
        mode="gem_grab", map_name="unknown map", owned_brawlers=["Shelly", "Poco", "NoExiste"],
        enemy_picks=["Shelly"], team_size=1, catalogue=sample_catalogue(), updated_at=None,
    )
    assert result["recommendations"][0]["brawler"] != "Shelly"
    assert result["input_validation"]["map_found"] is False
    assert result["input_validation"]["unknown_owned_brawlers"] == ["NoExiste"]


def test_dynamic_draft_handles_empty_owned_pool_by_using_full_roster():
    result = recommend_from_catalog(
        mode="knockout", map_name="Hard Rock Mine", owned_brawlers=[], enemy_picks=[],
        team_size=3, catalogue=sample_catalogue(), updated_at=None,
    )
    assert len(result["recommendations"]) == 3


def test_catalog_team_analysis_accepts_full_catalogue():
    from brawlbot.intelligence import analyze_catalog_team
    result = analyze_catalog_team(mode="gem_grab", map_name="Hard Rock Mine",
                                  team=["Poco", "Piper", "Barley"], catalogue=sample_catalogue())
    assert len(result["team"]) == 3
    assert "Poco" in result["team"]
    assert result["score"] >= 0
    assert "map_specific_note" in result


def test_bans_and_ally_picks_are_excluded_from_candidates():
    result = recommend_from_catalog(
        mode="Gem Grab", map_name="Hard Rock Mine", owned_brawlers=["Poco", "Piper", "Shelly", "Barley"],
        enemy_picks=["Shelly"], ally_picks=["Poco"], bans=["Barley"], team_size=2,
        catalogue=sample_catalogue(), updated_at=None, ranked_tier="Mythic",
    )
    names = [x["brawler"] for x in result["recommendations"]]
    assert "Shelly" not in names and "Poco" not in names and "Barley" not in names
    assert result["ranked_tier"] == "Mythic"


def test_solo_showdown_uses_showdown_profile():
    result = recommend_from_catalog(
        mode="Solo Showdown", map_name="unknown", owned_brawlers=[], enemy_picks=[],
        team_size=1, catalogue=sample_catalogue(), updated_at=None,
    )
    assert result["method"].startswith("Heurística transparente")
