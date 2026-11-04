import random
from typing import Annotated, Literal, Union

from pydantic import (BaseModel, ConfigDict, Field, field_validator,
                      model_validator)

# A config value that may be a single string or a list of variants
# (one is picked at random when used).
Variants = Union[str, list[str]]


def pick(variant: Variants | None) -> str | None:
    """Resolve a str-or-list config value to one string (random choice)."""
    if variant is None:
        return None
    if isinstance(variant, str):
        return variant
    if not variant:
        raise ValueError("variant list must not be empty")
    return random.choice(variant)


def _variants_validator(v):
    if isinstance(v, list) and not v:
        raise ValueError("list must contain at least one item")
    if isinstance(v, list) and not all(isinstance(x, str) and x.strip() for x in v):
        raise ValueError("every variant must be a non-empty string")
    return v


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
    spin: Variants | None = None
    tick: Variants | None = None
    result: Variants | None = None

    _check = field_validator("spin", "tick", "result")(_variants_validator)


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
    text: Variants

    _check = field_validator("text")(_variants_validator)


class NothingAction(StrictModel):
    type: Literal["nothing"] = "nothing"


class RerollAction(StrictModel):
    type: Literal["reroll"] = "reroll"


class VipAddAction(StrictModel):
    type: Literal["vip_add"] = "vip_add"
    # Seconds; omit for a permanent VIP.
    duration: int | None = Field(default=None, gt=0)


class VipRemoveAction(StrictModel):
    type: Literal["vip_remove"] = "vip_remove"


class AnnounceAction(StrictModel):
    type: Literal["announce"] = "announce"
    text: Variants
    color: Literal["blue", "green", "orange", "purple", "primary"] = "primary"

    _check = field_validator("text")(_variants_validator)


class SoundAction(StrictModel):
    type: Literal["sound"] = "sound"
    sound: Variants
    volume: float = Field(default=1.0, ge=0, le=1)

    _check = field_validator("sound")(_variants_validator)


SimpleAction = Annotated[
    Union[TimeoutAction, BanAction, MessageAction, NothingAction,
          RerollAction, VipAddAction, VipRemoveAction, AnnounceAction,
          SoundAction],
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
          AnnounceAction, SoundAction],
    Field(discriminator="type"),
]


class Outcome(StrictModel):
    image: str
    weight: float = Field(gt=0)
    sound: Variants | None = None
    sound_volume: float = Field(default=1.0, ge=0, le=1)
    action: Action

    _check = field_validator("sound")(_variants_validator)


class Config(StrictModel):
    twitch: TwitchConfig | None = None
    window: WindowConfig
    roulette: RouletteConfig = Field(default_factory=RouletteConfig)
    sounds: SoundConfig = Field(default_factory=SoundConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    outcomes: dict[str, Outcome]
