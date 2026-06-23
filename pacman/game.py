"""Game: the conductor that runs the whole show.

This module owns the pygame window, the main loop, and a small state machine
that moves the game between its phases:

    READY      -> brief "READY!" pause before control is handed over
    PLAYING    -> normal play
    DYING      -> Pac-Man's death animation after being caught
    GAME_OVER  -> all lives lost; wait for a restart
    WIN        -> every pellet eaten; wait to advance to the next level

It also tracks the score, lives and level; runs the scatter/chase schedule and
the frightened timer; handles all collisions; and draws the HUD.
"""

import os

import pygame

from . import settings as cfg
from .maze import Maze
from .player import Player
from .ghost import Blinky, Pinky, Inky, Clyde, FRIGHTENED, EATEN, HOUSE
from .sounds import SoundManager

# Game states.
READY = "ready"
PLAYING = "playing"
DYING = "dying"
GAME_OVER = "game_over"
WIN = "win"

HIGH_SCORE_FILE = os.path.join(os.path.dirname(__file__), "highscore.txt")


def frames(seconds):
    """Convert a duration in seconds to a whole number of 60-FPS frames."""
    return int(seconds * cfg.FPS)


class Game:
    """Owns the window, the main loop and all game state."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        pygame.display.set_caption(cfg.CAPTION)
        self.clock = pygame.time.Clock()
        self.sounds = SoundManager()

        # Fonts are wrapped defensively -- a missing font subsystem should not
        # take the whole game down.
        try:
            self.font = pygame.font.Font(None, 30)
            self.small_font = pygame.font.Font(None, 22)
            self.big_font = pygame.font.Font(None, 64)
        except pygame.error:
            self.font = self.small_font = self.big_font = None

        self.high_score = self._load_high_score()
        self.paused = False
        self.reset_game()

    # ------------------------------------------------------------------ #
    # Set-up / level management
    # ------------------------------------------------------------------ #
    def reset_game(self):
        """Start a brand new game from level 1."""
        self.score = 0
        self.lives = cfg.START_LIVES
        self.level = 1
        self.extra_life_awarded = False
        self._build_world()

    def next_level(self):
        """Advance to a fresh, slightly harder level (pellets refilled)."""
        self.level += 1
        self._build_world()

    def _build_world(self):
        """Create the maze and actors and arm all the per-level timers."""
        self.maze = Maze()
        self.player = Player(self.maze)
        self.blinky = Blinky(self.maze)
        self.ghosts = [self.blinky, Pinky(self.maze),
                       Inky(self.maze), Clyde(self.maze)]

        self.fruit_active = False
        self.fruit_timer = 0
        self.fruits_spawned = 0

        self._arm_timers()
        self.sounds.play_intro()
        self._enter_state(READY)

    def _arm_timers(self):
        """(Re)initialise the scatter/chase schedule, fright and release timers."""
        self.mode_index = 0
        self.global_mode = cfg.MODE_SCHEDULE[0][0]
        first_duration = cfg.MODE_SCHEDULE[0][1]
        self.mode_timer = frames(first_duration) if first_duration else 0
        self.fright_timer = 0
        self.ghost_combo = 0
        self.release_timers = {
            name: frames(delay) for name, delay in cfg.GHOST_RELEASE.items()
        }

    def _reset_after_death(self):
        """Put the actors back on their marks but keep the eaten pellets."""
        self.player.reset()
        for ghost in self.ghosts:
            ghost.reset(start_outside=(ghost.name == "blinky"))
        self.fruit_active = False
        self._arm_timers()

    def _enter_state(self, state):
        self.state = state
        if state == READY:
            self.state_timer = frames(cfg.READY_SECONDS)
        elif state == DYING:
            self.state_timer = frames(cfg.DEATH_SECONDS)

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self):
        """Run until the player quits. Wrapped so any crash still quits cleanly."""
        try:
            running = True
            while running:
                running = self._handle_events()
                if not self.paused:
                    self.update()
                self.draw()
                pygame.display.flip()
                self.clock.tick(cfg.FPS)
        finally:
            self._save_high_score()
            pygame.quit()

    def _handle_events(self):
        """Process the event queue. Returns False when the game should close."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_p and self.state == PLAYING:
                    self.paused = not self.paused
                elif self.state == GAME_OVER and event.key in (pygame.K_r, pygame.K_RETURN):
                    self.reset_game()
                elif self.state == WIN and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_r):
                    self.next_level()
        return True

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #
    def update(self):
        self.maze.update()  # pellet blink animation
        if self.state == READY:
            self.state_timer -= 1
            if self.state_timer <= 0:
                self._enter_state(PLAYING)
        elif self.state == PLAYING:
            self._update_play()
        elif self.state == DYING:
            self._update_dying()

    def _update_play(self):
        self._read_input()
        self._update_modes()
        self._release_ghosts()

        self.player.update()
        self._eat_pellet()

        for ghost in self.ghosts:
            ghost.update(self.player, self.blinky, self.global_mode)

        self._check_collisions()
        self._update_fruit()

        if self.maze.cleared:
            self._enter_state(WIN)

    def _read_input(self):
        """Steer Pac-Man from the currently held keys (arrows or WASD)."""
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.player.set_desired_direction(cfg.UP)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.player.set_desired_direction(cfg.DOWN)
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player.set_desired_direction(cfg.LEFT)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player.set_desired_direction(cfg.RIGHT)
        # If nothing is held we leave the last request in place so Pac-Man
        # keeps gliding -- exactly like the arcade.

    def _update_modes(self):
        """Run the scatter/chase clock (paused whenever ghosts are frightened)."""
        if self.fright_timer > 0:
            self.fright_timer -= 1
            if self.fright_timer == 0:
                for ghost in self.ghosts:
                    ghost.end_frightened()
            return

        duration = cfg.MODE_SCHEDULE[self.mode_index][1]
        if duration is None:
            return  # final phase lasts forever
        self.mode_timer -= 1
        if self.mode_timer <= 0:
            self.mode_index += 1
            mode, dur = cfg.MODE_SCHEDULE[self.mode_index]
            self.global_mode = mode
            self.mode_timer = frames(dur) if dur else 0
            # A mode flip makes every loose ghost reverse on the spot.
            for ghost in self.ghosts:
                ghost.force_reverse()

    def _release_ghosts(self):
        """Let ghosts out of the house once their individual timer expires."""
        for ghost in self.ghosts:
            if ghost.state == HOUSE:
                if self.release_timers[ghost.name] <= 0:
                    ghost.start_leaving()
                else:
                    self.release_timers[ghost.name] -= 1

    def _eat_pellet(self):
        col, row = self.player.current_tile()
        kind = self.maze.eat_pellet(col, row)
        if kind == "pellet":
            self.add_score(cfg.PELLET_POINTS)
            self.sounds.play_chomp()
            self._maybe_spawn_fruit()
        elif kind == "power":
            self.add_score(cfg.POWER_POINTS)
            self.sounds.play_power()
            self.ghost_combo = 0
            # Frightened time shrinks as the levels climb.
            duration = max(1.0, cfg.FRIGHT_SECONDS - (self.level - 1) * 0.6)
            self.fright_timer = frames(duration)
            for ghost in self.ghosts:
                ghost.set_frightened()
            self._maybe_spawn_fruit()

    def _check_collisions(self):
        """Resolve Pac-Man touching a ghost (eat it, or be caught)."""
        for ghost in self.ghosts:
            if abs(ghost.x - self.player.x) < cfg.TILE * 0.5 and \
                    abs(ghost.y - self.player.y) < cfg.TILE * 0.5:
                if ghost.state == FRIGHTENED:
                    ghost.get_eaten()
                    points = cfg.GHOST_POINTS[min(self.ghost_combo, 3)]
                    self.add_score(points)
                    self.ghost_combo += 1
                    self.sounds.play_eat_ghost()
                elif ghost.state == EATEN:
                    continue  # just eyes -- harmless
                else:
                    self._player_caught()
                    return

    def _player_caught(self):
        self.fright_timer = 0
        self.sounds.play_death()
        self.player.death_progress = 0.0
        self._enter_state(DYING)

    def _update_dying(self):
        self.state_timer -= 1
        total = frames(cfg.DEATH_SECONDS)
        self.player.death_progress = 1.0 - max(0, self.state_timer) / total
        if self.state_timer <= 0:
            self.lives -= 1
            if self.lives <= 0:
                self._enter_state(GAME_OVER)
                self._save_high_score()
            else:
                self._reset_after_death()
                self._enter_state(READY)

    # -- fruit -------------------------------------------------------------
    def _maybe_spawn_fruit(self):
        eaten = self.maze.pellets_eaten
        if (self.fruits_spawned < len(cfg.FRUIT_AT_PELLETS)
                and eaten >= cfg.FRUIT_AT_PELLETS[self.fruits_spawned]):
            self.fruit_active = True
            self.fruit_timer = frames(9.0)
            self.fruits_spawned += 1

    def _update_fruit(self):
        if not self.fruit_active:
            return
        self.fruit_timer -= 1
        if self.fruit_timer <= 0:
            self.fruit_active = False
        elif self.player.current_tile() == cfg.FRUIT_TILE:
            self.fruit_active = False
            self.add_score(cfg.FRUIT_POINTS)
            self.sounds.play_fruit()

    # -- scoring -----------------------------------------------------------
    def add_score(self, points):
        self.score += points
        if not self.extra_life_awarded and self.score >= cfg.EXTRA_LIFE_SCORE:
            self.extra_life_awarded = True
            self.lives += 1
            self.sounds.play_extra_life()
        if self.score > self.high_score:
            self.high_score = self.score

    def _load_high_score(self):
        try:
            with open(HIGH_SCORE_FILE, "r", encoding="utf-8") as fh:
                return int(fh.read().strip() or 0)
        except (OSError, ValueError):
            return 0

    def _save_high_score(self):
        try:
            with open(HIGH_SCORE_FILE, "w", encoding="utf-8") as fh:
                fh.write(str(self.high_score))
        except OSError:
            pass  # read-only filesystem: not worth crashing over

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #
    def draw(self):
        self.screen.fill(cfg.BLACK)
        self.maze.draw(self.screen)
        self._draw_fruit()

        # Hide Pac-Man only once the death animation has fully consumed him.
        if not (self.state == DYING and self.player.death_progress >= 1.0):
            self.player.draw(self.screen)

        # Ghosts vanish during the death animation, just like the arcade.
        if self.state != DYING:
            flash = self._fright_flash_on()
            for ghost in self.ghosts:
                ghost.draw(self.screen, flash=flash)

        self._draw_hud()
        self._draw_overlays()

    def _fright_flash_on(self):
        """Whether frightened ghosts should currently flash white."""
        flash_window = frames(cfg.FRIGHT_FLASH_SECONDS)
        if 0 < self.fright_timer < flash_window:
            return (self.fright_timer // 12) % 2 == 0
        return False

    def _draw_fruit(self):
        if not self.fruit_active:
            return
        cx, cy = self.maze.tile_center(*cfg.FRUIT_TILE)
        cy += cfg.MAZE_OFFSET_Y
        pygame.draw.circle(self.screen, cfg.FRUIT_COLOR, (cx - 4, cy + 3), 6)
        pygame.draw.circle(self.screen, cfg.FRUIT_COLOR, (cx + 4, cy + 3), 6)
        pygame.draw.line(self.screen, cfg.FRUIT_STEM, (cx - 4, cy - 3), (cx + 5, cy - 6), 2)

    def _draw_hud(self):
        if self.font is None:
            return
        # Top bar: current score (left) and high score (centre).
        self._blit_text("SCORE", self.small_font, cfg.WHITE, 16, 6)
        self._blit_text(str(self.score), self.font, cfg.WHITE, 16, 24)
        self._blit_text("HIGH SCORE", self.small_font, cfg.WHITE,
                        cfg.SCREEN_WIDTH // 2 - 50, 6)
        hi = max(self.high_score, self.score)
        self._blit_text(str(hi), self.font, cfg.WHITE,
                        cfg.SCREEN_WIDTH // 2 - 50, 24)

        # Bottom bar: remaining lives as little Pac-Man icons, level on the right.
        base_y = cfg.MAZE_OFFSET_Y + cfg.MAZE_HEIGHT + 18
        for i in range(max(0, self.lives - 1)):
            cx = 26 + i * 30
            pygame.draw.circle(self.screen, cfg.YELLOW, (cx, base_y + 8), 9)
            pygame.draw.polygon(self.screen, cfg.BLACK, [
                (cx, base_y + 8), (cx + 12, base_y + 2), (cx + 12, base_y + 14)])
        self._blit_text(f"LEVEL {self.level}", self.small_font, cfg.WHITE,
                        cfg.SCREEN_WIDTH - 96, base_y)

    def _draw_overlays(self):
        if self.state == READY:
            self._center_text("READY!", self.font, cfg.READY_COLOR, 17.5)
        elif self.state == GAME_OVER:
            self._center_text("GAME OVER", self.big_font, cfg.GAMEOVER_COLOR, 14)
            self._center_text("Press R to play again", self.small_font, cfg.WHITE, 17)
            self._center_text("Press Esc to quit", self.small_font, cfg.WHITE, 18.2)
        elif self.state == WIN:
            self._center_text("LEVEL CLEARED!", self.big_font, cfg.READY_COLOR, 14)
            self._center_text("Press Space for the next level",
                              self.small_font, cfg.WHITE, 17)
        if self.paused:
            self._center_text("PAUSED", self.big_font, cfg.WHITE, 15)

    # -- text helpers ------------------------------------------------------
    def _blit_text(self, text, font, color, x, y):
        if font is None:
            return
        self.screen.blit(font.render(text, True, color), (x, y))

    def _center_text(self, text, font, color, tile_row):
        """Draw centred text whose vertical position is given in maze rows."""
        if font is None:
            return
        surf = font.render(text, True, color)
        x = cfg.SCREEN_WIDTH // 2 - surf.get_width() // 2
        y = cfg.MAZE_OFFSET_Y + int(tile_row * cfg.TILE) - surf.get_height() // 2
        # A subtle dark plate keeps the text readable over the maze.
        plate = surf.get_rect(topleft=(x, y)).inflate(16, 8)
        pygame.draw.rect(self.screen, cfg.BLACK, plate)
        self.screen.blit(surf, (x, y))
