import logging
import os
import hmac
import time
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware

from .schemas import DraftRequest, TeamRequest, AgentState, TacticalState
from .strategy import recommend_draft, analyze_team, MAPS, BRAWLERS
from .simulator import Arena
from .contracts import ACTION_TO_ID, CONTRACT_VERSION
from .runtime import runtime
from . import models
from .knowledge import knowledge
from .intelligence import recommend_from_catalog, analyze_catalog_team
from .tactical import plan_action

# Logging básico estructurado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("brawlbot")

# Métricas simples en memoria
_metrics = defaultdict(int)
_metrics_latency = []


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("BrawlBot AI 0.7.0 arrancando...")
    runtime.bootstrap_from_registry()
    try:
        knowledge_result = await knowledge.refresh()
        logger.info("Catálogo remoto: %s", knowledge_result.get("counts"))
    except Exception:
        logger.exception("No se pudo actualizar el catálogo remoto; se conserva la caché local.")
    st = runtime.status()
    logger.info(
        "Brain activo: %s (%s)",
        st["active_brain"].get("brain_id"),
        st["active_brain"].get("brain_type"),
    )
    yield
    logger.info("BrawlBot AI detenido.")


app = FastAPI(title="BrawlBot AI API", version="0.7.0", lifespan=lifespan)
_cors_origins = [x.strip() for x in os.getenv(
    "BRAWLBOT_CORS_ORIGINS", "http://localhost,http://127.0.0.1"
).split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

API_KEY = os.getenv("BRAWLBOT_API_KEY", "")


def auth(x_api_key: str | None = Header(default=None)):
    if API_KEY and not hmac.compare_digest(x_api_key or "", API_KEY):
        raise HTTPException(status_code=401, detail="API key inválida.")
    return True


@app.get("/health")
def health():
    st = runtime.status()
    return {
        "status": "ok",
        "service": "BrawlBot AI",
        "version": "0.7.0",
        "contract_version": CONTRACT_VERSION,
        "active_brain_type": st["active_brain"]["brain_type"],
        "using_fallback": st.get("using_fallback", True),
    }


@app.get("/api/v1/brains/status")
def brains_status(_=Depends(auth)):
    return runtime.status()


@app.get("/api/v1/metrics")
def metrics(_=Depends(auth)):
    avg_lat = (
        round(sum(_metrics_latency) / len(_metrics_latency), 3)
        if _metrics_latency
        else None
    )
    return {
        "counters": dict(_metrics),
        "avg_inference_ms": avg_lat,
        "samples": len(_metrics_latency),
    }


@app.get("/api/v1/catalog")
def catalog(_=Depends(auth)):
    status = knowledge.status()
    if status["cache_available"]:
        return {
            "brawlers": [x.get("name") for x in knowledge.data["brawlers"] if x.get("name")],
            "maps": [x.get("name") for x in knowledge.data["maps"] if x.get("name")],
            "modes": [x.get("name") for x in knowledge.data["gamemodes"] if x.get("name")],
            "remote_catalog": status["counts"],
            "source": "BrawlAPI",
        }
    return {"brawlers": list(BRAWLERS.keys()), "maps": list(MAPS.keys()),
            "modes": ["gem_grab", "brawl_ball", "hot_zone", "bounty", "knockout", "heist", "showdown"],
            "remote_catalog": status["counts"], "source": "legacy_fallback"}



@app.get("/api/v1/knowledge/status")
def knowledge_status(_=Depends(auth)):
    return knowledge.status()


@app.post("/api/v1/knowledge/refresh")
async def knowledge_refresh(force: bool = True, _=Depends(auth)):
    result = await knowledge.refresh(force=force)
    if not result.get("cache_available"):
        raise HTTPException(status_code=503, detail={"message": "No se pudo obtener el catálogo remoto y no existe caché local.", "result": result})
    return result


@app.get("/api/v1/knowledge/search")
def knowledge_search(category: str, q: str, limit: int = 25, _=Depends(auth)):
    try:
        return knowledge.search(category, q, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/draft")
async def draft(req: DraftRequest, _=Depends(auth)):
    _metrics["draft_requests"] += 1
    # Refresh only when cache is missing/expired; retain local cache on provider failure.
    try:
        await knowledge.refresh(force=False)
    except Exception:
        logger.exception("No se pudo refrescar el catálogo antes del draft; se usa la caché.")
    if knowledge.status()["cache_available"]:
        try:
            return recommend_from_catalog(
                mode=req.mode, map_name=req.map_name, owned_brawlers=req.owned_brawlers,
                enemy_picks=req.enemy_picks, team_size=req.team_size,
                catalogue=knowledge.data, updated_at=knowledge.updated_at,
                ally_picks=req.ally_picks, bans=req.bans, ranked_tier=req.ranked_tier,
            )
        except ValueError as exc:
            logger.warning("Motor dinámico no disponible: %s", exc)
    result = recommend_draft(req.mode, req.map_name, req.owned_brawlers, req.enemy_picks, req.team_size)
    result["method"] = "Fallback heurístico legado; catálogo remoto no disponible."
    result["catalogue"] = knowledge.status()
    return result


@app.post("/api/v1/team/analyze")
def team(req: TeamRequest, _=Depends(auth)):
    _metrics["team_analyze_requests"] += 1
    if knowledge.data.get("brawlers"):
        return analyze_catalog_team(mode=req.mode, map_name=req.map_name, team=req.team,
                                    catalogue=knowledge.data)
    return analyze_team(req.mode, req.map_name, req.team)


@app.post("/api/v1/agent/decide")
async def decide(req: AgentState, _=Depends(auth)):
    t0 = time.perf_counter()
    result = await runtime.decide(req.model_dump())
    elapsed = (time.perf_counter() - t0) * 1000.0
    _metrics["decide_requests"] += 1
    _metrics[f"brain_{result.get('brain_type', 'unknown')}"] += 1
    if result.get("fallback_used"):
        _metrics["fallback_used"] += 1
    _metrics_latency.append(elapsed)
    if len(_metrics_latency) > 500:
        _metrics_latency.pop(0)
    logger.debug(
        "decide → %s (%.1f ms, fallback=%s)",
        result.get("action"),
        elapsed,
        result.get("fallback_used"),
    )
    return result


@app.post("/api/v1/simulator/episode")
async def simulator_episode(
    seed: int = 7, max_steps: int = 200, _=Depends(auth)
):
    _metrics["simulator_episodes"] += 1
    arena = Arena(seed)
    obs = arena.reset()
    total = 0.0
    history = []
    for step in range(min(max_steps, 200)):
        state = {
            "x": obs[0],
            "y": obs[1],
            "health": obs[2],
            "enemy_x": obs[3],
            "enemy_y": obs[4],
            "objective_x": obs[5],
            "objective_y": obs[6],
            "step_fraction": obs[7],
            "ammo": 3,
        }
        decision = await runtime.decide(state)
        obs, reward, done, _ = arena.step(ACTION_TO_ID[decision["action"]])
        total += reward
        if len(history) < 12:
            history.append(
                {
                    "step": step + 1,
                    "decision": decision["action"],
                    "brain": decision["brain_type"],
                    "reward": round(reward, 3),
                }
            )
        if done:
            break
    return {
        "episode_steps": arena.steps,
        "total_reward": round(total, 3),
        "remaining_health": round(arena.health, 3),
        "sample_log": history,
        "environment": "abstract_arena_v1",
    }


@app.post("/api/v1/tactical/plan")
def tactical_plan(req: TacticalState, _=Depends(auth)):
    """Plan movement/aim/fire/dodge from structured test observations; never executes input."""
    _metrics["tactical_plan_requests"] += 1
    return plan_action(req.model_dump())


@app.get("/api/v1/models")
def get_models(_=Depends(auth)):
    return models.list_models()


@app.post("/api/v1/models/upload")
async def upload_model(
    file: UploadFile = File(...),
    description: str = Form(default=""),
    version: str = Form(default="1.0.0"),
    _=Depends(auth),
):
    content = await file.read()
    try:
        item = models.add_model(
            file.filename or "model.onnx", content, description, version
        )
        logger.info("Modelo subido: %s (%s)", item["id"], item["filename"])
        return item
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/models/activate")
def activate(body: dict, _=Depends(auth)):
    try:
        result = runtime.activate_model(body.get("model_id"))
        logger.info("Modelo activado: %s", body.get("model_id"))
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/v1/models/{model_id}")
def delete(model_id: str, _=Depends(auth)):
    try:
        if runtime.status()["active_brain"]["brain_id"] == model_id:
            runtime.activate_model(None)
        result = models.delete_model(model_id)
        logger.info("Modelo eliminado: %s", model_id)
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
