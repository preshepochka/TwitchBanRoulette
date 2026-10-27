# AGENTS.md

## What this is

Local desktop app for streamers: viewers redeem a Twitch channel-points reward, a pygame window (captured in OBS via chroma key) spins a strip of outcome cards, and the bot applies the winning outcome (timeout/ban/message) to that viewer. No web server, no packaging.

## Layout & run model

- Flat top-level Python modules (no package, no pyproject). Deps: `pydantic`, `pygame`, `requests` (`requirements.txt`); Python 3.11+. Use a venv. Python 3.14 quirk: official `pygame` has no cp314 wheels — a source build can end up without PNG support (`File is not a Windows BMP file` on image load); use `pygame-ce` there.
- Run/verify everything from the repo root. Asset paths from config resolve relative to the config file's directory (`ConfigManager`).
- `config.toml` is gitignored — copy `config.example.toml` before anything can run.
- Module roles: `bot.py` = pure Twitch transport (Helix requests, poll thread, queue) and raises `TwitchError`; `outcomes.py` = action models' runtime (`apply(bot, action, user_id, user_name)`, `{user}` substitution); `audio.py` = `pygame.mixer` wrapper (`Audio`), plays by path with a cache and degrades to no-ops without an audio device; `config_schema.py` = all pydantic models incl. discriminated unions `Action` and `Background`; `roulette.py` = winner selection; `renderer.py` = pygame window + spin/tick sounds; `app.py` = result sounds (priority: action sound → outcome `sound` → `sounds.result`) and `reroll` control flow (`MAX_REROLL_CHAIN`); `main.py` = the only wiring point.

## Verification

- **No test framework, lint, typecheck, or CI.** `scripts/` contains standalone manual scripts, run individually from repo root with `PYTHONPATH=.`:
  - `PYTHONPATH=. python3 scripts/demo.py` — full pipeline with no config and no Twitch: config built in code, FakeBot auto-redemptions + Space for manual spins, placeholder sounds included. For fully headless runs (no display/audio device): `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`.
  - `PYTHONPATH=. python3 scripts/test_app.py` — full pipeline against `FakeBot` using the real `config.toml` (auto-redemptions, no Twitch traffic, opens a window).
  - `PYTHONPATH=. python3 scripts/test_renderer.py` — renderer only; Space triggers a spin.
  - `scripts/fake_bot.py` — bot stub; `scripts/list_rewards.py` — prints channel-points reward IDs (to fill `twitch.reward_id`, needs real credentials); `scripts/placeholders_generator.py` — regenerates placeholder assets.
- Quick static check with no setup: `python3 -m compileall -q .`
- `scripts/test_app.py` is the reference for how `App`/`Roulette`/`Renderer` connect; `main.py` shows the real wiring with `Bot`.

## Config gotchas

- Schema is strict (`extra="forbid"`): unknown keys fail validation.
- `[twitch]` is optional — omit it for local testing via `scripts/demo.py`; `main.py` refuses to run the real bot without it.
- `action` is a nested table discriminated by `type` (`timeout` needs `duration` > 0 in seconds, `message` needs `text` supporting `{user}`, `poll` needs `title` + 2–5 `choices` and `duration` 15–300, `ban`/`nothing`/`reroll`/`vip_add`/`vip_remove` need nothing) — pydantic rejects wrong shapes at load time.
- Weights are relative and don't need to sum to 100 (`weight: float > 0`, no sum validator).
- `window.background` is a discriminated union: `chroma` (default), `color`, `image` (stretched over the window); with `image`, OBS should capture the window directly, no chroma keying.
- `[sounds]` is optional; WAV/OGG only (MP3 flaky through SDL_mixer). Sound files are existence-checked by `ConfigManager.validate()` only while `sounds.enabled` is true. `sounds.spin` loops (Renderer owns its channel), `sounds.result` is the fallback for outcome reveal.
- `[logging]` is optional (`level`, `file`); `main.py` applies it after config load — early errors still go to console at default `info`. Log file paths resolve relative to the config file's directory.
- `chroma_key` RGB is the OBS key color: it must not appear in card art or the overlay; `window.overlay` is an alpha PNG sized to the window.
- Outcome card images, overlay and background image are checked for existence by `ConfigManager.validate()`.

## Twitch integration

- Pure Helix REST polling — no IRC or EventSub. A daemon thread polls UNFULFILLED redemptions every 2s (`bot.POLL_INTERVAL`), dedupes by redemption id, and pushes to a `Queue` that `App` drains between frames (a new spin only starts when the renderer is IDLE).
- `reroll` never reaches Twitch: App re-spins the same redemption (capped at `MAX_REROLL_CHAIN`), fulfillment happens only after the final outcome.
- `Bot.start()` resolves the broadcaster id eagerly and fails fast on a bad channel/token. Action/fulfill failures are logged, not raised — one bad request doesn't kill the stream loop.
- Auth: user OAuth token in `twitch.token` (the `oauth:` prefix is stripped automatically) plus app `client_id`. `twitch.reward_id` is a UUID not shown anywhere in the Twitch UI — get it via `scripts/list_rewards.py`. `poll` needs the `channel:manage:polls` scope, `vip_add`/`vip_remove` need `moderator:manage:vips` (README auth URL already includes both).

## Conventions

- Commit messages use conventional prefixes (`feat:`, `fix:`).
- README.md is the user-facing doc (setup, token, reward ID, OBS). Keep it in sync when changing the config schema or run steps.
