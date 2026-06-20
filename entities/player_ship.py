"""
entities/player_ship.py
Defines the three selectable ships and manages their parts, trail, and firing.
"""

import random
from ursina import (
    Entity, Vec3, color, time, destroy,
    curve, clamp, invoke
)
from constants import (
    COL_MAGENTA, COL_VIOLET, COL_CYAN, COL_ORANGE, COL_RED_HOT,
    COL_YELLOW, COL_CLEAR,
    PLAYER_START_POS, PLAYER_SPEED, PLAYER_CLAMP_X,
    FIRE_COOLDOWN, LASER_SPEED, LASER_LIFETIME,
)


# ── Ship definition blueprints ────────────────────────────────────────────────
SHIP_BLUEPRINTS = {
    'interceptor': {
        'label':        'THE INTERCEPTOR',
        'description':  'Balanced. Dual standard lasers.',
        'body_color':   COL_MAGENTA,
        'wing_color':   COL_VIOLET,
        'body_scale':   Vec3(1.4, 0.35, 2.4),
        'wing_l_pos':   Vec3(-0.9, 0, -0.15),
        'wing_r_pos':   Vec3(0.9,  0, -0.15),
        'wing_scale':   Vec3(0.7, 0.18, 1.0),
        'nose_scale':   Vec3(0.35, 0.25, 1.0),
        'nose_color':   COL_YELLOW,
        'dual_shot':    False,
        'collider_pad': 1.0,
        'unlock':       0,
    },
    'dreadnought': {
        'label':        'THE DREADNOUGHT',
        'description':  'Heavy. Wide dual fat blasters.',
        'body_color':   COL_ORANGE,
        'wing_color':   COL_RED_HOT,
        'body_scale':   Vec3(2.0, 0.55, 2.0),
        'wing_l_pos':   Vec3(-1.3, 0, -0.1),
        'wing_r_pos':   Vec3(1.3,  0, -0.1),
        'wing_scale':   Vec3(0.9, 0.28, 0.75),
        'nose_scale':   Vec3(0.55, 0.35, 0.6),
        'nose_color':   COL_YELLOW,
        'dual_shot':    True,
        'collider_pad': 1.35,
        'unlock':       500,
    },
    'wraith': {
        'label':        'THE WRAITH',
        'description':  'Stealth. Narrow body, wide wings.',
        'body_color':   COL_CYAN,
        'wing_color':   color.Color(0.3, 0.9, 1.0, 1),
        'body_scale':   Vec3(0.9, 0.25, 2.8),
        'wing_l_pos':   Vec3(-1.6, 0, 0.1),
        'wing_r_pos':   Vec3(1.6,  0, 0.1),
        'wing_scale':   Vec3(1.4, 0.14, 0.8),
        'nose_scale':   Vec3(0.22, 0.2, 1.4),
        'nose_color':   COL_CYAN,
        'dual_shot':    False,
        'collider_pad': 0.75,
        'unlock':       1000,
    },
}
SHIP_ORDER = ['interceptor', 'dreadnought', 'wraith']


class PlayerShip:
    """
    Manages the active player ship entity, exhaust trail, and laser firing.
    Call update() every frame while the game is PLAYING.
    """

    def __init__(self, ship_key: str = 'interceptor'):
        self.bp          = SHIP_BLUEPRINTS[ship_key]
        self.fire_timer  = 0.0
        self.lasers      = []          # Active laser bolts list
        self._trail      = []          # Exhaust trail particles
        self._trail_tick = 0.0

        # ── Main body ─────────────────────────────────────────────────────────
        self.entity = Entity(
            model='cube',
            color=self.bp['body_color'],
            scale=self.bp['body_scale'],
            position=PLAYER_START_POS,
            collider='box',
        )

        # ── Wings ─────────────────────────────────────────────────────────────
        self._wing_l = Entity(
            parent=self.entity,
            model='cube',
            color=self.bp['wing_color'],
            scale=self.bp['wing_scale'],
            position=self.bp['wing_l_pos'],
        )
        self._wing_r = Entity(
            parent=self.entity,
            model='cube',
            color=self.bp['wing_color'],
            scale=self.bp['wing_scale'],
            position=self.bp['wing_r_pos'],
        )

        # ── Nose cone ─────────────────────────────────────────────────────────
        self._nose = Entity(
            parent=self.entity,
            model='cube',
            color=self.bp['nose_color'],
            scale=self.bp['nose_scale'],
            position=Vec3(0, 0.08, 1.4),
        )

        # ── Engine glow pip ───────────────────────────────────────────────────
        self._glow = Entity(
            parent=self.entity,
            model='sphere',
            color=color.Color(0.8, 0.5, 1.0, 0.9),
            scale=Vec3(0.3, 0.3, 0.2),
            position=Vec3(0, 0, -1.1),
        )

    # ─────────────────────────────────────────────────────────────────────────
    @property
    def x(self) -> float:
        return self.entity.x

    @x.setter
    def x(self, value: float):
        self.entity.x = value

    @property
    def y(self) -> float:
        return self.entity.y

    @property
    def z(self) -> float:
        return self.entity.z

    @property
    def position(self) -> Vec3:
        return self.entity.position

    # ─────────────────────────────────────────────────────────────────────────
    def update(self, held_keys, game_speed: float) -> None:
        """Called every frame by GameManager."""
        dt = time.dt

        # Lateral movement
        if held_keys['a'] or held_keys['left arrow']:
            self.entity.x -= PLAYER_SPEED * dt
        if held_keys['d'] or held_keys['right arrow']:
            self.entity.x += PLAYER_SPEED * dt
        self.entity.x = clamp(self.entity.x, -PLAYER_CLAMP_X, PLAYER_CLAMP_X)

        # Subtle bank tilt
        target_rot = 0
        if held_keys['a'] or held_keys['left arrow']:
            target_rot = 12
        elif held_keys['d'] or held_keys['right arrow']:
            target_rot = -12
        self.entity.rotation_z += (target_rot - self.entity.rotation_z) * 8 * dt

        # Fire cooldown countdown
        self.fire_timer = max(0.0, self.fire_timer - dt)

        # Trail
        self._trail_tick += dt
        if self._trail_tick >= 0.045:
            self._trail_tick = 0.0
            self._spawn_trail_particle(game_speed)

        # Move and age trail particles
        for tp in list(self._trail):
            tp['age'] += dt
            tp['e'].z  -= game_speed * dt
            fade = max(0.0, 1.0 - tp['age'] / 0.55)
            c = tp['base_color']
            tp['e'].color = color.Color(c.r * fade, c.g * fade, c.b * fade, fade * 0.85)
            if tp['age'] > 0.55:
                destroy(tp['e'])
                self._trail.remove(tp)

        # Move lasers
        for lz in list(self.lasers):
            lz['e'].z  += LASER_SPEED * dt
            lz['age'] += dt
            if lz['age'] > LASER_LIFETIME:
                destroy(lz['e'])
                self.lasers.remove(lz)

    # ─────────────────────────────────────────────────────────────────────────
    def try_fire(self) -> bool:
        """Returns True (and spawns bolts) if cooldown has elapsed."""
        if self.fire_timer > 0:
            return False
        self.fire_timer = FIRE_COOLDOWN
        self._spawn_lasers()
        # Recoil
        self.entity.z -= 0.15
        self.entity.animate_z(PLAYER_START_POS.z, duration=0.12)
        return True

    def _spawn_lasers(self):
        bp = self.bp
        if bp['dual_shot']:
            offsets = [-0.75, 0.75]
            scale   = Vec3(0.22, 0.22, 2.8)
        else:
            offsets = [-0.6, 0.6]
            scale   = Vec3(0.14, 0.14, 2.5)

        for ox in offsets:
            bolt = Entity(
                model='cube',
                color=COL_YELLOW,
                scale=scale,
                position=Vec3(self.entity.x + ox, self.entity.y, self.entity.z + 2.0),
                collider='box',
            )
            # Glow core
            Entity(
                parent=bolt,
                model='sphere',
                color=color.Color(1, 1, 0.5, 0.6),
                scale=Vec3(0.6, 0.6, 0.25),
            )
            self.lasers.append({'e': bolt, 'age': 0.0})

    def _spawn_trail_particle(self, game_speed: float):
        bc = self.bp['body_color']
        # Slight random spread behind the ship
        ox = random.uniform(-0.3, 0.3)
        particle = Entity(
            model='sphere',
            color=color.Color(bc.r, bc.g, bc.b, 0.85),
            scale=random.uniform(0.12, 0.28),
            position=Vec3(self.entity.x + ox, self.entity.y - 0.05, self.entity.z - 1.3),
        )
        self._trail.append({'e': particle, 'age': 0.0, 'base_color': bc})

    # ─────────────────────────────────────────────────────────────────────────
    def shake(self):
        """Micro camera-entity shake on collision."""
        self.entity.animate_x(self.entity.x + 0.3, duration=0.06)
        self.entity.animate_x(self.entity.x - 0.3, duration=0.06, delay=0.06)

    def destroy_all(self):
        """Clean up everything owned by this ship."""
        for lz in self.lasers:
            destroy(lz['e'])
        self.lasers.clear()
        for tp in self._trail:
            destroy(tp['e'])
        self._trail.clear()
        destroy(self.entity)   # children destroyed automatically
