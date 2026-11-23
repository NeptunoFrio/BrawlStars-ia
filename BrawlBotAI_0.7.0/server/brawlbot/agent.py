"""
[DEPRECATED] Módulo de compatibilidad.

La lógica heurística se movió a HeuristicBrain (brains.py).
Este archivo se mantiene temporalmente para no romper posibles imports externos.
Se eliminará en una versión posterior (0.5.x).
"""
from __future__ import annotations

import warnings

from .brains import HeuristicBrain
from .contracts import ACTIONS

warnings.warn(
    "brawlbot.agent está deprecado. Usa HeuristicBrain desde brawlbot.brains.",
    DeprecationWarning,
    stacklevel=2,
)

_brain = HeuristicBrain()
_brain.load()


def choose_action(state: dict) -> dict:
    """Compatibilidad con la API antigua. Delega en HeuristicBrain."""
    obs = [
        float(state.get("x", 0.5)),
        float(state.get("y", 0.5)),
        float(state.get("health", 1.0)),
        float(state.get("enemy_x", 0.75)),
        float(state.get("enemy_y", 0.5)),
        float(state.get("objective_x", 0.5)),
        float(state.get("objective_y", 0.5)),
        float(state.get("step_fraction", 0.0)),
    ]
    pred = _brain.predict(obs, context=state)
    return {
        "action": pred.action,
        "reason": pred.reason,
        "confidence": pred.confidence,
        "policy": "heuristic-v2-compat",
        "allowed_actions": ACTIONS,
    }
