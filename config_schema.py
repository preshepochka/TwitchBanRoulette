from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class TwitchConfig(StrictModel):
    channel: str
    tocken: str
    reward_id: str

class WindowConfig(StrictModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    chroma_key: tuple[int, int, int]
    card_size: tuple[int, int] = (200, 150)
    pointer_size: tuple[int,int] = (40, 40)
    winner_pointer: str | None = None

    @field_validator("chroma_key")
    @classmethod
    def _chroma_range(cls, v):
        if not all(0 <= c <= 255 for c in v):
            raise ValueError("each RGB channel must be 0...255")
        return v

class Outcome(StrictModel):
    img: str
    chance: float = Field(gt=0, le=100)
    action: str
    duration: int | None = None
    text: str | None = None

class Config(StrictModel):
    twitch: TwitchConfig
    window: WindowConfig
    outcomes: dict[str, Outcome]

    @model_validator(mode="after")
    def _chance_sum_100(self):
        total = sum(o.chance for o in self.outcomes.values())
        if abs(total - 100) > 1e-6:
            raise ValueError(f"sum of chances must be 100, got {total}")
        return self
