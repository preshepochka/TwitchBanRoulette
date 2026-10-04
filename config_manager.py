import json
from pathlib import Path

class ConfigManager:
    """Config manager"""
    def __init__(self, config_path: str):
        """
        Args:
            config_path: path to config.json file
        """
        self.config_path = Path(config_path)
        self._config: dict = {}

    def load(self) -> dict:
        """Load config from file"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = json.load(f)
        print(f"Loading config from {self.config_path}")
        print(f"Config: {self._config}")
        return self._config
    
    def _ensure_loaded(self) -> None:
        if not self._config:
            self.load()

    def validate(self) -> bool:
        """
        Checks the correctness of the config
    
        Returns:
            True if config correct, else False
        """
        self._ensure_loaded()
        required_keys = {"img", "chance", "action"}
        chances_sum = 0
        img_exists_error = False
        required_keys_error = False
        print("Config validation")
        for name, o in self._config.get("outcomes", {}).items():
            chance = o.get("chance", 0)
            
            if not isinstance(chance, (int, float)):
                print(f"{name}: chance must be a number, got {chance!r}")
                required_keys_error = True
                continue
            chances_sum += chance
            
            missing = required_keys - o.keys()
            if missing:
                required_keys_error = True
                print(f"{name}: missing keys {missing}")
                continue

            img_path = Path(o.get("img"))
            if not img_path.exists():
                img_exists_error = True
                print(f"{name}: image {img_path} does not exists")
            
        twitch = self._config.get("twitch", {})
        for key in ("channel", "token", "reward_id"):
            if not twitch.get(key):
                required_keys_error = True
                print(f"twitch: missing or empty '{key}'")

        if not img_exists_error and not required_keys_error and chances_sum == 100:
            print("The config is valid")
            return True
        else:
            print("The config is invalid")
            return False
            


    
    def get_outcomes(self) -> list[dict]:
        """Returns list of outcomes from config"""
        self._ensure_loaded()
        return list(self._config.get("outcomes", {}).values())

    def get_window_settings(self) -> dict:
        """Returns window settings"""
        self._ensure_loaded()
        return self._config.get("window", {})
