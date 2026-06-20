"""
managers/game_manager.py
Central game-state machine.  Owns every sub-system and routes
Ursina's update() / input() callbacks to the right handlers.

States
------
  GARAGE_MENU  → ship selection before run
  PLAYING      → active gameplay
  PAUSED       → pause overlay (Esc toggle)
  GAME_OVER    → crash screen
"""

from ursina import (
    camera, Vec3, color, held_keys, time, mouse, invoke
)
from constants import (
    STATE_GARAGE, STATE_PLAYING, STATE_PAUSED, STATE_GAMEOVER,
    INITIAL_SPEED, MAX_SPEED, SPEED_INCREMENT,
    MAX_ENERGY, ENERGY_DRAIN_RATE, ENERGY_HIT_PENALTY,
    COL_MAGENTA,
)
from managers.fx_manager      import FXManager
from managers.obstacle_manager import ObstacleManager
from managers.ui_manager      import UIManager
from entities.player_ship     import PlayerShip
from entities.garage_preview  import GaragePreview
from utils.highscore          import load_highscore, save_highscore


_CAM_POS = Vec3(0, 5, -16)
_CAM_ROT = 13


class GameManager:
    """Top-level controller; instantiated once in main.py."""

    def __init__(self):
        # Camera setup
        camera.position  = _CAM_POS
        camera.rotation_x = _CAM_ROT

        # Sub-system construction
        self._fx  = FXManager()
        self._ui  = UIManager(
            on_ship_select = self._on_garage_ship_select,
            on_launch      = self._on_garage_launch,
            on_restart     = self._on_restart,
            on_resume      = self._on_resume,
        )
        self._obs = ObstacleManager(
            on_score      = self._add_score,
            on_energy_orb = self._collect_energy,
            on_player_hit = self._on_player_hit,
            on_laser_hit  = self._on_laser_hit,
        )

        # Runtime state
        self._state      = None
        self._ship_key   = 'interceptor'
        self._player     = None
        self._preview    = None
        self._score      = 0
        self._game_speed = INITIAL_SPEED
        self._energy     = MAX_ENERGY
        self._highscore  = load_highscore()

        # Enter the garage
        self._enter_garage()

    # ── State transitions ─────────────────────────────────────────────────────
    def _enter_garage(self):
        self._state = STATE_GARAGE
        if self._player:
            self._player.destroy_all()
            self._player = None
        if self._preview:
            self._preview.destroy_all()
        self._obs.destroy_all()
        self._obs.stop()

        self._preview = GaragePreview(self._ship_key)
        self._ui.show_garage(self._highscore)

    def _enter_playing(self):
        if self._preview:
            self._preview.destroy_all()
            self._preview = None
        self._ui.show_hud()

        self._score      = 0
        self._game_speed = INITIAL_SPEED
        self._energy     = MAX_ENERGY

        self._player = PlayerShip(self._ship_key)
        self._obs.start(self._game_speed)
        self._state  = STATE_PLAYING

    def _enter_paused(self):
        self._state = STATE_PAUSED
        self._obs.stop()
        self._ui.show_pause()

    def _enter_game_over(self):
        self._state = STATE_GAMEOVER
        self._obs.stop()
        save_highscore(self._score)
        self._highscore = load_highscore()
        self._ui.show_game_over(self._score, self._highscore)

    # ── UI callbacks ──────────────────────────────────────────────────────────
    def _on_garage_ship_select(self, key: str):
        self._ship_key = key
        if self._preview:
            self._preview.set_ship(key)

    def _on_garage_launch(self, key: str):
        self._ship_key = key
        self._enter_playing()

    def _on_restart(self):
        # Go back to garage (user can launch again from there)
        self._enter_garage()

    def _on_resume(self):
        # Remove pause overlay by rebuilding HUD, then resume
        self._ui.show_hud()
        self._ui.update_hud(self._score, self._game_speed, self._energy)
        self._obs.start(self._game_speed)
        self._state = STATE_PLAYING

    # ── Game-event callbacks (from ObstacleManager) ───────────────────────────
    def _add_score(self, pts: int):
        self._score      += pts
        self._game_speed  = min(MAX_SPEED, self._game_speed + SPEED_INCREMENT * 0.5)

    def _collect_energy(self, value: float):
        self._energy = min(MAX_ENERGY, self._energy + value)

    def _on_player_hit(self):
        if self._state != STATE_PLAYING:
            return
        self._energy -= ENERGY_HIT_PENALTY
        self._fx.trigger_screen_shake()
        if self._player:
            self._fx.trigger_explosion(self._player.position)
            self._player.shake()
        if self._energy <= 0:
            self._enter_game_over()

    def _on_laser_hit(self, position):
        self._fx.trigger_explosion(position)
        self._fx.trigger_screen_shake(magnitude=0.15, duration=0.2)

    # ── Ursina update loop ────────────────────────────────────────────────────
    def update(self):
        dt = time.dt

        if self._state == STATE_GARAGE:
            if self._preview:
                self._preview.update()
            # Keyboard ship cycling also supported
            # (buttons handle it; no held-keys needed here)

        elif self._state == STATE_PLAYING:
            # Energy drain
            self._energy -= ENERGY_DRAIN_RATE * dt
            if self._energy <= 0:
                self._energy = 0
                self._enter_game_over()
                return

            # Speed ramp
            self._game_speed = min(MAX_SPEED, self._game_speed + 0.6 * dt)

            # Player ship
            if self._player:
                self._player.update(held_keys, self._game_speed)

            # Obstacles / orbs — pass current game_speed for scheduling
            self._obs.update(self._player, self._game_speed)

            # FX environment scroll
            self._fx.update(self._game_speed, _CAM_POS)

            # HUD
            self._ui.update_hud(self._score, self._game_speed, self._energy)

        elif self._state == STATE_PAUSED:
            pass   # Nothing to update while paused

        elif self._state == STATE_GAMEOVER:
            pass

    # ── Ursina input dispatcher ───────────────────────────────────────────────
    def input(self, key: str):   # noqa: A003
        if self._state == STATE_GARAGE:
            if key == 'left arrow':
                from entities.player_ship import SHIP_ORDER
                idx = SHIP_ORDER.index(self._ship_key)
                self._ship_key = SHIP_ORDER[(idx - 1) % len(SHIP_ORDER)]
                self._on_garage_ship_select(self._ship_key)
            elif key == 'right arrow':
                from entities.player_ship import SHIP_ORDER
                idx = SHIP_ORDER.index(self._ship_key)
                self._ship_key = SHIP_ORDER[(idx + 1) % len(SHIP_ORDER)]
                self._on_garage_ship_select(self._ship_key)
            elif key == 'enter' or key == 'return':
                self._on_garage_launch(self._ship_key)

        elif self._state == STATE_PLAYING:
            if key == 'space':
                if self._player:
                    self._player.try_fire()
            elif key == 'escape':
                self._enter_paused()

        elif self._state == STATE_PAUSED:
            if key == 'escape':
                self._on_resume()

        elif self._state == STATE_GAMEOVER:
            if key == 'r':
                self._on_restart()
