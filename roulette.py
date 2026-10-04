from typing import Any

class Roulette:
    """Roulette logic"""

    def __init__(self):
        """Roulette initialization"""
        self._rewards : list[dict] = []

    def set_rewards(self, rewards: list[dict]) -> None:
        """
        Setting list of rewards

        Args:
            rewards: list of rewards from config
        """
        self._rewards = rewards

    def generate_sequence(self, lenght: int = 30) -> list[dict]:
        """
        Generates sequence of cards for displaying

        Args:
            lenght: count of cards in sequence

        Returns:
            list of cards in the display sequence
        """
        #TODO: result is determined here
        # Other position generated randomly
        print(f"Generating sequence for {lenght} cards")
        return []

    def spin(self) -> dict:
        """
        Rolling Roulette and return winner
        
        Returns:
            dict with data about the winner
        """
        #TODO: choosing the winner
        print("Rolling the roullette...")
        return {}
