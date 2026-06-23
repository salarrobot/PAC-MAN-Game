"""Static validation of the maze layout (no pygame needed).

Checks:
  * every row is the same width and the grid is the expected size,
  * the spawn tiles and ghost house are where the code expects them,
  * every pellet is reachable from Pac-Man's start (flood fill),
  * the tunnel row wraps left<->right.

Run:  python tools/validate_maze.py
"""

import sys
from collections import deque

sys.path.insert(0, ".")
from pacman import settings as cfg  # noqa: E402

WALLS = set(cfg.WALL_CHARS)


def walkable(grid, col, row, allow_door=False):
    if row < 0 or row >= len(grid):
        return False
    col %= len(grid[0])  # horizontal wrap (tunnel)
    ch = grid[row][col]
    if ch in WALLS:
        return False
    if ch == cfg.DOOR_CHAR:
        return allow_door
    return True


def main():
    grid = [list(r) for r in cfg.LAYOUT]
    rows, cols = len(grid), len(grid[0])
    problems = []

    # 1. Rectangular grid of the advertised size.
    if (cols, rows) != (cfg.COLS, cfg.ROWS):
        problems.append(f"size is {cols}x{rows}, expected {cfg.COLS}x{cfg.ROWS}")
    for r, row in enumerate(grid):
        if len(row) != cols:
            problems.append(f"row {r} width {len(row)} != {cols}")

    # 2. Spawn tiles are not buried inside walls.
    def check_tile(name, tile, must_walk=True):
        c, r = tile
        ch = grid[r][c]
        if must_walk and ch in WALLS:
            problems.append(f"{name} {tile} sits on a wall ('{ch}')")

    check_tile("PLAYER_START", cfg.PLAYER_START)
    check_tile("BLINKY_START", cfg.BLINKY_START)
    check_tile("HOUSE_EXIT", cfg.HOUSE_EXIT)
    check_tile("FRUIT_TILE", cfg.FRUIT_TILE)

    # 3. Flood fill from the player start; every pellet must be reachable.
    start = cfg.PLAYER_START
    seen = {start}
    queue = deque([start])
    while queue:
        c, r = queue.popleft()
        for dc, dr in (cfg.UP, cfg.DOWN, cfg.LEFT, cfg.RIGHT):
            nc, nr = c + dc, r + dr
            nc %= cols
            if (nc, nr) not in seen and walkable(grid, nc, nr):
                seen.add((nc, nr))
                queue.append((nc, nr))

    pellets = [(c, r) for r in range(rows) for c in range(cols)
               if grid[r][c] in (cfg.PELLET_CHAR, cfg.POWER_CHAR)]
    unreachable = [p for p in pellets if p not in seen]
    if unreachable:
        problems.append(f"{len(unreachable)} unreachable pellets: {unreachable[:8]}")

    # 4. Tunnel row should be open at both ends so the wrap is usable.
    trow = cfg.TUNNEL_ROW
    if grid[trow][0] in WALLS or grid[trow][cols - 1] in WALLS:
        problems.append(f"tunnel row {trow} is not open at the edges")

    # -- report ----------------------------------------------------------
    print(f"Grid:            {cols} x {rows}")
    print(f"Total pellets:   {len(pellets)}")
    print(f"Reachable tiles: {len(seen)}")
    print(f"Tunnel row {trow}: '{''.join(grid[trow])}'")
    if problems:
        print("\nFAILED:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("\nOK: maze is rectangular, fully connected, and all pellets reachable.")


if __name__ == "__main__":
    main()
