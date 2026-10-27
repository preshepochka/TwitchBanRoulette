from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TwitchConfig(StrictModel):
    channel: str
    client_id: str
    token: str
    reward_id: str


class WindowConfig(StrictModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    chroma_key: tuple[int, int, int]
    card_size: tuple[int, int] = (200, 150)
    gap: int = 10
    overlay: str | None = None

    @field_validator("chroma_key")
    @classmethod
    def _chroma_range(cls, v):
        if not all(0 <= c <= 255 for c in v):
            raise ValueError("each RGB channel must be 0...255")
        return v


class TimeoutAction(StrictModel):
    type: Literal["timeout"] = "timeout"
    duration: int = Field(gt=0)


class BanAction(StrictModel):
    type: Literal["ban"] = "ban"


class MessageAction(StrictModel):
    type: Literal["message"] = "message"
    text: str


class NothingAction(StrictModel):
    type: Literal["nothing"] = "nothing"


Action = Annotated[
    Union[TimeoutAction, BanAction, MessageAction, NothingAction],
    Field(discriminator="type"),
]


class Outcome(StrictModel):
    image: str
    weight: float = Field(gt=0)
    action: Action


class Config(StrictModel):
    twitch: TwitchConfig
    window: WindowConfig
    outcomes: dict[str, Outcome]
