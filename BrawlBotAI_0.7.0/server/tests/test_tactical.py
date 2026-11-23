from brawlbot.tactical import plan_action


def test_target_visible_and_line_of_sight_allows_fire():
    result = plan_action({
        "player_x": .2, "player_y": .5, "health": .9, "ammo": 3,
        "target": {"visible": True, "line_of_sight": True, "x": .6, "y": .5},
        "objective": {"x": .5, "y": .5}
    })
    assert result["fire"] is True
    assert result["aim_at"] == {"x": .6, "y": .5}
    assert result["execution"] == "PLAN_ONLY"
    assert result["live_game_control"] is False


def test_no_fire_without_visibility_or_ammo():
    invisible = plan_action({"target": {"visible": False, "line_of_sight": True}})
    empty = plan_action({"ammo": 0, "target": {"visible": True, "line_of_sight": True}})
    assert invisible["fire"] is False
    assert empty["fire"] is False


def test_incoming_projectile_triggers_dodge_and_suppresses_fire():
    result = plan_action({
        "player_x": .5, "player_y": .5,
        "target": {"visible": True, "line_of_sight": True, "x": .8, "y": .5},
        "incoming_projectiles": [{"x": .45, "y": .5}]
    })
    assert result["dodge"] is True
    assert result["movement"] == "dodge"
    assert result["fire"] is False
