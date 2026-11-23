from brawlbot.contracts import (
    validate_observation,
    state_to_observation,
    validate_action_id,
    ACTIONS,
    CONTRACT_VERSION,
)
from brawlbot.brains import HeuristicBrain
from brawlbot.runtime import BrainRuntime


def test_contract_version():
    assert CONTRACT_VERSION == "arena_obs8_act5_v1"
    assert len(ACTIONS) == 5


def test_validate_observation():
    obs = validate_observation([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
    assert len(obs) == 8
    assert all(0.0 <= v <= 1.0 for v in obs)


def test_state_to_observation():
    obs = state_to_observation({"x": 0.2, "health": 0.9})
    assert len(obs) == 8
    assert obs[0] == 0.2
    assert obs[2] == 0.9


def test_validate_action_id():
    assert validate_action_id(0) == 0
    assert validate_action_id(4) == 4
    try:
        validate_action_id(99)
        assert False, "Should have raised"
    except ValueError:
        pass


def test_heuristic_brain():
    brain = HeuristicBrain()
    brain.load()
    health = brain.health_check()
    assert health["ok"] is True
    meta = brain.metadata()
    assert meta["brain_type"] == "heuristic"

    # Low health → retreat
    pred = brain.predict([0.5, 0.5, 0.15, 0.8, 0.5, 0.5, 0.5, 0.1], context={"under_pressure": True})
    assert pred.action == "retreat"
    assert pred.action_id == 2


def test_runtime_fallback():
    rt = BrainRuntime()
    status = rt.status()
    assert status["using_fallback"] is True
    assert status["active_brain"]["brain_type"] == "heuristic"

    result = rt.decide_sync({"health": 0.1, "under_pressure": True})
    assert result["action"] == "retreat"
    assert result["fallback_used"] is True
    assert "inference_ms" in result
