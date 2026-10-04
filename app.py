from typing import Any

class App:
    def __init__(self, config: Any, bot: Any, roulette: Any, renderer: Any):
        self.config = config
        self.bot = bot
        self.roulette = roulette
        self.renderer = renderer

        self.event_queue: list[dict] = []

    def run(self) -> None:
        """Main cycle"""
        print("Connection call...")
        self.bot.connect()

        print("Window initialization")
        self.renderer.init()

        print("Ready for work. Waiting for requests...")

        #TODO: main cycle here
        # while True:
    
    def on_reward_redeemed(self, reward_id: str, user: str) -> None:
        """Bot Callback when request received"""
        print(f"A request {reward_id} has been received from {user}")
        self.event_queue.append({
            "reward_id": reward_id,
            "user": user
        })
    def _process_queue(self) -> None:
        #TODO: processing events from the event_queue
        pass
