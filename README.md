# Crossy Road (Python + PyQt6)

<div align="center">
  
![Nagrywanie2026-03-30175835-ezgif com-optimize](https://github.com/user-attachments/assets/8df04f95-1e76-427d-ba3c-2f1cb6eef90b)
</div>

A simple **Crossy Road**-style game with a procedurally generated map. You control a chicken, try to go as far upward as possible, avoid cars, and cross the river using logs / lily pads.

## Key features
- **Procedural generation** of terrain lanes: `grass / road / river`.
- **World management (chunking)**: lanes are **generated in front of the player** and **removed behind the player** (to keep the number of scene objects bounded).
- **AI mode** (bot makes decisions every `ai_timer_ms`).
- **Replay**: record inputs and replay a run using the same seed.
- **Save/Load** to/from `savegame.json`.
- A tiny **logger** (timestamp + message) printed to the console.

---

## Requirements
- Python 3.x
- Library: **PyQt6**

---

## Installation
Using a virtual environment is recommended.

### Windows (PowerShell)
```powershell
python -m pip install PyQt6
```

---

## Running
The main version of the game is in `main.py`.

```powershell
python .\main.py
```

## Controls
Movement:
- **Arrow keys** or **WASD** — move (up/down/left/right)

Functions:
- **H** — toggle debug (shows `debug_rect` if an object has it)
- **P** — toggle **AI**
- **R** — **replay** the last run (if an input log exists)
- **K** — **save** the game to `savegame.json`
- **L** — **load** the game from `savegame.json`
- **F5** — hot-reload `config.json` + reset

---

## Modes

### AI
- Toggle with **P**.
- The AI makes decisions periodically (timer). The interval is configured in `config.json` as `ai_timer_ms`.

### Replay
- The game records player actions as **(frame, action)** pairs.
- After pressing **R**, the game resets, sets the same `run_seed`, and replays inputs on the same frames.

---

## Save / Load (`savegame.json`)
- **K** saves the current state to `savegame.json`.
- **L** loads the save and restores e.g. the player position, generated lanes, and objects (cars, logs, trees, lilies).

---

## Configuration (`config.json`)
The game has default values in code and loads `config.json` if present (with basic type validation).

Useful options:
- `forward_rows` — how many lanes to keep/generate **in front of the player**
- `backward_rows` — how many lanes to keep **behind the player** (everything else is removed)
- `initial_chunk_load_size` — number of lanes generated at the start
- `generate_missing_map_count` — how many lanes to generate at once when more map is needed
- `max_consecutive_rivers`, `max_consecutive_roads` — limits for streaks of the same terrain
- `ai_timer_ms` — AI decision interval
- car/log speeds and spawn attempt counts for trees/lilies
- `use_custom_map` + `custom_map_layout` — optionally use a fixed lane layout

Hot reload:
- **F5** reloads `config.json`, updates selected parameters at runtime, and resets the game.

---

## Project structure
- `main.py` — main game (window, game loop, world generation, AI, replay, save/load, controls)
- `libs/` — shared constants and imports
- `factory/` — entity factory (`EntityFactory`)
- `player/` — player (`Player`)
- `obstacles/` — obstacles and terrain (`Car`, `Log`, `Tree`, `Lilypad`, `TerrainLane`)
- `logger/` — logger (prints to console)
- `*.png` — assets
- `savegame.json` — game save

---

## Technical notes: world management
To prevent the scene from growing indefinitely:
- when there are not enough lanes “ahead”, the generator creates new rows,
- objects far “behind” the player are removed from the scene and from internal lists.

