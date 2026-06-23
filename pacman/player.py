"""Pac-Man: the player-controlled character.

Adds three things on top of the generic :class:`Entity`:

* **Input buffering** -- the player can press the next turn slightly early and
  Pac-Man takes it as soon as the corridor allows (just like the arcade).
* **Instant reversal** -- pressing the opposite direction flips immediately
  instead of waiting for the next intersection.
* **Animation** -- the chomping mouth, oriented to the travel direction, plus a
  death "spin" that the game triggers when a ghost catches him.
"""

import math

import pygame

from . import settings as cfg
from .entity import Entity


class Player(Entity):
    """Pac-Man, driven by the keyboard."""

    def __init__(self, maze):
        super().__init__(cfg.PLAYER_START[0], cfg.PLAYER_START[1],
                         cfg.PACMAN_SPEED, maze)
        self.next_direction = cfg.STOP   # the most recently requested turn
        self.facing = cfg.LEFT           # last real heading (for drawing)
        self.direction = cfg.LEFT        # Pac-Man drifts left on spawn
        self.anim = 0                    # frame counter driving the mouth
        self.death_progress = 0.0        # 0 = alive, 1 = fully dissolved

    # -- control -----------------------------------------------------------
    def set_desired_direction(self, direction):
        """Queue a direction requested by the keyboard this frame."""
        self.next_direction = direction

    def reset(self, col=None, row=None, direction=cfg.LEFT):
        super().reset(col, row, direction=direction)
        self.next_direction = cfg.STOP
        self.facing = direction if direction != cfg.STOP else cfg.LEFT
        self.death_progress = 0.0

    # -- movement ----------------------------------------------------------
    def update(self):
        # A reversal can be honoured anywhere along a corridor, so handle it
        # before the normal tile-aligned movement.
        if (self.next_direction != cfg.STOP
                and self.direction != cfg.STOP
                and self.next_direction == cfg.opposite(self.direction)
                and self.can_move(self.next_direction)):
            self.reverse()
            self.next_direction = cfg.STOP

        super().update()

        if self.direction != cfg.STOP:
            self.facing = self.direction
            self.anim = (self.anim + 1) % 16  # advance the chomp animation

    def at_tile(self):
        # Stationary: start moving if the player has asked for a valid turn.
        if self.next_direction != cfg.STOP and self.can_move(self.next_direction):
            self.direction = self.next_direction

    def on_arrive(self):
        # At a tile centre, prefer the buffered turn, otherwise keep going,
        # otherwise stop dead at the wall.
        if self.next_direction != cfg.STOP and self.can_move(self.next_direction):
            self.direction = self.next_direction
        elif not self.can_move(self.direction):
            self.direction = cfg.STOP

    def current_tile(self):
        """Tile currently under Pac-Man's centre (used for eating pellets)."""
        return (int(self.x // cfg.TILE), int(self.y // cfg.TILE))

    # -- rendering ---------------------------------------------------------
    def _mouth_openness(self):
        """Return 0..1: a triangle wave so the mouth opens and closes."""
        phase = self.anim / 16.0
        return 1.0 - abs(2.0 * phase - 1.0)

    def draw(self, surface):
        sx = self.x
        sy = self.y + cfg.MAZE_OFFSET_Y
        radius = int(cfg.TILE * 0.46)
        face_angle = math.atan2(self.facing[1], self.facing[0])

        if self.death_progress > 0.0:
            # Death: the mouth yawns wider and wider until nothing is left.
            half = self.death_progress * math.pi
            if half >= math.pi:
                return  # fully gone
        else:
            # Alive: animated chomp, never fully closed so the eye still shows.
            half = math.radians(8 + self._mouth_openness() * 33)

        pygame.draw.circle(surface, cfg.YELLOW, (int(sx), int(sy)), radius)

        # Cut the mouth out with a black wedge pointing along the facing angle.
        if half > 0.01:
            reach = radius * 1.4
            p1 = (sx + reach * math.cos(face_angle - half),
                  sy + reach * math.sin(face_angle - half))
            p2 = (sx + reach * math.cos(face_angle + half),
                  sy + reach * math.sin(face_angle + half))
            pygame.draw.polygon(surface, cfg.BLACK, [(sx, sy), p1, p2])

        # A small eye (hidden once the death animation is well under way).
        if self.death_progress < 0.4:
            ex = sx - self.facing[0] * radius * 0.25
            ey = sy - radius * 0.45 - self.facing[1] * radius * 0.1
            pygame.draw.circle(surface, cfg.BLACK, (int(ex), int(ey)), 2)
