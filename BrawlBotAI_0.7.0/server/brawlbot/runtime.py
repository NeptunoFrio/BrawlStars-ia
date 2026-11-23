import asyncio
import threading
import time
from typing import Any
from .brain_interface import BrainInterface
from .brains import HeuristicBrain, ONNXBrain, PPOBrain
from .contracts import ACTIONS, CONTRACT_VERSION, state_to_observation
from . import models

class BrainRuntime:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._fallback = HeuristicBrain()
        self._fallback.load()
        self._active: BrainInterface = self._fallback
        self._fallback_reason: str | None = "Usando heurística por defecto."

    def bootstrap_from_registry(self) -> None:
        active_id = models.list_models().get("active_model")
        if active_id:
            try:
                self.activate_model(active_id)
            except Exception as exc:
                with self._lock:
                    self._active = self._fallback
                    self._fallback_reason = f"Error cargando modelo {active_id}: {exc}"

    def activate_model(self, model_id: str | None) -> dict[str, Any]:
        if not model_id or model_id == self._fallback.brain_id:
            with self._lock:
                self._active = self._fallback
                self._fallback_reason = "Heurística activada."
            models.set_active_model_id(None)
            return self.status()

        item = models.get_model(model_id)
        if not item:
            raise KeyError("Modelo no encontrado.")

        candidate: BrainInterface = (
            ONNXBrain(item["id"], item["path"], item.get("version", "1.0.0"))
            if item["brain_type"] == "onnx"
            else PPOBrain(item["id"], item["path"], item.get("version", "1.0.0"))
        )
        try:
            candidate.load()
        except Exception as exc:
            models.mark_validation(model_id, validated=False, error=str(exc))
            raise ValueError(f"Modelo incompatible: {exc}") from exc

        models.mark_validation(model_id, validated=True, error=None)
        models.set_active_model_id(model_id)
        with self._lock:
            self._active = candidate
            self._fallback_reason = None
        return self.status()

    def decide_sync(self, state: dict[str, Any]) -> dict[str, Any]:
        obs = state_to_observation(state)
        t0 = time.perf_counter()
        with self._lock:
            brain = self._active
            fallback_used = brain.brain_id == self._fallback.brain_id
            reason_note = self._fallback_reason

        try:
            pred = brain.predict(obs, context=state)
        except Exception as exc:
            pred = self._fallback.predict(obs, context=state)
            brain = self._fallback
            fallback_used = True
            reason_note = f"Fallback por error en inferencia: {exc}"

        return {
            "action": pred.action,
            "action_id": pred.action_id,
            "reason": pred.reason,
            "confidence": pred.confidence,
            "brain_id": brain.brain_id,
            "brain_type": brain.brain_type,
            "model_version": brain.model_version,
            "inference_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "fallback_used": fallback_used,
            "fallback_reason": reason_note,
            "contract_version": CONTRACT_VERSION,
            "allowed_actions": ACTIONS,
        }

    async def decide(self, state: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self.decide_sync, state)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active_brain": self._active.metadata(),
                "health": self._active.health_check(),
                "using_fallback": self._active.brain_id == self._fallback.brain_id,
                "fallback_reason": self._fallback_reason,
                "contract_version": CONTRACT_VERSION,
            }

runtime = BrainRuntime()
