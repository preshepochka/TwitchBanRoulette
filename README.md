# TwitchBanRoulette

A program that adds a channel points roulette to your stream: viewers redeem a reward, a window with cards spins, a random outcome is selected, and the bot automatically performs a consequence — ban, timeout, chat message, and so on.

Runs locally on the streamer's computer, no public IP required. The window is captured in OBS via chroma key.

## How it works

1. The streamer creates a single channel points reward in the Twitch panel.
2. The program listens for this reward and launches the roulette when it's redeemed.
3. The roulette selects one of the configured outcomes with specified probabilities.
4. The bot performs an action (timeout/ban/message) on the user who triggered the roulette.

## Requirements

- Python 3.11 or newer (tested on 3.11–3.13; on 3.14 install `pygame-ce` instead of `pygame` — official pygame has no 3.14 builds yet)
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

https://id.twitch.tv/oauth2/authorize?response_type=token&client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost&scope=channel%3Aread%3Aredemptions%20moderator%3Amanage%3Abanned_users%20chat%3Aread%20chat%3Aedit%20channel%3Amanage%3Apolls%20moderator%3Amanage%3Avips

(The `polls` and `vips` scopes are only needed if you use the `poll` / `vip_add` / `vip_remove` actions.)

7. Open the URL, log in, click "Authorize". The browser will redirect to `localhost#access_token=...` — the page won't load, this is normal.
8. Copy the token from the address bar (the part between `access_token=` and `&`) into the config as `twitch.token` (with the `oauth:` prefix).

## Getting the Reward ID

Twitch doesn't display the reward ID in the control panel. Get it with a helper script:

1. Create a reward in Creator Dashboard → Viewer Rewards → Channel Points Rewards.
2. Fill in `channel`, `client_id` and `token` in `config.toml` (see below).
3. Run:
   ```bash
   python3 scripts/list_rewards.py
   ```
4. A line like `123e4567-...  My reward` will appear in the console.
5. Copy the ID into the config as `twitch.reward_id`.

## Configuration

Copy `config.example.toml` to `config.toml` and fill it out (the example file also contains commented-out fields with their defaults). Minimal version:

```toml
[twitch]
channel = "your_channel_name"
client_id = "your_client_id"
token = "oauth:your_token_here"
reward_id = "your_reward_id"

[window]
width = 800
height = 200
chroma_key = [0, 255, 0]
overlay = "assets/overlay.png"

[outcomes.Timeout]
image = "assets/cards/timeout.png"
weight = 40
action = { type = "timeout", duration = 60 }

[outcomes.Ban]
image = "assets/cards/ban.png"
weight = 5
action = { type = "ban" }

[outcomes.Nothing]
image = "assets/cards/message.png"
weight = 55
action = { type = "message", text = "{user}, wow, absolutely nothing" }
```

### `twitch`

The whole section is optional — omit it to test locally with `scripts/demo.py` (no Twitch traffic).

- `channel` — the channel name the bot listens to.
- `client_id` — client ID of your registered application (from the token section).
- `token` — OAuth token from the previous section.
- `reward_id` — UUID of the trigger reward.

### `window`

- `width`, `height` — window dimensions in pixels.
- `chroma_key` — RGB background color. Used as the key color for OBS chroma key. Default is green `[0, 255, 0]`. This color should not appear in card art or overlay.
- `overlay` (optional) — path to a PNG sized `width × height`, drawn on top of everything (frame, pointer, logo). Transparency via alpha channel.
- `title` — window title, default `Twitch Ban Roulette`.
- `fps` — frame rate cap, default `60`.
- `spin_duration` — spin animation length in seconds, default `4.0`.
- `result_hold` — how long the winner card stays highlighted, seconds, default `3.0`.
- `highlight` — winner frame: `{ enabled = true, color = [255, 255, 255], thickness = 3, radius = 8 }` (rounded corners via `radius`; `enabled = false` turns it off).
- `background` — window background:
  - `{ type = "chroma" }` (default) — solid `chroma_key` fill for OBS chroma keying;
  - `{ type = "color", color = [20, 20, 30] }` — solid color, capture the window directly;
  - `{ type = "image", image = "assets/bg.png" }` — an image stretched over the window, capture directly.

### `roulette`

- `lead_cards = [20, 30]` — how many random cards scroll past before the winner lands (default `[20, 30]`).

### `sounds`

The whole section is optional; without it the app is silent. Formats: **WAV** or **OGG** (avoid MP3).

- `enabled` — default `true`; with `false` the app stays silent even with sounds configured.
- `volume` — master volume, `0.0..1.0`, default `1.0`.
- `spin` — played in a loop for the whole spin, stopped when the result is shown.
- `tick` — a click every time a card passes the pointer during the spin.
- `result` — played when the winner is revealed, unless the outcome has its own `sound`.

Per-outcome sound: add `sound = "assets/sounds/sting.ogg"` (and optional `sound_volume`) to any outcome — it replaces `sounds.result` for that card.

Priority when the winner is revealed: action sound (`type = "sound"`) → outcome `sound` → `sounds.result`.

### `outcomes`

Each section is one outcome: a card, its weight and the action:

- `image` — path to the card image.
- `weight` — relative drop weight. Weights don't have to sum to 100: `40/5/55` gives the same odds as `4/0.5/5.5`.
- `action` — inline table with a `type` and type-specific fields:
  - `{ type = "timeout", duration = 60 }` — timeout, `duration` in seconds (required).
  - `{ type = "ban" }` — permanent ban.
  - `{ type = "message", text = "..." }` — chat message from the bot, `text` (required). `{user}` in the text is replaced with the viewer's name.
  - `{ type = "nothing" }` — just show the card, do nothing.
  - `{ type = "reroll" }` — spin again for the same viewer (chain is capped at 8, then the redemption is fulfilled with no effect).
  - `{ type = "poll", title = "...", choices = ["A", "B"], duration = 60 }` — create a Twitch poll (2–5 choices, `duration` 15–300 s; needs the `channel:manage:polls` scope).
  - `{ type = "vip_add" }` / `{ type = "vip_remove" }` — grant/revoke VIP for the viewer (needs the `moderator:manage:vips` scope).
  - `{ type = "sound", sound = "...", volume = 1.0 }` — play a sound and do nothing else; the card itself is the show.

All paths are relative to the config file's directory.

## OBS Setup

1. Add a **Window Capture** source, select the `Twitch Ban Roulette` window.
2. Capture Method — `Windows 10 (1903 and up)`.
3. Right-click the source → Filters → **Chroma Key**.
4. Key Color Type — `Custom`, Key Color — same as `chroma_key` in config.
5. Adjust Similarity empirically (usually 400–600).

**Don't minimize the window** — move it behind other windows or to a second monitor. OBS will capture it anyway, and minimized windows on some systems stop rendering frames.

Sounds are played by the window itself — OBS window capture does **not** carry audio. Add your system/desktop audio as a separate OBS source if you want the sounds on stream.

## Running

Real bot (needs the `[twitch]` section):

```bash
# in activated venv
python main.py
```

Local demo without any Twitch setup — auto-redemptions every ~5 s plus Space for a manual spin:

```bash
PYTHONPATH=. python3 scripts/demo.py
```

## Troubleshooting

**`pygame.error: File is not a Windows BMP file`** on startup — your pygame build has no PNG support. This happens when pip has to compile pygame from source (e.g. on very new Python versions). Fix with either:

```bash
pip uninstall pygame && pip install pygame-ce   # same API, ships new-Python builds
```

or use Python 3.12/3.13 (official pygame wheels exist there), or install the dev packages (`libsdl2-image-dev`, `libpng-dev`) and reinstall pygame. To confirm the diagnosis:

```bash
python -c "import pygame.image; print(pygame.image.get_extended(), pygame.image.get_sdl_image_version())"
```

`False` / `None` in the output means no image format support.

## Project Structure

main.py                # entry point
app.py                 # coordinator, event queue
config_manager.py      # config loading and validation
config_schema.py       # config schema (pydantic)
outcomes.py            # outcome actions (timeout/ban/message/nothing)
bot.py                 # Twitch API client, redemption polling
roulette.py            # winner selection, strip generation
renderer.py            # Pygame window, animation
assets/                # card images and overlay
scripts/               # manual helper scripts (not a test suite)

## License

GPL-3.0.