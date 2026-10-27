import logging
import tomllib
from pathlib import Path

from pydantic import ValidationError

from config_schema import Config, ImageBackground, SoundAction

log = logging.getLogger(__name__)


class ConfigManager:
    """Loads config.toml and checks that referenced assets exist."""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self._config: Config | None = None

    def validate(self) -> bool:
        try:
            cfg = self._load_raw()
        except FileNotFoundError:
            log.error("config file not found: %s\n"
                      "Copy config.example.toml to config.toml and fill it in.",
                      self.config_path)
            return False
        except tomllib.TOMLDecodeError as e:
            log.error("config is not valid TOML: %s", e)
            return False
        except ValidationError as e:
            log.error("config is invalid:\n%s\n"
                      "See config.example.toml for the reference format.",
                      _format_errors(e))
            return False

        ok = True
        base = self.config_path.parent
        for name, o in cfg.outcomes.items():
            if not (base / o.image).exists():
                log.error("%s: image not found: %s", name, o.image)
                ok = False
        if cfg.window.overlay and not (base / cfg.window.overlay).exists():
            log.error("window.overlay: file not found: %s",
                      cfg.window.overlay)
            ok = False
        bg = cfg.window.background
        if isinstance(bg, ImageBackground) and not (base / bg.image).exists():
            log.error("window.background: image not found: %s", bg.image)
            ok = False
        if cfg.sounds.enabled:
            for key in ("spin", "tick", "result"):
                p = getattr(cfg.sounds, key)
                if p and not (base / p).exists():
                    log.error("sounds.%s: file not found: %s", key, p)
                    ok = False
            for name, o in cfg.outcomes.items():
                if o.sound and not (base / o.sound).exists():
                    log.error("%s: sound not found: %s", name, o.sound)
                    ok = False
                if (isinstance(o.action, SoundAction)
                        and not (base / o.action.sound).exists()):
                    log.error("%s: action sound not found: %s",
                              name, o.action.sound)
                    ok = False
        return ok

    def load(self) -> Config:
        if self._config is None:
            self._config = self._load_raw()
        return self._config

    def _load_raw(self) -> Config:
        with open(self.config_path, "rb") as f:
            return Config.model_validate(tomllib.load(f))

    def card_paths(self) -> list[Path]:
        base = self.config_path.parent
        return [base / o.image for o in self.load().outcomes.values()]

    def overlay_path(self) -> Path | None:
        overlay = self.load().window.overlay
        return (self.config_path.parent / overlay) if overlay else None

    def background_path(self) -> Path | None:
        bg = self.load().window.background
        return (self.config_path.parent / bg.image) if isinstance(bg, ImageBackground) else None


def _format_errors(e: ValidationError) -> str:
    return "\n".join(
        f"  {'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
        for err in e.errors()
    )
