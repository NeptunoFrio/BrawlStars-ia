"""Entrenamiento PPO del simulador abstracto.
Guarda y registra el modelo a través del Model Manager.
"""
import argparse
import tempfile
from pathlib import Path

from ..simulator import Arena
from .. import models


def main():
    parser = argparse.ArgumentParser(
        description="Entrena un agente PPO para el simulador abstracto de BrawlBot AI"
    )
    parser.add_argument("--timesteps", type=int, default=50_000)
    parser.add_argument(
        "--activate",
        action="store_true",
        help="Activar el modelo como activo tras el entrenamiento",
    )
    parser.add_argument("--version", type=str, default="1.0.0")
    parser.add_argument(
        "--description",
        type=str,
        default="Modelo PPO entrenado en Arena abstracta (BrawlBot AI 0.4.2)",
    )
    args = parser.parse_args()

    try:
        import gymnasium as gym
        import numpy as np
        from stable_baselines3 import PPO
    except ImportError as exc:
        raise SystemExit(
            "Instala requirements-training.txt antes de entrenar.\n"
            "pip install -r requirements-training.txt"
        ) from exc

    class ArenaEnv(gym.Env):
        metadata = {"render_modes": []}

        def __init__(self):
            super().__init__()
            self.action_space = gym.spaces.Discrete(5)
            self.observation_space = gym.spaces.Box(
                low=0, high=1, shape=(8,), dtype=np.float32
            )
            self.arena = Arena()

        def reset(self, seed=None, options=None):
            super().reset(seed=seed)
            self.arena = Arena(seed)
            return np.asarray(self.arena.reset(), dtype=np.float32), {}

        def step(self, action):
            obs, reward, done, info = self.arena.step(int(action))
            return (
                np.asarray(obs, dtype=np.float32),
                float(reward),
                bool(done),
                False,
                info,
            )

    env = ArenaEnv()
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        n_steps=1024,
        batch_size=64,
        learning_rate=3e-4,
    )
    model.learn(total_timesteps=args.timesteps)

    # Guardar temporalmente y registrar a través del Model Manager
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "ppo_arena"
        model.save(str(tmp_path))  # genera ppo_arena.zip
        zip_path = Path(str(tmp_path) + ".zip")

        item = models.register_trained_model(
            source_path=zip_path,
            brain_type="ppo",
            description=args.description,
            version=args.version,
            filename="ppo_arena.zip",
            activate=args.activate,
        )

    print("Modelo registrado correctamente:")
    print(f"  id          : {item['id']}")
    print(f"  path        : {item['path']}")
    print(f"  brain_type  : {item['brain_type']}")
    print(f"  version     : {item['version']}")
    if args.activate:
        print("  → Activado como modelo activo del Runtime")


if __name__ == "__main__":
    main()
