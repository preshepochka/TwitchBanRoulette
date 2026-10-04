import json
from pathlib import Path
from pydantic import ValidationError
from config_schema import Config, Outcome, TwitchConfig, WindowConfig

class ConfigManager:
    """Config manager"""
    def __init__(self, config_path: str):
        """
        Args:
            config_path: path to config.json file
        """
        self.config_path = Path(config_path)
        self._config: Config | None = None
    
    def validate(self) -> bool:
        try:
            cfg = self._load_raw()
        except (FileNotFoundError, json.JSONDecodeError) as e:
            prinf(f"Cannot read config: {e}")
            return False
        except ValidationError as e:
            print("Config is invalid:")
            print(e)
            return False

        ok = True
        base = self.config_path.parent
        for name, o in cfg.outcomes.items():
            if not (base / o.img).exists():
                print(f"{name}: image not found: {o.img}")
                ok = False
        if cfg.window.winner_pointer and not (base / cfg.window.winner_pointer).exists():
            print(f"window.winner_pointer: file not found: {cfg.window.winner_pointer}")
            ok = False
        return ok
    
    def load(self) -> Config:
        if self._config in None:
            self._config = self._load_raw()
        return self.config
    
    def _load_raw(self) -> Config:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return Config.model_validate(json.load(f))
    
    def get_twitch(self) -> TwitchConfig:
        return self.load().twitch

    def get_window(self) -> WindowConfig:
        return self.load().window

    def get_outcomes(self) -> dict[str, Outcome]:
        return self.load().outcomes
