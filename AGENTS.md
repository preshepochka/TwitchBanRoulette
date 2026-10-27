# AGENTS.md

## What this is

Local desktop app for streamers: viewers redeem a Twitch channel-points reward, a pygame window (captured in OBS via chroma key) spins a strip of outcome cards, and the bot applies the winning outcome (timeout/ban/message) to that viewer. No web server, no packaging.

## Layout & run model

- Flat top-level Python modules (no package, no pyproject). Deps: `pydantic`, `pygame`, `requests` (`requirements.txt`); Python 3.11+ per README. Use a venv.
- Run/verify everything from the repo root. Asset paths from config resolve relative to the config file's directory (`ConfigManager`).
- `config.json` is gitignored — copy `config.example.json` before anything can run.

## Verification

- **No test framework, lint, typecheck, or CI.** `tests/` contains standalone manual scripts, run individually from repo root with `PYTHONPATH=.`:
  - `PYTHONPATH=. python3 tests/test_app.py` — full pipeline against `FakeBot` (auto-redemptions, no Twitch traffic, opens a window).
  - `PYTHONPATH=. python3 tests/test_renderer.py` — renderer only; Space triggers a spin.
  - `tests/fake_bot.py` — bot stub; `tests/list_rewards.py` — prints channel-points reward IDs (to fill `twitch.reward_id`); `tests/placeholders_generator.py` — regenerates placeholder assets.
- Quick static check with no setup: `python3 -m compileall -q .` (currently flags real syntax errors in `bot.py` and `tests/list_rewards.py`).
- `tests/test_app.py` is the only place showing the current, correct wiring of `App`/`Roulette`/`Renderer` constructors — use it as the reference for how components connect.

## State: mid-refactor, partially broken

- The app does not currently run end to end: `bot.py` has a SyntaxError (`os None`), `main.py` instantiates `Bot`/`Renderer`/`Roulette` without required args and passes a `ConfigManager` where `App` expects the pydantic `Config`, and `tests/list_rewards.py` has an IndentationError.
- Verify against current code, not README or `main.py`; fix broken files rather than imitating their patterns. Update this section when fixed.

## Config gotchas

- Schema is strict (`extra="forbid"`): unknown keys fail validation. `twitch.client_id` is **required** by `config_schema.py` but missing from `config.example.json` and the README sample.
- `chance` values must sum to exactly 100 (pydantic model validator).
- `action` values handled by `bot.execute_action`: `timeout` (needs `duration`, seconds), `ban`, `message` (needs `text`), and `nothing` (undocumented in README). Unknown values are only logged, never an error.

## Twitch integration

- Pure Helix REST polling — no IRC or EventSub. A daemon thread polls UNFULFILLED redemptions every 2s (`bot.POLL_INTERVAL`), dedupes by redemption id, and pushes to a `Queue` that `App` drains between frames (a new spin only starts when the renderer is IDLE).
- Auth: user OAuth token in `twitch.token` (the `oauth:` prefix is stripped automatically) plus app `client_id`. `twitch.reward_id` is a UUID not shown anywhere in the Twitch UI — get it via `tests/list_rewards.py`.
- `chroma_key` RGB is the OBS key color: it must not appear in card art or the overlay; `window.overlay` is an alpha PNG sized to the window.

## Conventions

- Commit messages use conventional prefixes (`feat:`, `fix:`).
- The empty file `tests/first move to main folder` is a note-to-self to move these scripts to the repo root — not code.
- README.md is the user-facing doc (setup, token, reward ID, OBS). Keep it in sync when changing the config schema or run steps.
