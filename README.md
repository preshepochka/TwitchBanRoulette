# TwitchBanRoulette

A program that adds a channel points roulette to your stream: viewers redeem a reward, a window with cards spins, a random outcome is selected, and the bot automatically performs a consequence — ban, timeout, chat message, and so on.

Runs locally on the streamer's computer, no public IP required. The window is captured in OBS via chroma key.

## How it works

1. The streamer creates a single channel points reward in the Twitch panel.
2. The program listens for this reward and launches the roulette when it's redeemed.
3. The roulette selects one of the configured outcomes with specified probabilities.
4. The bot performs an action (timeout/ban/message) on the user who triggered the roulette.

## Requirements

- Python 3.11 or newer (tested on 3.11–3.13)
- pip
- OBS (or similar window capture software)

## Installation
```bash
git clone https://github.com/preshepochka/TwitchBanRoulette.git
cd TwitchBanRoulette

# create virtual environment
python -m venv venv

# activate
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```
## Getting a Twitch Token

The program works via the Twitch API and requires an OAuth token.

1. Open [Twitch Developer Console](https://dev.twitch.tv/console) → Applications → Register Your Application.
2. Name — anything (e.g., `BanRoulette`).
3. OAuth Redirect URLs — `http://localhost`.
4. Category — `Chat Bot`, Client Type — Public.
5. Save the Client ID.
6. Build the authorization URL (replace `YOUR_CLIENT_ID`):

https://id.twitch.tv/oauth2/authorize?response_type=token&client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost&scope=channel%3Aread%3Aredemptions%20moderator%3Amanage%3Abanned_users%20chat%3Aread%20chat%3Aedit

7. Open the URL, log in, click "Authorize". The browser will redirect to `localhost#access_token=...` — the page won't load, this is normal.
8. Copy the token from the address bar (the part between `access_token=` and `&`) into the config as `twitch.token` (with the `oauth:` prefix).

## Getting the Reward ID

Twitch doesn't display the reward ID in the control panel. You can get it via the bot's debug mode:

1. Create a reward in Creator Dashboard → Viewer Rewards → Channel Points Rewards.
2. Run the program in debug mode (see "Running" section).
3. Redeem the reward once yourself from a test account.
4. A line like `ID: 123e4567-... | Title: ...` will appear in the console.
5. Copy the ID into the config as `twitch.reward_id`.

## Configuration

Copy `config.example.json` to `config.json` and fill it out:
```json
{
  "twitch": {
    "channel": "your_channel_name",
    "token": "oauth:your_token_here",
    "reward_id": "twitch_reward_id"
  },
  "window": {
    "width": 800,
    "height": 200,
    "chroma_key": [0, 255, 0],
    "overlay": "assets/overlay.png"
  },
  "outcomes": {
    "timeout_60": {
      "img": "assets/cards/timeout.png",
      "chance": 40,
      "action": "timeout",
      "duration": 60
    },
    "ban": {
      "img": "assets/cards/ban.png",
      "chance": 5,
      "action": "ban"
    },
    "funny_message": {
      "img": "assets/cards/message.png",
      "chance": 55,
      "action": "message",
      "text": "Wow, absolutely nothing"
    }
  }
}
```
### `twitch`

- `channel` — the channel name the bot listens to.
- `token` — OAuth token from the previous section.
- `reward_id` — UUID of the trigger reward.

### `window`

- `width`, `height` — window dimensions in pixels.
- `chroma_key` — RGB background color. Used as the key color for OBS chroma key. Default is green `[0, 255, 0]`. This color should not appear in card art or overlay.
- `overlay` (optional) — path to a PNG sized `width × height`, drawn on top of everything (frame, pointer, logo). Transparency via alpha channel.

### `outcomes`

Each key is an outcome name, value is its parameters:

- `img` (required) — path to the card image.
- `chance` (required) — drop probability in percent. Sum of all `chance` values must equal exactly 100.
- `action` (required) — one of `timeout`, `ban`, `message`.
- `duration` — required for `timeout`, duration in seconds.
- `text` — required for `message`, text to send in chat on behalf of the bot.

All paths are relative to the project root.

## OBS Setup

1. Add a **Window Capture** source, select the `Twitch Ban Roulette` window.
2. Capture Method — `Windows 10 (1903 and up)`.
3. Right-click the source → Filters → **Chroma Key**.
4. Key Color Type — `Custom`, Key Color — same as `chroma_key` in config.
5. Adjust Similarity empirically (usually 400–600).

**Don't minimize the window** — move it behind other windows or to a second monitor. OBS will capture it anyway, and minimized windows on some systems stop rendering frames.

## Running
```bash
# in activated venv
python main.py
```
## Project Structure

main.py                # entry point
app.py                 # coordinator, event queue
config_manager.py      # config loading and validation
config_schema.py       # config schema (pydantic)
bot.py                 # Twitch listener + action execution
roulette.py            # winner selection, strip generation
renderer.py            # Pygame window, animation
assets/                # card images and overlay

## License

GPL-3.0.