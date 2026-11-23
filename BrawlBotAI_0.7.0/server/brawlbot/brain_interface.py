from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
@dataclass
class PredictionResult:
    action_id: int
    action: str
    reason: str
    confidence: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)
class BrainInterface(ABC):
    brain_id = "unknown"
    brain_type = "unknown"
    model_version = "0.4.2"
    contract_version = "arena_obs8_act5_v1"
    @abstractmethod
    def load(self): pass
    @abstractmethod
    def predict(self, observation, context=None): pass
    @abstractmethod
    def health_check(self): pass
    @abstractmethod
    def metadata(self): pass
