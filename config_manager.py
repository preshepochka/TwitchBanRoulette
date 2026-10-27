import logging
import tomllib
from pathlib import Path

from pydantic import ValidationError

from config_schema import Config

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
        return ok

    def load(self) -> Config:
        if self._config is None:
            self._config = self._load_raw()
        return self._config

    def _load_raw(self) -> Config:
        with open(self.config_path, "rb") as f:
            return Config.model_validate(tomllib.load(f))


def _format_errors(e: ValidationError) -> str:
    return "\n".join(
        f"  {'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
        for err in e.errors()
    )
