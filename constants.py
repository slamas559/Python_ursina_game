"""
constants.py — Centralised tuning values & neon palette.
Every magic number in the game lives here.
"""

from ursina import color, Vec3

# ── Game States ──────────────────────────────────────────────────────────────
STATE_GARAGE   = 'GARAGE_MENU'
STATE_PLAYING  = 'PLAYING'
STATE_PAUSED   = 'PAUSED'
STATE_GAMEOVER = 'GAME_OVER'

# ── Neon Palette ─────────────────────────────────────────────────────────────
COL_MAGENTA   = color.Color(1.0,  0.0,  0.9,  1)
COL_VIOLET    = color.Color(0.55, 0.0,  1.0,  1)
COL_CYAN      = color.Color(0.0,  1.0,  1.0,  1)
COL_ORANGE    = color.Color(1.0,  0.4,  0.0,  1)
COL_RED_HOT   = color.Color(1.0,  0.1,  0.1,  1)
COL_LIME      = color.Color(0.2,  1.0,  0.2,  1)
COL_YELLOW    = color.Color(1.0,  0.95, 0.0,  1)
COL_DEEP_BLUE = color.Color(0.0,  0.1,  0.55, 1)
COL_ROAD_GREY = color.Color(0.05, 0.05, 0.08, 1)
COL_UI_BG     = color.Color(0.0,  0.0,  0.0,  0.72)
COL_WHITE     = color.white
COL_CLEAR     = color.clear
COL_GREEN_ORB = color.Color(0.0,  1.0,  0.35, 1)

# ── Highway ──────────────────────────────────────────────────────────────────
ROAD_WIDTH     = 14
ROAD_HALF_W    = ROAD_WIDTH / 2          # 7
ROAD_LENGTH    = 240
PLAYER_CLAMP_X = 5.3                    # Left/right travel limit
LANE_POSITIONS = [-4.6, 0.0, 4.6]       # Three lanes (left, centre, right)
SPAWN_Z        = 120                    # Where obstacles/orbs appear
DESPAWN_Z      = -12                    # Where they are destroyed

# ── Player ───────────────────────────────────────────────────────────────────
PLAYER_START_POS = Vec3(0, 0.3, -5)
PLAYER_SPEED     = 18                   # Lateral move speed (units/s)
FIRE_COOLDOWN    = 0.33                 # Seconds between shots (~3/s)
LASER_SPEED      = 80                   # Forward speed of laser bolt
LASER_LIFETIME   = 2.5                  # Seconds before laser auto-destroys

# ── Physics / Progression ────────────────────────────────────────────────────
INITIAL_SPEED      = 32
SPEED_INCREMENT    = 0.45               # Per dodged obstacle
MAX_SPEED          = 90
SCORE_PER_DODGE    = 5
SCORE_PER_KILL     = 10
SPEEDOMETER_FACTOR = 2.2                # Virtual MPH = game_speed * factor

# ── Energy / Shield ──────────────────────────────────────────────────────────
MAX_ENERGY          = 100.0
ENERGY_DRAIN_RATE   = 3.0              # Per second while playing
ENERGY_ORB_VALUE    = 22.0
ENERGY_HIT_PENALTY  = 30.0

# ── Obstacle Spawn ───────────────────────────────────────────────────────────
OBS_SPAWN_MIN_DELAY = 0.28
OBS_SPAWN_BASE      = 0.9
OBS_PATROL_SPEED    = 4.5              # Type-B sweep speed

# ── Unlock Thresholds ────────────────────────────────────────────────────────
DREADNOUGHT_UNLOCK = 500
WRAITH_UNLOCK      = 1000

# ── High-score file path ──────────────────────────────────────────────────────
HIGHSCORE_FILE = 'highscore.txt'
