from roulette import Roulette

from config_manager import ConfigManager
from renderer import Renderer, RenderEvent


def main() -> None:
    manager = ConfigManager("config.json")
    if not manager.validate():
        raise SystemExit("Invalid config")
    cfg = manager.load()

    base = manager.config_path.parent
    outcomes = list(cfg.outcomes.items())            # [(name, Outcome), ...]
    card_paths = [base / o.img for _, o in outcomes]
    overlay_path = (base / cfg.window.overlay) if cfg.window.overlay else None

    renderer = Renderer(cfg.window, card_paths, overlay_path)
    roulette = Roulette(cfg.outcomes, cfg.window)
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
