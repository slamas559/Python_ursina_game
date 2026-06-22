"""
managers/fx_manager.py
Owns all environmental entities:
  • Highway deck + glowing borders
  • Scrolling neon lane markers
  • Distant synthwave skybox towers
  • Explosion / debris FX
  • Screen-shake helper
"""

import random
from ursina import (
    Entity, Vec3, color, time, camera,
    destroy, curve, DirectionalLight, AmbientLight, PointLight
)
from constants import (
    COL_CYAN, COL_WHITE, COL_LIME, COL_ROAD_GREY, COL_MAGENTA, COL_YELLOW,
    COL_VIOLET, COL_ORANGE,
    ROAD_LENGTH, SPAWN_Z, DESPAWN_Z,
)


class FXManager:
    """Handles environmental creation and per-frame scrolling."""

    def __init__(self):
        self._road_markers  = []
        self._bg_towers     = []
        self._shake_timer   = 0.0
        self._shake_mag     = 0.0
        self._cam_base_pos  = None   # Set from GameManager after camera is placed

        self._build_lights()
        self._build_highway()
        self._build_lane_markers()
        self._build_skybox_towers()

    # ─────────────────────────────────────────────────────────────────────────
    def _build_lights(self):
        DirectionalLight(y=12, z=-10, rotation=(38, -45, 0))
        AmbientLight(color=color.Color(0.12, 0.0, 0.25, 1))
        # Subtle magenta point light near player spawn
        pl = PointLight(position=Vec3(0, 3, -5))
        pl.color = color.Color(1.0, 0.0, 0.85, 1)

    def _build_highway(self):
        # Main deck
        Entity(
            model='cube',
            color=COL_ROAD_GREY,
            scale=Vec3(14, 0.1, ROAD_LENGTH),
            position=Vec3(0, 0, ROAD_LENGTH / 2 - 15),
        )

        # Glowing side rails
        for sx, col_ in [(-7, COL_CYAN), (7, COL_CYAN)]:
            Entity(
                model='cube',
                color=col_,
                scale=Vec3(0.25, 1.0, ROAD_LENGTH),
                position=Vec3(sx, 0.45, ROAD_LENGTH / 2 - 15),
            )
            
        # Dotted centre line (static, just cosmetic)
        for z in range(-10, ROAD_LENGTH, 12):
            Entity(
                model='cube',
                color=color.Color(0.3, 0.3, 0.4, 1),
                scale=Vec3(0.12, 0.06, 3.5),
                position=Vec3(0, 0.06, z),
            )

    def _build_lane_markers(self):
        spacing = 14
        for z in range(-5, 110, spacing):
            for lx in [-2.5, 2.5]:
                m = Entity(
                    model='cube',
                    color=COL_LIME,
                    scale=Vec3(0.12, 0.07, 4.5),
                    position=Vec3(lx, 0.07, z),
                )
                self._road_markers.append(m)

    def _build_skybox_towers(self):
        """Distant neon tower columns on either side for depth."""
        tower_configs = [
            (-12, 0, 60),  (-18, 0, 80),  (-14, 0, 100),
            (-20, 0, 130), (-11, 0, 155), (-17, 0, 175),
            (12, 0, 60),   (18, 0, 80),   (14, 0, 100),
            (20, 0, 130),  (11, 0, 155),  (17, 0, 175),
        ]
        tower_colors = [COL_MAGENTA, COL_WHITE, COL_VIOLET, COL_ORANGE]
        for (tx, ty, tz) in tower_configs:
            h = random.uniform(6, 18)
            col = random.choice(tower_colors)
            # Main tower block
            Entity(
                model='cube',
                color=color.Color(col.r * 0.15, col.g * 0.15, col.b * 0.15, 1),
                scale=Vec3(random.uniform(1.5, 3.5), h, random.uniform(1.5, 3.5)),
                position=Vec3(tx, h / 2, tz),
            )
            # Glowing top stripe
            Entity(
                model='cube',
                color=col,
                scale=Vec3(random.uniform(1.5, 3.5) + 0.1, 0.25, random.uniform(1.5, 3.5) + 0.1),
                position=Vec3(tx, h, tz),
            )

    # ─────────────────────────────────────────────────────────────────────────
    def update(self, game_speed: float, cam_base_pos: Vec3):
        dt = time.dt

        # Scroll lane markers
        for m in self._road_markers:
            m.z -= game_speed * dt
            if m.z < DESPAWN_Z:
                m.z += (len(self._road_markers) // 2) * 14

        # Screen shake
        if self._shake_timer > 0:
            self._shake_timer -= dt
            mag = self._shake_mag * (self._shake_timer / 0.45)
            import random as _r
            camera.position = cam_base_pos + Vec3(
                _r.uniform(-mag, mag),
                _r.uniform(-mag * 0.4, mag * 0.4),
                0,
            )
        else:
            camera.position = cam_base_pos

    # ─────────────────────────────────────────────────────────────────────────
    def trigger_screen_shake(self, magnitude: float = 0.4, duration: float = 0.45):
        self._shake_timer = duration
        self._shake_mag   = magnitude

    def trigger_explosion(self, position: Vec3):
        """Spawn a burst of debris particles at *position*."""
        for _ in range(12):
            offset = Vec3(
                random.uniform(-1.2, 1.2),
                random.uniform(0.0, 1.5),
                random.uniform(-0.8, 0.8),
            )
            debris = Entity(
                model='cube',
                color=random.choice([COL_ORANGE, COL_YELLOW, color.white]),
                scale=random.uniform(0.08, 0.28),
                position=position + offset,
            )
            # Animate outward and fade
            debris.animate_position(
                position + offset * 3.5,
                duration=random.uniform(0.3, 0.55),
                curve=curve.linear,
            )
            debris.animate_color(color.Color(1, 0.5, 0, 0), duration=0.5)
            destroy(debris, delay=0.55)

        # Central flash sphere
        flash = Entity(model='sphere', color=COL_YELLOW, position=position, scale=0.3)
        flash.animate_scale(3.5, duration=0.2, curve=curve.linear)
        flash.animate_color(color.Color(1, 1, 0, 0), duration=0.25)
        destroy(flash, delay=0.28)
