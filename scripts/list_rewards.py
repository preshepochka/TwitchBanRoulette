import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import Bot
from config_manager import ConfigManager


def main() -> None:
    cfg = ConfigManager("config.toml").load()
    if cfg.twitch is None:
        raise SystemExit("no [twitch] section in config.toml — "
                         "fill it in first (see README)")
    t = cfg.twitch
    bot = Bot(t.client_id, t.token, t.channel, t.reward_id)
    for r in bot.fetch_rewards():
        print(f'{r["id"]}  {r["title"]}')


if __name__ == "__main__":
    main()
