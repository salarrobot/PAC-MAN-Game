"""Pac-Man — a classic arcade clone built with Python and PyGame.

This package is organised into small, single-responsibility modules so the
codebase stays readable and easy to extend:

    settings.py  -- all tunable constants (sizes, colours, speeds, maze layout)
    maze.py      -- the Maze class: parses the layout, tracks pellets, draws walls
    entity.py    -- Entity base class: grid-based, smoothly-animated movement
    player.py    -- Player (Pac-Man): keyboard control, eating, animations
    ghost.py     -- Ghost enemies with four distinct AI personalities
    sounds.py    -- SoundManager: lightweight synthesised sound effects
    game.py      -- Game: the main loop, state machine, HUD and scoring
"""

__version__ = "1.0.0"
__all__ = ["settings", "maze", "entity", "player", "ghost", "sounds", "game"]
