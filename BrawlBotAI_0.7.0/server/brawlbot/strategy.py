from collections import defaultdict

BRAWLERS = {
    "Colt": {"roles": ["damage", "lane"], "modes": ["heist", "bounty"], "range": "long", "tags": ["open_map"]},
    "Poco": {"roles": ["support", "healer"], "modes": ["gem_grab", "hot_zone"], "range": "medium", "tags": ["team_sustain"]},
    "Shelly": {"roles": ["tank_counter", "control"], "modes": ["brawl_ball", "showdown"], "range": "short", "tags": ["bushes", "anti_tank"]},
    "Jessie": {"roles": ["control", "lane"], "modes": ["hot_zone", "gem_grab"], "range": "medium", "tags": ["objective"]},
    "Nita": {"roles": ["control", "pressure"], "modes": ["hot_zone", "brawl_ball"], "range": "medium", "tags": ["objective", "summon"]},
    "Brock": {"roles": ["damage", "range"], "modes": ["bounty", "knockout"], "range": "long", "tags": ["open_map"]},
    "Bull": {"roles": ["tank", "close_range"], "modes": ["heist", "brawl_ball"], "range": "short", "tags": ["walls", "bushes"]},
    "Barley": {"roles": ["area_control"], "modes": ["hot_zone", "gem_grab"], "range": "long", "tags": ["walls", "objective"]},
    "Rico": {"roles": ["damage", "lane"], "modes": ["brawl_ball", "gem_grab"], "range": "long", "tags": ["walls"]},
    "Gene": {"roles": ["support", "pick"], "modes": ["gem_grab", "bounty"], "range": "long", "tags": ["pick", "team_play"]},
    "Max": {"roles": ["support", "mobility"], "modes": ["gem_grab", "brawl_ball"], "range": "medium", "tags": ["mobility", "team_play"]},
    "Spike": {"roles": ["damage", "control"], "modes": ["gem_grab", "hot_zone", "brawl_ball"], "range": "long", "tags": ["anti_tank", "area_control"]},
    "Piper": {"roles": ["sniper", "damage"], "modes": ["bounty", "knockout"], "range": "very_long", "tags": ["open_map"]},
    "Frank": {"roles": ["tank", "control"], "modes": ["brawl_ball", "hot_zone"], "range": "short", "tags": ["walls", "objective"]},
}

MAPS = {
    "hard_rock_mine": {"modes": ["gem_grab"], "terrain": "mixed", "features": ["central_objective", "walls", "lanes"]},
    "parallel_plays": {"modes": ["hot_zone"], "terrain": "open", "features": ["multiple_zones", "long_sightlines"]},
    "super_beach": {"modes": ["brawl_ball"], "terrain": "bushy", "features": ["walls", "bushes", "central_lane"]},
    "shooting_star": {"modes": ["bounty"], "terrain": "open", "features": ["long_sightlines", "few_walls"]},
    "safe_zone": {"modes": ["heist"], "terrain": "mixed", "features": ["safe_objective", "lanes", "walls"]},
}

COUNTERS = {
    "Bull": ["Shelly", "Spike", "Colt"],
    "Frank": ["Shelly", "Spike", "Piper"],
    "Piper": ["Bull", "Shelly"],
    "Barley": ["Piper", "Brock"],
    "Colt": ["Piper", "Brock"],
}

def normalize(value: str) -> str:
    return value.strip().lower().replace(" ", "_")

def recommend_draft(mode: str, map_name: str, owned: list[str], enemies: list[str], team_size: int = 3):
    mode_key, map_key = normalize(mode), normalize(map_name)
    valid_owned = [b for b in owned if b in BRAWLERS]
    if not valid_owned:
        valid_owned = list(BRAWLERS)
    map_data = MAPS.get(map_key, {"terrain": "mixed", "features": []})
    enemy_counter_pressure = set()
    for enemy in enemies:
        enemy_counter_pressure.update(COUNTERS.get(enemy, []))

    scored = []
    for name in valid_owned:
        data = BRAWLERS[name]
        score, reasons = 0.0, []
        if mode_key in data["modes"]:
            score += 3.0; reasons.append(f"tiene buena sinergia con {mode_key}")
        if map_data["terrain"] == "open" and data["range"] in ("long", "very_long"):
            score += 2.0; reasons.append("aprovecha las líneas de visión abiertas")
        if map_data["terrain"] == "bushy" and ("bushes" in data["tags"] or data["range"] == "short"):
            score += 1.5; reasons.append("puede aprovechar la cobertura")
        if "objective" in data["tags"] and any("objective" in f for f in map_data["features"]):
            score += 1.0; reasons.append("aporta presión sobre el objetivo")
        if name in enemy_counter_pressure:
            score += 1.5; reasons.append("puede responder a una amenaza rival")
        scored.append({"brawler": name, "score": round(score, 2), "reasons": reasons or ["opción flexible"]})
    scored.sort(key=lambda x: (-x["score"], x["brawler"]))
    picks = scored[:team_size]
    roles = defaultdict(int)
    for pick in picks:
        for role in BRAWLERS[pick["brawler"]]["roles"]:
            roles[role] += 1
    warnings = []
    if not any(BRAWLERS[p["brawler"]]["roles"][0] in ("support", "healer") for p in picks):
        warnings.append("El equipo no tiene un apoyo/curación clara.")
    if not any(BRAWLERS[p["brawler"]]["range"] in ("long", "very_long") for p in picks):
        warnings.append("El equipo puede sufrir contra rivales de largo alcance.")
    return {
        "mode": mode_key, "map": map_key, "recommendations": picks,
        "team_roles": dict(roles), "warnings": warnings,
        "disclaimer": "Recomendación heurística inicial; valida con experiencia y datos actuales."
    }

def analyze_team(mode: str, map_name: str, team: list[str]):
    unknown = [b for b in team if b not in BRAWLERS]
    known = [b for b in team if b in BRAWLERS]
    if not known:
        return {"score": 0, "strengths": [], "weaknesses": ["No hay Brawlers reconocidos."], "unknown": unknown}
    roles = [r for b in known for r in BRAWLERS[b]["roles"]]
    strengths, weaknesses = [], []
    if any(r in roles for r in ("support", "healer")): strengths.append("Tiene herramientas de apoyo.")
    else: weaknesses.append("Carece de apoyo o curación.")
    if any(BRAWLERS[b]["range"] in ("long", "very_long") for b in known): strengths.append("Tiene alcance para controlar líneas.")
    else: weaknesses.append("Puede sufrir en mapas abiertos.")
    if len(set(known)) < len(known): weaknesses.append("Hay Brawlers repetidos.")
    if len(known) < 3: weaknesses.append("Composición incompleta: faltan integrantes.")
    mode_key = normalize(mode)
    if not any(mode_key in BRAWLERS[b]["modes"] for b in known): weaknesses.append("La composición no muestra una especialización clara para este modo.")
    return {"score": max(0, min(100, 55 + 10*len(strengths) - 10*len(weaknesses))),
            "strengths": strengths, "weaknesses": weaknesses, "unknown": unknown,
            "team": known, "map": normalize(map_name), "mode": mode_key}
