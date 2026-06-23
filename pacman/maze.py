"""The Maze: the static playfield plus the pellets scattered across it.

Responsibilities
----------------
* Parse the text ``LAYOUT`` into a grid we can query quickly.
* Answer collision questions ("is this tile a wall?").
* Track which pellets remain and award points when they are eaten.
* Render the walls (cached to a surface) and the pellets every frame.

The maze owns *no* moving objects -- Pac-Man and the ghosts live elsewhere and
simply ask the maze whether a tile is walkable.
"""

import math

import pygame

from . import settings as cfg


class Maze:
    """Represents the playfield grid and the pellets on it."""

    def __init__(self):
        # A mutable copy of the layout: pellets are removed by blanking cells.
        self._grid = [list(row) for row in cfg.LAYOUT]
        self.rows = len(self._grid)
        self.cols = len(self._grid[0])

        # Fail loudly and early if the layout is malformed -- this turns a
        # confusing in-game bug into an obvious start-up error.
        for r, row in enumerate(self._grid):
            if len(row) != self.cols:
                raise ValueError(
                    f"Maze row {r} has width {len(row)}, expected {self.cols}"
                )

        # Count edible pellets so we know when the level is cleared.
        self.total_pellets = sum(
            cell in (cfg.PELLET_CHAR, cfg.POWER_CHAR)
            for row in self._grid for cell in row
        )
        self.pellets_eaten = 0

        # Animation clock used to blink the power pellets.
        self._blink_timer = 0

        # The wall artwork never changes, so draw it once onto a cached surface
        # and simply blit that each frame.
        self._wall_surface = self._build_wall_surface()

    # -- queries -----------------------------------------------------------
    def in_bounds(self, col, row):
        """True if the tile coordinates fall inside the grid."""
        return 0 <= col < self.cols and 0 <= row < self.rows

    def tile_at(self, col, row):
        """Return the raw character at a tile (space if out of bounds)."""
        if not self.in_bounds(col, row):
            return " "
        return self._grid[row][col]

    def is_wall(self, col, row, allow_door=False):
        """Is the given tile solid?

        ``allow_door`` lets ghosts (and only ghosts, while leaving or returning
        home) pass through the ghost-house door, which is solid for Pac-Man.
        Anything above or below the grid counts as a wall; horizontal
        out-of-bounds is handled by the tunnel wrap in entity.py.
        """
        if row < 0 or row >= self.rows:
            return True
        if col < 0 or col >= self.cols:
            return False  # tunnel mouth -- the wrap logic deals with this
        cell = self._grid[row][col]
        if cell in cfg.WALL_CHARS:
            return True
        if cell == cfg.DOOR_CHAR:
            return not allow_door
        return False

    def has_pellet(self, col, row):
        return self.tile_at(col, row) == cfg.PELLET_CHAR

    def has_power(self, col, row):
        return self.tile_at(col, row) == cfg.POWER_CHAR

    @property
    def remaining_pellets(self):
        return self.total_pellets - self.pellets_eaten

    @property
    def cleared(self):
        """True once every pellet has been eaten (the win condition)."""
        return self.pellets_eaten >= self.total_pellets

    # -- mutation ----------------------------------------------------------
    def eat_pellet(self, col, row):
        """Eat whatever pellet is on a tile.

        Returns ``"pellet"``, ``"power"`` or ``None`` so the caller can react
        (add score, frighten ghosts, play a sound). Safe to call on any tile.
        """
        if not self.in_bounds(col, row):
            return None
        cell = self._grid[row][col]
        if cell == cfg.PELLET_CHAR:
            self._grid[row][col] = " "
            self.pellets_eaten += 1
            return "pellet"
        if cell == cfg.POWER_CHAR:
            self._grid[row][col] = " "
            self.pellets_eaten += 1
            return "power"
        return None

    # -- geometry helpers --------------------------------------------------
    @staticmethod
    def tile_center(col, row):
        """Pixel centre of a tile in *maze-local* coordinates (no HUD offset)."""
        return (col * cfg.TILE + cfg.TILE // 2,
                row * cfg.TILE + cfg.TILE // 2)

    # -- rendering ---------------------------------------------------------
    def _build_wall_surface(self):
        """Pre-render the walls once.

        Style: walls are filled with a dark navy and every edge that faces an
        open path gets a bright blue line. The result reads as classic Pac-Man
        corridors without the cost of recomputing it 60 times a second.
        """
        surface = pygame.Surface((cfg.MAZE_WIDTH, cfg.MAZE_HEIGHT),
                                 flags=pygame.SRCALPHA)
        t = cfg.TILE
        for row in range(self.rows):
            for col in range(self.cols):
                cell = self._grid[row][col]
                x, y = col * t, row * t

                if cell == cfg.DOOR_CHAR:
                    # The ghost-house door is a short horizontal bar.
                    pygame.draw.rect(surface, cfg.DOOR_COLOR,
                                     (x, y + t // 2 - 2, t, 4))
                    continue

                if cell not in cfg.WALL_CHARS:
                    continue  # open path -- nothing to draw

                # Soft navy fill so contiguous walls look like solid masses.
                pygame.draw.rect(surface, cfg.WALL_FILL, (x, y, t, t))

                # Draw a bright line on each side that borders a walkable tile.
                if not self._solid_neighbor(col, row, 0, -1):
                    pygame.draw.line(surface, cfg.WALL_LINE,
                                     (x, y), (x + t, y), 3)
                if not self._solid_neighbor(col, row, 0, 1):
                    pygame.draw.line(surface, cfg.WALL_LINE,
                                     (x, y + t - 1), (x + t, y + t - 1), 3)
                if not self._solid_neighbor(col, row, -1, 0):
                    pygame.draw.line(surface, cfg.WALL_LINE,
                                     (x, y), (x, y + t), 3)
                if not self._solid_neighbor(col, row, 1, 0):
                    pygame.draw.line(surface, cfg.WALL_LINE,
                                     (x + t - 1, y), (x + t - 1, y + t), 3)
        return surface

    def _solid_neighbor(self, col, row, dc, dr):
        """True if the neighbouring tile is also a wall or a door.

        Used purely for drawing, so doors count as solid -- that keeps the
        bright outline from leaking into the ghost-house doorway.
        """
        c, r = col + dc, row + dr
        if not self.in_bounds(c, r):
            return False
        return self._grid[r][c] in cfg.WALL_CHARS or self._grid[r][c] == cfg.DOOR_CHAR

    def update(self):
        """Advance the pellet-blink animation by one frame."""
        self._blink_timer = (self._blink_timer + 1) % 60

    def draw(self, surface):
        """Blit the cached walls, then draw all remaining pellets on top."""
        surface.blit(self._wall_surface, (0, cfg.MAZE_OFFSET_Y))

        # Power pellets blink: visible for roughly two-thirds of each cycle.
        power_visible = self._blink_timer < 40
        t = cfg.TILE
        for row in range(self.rows):
            for col in range(self.cols):
                cell = self._grid[row][col]
                if cell == cfg.PELLET_CHAR:
                    cx, cy = self.tile_center(col, row)
                    pygame.draw.circle(surface, cfg.PELLET_COLOR,
                                       (cx, cy + cfg.MAZE_OFFSET_Y), 3)
                elif cell == cfg.POWER_CHAR and power_visible:
                    cx, cy = self.tile_center(col, row)
                    pygame.draw.circle(surface, cfg.PELLET_COLOR,
                                       (cx, cy + cfg.MAZE_OFFSET_Y), 7)
