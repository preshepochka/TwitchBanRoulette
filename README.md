# TwitchBanRoulette

A channel-points roulette for your Twitch stream. Viewers redeem one reward, a window with spinning cards appears on stream, and the bot applies a random outcome to that viewer — a timeout, a ban, a silly message, a VIP, or whatever else you configure.

Everything runs locally on the streamer's computer: no web server, no public IP, no hosting. The roulette window is captured in OBS like any other window.

## How it works

1. You create a single channel-points reward in the Twitch dashboard (for example, "Play the roulette — 500 points").
2. The program watches for redemptions of that reward.
3. When a viewer redeems it, the window spins a strip of outcome cards and one wins — based on the weights you set.
4. The bot applies that outcome's action to the viewer, then marks the redemption as fulfilled.

Outcomes are fully yours to define: you decide how many there are, what each card looks like, how likely it is, what it does and whether it makes a sound.

## Requirements

- Python **3.11** or newer (tested on 3.11–3.13; on 3.14 install `pygame-ce` instead of `pygame` — official pygame has no 3.14 builds yet, see [Troubleshooting](#troubleshooting))
- `pip`
- OBS (or any other window-capture software) if you want the roulette on stream

On Windows, use the `py` launcher or `python` — the `python3` command often doesn't exist there, and a bare `python` may be a Microsoft Store stub that silently does nothing (Settings → Apps → Advanced app settings → App execution aliases → turn off *python.exe* / *python3.exe*). Run the program from an open terminal, not by double-clicking — errors stay visible, and a fatal error now waits for Enter before closing anyway.

## Quick start

```bash
git clone https://github.com/preshepochka/TwitchBanRoulette.git
cd TwitchBanRoulette

# create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Then try it with **zero configuration and zero Twitch credentials**:

```bash
python scripts/demo.py        # Windows: py scripts/demo.py
```

A window opens and spins automatically every ~5 seconds. Press **Space** for a manual spin. The demo uses placeholder cards, sounds and a fake Twitch bot — nothing leaves your computer.

Once you've seen it work, continue with the [Twitch setup](#twitch-setup) below.

## Twitch setup

Two things are needed from Twitch: an OAuth token and the reward ID. Register your application first:

1. Open the [Twitch Developer Console](https://dev.twitch.tv/console) → Applications → **Register Your Application**.
2. Name — anything (e.g. `BanRoulette`).
3. OAuth Redirect URLs — `http://localhost`.
4. Category — `Chat Bot`, Client Type — **Public**.
5. Save the **Client ID** — you'll need it for `twitch.client_id`.

### Getting a token

6. Build the authorization URL, replacing `YOUR_CLIENT_ID`:

   ```
   https://id.twitch.tv/oauth2/authorize?response_type=token&client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost&scope=channel%3Aread%3Aredemptions%20moderator%3Amanage%3Abanned_users%20chat%3Aread%20chat%3Aedit%20channel%3Amanage%3Apolls%20moderator%3Amanage%3Avips
   ```

   The `polls` and `vips` scopes are only needed if you plan to use the `poll` / `vip_add` / `vip_remove` actions — but including them up front saves you re-authorizing later.
7. Open the URL, log in as the **broadcaster**, click *Authorize*. The browser will redirect to `localhost#access_token=...` and the page won't load — that's normal.
8. Copy the token from the address bar (the part between `access_token=` and `&`) into the config as `twitch.token`. The `oauth:` prefix is optional — it's stripped automatically.

### Getting the reward ID

Twitch never shows the reward's UUID anywhere in the UI. Get it with a helper script:

1. Create the reward in Creator Dashboard → Viewer Rewards → Channel Points Rewards.
2. Fill in `channel`, `client_id` and `token` in `config.toml` (see [Configuration](#configuration)).
3. Run:

   ```bash
   python scripts/list_rewards.py    # Windows: py scripts/list_rewards.py
   ```

4. You'll see lines like `123e4567-...  My reward`.
5. Copy the UUID of your reward into `twitch.reward_id`.

## Configuration

Copy `config.example.toml` to `config.toml` and edit it. The example file contains every field with comments; the minimal version looks like this:

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

The config is validated on startup with plain-language errors that point to the exact key — if you mistype something, the program tells you where. Unknown keys are rejected, so typos don't pass silently.

All file paths are relative to the config file's directory.

### `twitch`

The whole section is optional — omit it entirely to test locally with `scripts/demo.py`.

| Key | Meaning |
|---|---|
| `channel` | Your channel name, as in `twitch.tv/<channel>` |
| `client_id` | Client ID of the registered application |
| `token` | OAuth user token from the setup above |
| `reward_id` | UUID of the reward that triggers the roulette |

### `window`

| Key | Default | Meaning |
|---|---|---|
| `width`, `height` | — | Window size in pixels |
| `chroma_key` | — | RGB fill color used as the OBS chroma-key color; must not appear in card art or overlay |
| `overlay` | none | Optional alpha PNG on top of everything (frame, pointer, logo), sized exactly `width × height` |
| `background` | chroma | See below |
| `highlight` | white, 3 px, radius 8 | Winner frame: `{ enabled, color, thickness, radius }`; `thickness = 0` draws it filled; `enabled = false` turns it off |
| `title` | `Twitch Ban Roulette` | Window title (this is the name you pick in OBS) |
| `fps` | 60 | Frame rate cap |
| `spin_duration` | 4.0 | Spin animation length, seconds |
| `result_hold` | 3.0 | How long the winner stays highlighted, seconds |
| `card_size` | `[200, 150]` | On-screen card size; art is scaled to fit |
| `gap` | 10 | Space between cards, pixels |

Background variants:

```toml
background = { type = "chroma" }                      # solid chroma_key fill — for OBS chroma keying (default)
background = { type = "color", color = [20, 20, 30] } # solid color — capture the window directly
background = { type = "image", image = "assets/bg.png" }  # stretched over the window — capture directly
```

With `color` or `image` backgrounds you don't need chroma keying at all: just capture the window in OBS as-is.

### `roulette`

| Key | Default | Meaning |
|---|---|---|
| `lead_cards` | `[20, 30]` | How many random cards scroll past before the winner lands — raise it for a longer-feeling spin |

### `sounds`

The whole section is optional; without it the app is silent. Formats: **WAV** or **OGG** — avoid MP3 (support is flaky in SDL_mixer).

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `true` | `false` silences everything, even configured sounds |
| `volume` | 1.0 | Master volume, `0.0..1.0` |
| `spin` | none | Played in a loop for the whole spin, stopped when the result shows |
| `tick` | none | A click every time a card passes the pointer |
| `result` | none | Played when the winner is revealed — unless the outcome has its own sound |

Any outcome can carry its own sound:

```toml
[outcomes.Timeout]
image = "assets/cards/timeout.png"
weight = 40
sound = "assets/sounds/sting.ogg"   # replaces sounds.result for this card
sound_volume = 1.0
action = { type = "timeout", duration = 60 }
```

Priority when the winner is revealed: **action sound** (`type = "sound"`) → **outcome `sound`** → **`sounds.result`**.

### `logging`

The whole section is optional — by default the program logs to the console at `info` level.

| Key | Default | Meaning |
|---|---|---|
| `level` | `info` | Verbosity: `debug`, `info`, `warning` or `error` |
| `file` | none | Also append the log to this file (path relative to the config file) |

The log covers the useful trail: redemptions received, spin results with the chosen outcome, action and fulfill failures, poll/API errors. The file is appended, not replaced — clean it up or rename it occasionally if you run the bot for a long time.

```toml
[logging]
level = "info"
file = "roulette.log"
```

### `outcomes`

Each `[outcomes.Name]` section is one outcome: a card, its weight, an optional sound and an action.

| Key | Meaning |
|---|---|
| `image` | Path to the card image (PNG recommended) |
| `weight` | Relative drop weight — doesn't need to sum to 100: `40/5/55` gives the same odds as `4/0.5/5.5` |
| `sound` | Optional sound for this card, replaces `sounds.result` |
| `sound_volume` | That sound's volume, `0.0..1.0` (default 1.0) |
| `action` | What happens to the viewer — see below |

Actions (inline table, validated by `type`):

| Action | Fields | Effect |
|---|---|---|
| `{ type = "timeout" }` | `duration` (seconds, required) | Times the viewer out |
| `{ type = "ban" }` | — | Permanent ban |
| `{ type = "message" }` | `text` (required) | Chat message from the bot; `{user}` is replaced with the viewer's name |
| `{ type = "nothing" }` | — | Just show the card |
| `{ type = "reroll" }` | — | Spin again for the same viewer; chains are capped at 8, then the redemption is closed with no effect |
| `{ type = "poll" }` | `title`, `choices` (2–5), `duration` (15–300 s), `on_win` (optional) | Starts a Twitch poll (needs the `channel:manage:polls` scope) |
| `{ type = "vip_add" }` | — | Grants the viewer VIP (needs `moderator:manage:vips`) |
| `{ type = "vip_remove" }` | — | Revokes the viewer's VIP (needs `moderator:manage:vips`) |
| `{ type = "sound" }` | `sound`, `volume` (optional) | Plays a sound and does nothing else — the card itself is the show |

Example of a sound-only outcome:

```toml
[outcomes.Airhorn]
image = "assets/cards/airhorn.png"
weight = 5
action = { type = "sound", sound = "assets/sounds/airhorn.wav", volume = 1.0 }
```

### Poll outcomes: let chat decide

A poll can carry consequences — chat votes, and the winning choice's action applies to the viewer who triggered the roulette:

```toml
[outcomes.FatePoll]
image = "assets/cards/fate.png"
weight = 10

[outcomes.FatePoll.action]
type = "poll"
title = "The fate of {user}?"
choices = ["Timeout", "VIP", "Mercy"]
duration = 60

[outcomes.FatePoll.action.on_win]
Timeout = { type = "timeout", duration = 120 }
VIP = { type = "vip_add" }
Mercy = { type = "nothing" }
```

How it works and what to keep in mind:

- After the poll ends, the bot reads the result and applies the action mapped to the winning choice (keys of `on_win` must match choice titles exactly; for non-Latin titles quote them in TOML: `"Баня" = { type = "timeout" }`).
- Actions apply to the **viewer who triggered the roulette**, and `{user}` works in their texts as usual.
- A choice without a mapping simply does nothing.
- Twitch allows **one active poll at a time** — if the previous poll is still running, creating a new one fails; the error is logged and the spin just shows the card.
- If the poll is cancelled or fetch fails, the error is logged and nothing happens; the bot keeps retrying for a short while, then gives up.
- `reroll` is not supported as a poll result.

## Assets: what works best

Everything lives under `assets/`. Placeholder art and sounds are included, so the app works out of the box — replace them when you're ready. You can regenerate the placeholders any time with `python scripts/placeholders_generator.py`.

**Cards** (`assets/cards/*.png`)

- PNG with transparency (RGBA): transparent corners look much better than white boxes.
- Cards are scaled to `card_size` (200×150 by default — a 4:3 ratio). Make the art in the **same aspect ratio**, ideally **2× larger** (400×300 or 600×450) so the downscale stays crisp.
- Do **not** use the `chroma_key` color anywhere in card art.
- The winner is framed by the `highlight` rectangle — keep a few pixels of margin in the art so the frame doesn't clip anything important.

**Overlay** (`window.overlay`)

- An alpha PNG **exactly** `width × height` (800×200 with defaults).
- Everything transparent in it shows the roulette; everything opaque covers it. Typical use: a frame, a pointer triangle at the top, a channel logo in a corner.
- Again: no `chroma_key` color in it.

**Background image** (`background = { type = "image", ... }`)

- It's stretched to the window, so make it the **exact window size** (or the same aspect ratio) to avoid distortion.

**Sounds** (`assets/sounds/*`)

- **WAV** or **OGG**.
- `spin` should loop seamlessly: either a track long enough to cover `spin_duration` (~4 s) or a clean loopable noise/whoosh.
- `tick` works best as a very short click (30–80 ms).
- `result` and outcome sounds: a short sting, ideally under `result_hold` (~3 s).

**Window size**

- The default **800×200** works well as a banner strip under a webcam or gameplay — in OBS you position and scale the source freely.
- Going bigger? Scale `window`, `card_size` and the overlay together; keep `height` at least `card_size[1]` plus a small margin. For a chunky fullscreen-style roulette, something like `width = 1200`, `height = 300`, `card_size = [300, 225]` works nicely.

## OBS setup

With the default chroma background:

1. Add a **Window Capture** source and select the `Twitch Ban Roulette` window (the `title` from config).
2. On Windows, Capture Method — `Windows 10 (1903 and up)`.
3. Right-click the source → Filters → **Chroma Key**.
4. Key Color Type — `Custom`, Key Color — same as `chroma_key` in the config (default green `[0, 255, 0]`).
5. Adjust **Similarity** by eye — usually 400–600.

With a `color` or `image` background, skip the chroma key entirely and just capture the window.

**Don't minimize the window** — move it behind other windows or onto a second monitor. OBS keeps capturing it there, while minimized windows on some systems stop rendering frames.

Sounds are played by the window itself, and window capture does **not** carry audio. If you want the sounds on stream, add your system/desktop audio as a separate OBS audio source.

## Running

The real bot (needs the `[twitch]` section):

```bash
# in the activated venv
python main.py
```

The no-Twitch demo — auto-redemptions every ~5 s, **Space** for a manual spin:

```bash
python scripts/demo.py        # Windows: py scripts/demo.py
```

Console output shows every redemption and action, so you can follow the bot's decisions live. If the config or assets have problems, the program tells you exactly what it didn't like and exits.

## Troubleshooting

**Nothing happens at all — no window, no errors.** Run from an open terminal (`cmd`/`PowerShell`), not by double-clicking, and check in order:

1. `python --version` (or `py --version` on Windows) prints 3.11+ — if nothing prints or the Microsoft Store opens, you're hitting the Store alias stub; disable it (Settings → Apps → Advanced app settings → **App execution aliases**) and use `py`.
2. The very first log line `starting TwitchBanRoulette (python ..., pygame ...)` appears — if it does, Python and imports are fine, the problem is in config/assets; read the lines after it. If it doesn't, the interpreter or dependencies are broken: `pip install -r requirements.txt` in the same interpreter you run with.
3. `config.toml` exists in the project root (copy from `config.example.toml`) — without it the program logs where it looked and exits.
4. On a fatal error the console now waits for **Enter** before closing, so double-clicked launches stay readable.

**`pygame.error: File is not a Windows BMP file`** on startup — your pygame build has no PNG support. This happens when pip has to compile pygame from source (typically on very new Python versions). Fix it with one of:

```bash
pip uninstall pygame && pip install pygame-ce   # same API, ships builds for new Pythons
```

or use Python 3.12/3.13 (official pygame wheels exist there), or install the dev packages (`libsdl2-image-dev`, `libpng-dev`) and reinstall pygame. To confirm the diagnosis:

```bash
python -c "import pygame.image; print(pygame.image.get_extended(), pygame.image.get_sdl_image_version())"
```

`False` / `None` in the output means no image format support.

**No sounds.** Check, in order: the `[sounds]` section exists and points to real files; `enabled` is not `false`; the files are WAV/OGG, not MP3; and the machine actually has an audio device — without one the app logs `audio device unavailable, sounds are disabled` and keeps running silently.

**`config is invalid: ...`** — read the message: it names the exact key and what's wrong with it (`outcomes.Timeout.action.timeout.duration: Input should be greater than 0`). Compare with `config.example.toml`.

**The bot doesn't react to redemptions.** Check that `twitch.reward_id` is the UUID of the right reward, that the token's account owns the channel, and that the token hasn't expired — re-run the authorization URL if needed.

## Project structure

```
main.py             entry point, wires everything together
app.py              main loop: redemptions → spins → consequences
bot.py              Twitch API client and redemption polling
outcomes.py         applying outcome actions (timeout/ban/message/...)
roulette.py         winner selection, spin plan
renderer.py         pygame window, animation, spin/tick sounds
audio.py            sound playback (mixer wrapper)
config_manager.py   config.toml loading and validation
config_schema.py    config schema (pydantic)
assets/             cards, overlay, sounds
scripts/            helper scripts: demo, reward list, placeholders (not a test suite)
```

## License

GPL-3.0.
