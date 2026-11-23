"""Tactical action planner for structured observations.

This module plans controls from observations supplied by a trusted test harness.
It does not capture the game screen or inject input into the Brawl Stars client.
"""
from __future__ import annotations
import math
from typing import Any


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _point(x: float, y: float) -> dict[str, float]:
    return {"x": round(_clamp(x), 4), "y": round(_clamp(y), 4)}


def plan_action(state: dict[str, Any]) -> dict[str, Any]:
    """Return a conservative, normalized tactical control plan."""
    x, y = _clamp(state.get("player_x", .5)), _clamp(state.get("player_y", .5))
    hp = _clamp(state.get("health", 1.0))
    ammo = max(0, min(3, int(state.get("ammo", 3))))
    target = state.get("target") or {}
    objective = state.get("objective") or {"x": .5, "y": .5}
    projectiles = state.get("incoming_projectiles") or []
    visible = bool(target.get("visible", False))
    los = bool(target.get("line_of_sight", False))
    tx, ty = _clamp(target.get("x", .5)), _clamp(target.get("y", .5))
    ox, oy = _clamp(objective.get("x", .5)), _clamp(objective.get("y", .5))
    enemy_dist = math.dist((x, y), (tx, ty))

    # Dodge direction is perpendicular to the nearest reported projectile path.
    dodge = None
    if projectiles:
        nearest = min(projectiles, key=lambda p: math.dist((x, y), (float(p.get("x", 0)), float(p.get("y", 0)))))
        px, py = _clamp(nearest.get("x", x)), _clamp(nearest.get("y", y))
        vx, vy = x - px, y - py
        norm = math.hypot(vx, vy) or 1.0
        # Choose the perpendicular direction that remains inside the arena.
        candidates = [(x - vy / norm * .22, y + vx / norm * .22),
                      (x + vy / norm * .22, y - vx / norm * .22)]
        dodge = min(candidates, key=lambda p: (max(0, -p[0]) + max(0, p[0]-1) + max(0, -p[1]) + max(0, p[1]-1)))
        destination = _point(*dodge)
        movement = "dodge"
        reason = "Amenaza de proyectil detectada; desplazamiento lateral evasivo."
    elif hp <= .28:
        dx, dy = x - tx, y - ty
        norm = math.hypot(dx, dy) or 1.0
        destination = _point(x + dx / norm * .2, y + dy / norm * .2)
        movement, reason = "retreat", "Salud crítica; prioriza ganar distancia."
    elif visible and enemy_dist < .18:
        destination = _point(x, y + (.18 if y < .5 else -.18))
        movement, reason = "strafe", "Enemigo cercano; cambia lateralmente de posición."
    else:
        dx, dy = ox - x, oy - y
        norm = math.hypot(dx, dy) or 1.0
        destination = _point(x + dx / norm * min(.2, norm), y + dy / norm * min(.2, norm))
        movement, reason = "objective", "Avanza hacia el objetivo mientras no exista amenaza inmediata."

    fire = bool(visible and los and ammo > 0 and enemy_dist <= .72 and hp > .12 and not projectiles)
    aim = _point(tx, ty) if visible else None
    return {
        "planner": "tactical_planner_v1",
        "movement": movement,
        "move_to": destination,
        "aim_at": aim,
        "fire": fire,
        "dodge": bool(projectiles),
        "use_super": bool(state.get("super_ready", False) and visible and los and enemy_dist < .38 and hp > .35),
        "reason": reason,
        "confidence": round(.78 if visible else .62, 2),
        "execution": "PLAN_ONLY",
        "live_game_control": False,
        "limitations": [
            "La observación debe ser proporcionada por un adaptador externo.",
            "Este endpoint no captura pantalla ni envía toques al cliente del juego.",
            "Las coordenadas son normalizadas para un entorno de prueba, no calibradas para una pantalla real."
        ]
    }
