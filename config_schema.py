from typing import Annotated, Literal, Union

from pydantic import (BaseModel, ConfigDict, Field, field_validator,
                      model_validator)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TwitchConfig(StrictModel):
    channel: str
    client_id: str
    token: str
    reward_id: str


def _validate_rgb(v):
    if not all(0 <= c <= 255 for c in v):
        raise ValueError("each RGB channel must be 0...255")
    return v


class ChromaBackground(StrictModel):
    type: Literal["chroma"] = "chroma"


class ColorBackground(StrictModel):
    type: Literal["color"] = "color"
    color: tuple[int, int, int]

    @field_validator("color")
    @classmethod
    def _color_range(cls, v):
        return _validate_rgb(v)


class ImageBackground(StrictModel):
    type: Literal["image"] = "image"
    image: str


Background = Annotated[
    Union[ChromaBackground, ColorBackground, ImageBackground],
    Field(discriminator="type"),
]


class HighlightStyle(StrictModel):
    enabled: bool = True
    color: tuple[int, int, int] = (255, 255, 255)
    thickness: int = Field(default=3, ge=0)
    radius: int = Field(default=8, ge=0)


class WindowConfig(StrictModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    chroma_key: tuple[int, int, int]
    card_size: tuple[int, int] = (200, 150)
    gap: int = 10
    overlay: str | None = None
    title: str = "Twitch Ban Roulette"
    fps: int = Field(default=60, ge=1)
    spin_duration: float = Field(default=4.0, gt=0)
    result_hold: float = Field(default=3.0, ge=0)
    highlight: HighlightStyle = Field(default_factory=HighlightStyle)
    background: Background = Field(default_factory=ChromaBackground)

    @field_validator("chroma_key")
    @classmethod
    def _chroma_range(cls, v):
        return _validate_rgb(v)


class RouletteConfig(StrictModel):
    lead_cards: tuple[int, int] = (20, 30)

    @model_validator(mode="after")
    def _lead_order(self):
        if self.lead_cards[0] > self.lead_cards[1]:
            raise ValueError("lead_cards: first value must be <= second")
        return self


class SoundConfig(StrictModel):
    enabled: bool = True
    volume: float = Field(default=1.0, ge=0, le=1)
    spin: str | None = None
    tick: str | None = None
    result: str | None = None


class LoggingConfig(StrictModel):
    level: Literal["debug", "info", "warning", "error"] = "info"
    file: str | None = None


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


class RerollAction(StrictModel):
    type: Literal["reroll"] = "reroll"


class VipAddAction(StrictModel):
    type: Literal["vip_add"] = "vip_add"


class VipRemoveAction(StrictModel):
    type: Literal["vip_remove"] = "vip_remove"


class SoundAction(StrictModel):
    type: Literal["sound"] = "sound"
    sound: str
    volume: float = Field(default=1.0, ge=0, le=1)


SimpleAction = Annotated[
    Union[TimeoutAction, BanAction, MessageAction, NothingAction,
          RerollAction, VipAddAction, VipRemoveAction, SoundAction],
    Field(discriminator="type"),
]


class PollAction(StrictModel):
    type: Literal["poll"] = "poll"
    title: str
    choices: list[str] = Field(min_length=2, max_length=5)
    duration: int = Field(default=60, ge=15, le=300)
    on_win: dict[str, SimpleAction] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _on_win_matches_choices(self):
        unknown = sorted(set(self.on_win) - set(self.choices))
        if unknown:
            raise ValueError(f"on_win keys not in choices: {unknown}")
        return self


Action = Annotated[
    Union[TimeoutAction, BanAction, MessageAction, NothingAction,
          RerollAction, PollAction, VipAddAction, VipRemoveAction,
          SoundAction],
    Field(discriminator="type"),
]


class Outcome(StrictModel):
    image: str
    weight: float = Field(gt=0)
    sound: str | None = None
    sound_volume: float = Field(default=1.0, ge=0, le=1)
    action: Action


class Config(StrictModel):
    twitch: TwitchConfig | None = None
    window: WindowConfig
    roulette: RouletteConfig = Field(default_factory=RouletteConfig)
    sounds: SoundConfig = Field(default_factory=SoundConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    outcomes: dict[str, Outcome]
