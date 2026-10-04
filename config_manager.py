import json
from pathlib import Path
from typing import Any

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
        #TODO: json reading
        print(f"Loading config from {self.config_path}")
        return self._config

    def validate(self) -> bool:
        """
        Checks the correctness of the config
    
        Returns:
            True if config correct, else False
        """
        #TODO: Validation
        # - summ of chances = 100%
        # - images exist
        # - all required fields are present
        print("Config validation")
        return True
    
    def get_rewards(self) -> list[dict]:
        """Returns list of rewards from config"""
        return []

    def get_window_settings(self) -> dict:
        """Returns windiw settings"""
        return {"width": 800, "height": 200}
