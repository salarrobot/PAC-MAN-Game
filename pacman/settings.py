"""Central configuration for the whole game.

Every "magic number" lives here. Keeping them in one place means you can
re-balance the game (faster ghosts, a bigger maze, different colours) without
hunting through the logic. Nothing in this module imports pygame, so it stays
trivial to read and to unit-test.
"""

# ---------------------------------------------------------------------------
# Maze layout
# ---------------------------------------------------------------------------
# The maze is described as a grid of characters. Every row MUST be exactly the
# same width (this is validated when the maze loads). Legend:
#
#     X   wall
#     .   pellet        (small dot, eaten for points)
#     o   power pellet  (energizer: turns ghosts blue/edible)
#     =   ghost-house door (ghosts may pass through, Pac-Man may not)
#   space empty path    (no pellet) -- used for the tunnel and ghost house
#
# The layout is 28 columns wide and 31 rows tall, matching the proportions of
# the original 1980 arcade board.
LAYOUT = [
    "XXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "X............XX............X",
    "X.XXXX.XXXXX.XX.XXXXX.XXXX.X",
    "XoXXXX.XXXXX.XX.XXXXX.XXXXoX",
    "X.XXXX.XXXXX.XX.XXXXX.XXXX.X",
    "X..........................X",
    "X.XXXX.XX.XXXXXXXX.XX.XXXX.X",
    "X.XXXX.XX.XXXXXXXX.XX.XXXX.X",
    "X......XX....XX....XX......X",
    "XXXXXX.XXXXX.XX.XXXXX.XXXXXX",
    "XXXXXX.XXXXX.XX.XXXXX.XXXXXX",
    "XXXXXX.XX..........XX.XXXXXX",
    "XXXXXX.XX.XXX==XXX.XX.XXXXXX",
    "XXXXXX.XX.X      X.XX.XXXXXX",
    "          X      X          ",
    "XXXXXX.XX.X      X.XX.XXXXXX",
    "XXXXXX.XX.XXXXXXXX.XX.XXXXXX",
    "XXXXXX.XX..........XX.XXXXXX",
    "XXXXXX.XX.XXXXXXXX.XX.XXXXXX",
    "XXXXXX.XX.XXXXXXXX.XX.XXXXXX",
    "X............XX............X",
    "X.XXXX.XXXXX.XX.XXXXX.XXXX.X",
    "X.XXXX.XXXXX.XX.XXXXX.XXXX.X",
    "Xo..XX..XX........XX..XX..oX",
    "XXX.XX.XX.XXXXXXXX.XX.XX.XXX",
    "XXX.XX.XX.XXXXXXXX.XX.XX.XXX",
    "X......XX....XX....XX......X",
    "X.XXXXXXXXXX.XX.XXXXXXXXXX.X",
    "X.XXXXXXXXXX.XX.XXXXXXXXXX.X",
    "X..........................X",
    "XXXXXXXXXXXXXXXXXXXXXXXXXXXX",
]

# Characters that are considered solid for movement / collision purposes.
WALL_CHARS = "X#"
DOOR_CHAR = "="
PELLET_CHAR = "."
POWER_CHAR = "o"

# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
TILE = 24                              # pixel size of one maze cell
COLS = len(LAYOUT[0])                  # 28
ROWS = len(LAYOUT)                     # 31
MAZE_WIDTH = COLS * TILE               # 672
MAZE_HEIGHT = ROWS * TILE              # 744

TUNNEL_ROW = 14                        # the row with the wrap-around side tunnels
HUD_TOP = 56                           # space above the maze for the score
HUD_BOTTOM = 64                        # space below the maze for the lives
MAZE_OFFSET_Y = HUD_TOP                # where the maze starts vertically

SCREEN_WIDTH = MAZE_WIDTH
SCREEN_HEIGHT = MAZE_HEIGHT + HUD_TOP + HUD_BOTTOM

FPS = 60
CAPTION = "Pac-Man"

# ---------------------------------------------------------------------------
# Movement directions  (column delta, row delta)
# ---------------------------------------------------------------------------
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
STOP = (0, 0)

# The order ghosts prefer when two routes are equally good (classic tie-break).
DIRECTION_PRIORITY = (UP, LEFT, DOWN, RIGHT)


def opposite(direction):
    """Return the reverse of a direction tuple, e.g. opposite(UP) == DOWN."""
    return (-direction[0], -direction[1])


# ---------------------------------------------------------------------------
# Speeds (pixels per frame at 60 FPS)
# ---------------------------------------------------------------------------
PACMAN_SPEED = 2.0
GHOST_SPEED = 1.9
GHOST_FRIGHT_SPEED = 1.3               # ghosts crawl while frightened
GHOST_EATEN_SPEED = 4.0               # eyes race back home quickly
GHOST_TUNNEL_SPEED = 1.0              # ghosts slow down inside the side tunnel

# ---------------------------------------------------------------------------
# Timing (seconds -> frames helper applied in game.py)
# ---------------------------------------------------------------------------
FRIGHT_SECONDS = 7.0                  # how long a power pellet lasts
FRIGHT_FLASH_SECONDS = 2.0            # ghosts flash during the final stretch
READY_SECONDS = 2.0                   # "READY!" pause before each life
DEATH_SECONDS = 1.6                   # length of Pac-Man's death animation

# Scatter/chase schedule for level 1, as (mode, seconds) pairs. The final
# phase has no duration -> ghosts chase forever once it is reached.
MODE_SCHEDULE = [
    ("scatter", 7),
    ("chase", 20),
    ("scatter", 7),
    ("chase", 20),
    ("scatter", 5),
    ("chase", 20),
    ("scatter", 5),
    ("chase", None),
]

# How long each ghost waits in the house before leaving (seconds).
GHOST_RELEASE = {
    "blinky": 0.0,      # starts outside the house
    "pinky": 1.0,
    "inky": 4.0,
    "clyde": 8.0,
}

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
PELLET_POINTS = 10
POWER_POINTS = 50
GHOST_POINTS = [200, 400, 800, 1600]  # doubles for each ghost in one fright
FRUIT_POINTS = 100
EXTRA_LIFE_SCORE = 10000              # award one bonus life at this score
START_LIVES = 3
FRUIT_TILE = (13, 17)                 # where the bonus fruit appears
FRUIT_AT_PELLETS = (70, 170)          # spawn fruit after N pellets eaten

# ---------------------------------------------------------------------------
# Spawn tiles (column, row)
# ---------------------------------------------------------------------------
PLAYER_START = (13, 23)
BLINKY_START = (13, 11)               # red ghost starts just above the door
PINKY_START = (13, 14)
INKY_START = (11, 14)
CLYDE_START = (16, 14)

HOUSE_EXIT = (13, 11)                 # tile every ghost climbs to when leaving
HOUSE_CENTER = (13, 14)               # tile eaten ghosts return to

# Scatter targets: each ghost flees to "its" corner during scatter mode. The
# tiles intentionally sit outside the maze so ghosts loop around the corner.
BLINKY_SCATTER = (COLS - 3, 0)
PINKY_SCATTER = (2, 0)
INKY_SCATTER = (COLS - 1, ROWS - 1)
CLYDE_SCATTER = (0, ROWS - 1)

# ---------------------------------------------------------------------------
# Colours (R, G, B)
# ---------------------------------------------------------------------------
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
PELLET_COLOR = (255, 203, 164)
WALL_FILL = (8, 8, 56)
WALL_LINE = (40, 64, 222)
DOOR_COLOR = (255, 184, 222)
TEXT_COLOR = (255, 255, 255)
READY_COLOR = (255, 255, 0)
GAMEOVER_COLOR = (255, 60, 60)

# Ghost body colours, keyed by name.
GHOST_COLORS = {
    "blinky": (255, 0, 0),       # red
    "pinky": (255, 184, 255),    # pink
    "inky": (0, 255, 222),       # cyan
    "clyde": (255, 184, 82),     # orange
}
FRIGHT_COLOR = (36, 36, 255)     # frightened ghost body (blue)
FRIGHT_FLASH_COLOR = (255, 255, 255)  # flash colour near the end
FRIGHT_FACE = (255, 255, 255)    # frightened eyes / mouth
EYE_WHITE = (255, 255, 255)
EYE_PUPIL = (33, 33, 180)
FRUIT_COLOR = (255, 40, 40)
FRUIT_STEM = (0, 180, 0)
