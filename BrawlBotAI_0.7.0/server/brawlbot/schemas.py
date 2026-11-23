from pydantic import BaseModel, Field
from typing import Optional

class DraftRequest(BaseModel):
    mode: str = "gem_grab"
    map_name: str = "hard_rock_mine"
    owned_brawlers: list[str] = Field(default_factory=lambda: ["Colt", "Poco", "Shelly", "Jessie"])
    enemy_picks: list[str] = Field(default_factory=list)
    ally_picks: list[str] = Field(default_factory=list)
    bans: list[str] = Field(default_factory=list)
    ranked_tier: Optional[str] = None
    team_size: int = Field(default=3, ge=1, le=3)

class TeamRequest(BaseModel):
    mode: str = "gem_grab"
    map_name: str = "hard_rock_mine"
    team: list[str] = Field(min_length=1, max_length=3)

class AgentState(BaseModel):
    x: float = 0.5
    y: float = 0.5
    health: float = 1.0
    ammo: int = Field(default=3, ge=0, le=3)
    enemy_x: float = 0.75
    enemy_y: float = 0.5
    objective_x: float = 0.5
    objective_y: float = 0.5
    mode: str = "gem_grab"
    under_pressure: bool = False

class ModelActivation(BaseModel):
    model_id: str

class TacticalState(BaseModel):
    player_x: float = Field(default=0.5, ge=0, le=1)
    player_y: float = Field(default=0.5, ge=0, le=1)
    health: float = Field(default=1.0, ge=0, le=1)
    ammo: int = Field(default=3, ge=0, le=3)
    target: dict = Field(default_factory=dict)
    objective: dict = Field(default_factory=lambda: {"x": 0.5, "y": 0.5})
    incoming_projectiles: list[dict] = Field(default_factory=list)
    super_ready: bool = False
