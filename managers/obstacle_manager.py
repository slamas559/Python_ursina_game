"""
managers/obstacle_manager.py
Handles spawning, movement, collision, and cleanup of:
  • Type-A (static) obstacles
  • Type-B (patrolling) obstacles
  • Energy orbs (collectibles)
"""

import random
from ursina import Entity, Vec3, color, time, destroy, invoke

from constants import (
    COL_ORANGE, COL_RED_HOT, COL_CYAN, COL_GREEN_ORB, COL_YELLOW,
    SPAWN_Z, DESPAWN_Z,
    OBS_SPAWN_MIN_DELAY, OBS_SPAWN_BASE,
    OBS_PATROL_SPEED,
    SCORE_PER_DODGE, SCORE_PER_KILL,
    ENERGY_ORB_VALUE,
    PLAYER_CLAMP_X,
    INITIAL_SPEED,
)


class ObstacleManager:
    """
    Creates and updates all in-world hazards and collectibles.
    Calls back into GameManager via the provided callback hooks.
    """

    def __init__(self, on_score, on_energy_orb, on_player_hit, on_laser_hit):
        """
        on_score(pts)      — called when an obstacle is dodged or destroyed
        on_energy_orb(v)   — called when the player picks up an orb
        on_player_hit()    — called when an obstacle hits the player
        on_laser_hit(obs)  — called when a laser bolt hits an obstacle
        """
        self._on_score      = on_score
        self._on_energy_orb = on_energy_orb
        self._on_player_hit = on_player_hit
        self._on_laser_hit  = on_laser_hit

        self.obstacles    = []    # [{'e': Entity, 'type': 'A'|'B', 'dir': ±1}]
        self.orbs         = []    # [Entity]
        self._active      = False
        self._game_speed  = INITIAL_SPEED    # Updated each frame by GameManager

    # ─────────────────────────────────────────────────────────────────────────
    def start(self, game_speed: float):
        self._active     = True
        self._game_speed = game_speed
        self._schedule_spawn()

    def stop(self):
        self._active = False

    # ─────────────────────────────────────────────────────────────────────────
    def _schedule_spawn(self):
        if not self._active:
            return
        delay = max(
            OBS_SPAWN_MIN_DELAY,
            OBS_SPAWN_BASE - (self._game_speed - INITIAL_SPEED) * 0.004
        )
        invoke(self._spawn_wave, delay=random.uniform(delay * 0.8, delay * 1.4))

    def _spawn_wave(self):
        if not self._active:
            return

        # 30 % chance of spawning an energy orb alongside the obstacle
        if random.random() < 0.30:
            self._spawn_orb()

        # Pick obstacle type: 25 % chance of Type-B patrol
        obs_type = 'B' if random.random() < 0.25 else 'A'
        self._spawn_obstacle(obs_type)

        # Schedule the next wave
        self._schedule_spawn()

    def _spawn_obstacle(self, obs_type: str):
        x_pos   = random.uniform(-PLAYER_CLAMP_X + 0.5, PLAYER_CLAMP_X - 0.5)
        width   = random.uniform(1.2, 2.8)
        height  = random.uniform(0.9, 1.8)

        if obs_type == 'A':
            col = COL_ORANGE
        else:
            col = COL_RED_HOT      # Type-B is hotter red

        body = Entity(
            model='cube',
            color=col,
            scale=Vec3(width, height, 1.5),
            position=Vec3(x_pos, height / 2, SPAWN_Z),
            collider='box',
        )
        # Neon trim edge
        trim = Entity(
            parent=body,
            model='cube',
            color=COL_YELLOW,
            scale=Vec3(1.02, 0.08, 1.05),
            position=Vec3(0, 0.52, 0),
        )
        # body.texture_scale = (width, height)

        patrol_dir = random.choice([-1, 1])
        self.obstacles.append({'e': body, 'type': obs_type, 'dir': patrol_dir})

    def _spawn_orb(self):
        x_pos = random.uniform(-PLAYER_CLAMP_X + 1, PLAYER_CLAMP_X - 1)
        orb = Entity(
            model='sphere',
            color=COL_GREEN_ORB,
            scale=0.85,                          # Slightly larger — easier to hit
            position=Vec3(x_pos, 0.3, SPAWN_Z + random.uniform(-10, 10)),
            collider='box',                      # box collider is reliable with intersects()
        )
        self.orbs.append(orb)

    # ─────────────────────────────────────────────────────────────────────────
    def update(self, player_ship, game_speed: float):
        """Called every frame by GameManager."""
        dt = time.dt
        self._game_speed = game_speed   # Keep in sync for spawn rate scaling

        # ── Obstacles ─────────────────────────────────────────────────────────
        for obs in list(self.obstacles):
            e = obs['e']
            # Move toward player
            e.z -= game_speed * dt

            # Type-B patrol sweep
            if obs['type'] == 'B':
                e.x += OBS_PATROL_SPEED * obs['dir'] * dt
                if abs(e.x) > PLAYER_CLAMP_X - 0.4:
                    obs['dir'] *= -1

            # Laser hit check
            hit_by_laser = False
            for lz_dict in list(player_ship.lasers):
                if lz_dict['e'].intersects(e).hit:
                    self._on_laser_hit(e.position)
                    self._on_score(SCORE_PER_KILL)
                    destroy(lz_dict['e'])
                    player_ship.lasers.remove(lz_dict)
                    destroy(e)
                    self.obstacles.remove(obs)
                    hit_by_laser = True
                    break
            if hit_by_laser:
                continue

            # Player collision
            if player_ship.entity.intersects(e).hit:
                self._on_player_hit()
                self.obstacles.remove(obs)
                destroy(e)
                continue

            # Passed behind player safely
            if e.z < DESPAWN_Z:
                self._on_score(SCORE_PER_DODGE)
                self.obstacles.remove(obs)
                destroy(e)

        # ── Energy Orbs ───────────────────────────────────────────────────────
        player_pos = player_ship.entity.position
        for orb in list(self.orbs):
            orb.z -= game_speed * dt
            orb.rotation_y += 60 * dt   # Spin

            # Distance-based pickup: reliable regardless of collider quirks
            dx = orb.x - player_pos.x
            dy = orb.y - player_pos.y
            dz = orb.z - player_pos.z
            dist_sq = dx * dx + dy * dy * 0.5 + dz * dz   # weight Y less (ships are flat)
            if dist_sq < 2.8:                              # ~1.67 unit radius pickup
                self._on_energy_orb(ENERGY_ORB_VALUE)
                self.orbs.remove(orb)
                destroy(orb)
                continue

            if orb.z < DESPAWN_Z:
                self.orbs.remove(orb)
                destroy(orb)

    # ─────────────────────────────────────────────────────────────────────────
    def destroy_all(self):
        for obs in self.obstacles:
            destroy(obs['e'])
        self.obstacles.clear()
        for orb in self.orbs:
            destroy(orb)
        self.orbs.clear()
        self._active = False