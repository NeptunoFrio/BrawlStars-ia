"""
[DEPRECATED] Módulo de compatibilidad.

La implementación real de ONNX está en brains.ONNXBrain.
Este archivo se mantiene temporalmente y se eliminará en 0.5.x.
"""
from __future__ import annotations

import warnings

from .brains import ONNXBrain

warnings.warn(
    "brawlbot.onnx_brain está deprecado. Usa ONNXBrain desde brawlbot.brains.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ONNXBrain", "predict_onnx"]


def predict_onnx(model_path: str, observation: list[float]) -> int:
    """Función legacy. Se recomienda usar ONNXBrain directamente."""
    brain = ONNXBrain(brain_id="legacy-onnx", model_path=model_path)
    brain.load()
    pred = brain.predict(observation)
    return pred.action_id
