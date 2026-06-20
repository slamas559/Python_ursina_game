"""
╔══════════════════════════════════════════════════════════╗
║       NEON HORIZON — Cyberpunk Infinite Racer v2.0       ║
║         Built with Ursina Engine · Python 3.x            ║
╚══════════════════════════════════════════════════════════╝

Controls:
  GARAGE:  ←/→ Arrows to cycle ships  |  ENTER / LAUNCH to start
  GAME:    A/D or ←/→ to steer
           SPACE to fire lasers
           P to pause
           R to restart after Game Over
"""

import random
import os
import sys
import math
from ursina import *


# ─────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────
HIGHSCORE_FILE   = "highscore.txt"
LANE_HALF_WIDTH  = 5.3          # Player horizontal clamp
ROAD_Z_FAR       = 110          # Despawn obstacles behind camera
ROAD_Z_SPAWN     = 95           # Spawn Z for obstacles / pickups
MARKER_SPACING   = 15           # Gap between lane-line pairs
MARKER_COUNT     = 12           # How many marker pairs on the road
TOWER_COUNT      = 14           # Neon city towers in BG
EXHAUST_MAX      = 8            # Max exhaust particles per ship
LASER_COOLDOWN   = 0.33         # seconds between shots  (3/sec max)
ENERGY_MAX       = 100.0        # Full energy bar value
ENERGY_DRAIN     = 4.0          # Energy lost per second passively
ENERGY_PICKUP    = 30.0         # Energy gained per pickup collected
BASE_SPEED       = 35.0         # Starting scroll speed
SPEED_INCREMENT  = 0.35         # Speed gained per obstacle dodged
SCORE_PER_DODGE  = 5

# Ship unlock thresholds (high-score based)
UNLOCK_DREADNOUGHT = 500
UNLOCK_WRAITH      = 1000


# ─────────────────────────────────────────────────────────────────
#  SHIP DEFINITIONS  (pure data – no entities here)
# ─────────────────────────────────────────────────────────────────
SHIP_DEFS = [
    {
        "id":          "interceptor",
        "name":        "THE INTERCEPTOR",
        "tagline":     "Balanced · Speed · Precision",
        "unlock_at":   0,
        "body_color":  color.magenta,
        "wing_color":  color.violet,
        "laser_color": color.yellow,
        "exhaust_col": color.cyan,
        # Body: main hull + two wings
        "parts": [
            # (offset_x, offset_y, offset_z,  sx, sy, sz,  col_key)
            (0,    0,    0,     1.4, 0.35, 2.2,  "body"),
            (-0.85, 0,  -0.3,  0.55, 0.18, 0.9,  "wing"),
            ( 0.85, 0,  -0.3,  0.55, 0.18, 0.9,  "wing"),
            (0,    0.25, 0.8,  0.35, 0.35, 0.8,  "body"),   # nose pod
        ],
        "hitbox_scale": (1.4, 0.45, 2.2),
        "laser_spread": 0.65,
        "laser_fat":    False,
    },
    {
        "id":          "dreadnought",
        "name":        "THE DREADNOUGHT",
        "tagline":     "Heavy · Dual Cannons · Wide",
        "unlock_at":   UNLOCK_DREADNOUGHT,
        "body_color":  color.orange,
        "wing_color":  color.red,
        "laser_color": color.orange,
        "exhaust_col": color.yellow,
        "parts": [
            (0,    0,    0,     2.1, 0.55, 2.0,  "body"),
            (-1.15, 0,  -0.1,  0.5, 0.3,  1.4,  "wing"),
            ( 1.15, 0,  -0.1,  0.5, 0.3,  1.4,  "wing"),
            (-1.4, 0.1,  0.4,  0.22, 0.22, 1.1, "body"),   # L cannon
            ( 1.4, 0.1,  0.4,  0.22, 0.22, 1.1, "body"),   # R cannon
        ],
        "hitbox_scale": (2.1, 0.6, 2.0),
        "laser_spread": 1.2,
        "laser_fat":    True,
    },
    {
        "id":          "wraith",
        "name":        "THE WRAITH",
        "tagline":     "Narrow · Fast · Agile",
        "unlock_at":   UNLOCK_WRAITH,
        "body_color":  color.cyan,
        "wing_color":  color.azure,
        "laser_color": color.white,
        "exhaust_col": color.blue,
        "parts": [
            (0,    0,    0,     0.85, 0.28, 2.6, "body"),
            (-1.3, 0,   -0.5,  1.1, 0.15,  1.1, "wing"),
            ( 1.3, 0,   -0.5,  1.1, 0.15,  1.1, "wing"),
            (0,    0.18, 1.0,  0.25, 0.25,  0.9, "body"),  # blade nose
        ],
        "hitbox_scale": (0.85, 0.35, 2.6),
        "laser_spread": 0.4,
        "laser_fat":    False,
    },
]


# ─────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────
def read_highscore() -> int:
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def write_highscore(score: int):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(score))
    except Exception:
        pass


def destroy_list(lst: list):
    """Destroy every entity in a list and clear it."""
    for e in lst:
        if e is not None:
            destroy(e)
    lst.clear()


# ─────────────────────────────────────────────────────────────────
#  FX MANAGER
# ─────────────────────────────────────────────────────────────────
class FXManager:
    """Handles explosions, screen shake, and exhaust particles."""

    def __init__(self, camera_ref):
        self._cam = camera_ref
        self._shaking = False

    # ── Explosion ────────────────────────────────────────────────
    def explosion(self, position: Vec3, count: int = 14):
        for _ in range(count):
            shard = Entity(
                model    = 'cube',
                color    = random.choice([color.orange, color.yellow, color.red, color.white]),
                position = position + Vec3(random.uniform(-1, 1),
                                           random.uniform(0, 1.5),
                                           random.uniform(-1, 1)),
                scale    = random.uniform(0.15, 0.55),
            )
            target_pos = shard.position + Vec3(
                random.uniform(-3, 3), random.uniform(-1, 3), random.uniform(-2, 2)
            )
            shard.animate_position(target_pos, duration=0.45, curve=curve.linear)
            shard.animate_color(color.clear, duration=0.45)
            destroy(shard, delay=0.5)

        # Central flash
        flash = Entity(model='sphere', color=color.yellow,
                       position=position, scale=0.3)
        flash.animate_scale(3.5, duration=0.22, curve=curve.linear)
        flash.animate_color(color.clear, duration=0.22)
        destroy(flash, delay=0.25)

    # ── Screen Shake ─────────────────────────────────────────────
    def screen_shake(self, magnitude: float = 0.8, duration: float = 0.4):
        if self._shaking:
            return
        self._shaking = True
        original_rot = self._cam.rotation_x
        steps         = 10
        step_t        = duration / steps

        def do_shake(step=0):
            if step >= steps:
                self._cam.rotation_x = original_rot
                self._shaking = False
                return
            offset = random.uniform(-magnitude, magnitude)
            self._cam.rotation_x = original_rot + offset
            invoke(do_shake, delay=step_t, args=[step + 1])

        do_shake()

    # ── Collect sparkle ──────────────────────────────────────────
    def collect_sparkle(self, position: Vec3):
        for _ in range(6):
            sp = Entity(
                model    = 'sphere',
                color    = color.lime,
                position = position + Vec3(random.uniform(-0.4, 0.4),
                                           random.uniform(0, 0.6),
                                           random.uniform(-0.4, 0.4)),
                scale    = 0.18,
            )
            sp.animate_scale(0, duration=0.3)
            sp.animate_color(color.clear, duration=0.3)
            destroy(sp, delay=0.35)


# ─────────────────────────────────────────────────────────────────
#  PLAYER SHIP
# ─────────────────────────────────────────────────────────────────
class PlayerShip:
    """Assembles the chosen ship from primitives and manages laser fire."""

    def __init__(self, ship_def: dict):
        self.defn          = ship_def
        self._laser_timer  = 0.0
        self.entities: list[Entity] = []

        # Root entity carries the collider
        hx, hy, hz = ship_def["hitbox_scale"]
        self.root = Entity(
            model    = 'cube',
            color    = ship_def["body_color"],
            scale    = Vec3(hx, hy, hz),
            position = Vec3(0, 0.3, -3),
            collider = 'box',
        )
        self.entities.append(self.root)

        # Attach cosmetic parts
        for (ox, oy, oz, sx, sy, sz, col_key) in ship_def["parts"][1:]:
            col = ship_def["body_color"] if col_key == "body" else ship_def["wing_color"]
            part = Entity(
                parent   = self.root,
                model    = 'cube',
                color    = col,
                scale    = Vec3(sx / hx, sy / hy, sz / hz),
                position = Vec3(ox / hx, oy / hy, oz / hz),
            )
            self.entities.append(part)

        # Exhaust particle pool
        self._exhaust: list[Entity] = []
        for _ in range(EXHAUST_MAX):
            ex = Entity(
                model    = 'sphere',
                color    = ship_def["exhaust_col"],
                scale    = 0.0,
                position = self.root.position,
            )
            self._exhaust.append(ex)
        self._ex_idx = 0

    # ── Position property proxy ───────────────────────────────────
    @property
    def x(self): return self.root.x
    @x.setter
    def x(self, v): self.root.x = v

    @property
    def z(self): return self.root.z
    @z.setter
    def z(self, v): self.root.z = v

    @property
    def position(self): return self.root.position

    # ── Exhaust tick ─────────────────────────────────────────────
    def update_exhaust(self, dt: float):
        ex = self._exhaust[self._ex_idx % EXHAUST_MAX]
        self._ex_idx += 1
        col  = self.defn["exhaust_col"]
        ex.position = self.root.position + Vec3(
            random.uniform(-0.3, 0.3), -0.1, -1.1
        )
        ex.scale  = random.uniform(0.2, 0.45)
        ex.color  = col
        ex.animate_scale(0, duration=0.35, curve=curve.linear)
        ex.animate_color(color.clear, duration=0.35)

    # ── Laser ready? ─────────────────────────────────────────────
    def can_fire(self) -> bool:
        return self._laser_timer <= 0.0

    def tick_cooldown(self, dt: float):
        if self._laser_timer > 0:
            self._laser_timer -= dt

    def fire(self) -> list[Entity]:
        """Spawn and return laser entities. Caller owns their lifecycle."""
        if not self.can_fire():
            return []
        self._laser_timer = LASER_COOLDOWN

        spread = self.defn["laser_spread"]
        fat    = self.defn["laser_fat"]
        lc     = self.defn["laser_color"]
        lw     = 0.28 if fat else 0.14
        lh     = 0.28 if fat else 0.14

        laser_l = Entity(
            model    = 'cube',
            color    = lc,
            scale    = Vec3(lw, lh, 2.8),
            position = Vec3(self.root.x - spread, 0.35, self.root.z + 1.6),
            collider = 'box',
        )
        laser_r = Entity(
            model    = 'cube',
            color    = lc,
            scale    = Vec3(lw, lh, 2.8),
            position = Vec3(self.root.x + spread, 0.35, self.root.z + 1.6),
            collider = 'box',
        )
        # Recoil nudge
        self.root.z -= 0.12
        self.root.animate_z(-3, duration=0.08)

        return [laser_l, laser_r]

    # ── Intersects pass-through ───────────────────────────────────
    def intersects(self, other: Entity):
        return self.root.intersects(other)

    # ── Cleanup ───────────────────────────────────────────────────
    def destroy(self):
        destroy_list(self._exhaust)
        destroy_list(self.entities)


# ─────────────────────────────────────────────────────────────────
#  OBSTACLE MANAGER
# ─────────────────────────────────────────────────────────────────
class ObstacleManager:
    """Spawns, moves, and despawns obstacles and energy pickups."""

    def __init__(self):
        self.obstacles: list[dict] = []   # {entity, type, sweep_dir}
        self.pickups:   list[Entity] = []
        self._spawn_timer   = 0.0
        self._pickup_timer  = 0.0

    # ── Spawn one obstacle ───────────────────────────────────────
    def _spawn_obstacle(self, speed: float):
        rx = random.uniform(-4.2, 4.2)
        rw = random.uniform(1.1, 2.8)
        rh = random.uniform(0.9, 2.0)
        obs_type = random.choice(["static", "static", "patrol"])  # 1/3 patrol
        col = color.orange if obs_type == "static" else color.red

        ent = Entity(
            model    = 'cube',
            color    = col,
            scale    = Vec3(rw, rh, 1.4),
            position = Vec3(rx, rh * 0.5, ROAD_Z_SPAWN),
            collider = 'box',
        )
        sweep = random.choice([-1, 1]) * random.uniform(2.5, 5.0)
        self.obstacles.append({"entity": ent, "type": obs_type, "sweep": sweep})

    # ── Spawn one energy pickup ──────────────────────────────────
    def _spawn_pickup(self):
        rx = random.uniform(-4.0, 4.0)
        pu = Entity(
            model    = 'sphere',
            color    = color.lime,
            scale    = 0.55,
            position = Vec3(rx, 0.55, ROAD_Z_SPAWN),
            collider = 'sphere',
        )
        pu.animate_scale(0.65, duration=0.5, loop=True)
        self.pickups.append(pu)

    # ── Per-frame update ─────────────────────────────────────────
    def update(self, dt: float, speed: float):
        # Spawn timers
        self._spawn_timer -= dt
        if self._spawn_timer <= 0:
            self._spawn_obstacle(speed)
            self._spawn_timer = max(0.28, random.uniform(0.45, 1.0) - speed * 0.002)

        self._pickup_timer -= dt
        if self._pickup_timer <= 0:
            self._spawn_pickup()
            self._pickup_timer = random.uniform(3.0, 6.5)

        # Move obstacles
        for rec in self.obstacles:
            ent = rec["entity"]
            ent.z -= speed * dt
            if rec["type"] == "patrol":
                ent.x += rec["sweep"] * dt
                # Reverse at road edges
                if abs(ent.x) > 5.5:
                    rec["sweep"] *= -1

        # Move pickups
        for pu in self.pickups:
            pu.z -= speed * dt

    # ── Returns list of obstacles that went off-screen ────────────
    def collect_escaped(self) -> list[Entity]:
        escaped = [r["entity"] for r in self.obstacles if r["entity"].z < -10]
        self.obstacles = [r for r in self.obstacles if r["entity"].z >= -10]
        return escaped

    # ── Returns pickup entities hit by a given position/entity ────
    def collect_pickups_hit(self, player_ship: PlayerShip) -> list[Entity]:
        hit = [pu for pu in self.pickups if player_ship.intersects(pu).hit]
        self.pickups = [pu for pu in self.pickups if pu not in hit]
        return hit

    # ── Returns list of (entity, did_laser_hit) ───────────────────
    def check_laser_hits(self, lasers: list[Entity]) -> list[Entity]:
        """Return obstacles that were hit by any laser."""
        hit_obs = []
        for rec in list(self.obstacles):
            ent = rec["entity"]
            for laser in lasers:
                if laser.intersects(ent).hit:
                    if ent not in hit_obs:
                        hit_obs.append(ent)
        # Remove hit ones from internal list
        self.obstacles = [r for r in self.obstacles if r["entity"] not in hit_obs]
        return hit_obs

    # ── Full reset ────────────────────────────────────────────────
    def reset(self):
        for rec in self.obstacles:
            destroy(rec["entity"])
        self.obstacles.clear()
        destroy_list(self.pickups)
        self._spawn_timer  = 0.0
        self._pickup_timer = 0.0


# ─────────────────────────────────────────────────────────────────
#  ENVIRONMENT
# ─────────────────────────────────────────────────────────────────
class Environment:
    """Builds and scrolls the highway, lane markers, and BG towers."""

    def __init__(self):
        self._entities: list[Entity] = []
        self._markers:  list[Entity] = []
        self._towers:   list[Entity] = []
        self._build()

    def _build(self):
        # Highway deck
        hw = Entity(model='cube', scale=(14, 0.1, 200, 1),
                    color=color.black, position=(0, 0, 70))
        self._entities.append(hw)

        # Glowing cyan border rails
        for side in (-1, 1):
            b = Entity(model='cube', scale=(0.3, 0.9, 200, 1),
                       color=color.cyan, position=(side * 7, 0.45, 70))
            self._entities.append(b)

        # Neon lane dividers (scrolling)
        for i in range(MARKER_COUNT):
            z = i * MARKER_SPACING
            for lx in (-2.3, 2.3):
                m = Entity(model='cube', scale=(0.14, 0.1, 3.8, 1),
                           color=color.lime, position=(lx, 0.06, z))
                self._markers.append(m)

        # Background neon city towers
        tower_cols = [color.cyan, color.magenta, color.violet,
                      color.azure, color.orange]
        for i in range(TOWER_COUNT):
            side = 1 if i % 2 == 0 else -1
            tx   = side * random.uniform(9, 22)
            tz   = random.uniform(20, 110)
            th   = random.uniform(8, 28)
            tw   = random.uniform(1.5, 4.0)
            t_col = random.choice(tower_cols)

            tower = Entity(model='cube', color=t_col,
                           scale=(tw, th, tw),
                           position=(tx, th / 2, tz))
            self._towers.append(tower)

            # Window accent strip
            win = Entity(model='cube', color=color.white,
                         scale=(tw * 0.6, th * 0.08, tw * 0.6),
                         position=(tx, th * 0.75, tz))
            self._towers.append(win)

        # Dark sky backdrop
        sky = Entity(model='cube', color=Color(0.04, 0.0, 0.08, 1),
                     scale=(300, 80, 5), position=(0, 38, 115))
        self._entities.append(sky)

        # Grid-floor far horizon strips
        for gi in range(0, 12):
            strip = Entity(model='cube', color=Color(0.1, 0.0, 0.2, 1),
                           scale=(14, 0.02, 0.3),
                           position=(0, 0.02, 30 + gi * 8))
            self._entities.append(strip)

    def update(self, dt: float, speed: float):
        # Scroll lane markers and loop them
        for m in self._markers:
            m.z -= speed * dt
            if m.z < -5:
                m.z += MARKER_COUNT * MARKER_SPACING

        # Scroll towers slowly (parallax)
        for t in self._towers:
            t.z -= speed * 0.18 * dt
            if t.z < -20:
                t.z += 135

    def destroy(self):
        destroy_list(self._entities)
        destroy_list(self._markers)
        destroy_list(self._towers)


# ─────────────────────────────────────────────────────────────────
#  UI MANAGER
# ─────────────────────────────────────────────────────────────────
class UIManager:
    """Manages all HUD elements for the PLAYING state."""

    def __init__(self):
        # Score panel
        self._score_bg = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = Color(0, 0.05, 0.12, 0.72),
            scale    = (0.32, 0.1),
            position = (-0.72, 0.42),
        )
        self.score_text = Text(
            parent   = self._score_bg,
            text     = 'SCORE: 0',
            scale    = 1.4,
            origin   = (0, 0),
            color    = color.cyan,
        )

        # Speed panel
        self._speed_bg = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = Color(0, 0.05, 0.12, 0.72),
            scale    = (0.28, 0.1),
            position = (0.71, 0.42),
        )
        self.speed_text = Text(
            parent   = self._speed_bg,
            text     = '0 MPH',
            scale    = 1.4,
            origin   = (0, 0),
            color    = color.magenta,
        )

        # Energy bar background
        self._energy_bg = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = Color(0, 0, 0, 0.65),
            scale    = (0.55, 0.055),
            position = (0, 0.43),
        )
        # Energy fill
        self._energy_fill = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = color.lime,
            scale    = (0.53, 0.038),
            position = (0, 0.43),
            origin   = (-0.5, 0),
        )
        self._energy_label = Text(
            parent   = self._energy_bg,
            text     = 'ENERGY',
            scale    = 0.9,
            origin   = (0, 2.8),
            color    = color.white,
        )

        # Controls strip
        self._ctrl = Text(
            text     = "[A/D] Move  |  [SPACE] Fire  |  [P] Pause",
            position = (0, -0.46),
            scale    = 1.1,
            origin   = (0, 0),
            color    = color.light_gray,
        )

        # Pause overlay (hidden by default)
        self._pause_overlay = Entity(
            parent   = camera.ui,
            model    = 'quad',
            color    = Color(0, 0, 0.08, 0.75),
            scale    = (2, 2),
            enabled  = False,
        )
        self._pause_text = Text(
            parent   = self._pause_overlay,
            text     = '— PAUSED —\nPress P to Resume',
            scale    = 2.2,
            origin   = (0, 0),
            color    = color.cyan,
            enabled  = False,
        )

        self._elements = [
            self._score_bg, self._speed_bg, self._energy_bg,
            self._energy_fill, self._ctrl, self._pause_overlay, self._pause_text
        ]

    def update_score(self, score: int):
        self.score_text.text = f'SCORE: {score}'

    def update_speed(self, speed: float):
        mph = int((speed - BASE_SPEED) * 3.2 + 80)
        self.speed_text.text = f'{mph} MPH'

    def update_energy(self, energy: float):
        pct = max(0.0, energy / ENERGY_MAX)
        # Shrink fill bar left→right
        self._energy_fill.scale_x = 0.53 * pct
        if pct > 0.5:
            self._energy_fill.color = color.lime
        elif pct > 0.25:
            self._energy_fill.color = color.yellow
        else:
            self._energy_fill.color = color.red

    def show_pause(self, visible: bool):
        self._pause_overlay.enabled = visible
        self._pause_text.enabled    = visible

    def destroy(self):
        for e in self._elements:
            destroy(e)
        # Text entities parented to camera.ui need explicit removal
        for t in [self.score_text, self.speed_text, self._energy_label,
                  self._ctrl, self._pause_text]:
            destroy(t)


# ─────────────────────────────────────────────────────────────────
#  GARAGE MENU
# ─────────────────────────────────────────────────────────────────
class GarageMenu:
    """3D garage ship-selection screen."""

    def __init__(self, highscore: int, on_launch):
        self._on_launch   = on_launch
        self._highscore   = highscore
        self._sel_idx     = 0
        self._preview_ents: list[Entity] = []
        self._ui_ents:      list[Entity] = []
        self._spin_angle    = 0.0
        self._active        = True

        self._build_ui()
        self._build_preview()

    # ── Static UI ────────────────────────────────────────────────
    def _build_ui(self):
        hs = self._highscore

        # Dark backdrop
        bg = Entity(parent=camera.ui, model='quad',
                    color=Color(0, 0, 0.06, 1), scale=(2, 2))
        self._ui_ents.append(bg)

        # Title
        title = Text(
            text     = "NEON HORIZON",
            position = (0, 0.41),
            scale    = 4.2,
            origin   = (0, 0),
            color    = color.cyan,
        )
        sub = Text(
            text     = "SELECT YOUR SHIP",
            position = (0, 0.32),
            scale    = 1.8,
            origin   = (0, 0),
            color    = color.magenta,
        )
        hs_txt = Text(
            text     = f"LOCAL BEST: {hs}",
            position = (0, 0.24),
            scale    = 1.3,
            origin   = (0, 0),
            color    = color.yellow,
        )
        ctrl_txt = Text(
            text     = "[ ← / → ] Browse   [ ENTER ] Launch",
            position = (0, -0.43),
            scale    = 1.3,
            origin   = (0, 0),
            color    = color.light_gray,
        )

        # Ship name plate
        self._name_text = Text(
            text     = "",
            position = (0, -0.08),
            scale    = 2.5,
            origin   = (0, 0),
            color    = color.white,
        )
        self._tag_text = Text(
            text     = "",
            position = (0, -0.18),
            scale    = 1.3,
            origin   = (0, 0),
            color    = color.light_gray,
        )
        self._lock_text = Text(
            text     = "",
            position = (0, -0.27),
            scale    = 1.2,
            origin   = (0, 0),
            color    = color.orange,
        )

        extra = [title, sub, hs_txt, ctrl_txt,
                 self._name_text, self._tag_text, self._lock_text]
        self._ui_ents.extend(extra)

        self._refresh_labels()

    def _refresh_labels(self):
        defn = SHIP_DEFS[self._sel_idx]
        locked = self._highscore < defn["unlock_at"]
        self._name_text.text = defn["name"]
        self._tag_text.text  = defn["tagline"]
        if locked:
            self._lock_text.text = f"LOCKED — reach {defn['unlock_at']} pts"
            self._lock_text.color = color.orange
        else:
            self._lock_text.text  = "[ READY TO LAUNCH ]"
            self._lock_text.color = color.lime

    # ── 3D Preview ───────────────────────────────────────────────
    def _build_preview(self):
        destroy_list(self._preview_ents)
        defn = SHIP_DEFS[self._sel_idx]
        hx, hy, hz = defn["hitbox_scale"]

        root_pos = Vec3(0, 1.8, 12)

        # Build preview parts
        body = Entity(
            model    = 'cube',
            color    = defn["body_color"],
            scale    = Vec3(hx, hy, hz) * 1.6,
            position = root_pos,
        )
        self._preview_ents.append(body)

        for (ox, oy, oz, sx, sy, sz, col_key) in defn["parts"][1:]:
            col = defn["body_color"] if col_key == "body" else defn["wing_color"]
            part = Entity(
                parent   = body,
                model    = 'cube',
                color    = col,
                scale    = Vec3(sx / hx, sy / hy, sz / hz),
                position = Vec3(ox / hx, oy / hy, oz / hz),
            )
            self._preview_ents.append(part)

        # Glow platform under ship
        plat = Entity(model='cube', color=Color(0.1, 0.1, 0.3, 1),
                      scale=(4, 0.08, 4), position=root_pos + Vec3(0, -hy * 0.8, 0))
        self._preview_ents.append(plat)

        self._preview_root = body

    # ── Update (spin preview) ────────────────────────────────────
    def update(self, dt: float):
        if not self._active:
            return
        self._spin_angle += dt * 55
        if self._preview_root:
            self._preview_root.rotation_y = self._spin_angle

    # ── Input ─────────────────────────────────────────────────────
    def handle_key(self, key: str) -> bool:
        """Return True if garage consumed the key and launched."""
        if not self._active:
            return False
        if key in ('left arrow', 'a'):
            self._sel_idx = (self._sel_idx - 1) % len(SHIP_DEFS)
            self._build_preview()
            self._refresh_labels()
            return True
        if key in ('right arrow', 'd'):
            self._sel_idx = (self._sel_idx + 1) % len(SHIP_DEFS)
            self._build_preview()
            self._refresh_labels()
            return True
        if key in ('enter', 'return'):
            defn   = SHIP_DEFS[self._sel_idx]
            locked = self._highscore < defn["unlock_at"]
            if locked:
                self._lock_text.text  = "NOT UNLOCKED YET!"
                self._lock_text.color = color.red
                return True
            self._active = False
            self.destroy()
            self._on_launch(self._sel_idx)
            return True
        return False

    # ── Cleanup ───────────────────────────────────────────────────
    def destroy(self):
        destroy_list(self._preview_ents)
        for e in self._ui_ents:
            destroy(e)
        self._ui_ents.clear()


# ─────────────────────────────────────────────────────────────────
#  GAME OVER SCREEN
# ─────────────────────────────────────────────────────────────────
class GameOverScreen:
    def __init__(self, score: int, highscore: int):
        self._ents: list[Entity] = []

        overlay = Entity(parent=camera.ui, model='quad',
                         color=Color(0, 0, 0, 0.78), scale=(2, 2))
        self._ents.append(overlay)

        crash = Text(text='CRASH SYSTEM ERROR', position=(0, 0.2),
                     scale=4.0, origin=(0, 0), color=color.red)
        score_t = Text(text=f'SCORE: {score}', position=(0, 0.04),
                       scale=2.5, origin=(0, 0), color=color.white)
        best_t = Text(text=f'LOCAL BEST: {highscore}',
                      position=(0, -0.08), scale=2.0,
                      origin=(0, 0), color=color.yellow)
        hint = Text(text='[ R ] Restart  |  [ G ] Garage',
                    position=(0, -0.22), scale=1.5,
                    origin=(0, 0), color=color.light_gray)

        self._ents.extend([crash, score_t, best_t, hint])

    def destroy(self):
        destroy_list(self._ents)


# ─────────────────────────────────────────────────────────────────
#  GAME MANAGER  (state machine)
# ─────────────────────────────────────────────────────────────────
class GameManager:
    """
    State machine:
      GARAGE_MENU → PLAYING → PAUSED → PLAYING
                            → GAME_OVER → GARAGE_MENU / PLAYING
    """

    STATE_GARAGE    = "GARAGE_MENU"
    STATE_PLAYING   = "PLAYING"
    STATE_PAUSED    = "PAUSED"
    STATE_GAME_OVER = "GAME_OVER"

    def __init__(self):
        self._state         = None
        self._highscore     = read_highscore()

        # Sub-systems (created/destroyed per state)
        self._garage:    GarageMenu      = None
        self._env:       Environment     = None
        self._ship:      PlayerShip      = None
        self._obs_mgr:   ObstacleManager = None
        self._ui:        UIManager       = None
        self._fx:        FXManager       = None
        self._game_over_screen: GameOverScreen = None

        # Game session vars
        self._score      = 0
        self._speed      = BASE_SPEED
        self._energy     = ENERGY_MAX
        self._paused     = False
        self._lasers:    list[Entity] = []
        self._ship_idx   = 0

        # Setup camera and lighting
        DirectionalLight(y=10, z=-10, rotation=(45, -45, 0))
        AmbientLight(color=color.dark_gray)
        camera.position    = Vec3(0, 4, -15)
        camera.rotation_x  = 12

        # FX is always alive (camera ref is stable)
        self._fx = FXManager(camera)

        # Start in garage
        self._enter_garage()

    # ── State transitions ─────────────────────────────────────────

    def _enter_garage(self):
        # Tear down playing state if coming from game
        self._teardown_game()
        self._state  = self.STATE_GARAGE
        self._garage = GarageMenu(
            highscore  = self._highscore,
            on_launch  = self._on_garage_launch,
        )

    def _on_garage_launch(self, ship_idx: int):
        self._ship_idx = ship_idx
        self._enter_playing()

    def _enter_playing(self):
        self._state   = self.STATE_PLAYING
        self._score   = 0
        self._speed   = BASE_SPEED
        self._energy  = ENERGY_MAX

        self._env     = Environment()
        self._obs_mgr = ObstacleManager()
        self._ui      = UIManager()
        self._ship    = PlayerShip(SHIP_DEFS[self._ship_idx])

        self._lasers.clear()

    def _enter_pause(self):
        if self._state != self.STATE_PLAYING:
            return
        self._state = self.STATE_PAUSED
        self._ui.show_pause(True)

    def _resume(self):
        if self._state != self.STATE_PAUSED:
            return
        self._state = self.STATE_PLAYING
        self._ui.show_pause(False)

    def _enter_game_over(self):
        self._state = self.STATE_GAME_OVER

        # Check / update high score
        if self._score > self._highscore:
            self._highscore = self._score
            write_highscore(self._highscore)

        # Show game over overlay (keep env/ship visible underneath)
        self._game_over_screen = GameOverScreen(self._score, self._highscore)

    def _teardown_game(self):
        if self._game_over_screen:
            self._game_over_screen.destroy()
            self._game_over_screen = None
        if self._ui:
            self._ui.destroy()
            self._ui = None
        if self._ship:
            self._ship.destroy()
            self._ship = None
        if self._obs_mgr:
            self._obs_mgr.reset()
            self._obs_mgr = None
        if self._env:
            self._env.destroy()
            self._env = None
        destroy_list(self._lasers)

    # ── Input ─────────────────────────────────────────────────────
    def handle_input(self, key: str):
        # Garage captures its own keys
        if self._state == self.STATE_GARAGE:
            self._garage.handle_key(key)
            return

        if self._state in (self.STATE_PLAYING, self.STATE_PAUSED):
            if key == 'p':
                if self._state == self.STATE_PLAYING:
                    self._enter_pause()
                else:
                    self._resume()
                return

        if self._state == self.STATE_PLAYING:
            if key == 'space':
                new_lasers = self._ship.fire()
                self._lasers.extend(new_lasers)
            return

        if self._state == self.STATE_GAME_OVER:
            if key == 'r':
                if self._game_over_screen:
                    self._game_over_screen.destroy()
                    self._game_over_screen = None
                self._enter_playing()
            elif key == 'g':
                self._enter_garage()
            return

    # ── Frame update ─────────────────────────────────────────────
    def update(self, dt: float):
        if self._state == self.STATE_GARAGE:
            self._garage.update(dt)
            return

        if self._state == self.STATE_PAUSED:
            return

        if self._state != self.STATE_PLAYING:
            return

        # ── Player movement ───────────────────────────────────────
        if held_keys['a'] or held_keys['left arrow']:
            self._ship.x -= 18 * dt
        if held_keys['d'] or held_keys['right arrow']:
            self._ship.x += 18 * dt
        self._ship.x = clamp(self._ship.x, -LANE_HALF_WIDTH, LANE_HALF_WIDTH)

        # Laser cooldown tick
        self._ship.tick_cooldown(dt)

        # ── Exhaust ───────────────────────────────────────────────
        self._ship.update_exhaust(dt)

        # ── Scroll environment ────────────────────────────────────
        self._env.update(dt, self._speed)

        # ── Obstacle & pickup update ──────────────────────────────
        self._obs_mgr.update(dt, self._speed)

        # ── Laser movement ────────────────────────────────────────
        for laser in list(self._lasers):
            laser.z += 80 * dt

        # ── Laser vs obstacle collision ───────────────────────────
        hit_obs = self._obs_mgr.check_laser_hits(self._lasers)
        for obs_ent in hit_obs:
            self._fx.explosion(obs_ent.position)
            destroy(obs_ent)
            self._score += 10
            self._speed  = min(self._speed + SPEED_INCREMENT * 0.5, 120)

        # Clean up lasers gone off-screen
        for laser in list(self._lasers):
            if laser.z > ROAD_Z_SPAWN + 10:
                self._lasers.remove(laser)
                destroy(laser)

        # ── Pickup collection ─────────────────────────────────────
        hit_pickups = self._obs_mgr.collect_pickups_hit(self._ship)
        for pu in hit_pickups:
            self._fx.collect_sparkle(pu.position)
            self._energy = min(ENERGY_MAX, self._energy + ENERGY_PICKUP)
            destroy(pu)

        # ── Player vs obstacle ────────────────────────────────────
        for rec in self._obs_mgr.obstacles:
            if self._ship.intersects(rec["entity"]).hit:
                self._fx.explosion(self._ship.position)
                self._fx.screen_shake(magnitude=1.2, duration=0.5)
                self._enter_game_over()
                return

        # ── Dodge scoring ─────────────────────────────────────────
        escaped = self._obs_mgr.collect_escaped()
        for ent in escaped:
            destroy(ent)
            self._score += SCORE_PER_DODGE
            self._speed  = min(self._speed + SPEED_INCREMENT, 120)

        # ── Energy drain ──────────────────────────────────────────
        self._energy -= ENERGY_DRAIN * dt
        if self._energy <= 0:
            self._energy = 0
            self._enter_game_over()
            return

        # ── HUD updates ───────────────────────────────────────────
        self._ui.update_score(self._score)
        self._ui.update_speed(self._speed)
        self._ui.update_energy(self._energy)


# ─────────────────────────────────────────────────────────────────
#  APPLICATION BOOTSTRAP
# ─────────────────────────────────────────────────────────────────
app = Ursina(title="Neon Horizon", borderless=False)
window.color = Color(0.02, 0.0, 0.06, 1)
window.exit_button.visible = False

gm = GameManager()


def update():
    gm.update(time.dt)


def input(key):
    if key == 'escape':
        application.quit()
    gm.handle_input(key)


app.run()