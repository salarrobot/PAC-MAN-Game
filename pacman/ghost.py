"""The ghosts: four enemies, four personalities.

Each ghost shares the same engine but chooses its *target tile* differently,
which is what gives the originals their famous character:

* **Blinky** (red)    -- chases Pac-Man directly.
* **Pinky**  (pink)   -- aims four tiles *ahead* of Pac-Man to cut him off.
* **Inky**   (cyan)   -- uses Blinky's position to flank from the far side.
* **Clyde**  (orange) -- chases up close but flees to his corner when near.

A ghost is always in exactly one *state*:

    HOUSE      waiting inside the ghost house (gently bobbing)
    LEAVING    climbing out through the door
    NORMAL     out in the maze, obeying the global scatter/chase mode
    FRIGHTENED blue and edible after a power pellet (wanders randomly)
    EATEN      just a pair of eyes hurrying back home to respawn

The standard movement rule for a ghost is: at every tile, look at each
direction except a U-turn, discard walls, and step towards whichever option
lands closest (straight-line distance) to its current target tile. Ties break
in the fixed order up, left, down, right -- exactly as the arcade did.
"""

import math
import random

import pygame

from . import settings as cfg
from .entity import Entity

# Ghost states.
HOUSE = "house"
LEAVING = "leaving"
NORMAL = "normal"
FRIGHTENED = "frightened"
EATEN = "eaten"


class Ghost(Entity):
    """Base class for all four ghosts."""

    name = "ghost"
    scatter_corner = (0, 0)

    def __init__(self, maze, start_tile, color, start_outside=False):
        super().__init__(start_tile[0], start_tile[1], cfg.GHOST_SPEED, maze)
        self.color = color
        self.home_tile = start_tile
        # Blinky begins life already out in the maze; the rest wait inside.
        if start_outside:
            self.state = NORMAL
            self.direction = cfg.LEFT
        else:
            self.state = HOUSE
            self.direction = cfg.UP
        self._bob = 0.0  # phase for the in-house bobbing animation

        # Context refreshed each frame by :meth:`update`.
        self._player = None
        self._blinky = None
        self._global_mode = "scatter"

    # -- state transitions -------------------------------------------------
    def reset(self, start_outside=False):
        """Return to the spawn tile and starting state (after a death)."""
        super().reset(self.home_tile[0], self.home_tile[1],
                      cfg.LEFT if start_outside else cfg.UP)
        self.speed = cfg.GHOST_SPEED
        self.state = NORMAL if start_outside else HOUSE
        self._bob = 0.0

    def start_leaving(self):
        """Begin climbing out of the house (called by the game on a timer)."""
        if self.state == HOUSE:
            self.state = LEAVING
            self.progress = 0.0
            self._sync_pixel()
            self._leaving_decision()

    def set_frightened(self):
        """Turn blue and edible -- only affects ghosts loose in the maze."""
        if self.state == NORMAL:
            self.state = FRIGHTENED
            self.speed = cfg.GHOST_FRIGHT_SPEED
            self.reverse()  # ghosts spin around when a power pellet is eaten

    def end_frightened(self):
        if self.state == FRIGHTENED:
            self.state = NORMAL
            self.speed = cfg.GHOST_SPEED

    def get_eaten(self):
        """Pac-Man ate this ghost: leave only the eyes, racing home."""
        self.state = EATEN
        self.speed = cfg.GHOST_EATEN_SPEED

    def force_reverse(self):
        """Spin around -- used when the global scatter/chase mode flips."""
        if self.state == NORMAL:
            self.reverse()

    @property
    def is_frightened(self):
        return self.state == FRIGHTENED

    @property
    def is_eaten(self):
        return self.state == EATEN

    @property
    def is_edible(self):
        return self.state == FRIGHTENED

    # -- per-frame update --------------------------------------------------
    def update(self, player, blinky, global_mode):
        # Stash the context so the tile-arrival callbacks can read it.
        self._player = player
        self._blinky = blinky
        self._global_mode = global_mode

        if self.state == HOUSE:
            self._bob_in_house()
            return
        super().update()

    def current_speed(self):
        # Eyes ignore the tunnel slowdown; everything else crawls in tunnels.
        if self.state == EATEN:
            return cfg.GHOST_EATEN_SPEED
        if self.row == cfg.TUNNEL_ROW and (self.col <= 5 or self.col >= cfg.COLS - 6):
            return min(self.speed, cfg.GHOST_TUNNEL_SPEED)
        return self.speed

    def _bob_in_house(self):
        """Gently float up and down while waiting to be released."""
        self._bob = (self._bob + 0.1) % (2 * math.pi)
        cx, cy = self.maze.tile_center(self.col, self.row)
        self.x = cx
        self.y = cy + math.sin(self._bob) * (cfg.TILE * 0.18)

    # -- decision making (called the moment a tile centre is reached) -------
    def on_arrive(self):
        if self.state == LEAVING:
            self._leaving_decision()
        elif self.state == EATEN:
            self._eaten_decision()
        elif self.state == FRIGHTENED:
            self.direction = self._random_direction()
        else:  # NORMAL
            self.direction = self._best_direction(self._target_tile())

    def _leaving_decision(self):
        """Scripted path out of the house: slide to the door column, then up."""
        if (self.col, self.row) == cfg.HOUSE_EXIT:
            # We're out -- rejoin normal play, picking a sensible first move.
            self.state = NORMAL
            self.speed = cfg.GHOST_SPEED
            self.direction = self._best_direction(self._target_tile())
            return
        if self.col != cfg.HOUSE_EXIT[0]:
            if self.row != cfg.HOUSE_CENTER[1]:
                self.direction = cfg.DOWN if self.row < cfg.HOUSE_CENTER[1] else cfg.UP
            else:
                self.direction = cfg.RIGHT if self.col < cfg.HOUSE_EXIT[0] else cfg.LEFT
        else:
            self.direction = cfg.UP

    def _eaten_decision(self):
        """Navigate the eyes back to the house, then come alive again."""
        if (self.col, self.row) == cfg.HOUSE_CENTER:
            # Home at last: revive and start climbing back out.
            self.state = LEAVING
            self.speed = cfg.GHOST_SPEED
            self._leaving_decision()
            return
        # Once in the door column at/below the entrance, dive straight down.
        if self.col == cfg.HOUSE_EXIT[0] and self.row >= cfg.HOUSE_EXIT[1]:
            self.direction = cfg.DOWN
            return
        self.direction = self._best_direction(cfg.HOUSE_EXIT, allow_door=True)

    # -- targeting ---------------------------------------------------------
    def _target_tile(self):
        """Where this ghost wants to go right now (scatter corner vs. chase)."""
        if self._global_mode == "scatter":
            return self.scatter_corner
        return self.chase_target()

    def chase_target(self):
        """Overridden by each ghost to give it a personality."""
        return (self._player.col, self._player.row)

    def _player_heading(self):
        """Pac-Man's direction of travel (falls back to his last heading)."""
        p = self._player
        return p.direction if p.direction != cfg.STOP else p.facing

    # -- direction selection ----------------------------------------------
    def _best_direction(self, target, allow_door=False):
        """Pick the legal, non-reversing move that gets closest to ``target``."""
        best = None
        for d in cfg.DIRECTION_PRIORITY:
            if d == cfg.opposite(self.direction):
                continue
            c, r = self.next_tile(self.col, self.row, d)
            if self.maze.is_wall(c, r, allow_door=allow_door):
                continue
            dist = (target[0] - c) ** 2 + (target[1] - r) ** 2
            if best is None or dist < best[0]:
                best = (dist, d)
        if best is not None:
            return best[1]
        # Dead end: the only way out is to turn around.
        return cfg.opposite(self.direction)

    def _random_direction(self):
        """Frightened ghosts choose any legal non-reversing direction at random."""
        choices = []
        for d in cfg.DIRECTION_PRIORITY:
            if d == cfg.opposite(self.direction):
                continue
            c, r = self.next_tile(self.col, self.row, d)
            if not self.maze.is_wall(c, r):
                choices.append(d)
        if choices:
            return random.choice(choices)
        return cfg.opposite(self.direction)

    # -- rendering ---------------------------------------------------------
    def draw(self, surface, flash=False):
        sx = self.x
        sy = self.y + cfg.MAZE_OFFSET_Y
        look = self.direction if self.direction != cfg.STOP else cfg.LEFT

        if self.state == EATEN:
            # Only the eyes remain, drifting home.
            self._draw_eyes(surface, sx, sy, look)
            return

        if self.state == FRIGHTENED:
            color = cfg.FRIGHT_FLASH_COLOR if flash else cfg.FRIGHT_COLOR
            self._draw_body(surface, sx, sy, color)
            self._draw_fright_face(surface, sx, sy)
            return

        # Normal / leaving: coloured body with eyes tracking the heading.
        self._draw_body(surface, sx, sy, self.color)
        self._draw_eyes(surface, sx, sy, look)

    @staticmethod
    def _draw_body(surface, sx, sy, color):
        """Draw the classic dome-with-wavy-skirt ghost silhouette."""
        r = cfg.TILE * 0.46
        points = []
        # Top dome, traced left -> right.
        steps = 10
        for i in range(steps + 1):
            ang = math.pi + math.pi * (i / steps)
            points.append((sx + r * math.cos(ang), sy + r * math.sin(ang)))
        # Wavy bottom skirt, traced right -> left (alternating feet/notches).
        bottom = sy + r
        n = 7
        for k in range(n):
            x = sx + r - (2 * r) * (k / (n - 1))
            y = bottom if k % 2 == 0 else bottom - r * 0.30
            points.append((x, y))
        pygame.draw.polygon(surface, color, [(int(px), int(py)) for px, py in points])

    @staticmethod
    def _draw_eyes(surface, sx, sy, look):
        r = cfg.TILE * 0.46
        eye_dx = r * 0.38
        eye_y = sy - r * 0.12
        for ex in (sx - eye_dx, sx + eye_dx):
            pygame.draw.circle(surface, cfg.EYE_WHITE, (int(ex), int(eye_y)),
                               int(r * 0.27))
            px = ex + look[0] * r * 0.15
            py = eye_y + look[1] * r * 0.15
            pygame.draw.circle(surface, cfg.EYE_PUPIL, (int(px), int(py)),
                               int(r * 0.14))

    @staticmethod
    def _draw_fright_face(surface, sx, sy):
        r = cfg.TILE * 0.46
        pygame.draw.circle(surface, cfg.FRIGHT_FACE,
                           (int(sx - r * 0.35), int(sy - r * 0.1)), int(r * 0.12))
        pygame.draw.circle(surface, cfg.FRIGHT_FACE,
                           (int(sx + r * 0.35), int(sy - r * 0.1)), int(r * 0.12))
        y = sy + r * 0.35
        pts = [(sx - r * 0.55, y), (sx - r * 0.27, y - r * 0.2),
               (sx, y), (sx + r * 0.27, y - r * 0.2), (sx + r * 0.55, y)]
        pygame.draw.lines(surface, cfg.FRIGHT_FACE, False,
                          [(int(px), int(py)) for px, py in pts], 2)


# ---------------------------------------------------------------------------
# The four individual ghosts -- only their targeting differs.
# ---------------------------------------------------------------------------
class Blinky(Ghost):
    """Red. Relentlessly targets Pac-Man's exact tile."""

    name = "blinky"
    scatter_corner = cfg.BLINKY_SCATTER

    def __init__(self, maze):
        super().__init__(maze, cfg.BLINKY_START, cfg.GHOST_COLORS["blinky"],
                         start_outside=True)

    def chase_target(self):
        return (self._player.col, self._player.row)


class Pinky(Ghost):
    """Pink. Aims four tiles ahead of Pac-Man to ambush him."""

    name = "pinky"
    scatter_corner = cfg.PINKY_SCATTER

    def __init__(self, maze):
        super().__init__(maze, cfg.PINKY_START, cfg.GHOST_COLORS["pinky"])

    def chase_target(self):
        dx, dy = self._player_heading()
        return (self._player.col + dx * 4, self._player.row + dy * 4)


class Inky(Ghost):
    """Cyan. Uses Blinky as a pivot to attack from the opposite flank."""

    name = "inky"
    scatter_corner = cfg.INKY_SCATTER

    def __init__(self, maze):
        super().__init__(maze, cfg.INKY_START, cfg.GHOST_COLORS["inky"])

    def chase_target(self):
        dx, dy = self._player_heading()
        pivot_c = self._player.col + dx * 2
        pivot_r = self._player.row + dy * 2
        # Double the vector from Blinky to that pivot point.
        return (2 * pivot_c - self._blinky.col, 2 * pivot_r - self._blinky.row)


class Clyde(Ghost):
    """Orange. Chases when far, but bolts for his corner when within 8 tiles."""

    name = "clyde"
    scatter_corner = cfg.CLYDE_SCATTER

    def __init__(self, maze):
        super().__init__(maze, cfg.CLYDE_START, cfg.GHOST_COLORS["clyde"])

    def chase_target(self):
        dist2 = (self.col - self._player.col) ** 2 + (self.row - self._player.row) ** 2
        if dist2 > 64:  # more than 8 tiles away -> behave like Blinky
            return (self._player.col, self._player.row)
        return self.scatter_corner
