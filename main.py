"""Run the game:  python main.py

This thin entry point keeps the launch logic separate from the game itself, so
the ``pacman`` package can also be imported and driven by tests or tools.
"""

import sys

from pacman.game import Game


def main():
    """Create the game and hand control to its main loop."""
    try:
        Game().run()
    except Exception as exc:  # last-ditch guard so we never dump a raw traceback
        print(f"Pac-Man exited with an error: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
