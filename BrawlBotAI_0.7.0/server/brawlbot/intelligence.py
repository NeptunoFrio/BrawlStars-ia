"""Catalogue-driven draft intelligence.

Uses the live BrawlAPI catalogue for the complete roster, map and mode names.
It deliberately does not invent map win-rates, pick-rates or statistical counters:
BrawlAPI's public static map dataset does not contain those samples.
Scores here are transparent class/mode heuristics, not measured meta statistics.
"""
from __future__ import annotations

from difflib import get_close_matches
from typing import Any
import re

MODE_PROFILES: dict[str, dict[str, float]] = {
    "gem grab": {"Controller": 3.0, "Support": 2.3, "Marksman": 1.4, "Damage Dealer": 1.4, "Assassin": 0.8},
    "brawl ball": {"Tank": 2.4, "Assassin": 2.0, "Support": 1.5, "Controller": 1.3, "Damage Dealer": 1.3},
    "hot zone": {"Controller": 3.0, "Tank": 2.0, "Support": 1.5, "Damage Dealer": 1.4, "Assassin": 0.8},
    "bounty": {"Marksman": 3.0, "Damage Dealer": 2.2, "Controller": 1.3, "Support": 1.0, "Tank": 0.3},
    "knockout": {"Marksman": 3.0, "Damage Dealer": 2.2, "Controller": 1.5, "Assassin": 1.0, "Tank": 0.4},
    "heist": {"Damage Dealer": 3.0, "Tank": 2.0, "Assassin": 1.0, "Marksman": 1.0, "Controller": 0.8},
    "showdown": {"Assassin": 2.0, "Tank": 1.8, "Damage Dealer": 1.8, "Marksman": 1.4, "Controller": 1.2, "Support": 0.4},
    "duels": {"Assassin": 2.0, "Damage Dealer": 2.0, "Tank": 1.6, "Marksman": 1.5, "Controller": 1.3},
    "wipeout": {"Marksman": 2.8, "Damage Dealer": 2.2, "Controller": 1.5, "Assassin": 1.0},
    "basket brawl": {"Tank": 2.0, "Assassin": 1.8, "Damage Dealer": 1.8, "Support": 1.4, "Controller": 1.2},
    "paint brawl": {"Controller": 2.5, "Damage Dealer": 2.0, "Assassin": 1.6, "Tank": 1.5, "Support": 1.2},
}


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _resolve(items: list[dict[str, Any]], query: str) -> dict[str, Any] | None:
    q = norm(query)
    if not q:
        return None
    for item in items:
        if q in {norm(item.get("name")), norm(item.get("hash")), norm(item.get("scHash"))}:
            return item
    names = {norm(x.get("name")): x for x in items if x.get("name")}
    close = get_close_matches(q, list(names), n=1, cutoff=0.82)
    return names[close[0]] if close else None


def _profile_for_mode(mode_key: str) -> dict[str, float]:
    if mode_key in MODE_PROFILES:
        return MODE_PROFILES[mode_key]
    aliases = {
        "solo showdown": "showdown", "duo showdown": "showdown", "trio showdown": "showdown",
        "knockout 5v5": "knockout", "brawl ball 5v5": "brawl ball",
        "hot zone 5v5": "hot zone", "heist 5v5": "heist", "wipeout 5v5": "wipeout",
    }
    return MODE_PROFILES.get(aliases.get(mode_key, ""), {})


def _class_name(brawler: dict[str, Any]) -> str:
    value = brawler.get("class")
    if isinstance(value, dict):
        return str(value.get("name") or "Unknown")
    return str(value or "Unknown")


def recommend_from_catalog(
    *, mode: str, map_name: str, owned_brawlers: list[str], enemy_picks: list[str],
    team_size: int, catalogue: dict[str, list[dict[str, Any]]], updated_at: float | None,
    ally_picks: list[str] | None = None, bans: list[str] | None = None,
    ranked_tier: str | None = None,
) -> dict[str, Any]:
    brawlers = [b for b in catalogue.get("brawlers", []) if b.get("name") and b.get("released", True)]
    maps = catalogue.get("maps", [])
    modes = catalogue.get("gamemodes", [])
    if not brawlers:
        raise ValueError("El catálogo remoto de Brawlers está vacío.")

    mode_obj = _resolve(modes, mode)
    map_obj = _resolve(maps, map_name)
    resolved_mode = str((mode_obj or {}).get("name") or mode)
    resolved_map = str((map_obj or {}).get("name") or map_name)
    mode_key = norm(resolved_mode)
    profile = _profile_for_mode(mode_key)

    by_name = {norm(b.get("name")): b for b in brawlers}
    owned = [by_name[norm(name)] for name in owned_brawlers if norm(name) in by_name]
    owned_filter_applied = bool(owned_brawlers)
    pool = owned if owned else (brawlers if not owned_filter_applied else brawlers)
    banned = list(bans or [])
    allies = list(ally_picks or [])
    excluded = {norm(x) for x in enemy_picks} | {norm(x) for x in banned} | {norm(x) for x in allies}
    pool = [b for b in pool if norm(b.get("name")) not in excluded]

    ally_classes = [_class_name(by_name[norm(name)]) for name in allies if norm(name) in by_name]
    enemy_classes = [_class_name(by_name[norm(name)]) for name in enemy_picks if norm(name) in by_name]
    scored: list[dict[str, Any]] = []
    for b in pool:
        name = str(b["name"])
        cls = _class_name(b)
        score = profile.get(cls, 0.6 if not profile else 0.25)
        reasons: list[str] = []
        if cls in profile:
            reasons.append(f"su clase ({cls}) encaja con el perfil general del modo {resolved_mode}")
        else:
            reasons.append("clase sin bonificación específica para este modo")
        if cls == "Support" and team_size >= 2:
            score += 0.35
            reasons.append("añade una función de apoyo al equipo")
        if ally_classes and cls not in ally_classes:
            score += 0.6
            reasons.append("complementa las clases ya elegidas por tus aliados")
        elif ally_classes and cls in ally_classes:
            score -= 0.35
            reasons.append("repite una clase ya presente en tus aliados")
        if enemy_classes:
            # Composition context only. This is not a validated counter table.
            known_roles = {"Tank", "Marksman", "Assassin", "Controller", "Support", "Damage Dealer"}
            if cls in known_roles and cls not in enemy_classes:
                score += 0.2
                reasons.append("añade diversidad de clase frente al rival; no es un counter estadístico")
        scored.append({"brawler": name, "class": cls, "score": round(float(score), 2), "reasons": reasons})

    # Greedy diversity: avoid returning three identical classes when close alternatives exist.
    selected: list[dict[str, Any]] = []
    remaining = scored[:]
    while remaining and len(selected) < team_size:
        def adjusted(item: dict[str, Any]) -> tuple[float, str]:
            repeats = sum(1 for p in selected if p["class"] == item["class"])
            return (item["score"] - repeats * 0.55, item["brawler"])
        best = max(remaining, key=adjusted)
        selected.append(best)
        remaining.remove(best)

    age = None
    if updated_at:
        import time
        age = max(0, int(time.time() - updated_at))
    map_mode_match = None
    if map_obj and isinstance(map_obj.get("gameMode"), dict):
        map_mode_match = norm(map_obj["gameMode"].get("name")) == mode_key

    return {
        "mode": resolved_mode,
        "mode_objective": {"short_description": (mode_obj or {}).get("shortDescription"),
                           "description": (mode_obj or {}).get("description")},
        "ranked_tier": ranked_tier,
        "map": resolved_map,
        "map_details": {"environment": ((map_obj or {}).get("environment") or {}).get("name") if isinstance((map_obj or {}).get("environment"), dict) else None,
                        "game_mode": ((map_obj or {}).get("gameMode") or {}).get("name") if isinstance((map_obj or {}).get("gameMode"), dict) else None,
                        "disabled": (map_obj or {}).get("disabled"),
                        "source_link": (map_obj or {}).get("link")},
        "map_id": (map_obj or {}).get("id"),
        "mode_id": (mode_obj or {}).get("id"),
        "recommendations": selected,
        "alternatives": sorted([x for x in scored if x not in selected], key=lambda x: (-x["score"], x["brawler"]))[:5],
        "catalogue": {"source": "BrawlAPI", "updated_at": updated_at, "age_seconds": age,
                      "brawlers_available": len(brawlers), "maps_available": len(maps),
                      "modes_available": len(modes)},
        "input_validation": {"map_found": map_obj is not None, "map_disabled": (map_obj or {}).get("disabled"),
                             "mode_found": mode_obj is not None, "map_mode_matches": map_mode_match,
                             "excluded_bans": banned, "excluded_enemy_picks": list(enemy_picks),
                             "ally_picks_recognized": [x for x in allies if norm(x) in by_name],
                             "owned_filter_applied": bool(owned) if owned_filter_applied else False,
                             "unknown_owned_brawlers": [x for x in owned_brawlers if norm(x) not in by_name]},
        "statistics": {"win_rate_available": False, "pick_rate_available": False,
                       "reason": "El catálogo público consultado no aporta muestras estadísticas por mapa."},
        "method": "Heurística transparente por clase, modo y diversidad de equipo; no es un ranking estadístico ni un counter validado.",
        "map_specific_note": "Se reconoce el mapa y su modo asociado, pero no se puntúa su geometría ni win rate porque esta fuente no proporciona esos datos.",
    }


def analyze_catalog_team(*, mode: str, map_name: str, team: list[str],
                         catalogue: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    brawlers = {norm(x.get("name")): x for x in catalogue.get("brawlers", []) if x.get("name")}
    known = [brawlers[norm(name)] for name in team if norm(name) in brawlers]
    unknown = [name for name in team if norm(name) not in brawlers]
    classes = [_class_name(x) for x in known]
    profile = _profile_for_mode(norm(mode))
    mode_fit = sum(profile.get(c, 0.25) for c in classes)
    strengths, weaknesses = [], []
    if "Support" in classes: strengths.append("La composición incluye apoyo.")
    else: weaknesses.append("No hay un Brawler de clase Support reconocido.")
    if "Marksman" in classes: strengths.append("Incluye alcance de tipo Marksman.")
    if len(set(classes)) == len(classes) and len(classes) > 1: strengths.append("Las clases están diversificadas.")
    elif len(classes) > 1: weaknesses.append("Hay clases repetidas; revisa la diversidad del equipo.")
    if len(known) < 3: weaknesses.append("La composición tiene menos de tres Brawlers reconocidos.")
    if unknown: weaknesses.append("Hay nombres que no aparecen en el catálogo actualizado.")
    if not profile: weaknesses.append("No existe un perfil heurístico específico para este modo.")
    map_obj = _resolve(catalogue.get("maps", []), map_name)
    score = round(min(100, max(0, 45 + mode_fit * 7 + len(strengths) * 5 - len(weaknesses) * 7)), 1)
    return {"score": score, "team": [x.get("name") for x in known], "classes": classes,
            "strengths": strengths, "weaknesses": weaknesses, "unknown": unknown,
            "mode": mode, "map": (map_obj or {}).get("name", map_name),
            "method": "Evaluación heurística por clase y modo; no es una predicción estadística.",
            "map_specific_note": "No hay datos verificados de win rate o geometría de mapa en el catálogo público."}
