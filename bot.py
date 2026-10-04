from typing import Callable, Any

class Bot:
    """Twitch Bot"""

    def __init__(self):
        """Bot initialization"""

        self._connected = False
        self._callback: Callable | None = None

    def connect(self) -> None:
        """Connect to Twitch"""
        #TODO: connection to twitch with twitchio
        print("Connection to Twitch...")
        self._connected = True

    def listen_for_rewards(self, callback: Callable) -> None:
        """
        Registring callback

        Args:
            callback: function(reward_id: str, user: str)
        """
        self._callback = callback
        print("Listening to rewards")
    def execute_action(self, action: str, params: dict, user: str) -> None:
        """
        Execute action

        Args:
            action: action type
            params: action parametrs
            user: username
        """
        #TODO: Twitch API integration
        print(f"Executing {action} with parametrs {params} for user {user}")

