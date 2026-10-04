from app import App
from config_manager import ConfigManager
from bot import Bot
from roulette import Roulette
from renderer import Renderer

def main():
    """Entry Point"""

    config = ConfigManager("config.json")
    bot = Bot()
    renderer = Renderer()
    roulette = Roulette()

    app = App(
        config=config,
        bot=bot,
        roulette=roulette,
        renderer=renderer
    )

    app.run()

if __name__ == "__main__":
    main()
