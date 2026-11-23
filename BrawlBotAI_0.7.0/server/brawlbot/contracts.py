import math
CONTRACT_VERSION = "arena_obs8_act5_v1"
OBS_DIM, ACT_DIM = 8, 5
ACTIONS = ["hold", "move_to_objective", "retreat", "approach_enemy", "strafe"]
ACTION_TO_ID = {n: i for i, n in enumerate(ACTIONS)}
ID_TO_ACTION = {i: n for i, n in enumerate(ACTIONS)}
def validate_observation(obs):
    if len(obs) != 8: raise ValueError("Se esperan 8 valores")
    return [max(0.0, min(1.0, float(v))) for v in obs]
def state_to_observation(s):
    return validate_observation([s.get("x",0.5), s.get("y",0.5), s.get("health",1.0), s.get("enemy_x",0.75), s.get("enemy_y",0.5), s.get("objective_x",0.5), s.get("objective_y",0.5), s.get("step_fraction",0.0)])
def validate_action_id(a):
    aid = int(a)
    if aid not in ID_TO_ACTION: raise ValueError("Accion invalida")
    return aid
