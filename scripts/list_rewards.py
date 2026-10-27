from bot import Bot
from config_manager import ConfigManager


def main() -> None:
    t = ConfigManager("config.toml").load().twitch
    bot = Bot(t.client_id, t.token, t.channel, t.reward_id)
    for r in bot.fetch_rewards():
        print(f'{r["id"]}  {r["title"]}')


if __name__ == "__main__":
    main()
