"""Entity: the shared, grid-based movement engine.

Both Pac-Man and the ghosts move the same way, so that logic lives here once.

The movement model
------------------
Every entity is "anchored" to an integer tile (``col``, ``row``) and carries a
floating-point ``progress`` value -- how many pixels it has travelled out of
the current tile towards the next one in ``direction``. Each frame:

    1. ``progress`` increases by ``speed``.
    2. When ``progress`` reaches a full tile, the entity *arrives* at the next
       tile: the anchor advances, and ``on_arrive`` is called so subclasses can
       choose a new direction (turning, AI decisions, eating pellets...).

Because direction changes only happen at tile centres, an entity can never end
up halfway inside a wall, and turns always line up perfectly with corridors.
The one exception is an instant *reverse*, which is handled specially so input
(and ghost mode changes) feel responsive.
"""

from . import settings as cfg


class Entity:
    """A creature that walks the maze on a tile grid with smooth animation."""

    def __init__(self, col, row, speed, maze):
        self.maze = maze
        self.start_col = col
        self.start_row = row
        self.col = col
        self.row = row
        self.direction = cfg.STOP
        self.speed = speed
        self.progress = 0.0  # pixels travelled out of the current tile

        # Pixel centre in maze-local coordinates; kept in sync via _sync_pixel.
        self.x, self.y = maze.tile_center(col, row)

    # -- helpers -----------------------------------------------------------
    def reset(self, col=None, row=None, direction=cfg.STOP):
        """Snap the entity back to a tile (used on spawn and after a death)."""
        self.col = self.start_col if col is None else col
        self.row = self.start_row if row is None else row
        self.direction = direction
        self.progress = 0.0
        self._sync_pixel()

    def next_tile(self, col, row, direction):
        """Tile reached by stepping one cell in ``direction``, with tunnel wrap.

        Stepping off the left or right edge wraps to the opposite side, which is
        what creates the side tunnels. Vertical wrap never happens because the
        top and bottom rows are solid walls.
        """
        c = col + direction[0]
        r = row + direction[1]
        if c < 0:
            c = self.maze.cols - 1
        elif c >= self.maze.cols:
            c = 0
        return c, r

    def can_move(self, direction, allow_door=False):
        """Is the neighbouring tile in ``direction`` walkable?"""
        if direction == cfg.STOP:
            return False
        c, r = self.next_tile(self.col, self.row, direction)
        return not self.maze.is_wall(c, r, allow_door=allow_door)

    def _sync_pixel(self):
        """Recompute the pixel position from the anchor tile + progress."""
        cx, cy = self.maze.tile_center(self.col, self.row)
        self.x = cx + self.direction[0] * self.progress
        self.y = cy + self.direction[1] * self.progress

    def reverse(self):
        """Instantly flip direction without waiting for the next tile centre.

        We re-anchor to the tile we were heading toward and invert progress, so
        the pixel position is unchanged but the entity now travels the other
        way. Used for Pac-Man's snappy turns and forced ghost mode reversals.
        """
        if self.direction == cfg.STOP:
            return
        self.col, self.row = self.next_tile(self.col, self.row, self.direction)
        self.direction = cfg.opposite(self.direction)
        self.progress = cfg.TILE - self.progress
        self._sync_pixel()

    # -- per-frame update --------------------------------------------------
    def update(self):
        """Advance one frame. Subclasses override ``on_arrive``/``at_tile``."""
        # Let a stationary entity start moving if its controller wants to.
        if self.direction == cfg.STOP:
            self.at_tile()
            if self.direction == cfg.STOP:
                return

        self.progress += self.current_speed()

        # Arrive at the next tile (speed is always well below one tile/frame,
        # so at most one arrival happens per frame).
        if self.progress >= cfg.TILE:
            self.progress -= cfg.TILE
            self.col, self.row = self.next_tile(self.col, self.row, self.direction)
            self.on_arrive()
            if self.direction == cfg.STOP:
                self.progress = 0.0

        self._sync_pixel()

    # -- hooks for subclasses ---------------------------------------------
    def current_speed(self):
        """Speed for this frame -- ghosts override to slow down in tunnels."""
        return self.speed

    def at_tile(self):
        """Called while stopped, giving a chance to begin moving."""

    def on_arrive(self):
        """Called the instant the entity reaches a new tile centre."""
