from bot import bot
from config_manager import ConfigManager

t = ConfigManager("config.json").load().twitch
bot = Bot(t.client_id, t.token, t.channel, t.reward_id)
    for r in bot.fetch_rewards():
    print(f'{r["id]"} {r["title"]}')
