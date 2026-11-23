import math
from pathlib import Path
from .brain_interface import BrainInterface, PredictionResult
from .contracts import CONTRACT_VERSION, OBS_DIM, ACT_DIM, ACTION_TO_ID, ID_TO_ACTION, validate_observation, validate_action_id
class HeuristicBrain(BrainInterface):
    brain_id, brain_type, model_version, contract_version = "builtin-heuristic-v2", "heuristic", "0.4.2-heuristic", CONTRACT_VERSION
    def load(self): pass
    def predict(self, observation, context=None):
        obs = validate_observation(observation); ctx = context or {}
        x, y, hp, ex, ey, ox, oy, _ = obs
        de, do = math.dist((x, y), (ex, ey)), math.dist((x, y), (ox, oy))
        if hp < 0.28 or ctx.get("under_pressure", False): a, r = "retreat", "Prioriza conservar salud."
        elif do > 0.18: a, r = "move_to_objective", "Gana posicion en objetivo."
        elif de > 0.42 and int(ctx.get("ammo", 3)) > 0: a, r = "approach_enemy", "Distancia segura para presionar."
        elif de < 0.16: a, r = "strafe", "Maniobra lateral."
        else: a, r = "hold", "Mantiene posicion."
        return PredictionResult(ACTION_TO_ID[a], a, r, round(min(0.95, max(0.55, 0.64 + 0.22*(1-hp))), 3))
    def health_check(self): return {"ok": True, "brain_id": self.brain_id, "brain_type": self.brain_type}
    def metadata(self): return {"brain_id": self.brain_id, "brain_type": self.brain_type, "model_version": self.model_version, "contract_version": self.contract_version}
class PPOBrain(BrainInterface):
    brain_type, contract_version = "ppo", CONTRACT_VERSION
    def __init__(self, brain_id, model_path, model_version="1.0.0"):
        self.brain_id, self.model_path, self.model_version, self._model = brain_id, Path(model_path), model_version, None
    def load(self):
        import numpy as np
        from stable_baselines3 import PPO
        m = PPO.load(str(self.model_path), device="cpu")
        if getattr(m.observation_space, "shape", None) != (OBS_DIM,) or getattr(m.action_space, "n", None) != ACT_DIM: raise ValueError("Contrato PPO incompatible")
        act, _ = m.predict(np.zeros((OBS_DIM,), dtype=np.float32), deterministic=True)
        validate_action_id(int(act)); self._model = m
    def predict(self, observation, context=None):
        import numpy as np
        obs = validate_observation(observation)
        act, _ = self._model.predict(np.asarray(obs, dtype=np.float32), deterministic=True)
        aid = validate_action_id(int(act))
        return PredictionResult(aid, ID_TO_ACTION[aid], f"Politica PPO ({self.brain_id}) en CPU.", None)
    def health_check(self): return {"ok": self._model is not None, "brain_id": self.brain_id, "brain_type": self.brain_type}
    def metadata(self): return {"brain_id": self.brain_id, "brain_type": self.brain_type, "model_version": self.model_version, "contract_version": self.contract_version}
class ONNXBrain(BrainInterface):
    brain_type, contract_version = "onnx", CONTRACT_VERSION
    def __init__(self, brain_id, model_path, model_version="1.0.0"):
        self.brain_id, self.model_path, self.model_version, self._session = brain_id, Path(model_path), model_version, None
    def load(self):
        import numpy as np, onnxruntime as ort
        s = ort.InferenceSession(str(self.model_path), providers=["CPUExecutionProvider"])
        inp, out = s.get_inputs()[0], s.get_outputs()[0]
        res = s.run([out.name], {inp.name: np.zeros((1, OBS_DIM), dtype=np.float32)})[0]
        if res.shape != (1, ACT_DIM): raise ValueError("Salida ONNX incompatible")
        self._session, self._in, self._out = s, inp.name, out.name
    def predict(self, observation, context=None):
        import numpy as np
        obs = validate_observation(observation)
        logits = self._session.run([self._out], {self._in: np.asarray([obs], dtype=np.float32)})[0][0]
        aid = validate_action_id(int(np.argmax(logits)))
        return PredictionResult(aid, ID_TO_ACTION[aid], f"Inferencia ONNX ({self.brain_id}).", None)
    def health_check(self): return {"ok": self._session is not None, "brain_id": self.brain_id, "brain_type": self.brain_type}
    def metadata(self): return {"brain_id": self.brain_id, "brain_type": self.brain_type, "model_version": self.model_version, "contract_version": self.contract_version}
