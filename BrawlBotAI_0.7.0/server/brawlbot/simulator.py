"""Arena abstracta 2D para experimentar con agentes sin conectarse al juego."""
import math
import random


class Arena:
    def __init__(self, seed=None):
        self.random = random.Random(seed)
        self.reset()

    def reset(self):
        self.agent = [0.15, 0.5]
        self.enemy = [0.85, 0.5]
        self.objective = [0.5, 0.5]
        self.health = 1.0
        self.steps = 0
        return self.observe()

    def observe(self):
        return [
            self.agent[0],
            self.agent[1],
            self.health,
            self.enemy[0],
            self.enemy[1],
            self.objective[0],
            self.objective[1],
            min(self.steps / 200, 1.0),
        ]

    def step(self, action: int):
        # 0 hold, 1 move_to_objective, 2 retreat, 3 approach_enemy, 4 strafe
        # Corregido: move_to_objective y approach_enemy ya no tienen el mismo delta.
        ax, ay = self.agent
        ox, oy = self.objective
        ex, ey = self.enemy

        if int(action) == 0:  # hold
            dx, dy = 0.0, 0.0
        elif int(action) == 1:  # move_to_objective
            # Moverse hacia el objetivo
            dist = math.dist((ax, ay), (ox, oy)) or 1e-6
            step = 0.045
            dx = (ox - ax) / dist * step
            dy = (oy - ay) / dist * step
        elif int(action) == 2:  # retreat (alejarse del enemigo)
            dist = math.dist((ax, ay), (ex, ey)) or 1e-6
            step = 0.05
            dx = (ax - ex) / dist * step
            dy = (ay - ey) / dist * step
        elif int(action) == 3:  # approach_enemy
            dist = math.dist((ax, ay), (ex, ey)) or 1e-6
            step = 0.04
            dx = (ex - ax) / dist * step
            dy = (ey - ay) / dist * step
        elif int(action) == 4:  # strafe
            # Movimiento lateral relativo al enemigo
            dx = 0.0
            dy = 0.05 if ay < 0.5 else -0.05
        else:
            dx, dy = 0.0, 0.0

        self.agent[0] = min(1.0, max(0.0, ax + dx))
        self.agent[1] = min(1.0, max(0.0, ay + dy))

        # Rival abstracto presiona lentamente; no replica mecánicas reales.
        if self.enemy[0] > self.agent[0]:
            self.enemy[0] -= 0.008

        dist = math.dist(self.agent, self.objective)
        reward = 0.08 if dist < 0.18 else -0.015
        enemy_dist = math.dist(self.agent, self.enemy)
        if enemy_dist < 0.12:
            self.health = max(0.0, self.health - 0.035)
        if int(action) == 2 and self.health < 0.5:
            reward += 0.025

        self.steps += 1
        done = self.health <= 0 or self.steps >= 200
        if done and self.health > 0.4:
            reward += 0.5

        return self.observe(), reward, done, {
            "objective_distance": dist,
            "health": self.health,
        }
