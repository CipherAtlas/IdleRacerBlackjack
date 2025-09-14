# Idle Racer + Blackjack

A slick single-file idle game. Race cars around multiple track types to earn gold, unlock upgrades, and dive into a fully playable Blackjack side-game. Features particle effects, animated starfield, prestige & achievements, and a clean, responsive UI.

> **TL;DR**  
> - **Click anywhere on the track area** (left side) for a satisfying speed boost  
> - Scroll the right panel to access all upgrades  
> - Blackjack unlocks at **1000 gold**  
> - Autosaves every 30s and grants **offline earnings**  

---

## ✨ Highlights

- **Enhanced Idle Mechanics**
  - Car variety (colors, sizes, speed variance)
  - Random **boost effects** + click-to-boost anywhere on the main scene
  - **Glowing trails** & juicy particle bursts
  - **Multiple track types**: Circle, Figure-8, Oval, Complex
  - **Gold multipliers** that stack from upgrades/prestige
  - **Gold per all-cars lap** readout (fixed, speed-independent metric)

- **Progression**
  - **Prestige** (1M+ gold) → permanent sponsor bonus
  - **Achievements** (11+ categories) → prestige points
  - Upgrades: **Auto-Clicker**, **Gold Multiplier**, **Offline Earnings**, **Track Ads**, **Speed**

- **Visual & UI**
  - Animated starfield background
  - Particles for lap completion, purchases, and boosts
  - Number formatting (K/M/B…)
  - Themed right-panel UI with **scrolling**
  - **Closeable** overlays (Achievements, Stats, BJ Stats)

- **Blackjack**
  - Player vs Dealer with standard rules
  - Visual cards, quick bet buttons (±10/±100/±1K)
  - Stats: games, wins, win rate
  - Toggleable/closeable stats panel

- **Quality of Life**
  - **Autosave** every 30 seconds (+ manual save)
  - **Offline earnings** (leveled, capped, generous)
  - **Resizable window** + **Options** menu for resolution & fullscreen
  - 60 FPS default; optional 120 FPS toggle

---
## 📦 Prerequisites

Before running this project, make sure you have:

- [Python 3.13+](https://www.python.org/downloads/)
- [uv](https://github.com/astral-sh/uv) installed

### Install uv

```bash
pip install uv
```

Or download a standalone binary from the [uv releases page](https://github.com/astral-sh/uv/releases).

---

## ▶️ Running the Script

1. Clone or download this repository.
2. Open a terminal in the project directory.
3. Run:

```bash
uv run main.py
```

✅ That’s it! `uv` will:

- Create an isolated virtual environment automatically
- Install all dependencies from `uv.lock`
- Run the script in that environment