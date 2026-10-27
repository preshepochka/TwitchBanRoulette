from audio import Audio
from config_manager import ConfigManager
from renderer import Renderer, RenderEvent
from roulette import Roulette


def main() -> None:
    manager = ConfigManager("config.toml")
    if not manager.validate():
        raise SystemExit("Invalid config")
    cfg = manager.load()

    audio = Audio(manager.config_path.parent, cfg.sounds)
    renderer = Renderer(cfg.window, manager.card_paths(),
                        manager.overlay_path(), manager.background_path(),
                        audio)
    roulette = Roulette(cfg.outcomes, cfg.window, cfg.roulette)
    print("Window started. Space — roll.")

    last_winner = None
    running = True
    while running:
        running = renderer.poll_events()
        if renderer.pop_debug_spin():
            plan = roulette.generate_spin()
            last_winner = plan.winner_name
            renderer.start_spin(plan.sequence, plan.winner_index)

        event = renderer.draw()
        if event is RenderEvent.SPIN_FINISHED:
            print(f"Result: {last_winner}")
        elif event is RenderEvent.RESULT_HIDDEN:
            print("Returned to idle.")


if __name__ == "__main__":
    main()
