from typing import Any

class Renderer:
    """Render with pygame"""

    def __init__(self):
        """Renderer initialization"""
        self._window = None
        self.width = 800
        self.height = 200

    def init(self, width: int = 800, height: int = 200) -> None:
        """
        Creates a pygame window

        Args:
            width: window width
            height: window height
        """
        # TODO: pygame initialization
        self._width = width
        self._height = height
        print(f"initialization window {width}x{height}")

    def draw_roulette(self, sequence: list[dict], position: float) -> None:
        """
        Draws a roulette in the current position

        Args:
            sequence: list of cards
            position: current position (pixels)
        """
        #TODO: Rendering
        pass
    def animate_spin(self, sequence: list[dict], duration: float = 3.0) -> dict:
        """
        Starts an animation

        Args:
            sequence: a sequence of cards
            duration: duration of animation in seconds

        Returns:
            winner
        """
        print(f"Animation starts for {duration} seconds")
        return {}

    def draw_winner(self, reward: dict) -> None:
        """
        Draws the result in center

        Args:
            reward: data of winner
        """
        #TODO: Realize 
        print(f"Winner {reward}")

    def update(self) -> bool:
        """
        Processes events

        Returns:
            True if window opened, False if closed
        """
        #TODO: Realize events processing
        return True

