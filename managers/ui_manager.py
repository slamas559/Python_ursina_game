"""
managers/ui_manager.py
Owns every 2-D UI element:
  • Garage / ship-select screen
  • In-game HUD (score, speed, energy bar)
  • Pause overlay
  • Game-over overlay
"""

from ursina import (
    Entity, Text, Vec2, Vec3, color, camera, destroy, Button,
    curve, invoke, mouse
)
from constants import (
    COL_MAGENTA, COL_CYAN, COL_ORANGE, COL_LIME, COL_YELLOW,
    COL_UI_BG, COL_WHITE,
    MAX_ENERGY,
    DREADNOUGHT_UNLOCK, WRAITH_UNLOCK,
)
from entities.player_ship import SHIP_BLUEPRINTS, SHIP_ORDER


_FONT_MONO = 'VeraMono.ttf'   # bundled with Ursina; always available


class UIManager:
    """
    Create / destroy UI layers by calling show_garage(), show_hud(),
    show_game_over(), clear_all().
    """

    def __init__(self, on_ship_select, on_launch, on_restart, on_resume):
        """
        Callbacks supplied by GameManager:
          on_ship_select(key) — user cycled to a new ship in the garage
          on_launch(key)      — user clicked LAUNCH
          on_restart()        — user clicked RESTART on game-over screen
          on_resume()         — user clicked RESUME on pause screen
        """
        self._on_ship_select = on_ship_select
        self._on_launch      = on_launch
        self._on_restart     = on_restart
        self._on_resume      = on_resume

        self._entities       = []   # All active UI entities for easy teardown
        self._hud            = {}   # Named HUD widget refs
        self._garage_idx     = 0    # Currently selected ship index

    # ── Utility ──────────────────────────────────────────────────────────────
    def _track(self, *entities):
        """Register entities for cleanup."""
        self._entities.extend(entities)
        return entities[0] if len(entities) == 1 else entities

    def clear_all(self):
        for e in self._entities:
            try:
                destroy(e)
            except Exception:
                pass
        self._entities.clear()
        self._hud.clear()

    # ── Garage screen ─────────────────────────────────────────────────────────
    def show_garage(self, highscore: int = 0):
        self.clear_all()
        self._garage_idx = 0
        self._hs = highscore

        # Dark tinted full-screen panel
        bg = Entity(
            parent=camera.ui,
            model='quad',
            color=color.Color(0.0, 0.0, 0.06, 0.32),
            scale=(2, 1),
            z=1,
        )
        self._track(bg)

        # Title
        title = Text(
            parent=camera.ui,
            text='CYBERPUNK NEON RACER',
            scale=2.8,
            position=(0, 0.40),
            origin=(0, 0),
            color=COL_MAGENTA,
            font=_FONT_MONO,
        )
        self._track(title)

        sub = Text(
            parent=camera.ui,
            text='── SELECT YOUR SHIP ──',
            scale=1.4,
            position=(0, 0.32),
            origin=(0, 0),
            color=COL_CYAN,
            font=_FONT_MONO,
        )
        self._track(sub)

        # High-score banner
        hs_txt = Text(
            parent=camera.ui,
            text=f'LOCAL BEST: {highscore}',
            scale=1.2,
            position=(0, 0.25),
            origin=(0, 0),
            color=COL_LIME,
            font=_FONT_MONO,
        )
        self._track(hs_txt)

        # Ship info card
        self._ship_name_txt = Text(
            parent=camera.ui,
            text='',
            scale=1.8,
            position=(0, 0.10),
            origin=(0, 0),
            color=COL_YELLOW,
            font=_FONT_MONO,
        )
        self._track(self._ship_name_txt)

        self._ship_desc_txt = Text(
            parent=camera.ui,
            text='',
            scale=1.1,
            position=(0, 0.02),
            origin=(0, 0),
            color=COL_WHITE,
            font=_FONT_MONO,
        )
        self._track(self._ship_desc_txt)

        self._unlock_txt = Text(
            parent=camera.ui,
            text='',
            scale=1.0,
            position=(0, -0.06),
            origin=(0, 0),
            color=COL_ORANGE,
            font=_FONT_MONO,
        )
        self._track(self._unlock_txt)

        # ◀ ▶ buttons
        btn_prev = Button(
            parent=camera.ui,
            text='PREV',
            scale=(0.18, 0.07),
            position=(-0.22, -0.15),
            color=color.Color(0.1, 0.1, 0.25, 0.9),
            highlight_color=color.Color(0.3, 0.0, 0.6, 1),
            on_click=self._garage_prev,
        )
        self._track(btn_prev)

        btn_next = Button(
            parent=camera.ui,
            text='NEXT',
            scale=(0.18, 0.07),
            position=(0.22, -0.15),
            color=color.Color(0.1, 0.1, 0.25, 0.9),
            highlight_color=color.Color(0.3, 0.0, 0.6, 1),
            on_click=self._garage_next,
        )
        self._track(btn_next)

        # LAUNCH button
        self._launch_btn = Button(
            parent=camera.ui,
            text='LAUNCH',
            scale=(0.26, 0.09),
            position=(0, -0.27),
            color=COL_MAGENTA,
            highlight_color=color.Color(1, 0.3, 1, 1),
            on_click=self._on_launch_click,
        )
        self._track(self._launch_btn)

        # Controls hint
        ctrl_hint = Text(
            parent=camera.ui,
            text='[←/→] Cycle ships   [A/D] Move   [SPACE] Shoot   [ESC] Pause',
            scale=0.85,
            position=(0, -0.42),
            origin=(0, 0),
            color=color.light_gray,
            font=_FONT_MONO,
        )
        self._track(ctrl_hint)

        # Refresh card for first ship
        self._refresh_garage_card(highscore)

    def _garage_prev(self):
        self._garage_idx = (self._garage_idx - 1) % len(SHIP_ORDER)
        self._on_ship_select(SHIP_ORDER[self._garage_idx])
        self._refresh_garage_card(self._hs)

    def _garage_next(self):
        self._garage_idx = (self._garage_idx + 1) % len(SHIP_ORDER)
        self._on_ship_select(SHIP_ORDER[self._garage_idx])
        self._refresh_garage_card(self._hs)

    def _on_launch_click(self):
        key = SHIP_ORDER[self._garage_idx]
        bp  = SHIP_BLUEPRINTS[key]
        hs  = self._hs
        # Check unlock
        if bp['unlock'] > hs:
            self._unlock_txt.text = f'LOCKED — need {bp["unlock"]} pts to unlock'
            return
        self._on_launch(key)

    def _refresh_garage_card(self, highscore: int):
        key = SHIP_ORDER[self._garage_idx]
        bp  = SHIP_BLUEPRINTS[key]
        self._ship_name_txt.text = bp['label']
        self._ship_desc_txt.text = bp['description']
        if bp['unlock'] > highscore:
            self._unlock_txt.text = f'LOCKED  —  requires {bp["unlock"]} pts'
            self._launch_btn.color = color.Color(0.3, 0.3, 0.3, 0.85)
        else:
            self._unlock_txt.text = 'UNLOCKED'
            self._unlock_txt.color = COL_LIME
            self._launch_btn.color = COL_MAGENTA

    # ── In-game HUD ───────────────────────────────────────────────────────────
    def show_hud(self):
        self.clear_all()

        # Score panel
        score_bg = Entity(
            parent=camera.ui,
            model='quad',
            color=COL_UI_BG,
            scale=(0.32, 0.10),
            position=(-0.65, 0.44),
        )
        self._track(score_bg)

        score_txt = Text(
            parent=score_bg,
            text='SCORE: 0',
            scale=(5.55, 3),
            origin=(0, 0),
            color=COL_WHITE,
            font=_FONT_MONO,
        )
        self._hud['score'] = score_txt
        self._track(score_txt)

        # Speed panel
        speed_bg = Entity(
            parent=camera.ui,
            model='quad',
            color=COL_UI_BG,
            scale=(0.30, 0.10),
            position=(0.64, 0.44),
        )
        self._track(speed_bg)

        speed_txt = Text(
            parent=speed_bg,
            text='0 MPH',
            scale=(5.55, 3),
            origin=(0, 0),
            color=COL_CYAN,
            font=_FONT_MONO,
        )
        self._hud['speed'] = speed_txt
        self._track(speed_txt)

        # Energy bar background
        en_bg = Entity(
            parent=camera.ui,
            model='quad',
            color=color.Color(0.05, 0.05, 0.12, 0.88),
            scale=(0.50, 0.045),
            position=(0, -0.43),
        )
        self._track(en_bg)

        en_label = Text(
            parent=camera.ui,
            text='ENERGY',
            scale=0.9,
            position=(-0.275, -0.41),
            origin=(0, 0),
            color=COL_LIME,
            font=_FONT_MONO,
        )
        self._track(en_label)

        # Energy fill bar
        en_fill = Entity(
            parent=camera.ui,
            model='quad',
            color=COL_LIME,
            scale=(0.48, 0.028),
            position=(0, -0.43),
            origin=(0, 0),
        )
        self._hud['energy_fill'] = en_fill
        self._track(en_fill)

        # Pause hint
        pause_hint = Text(
            parent=camera.ui,
            text='[ESC] Pause',
            scale=0.75,
            position=(0.72, -0.46),
            origin=(0, 0),
            color=color.gray,
            font=_FONT_MONO,
        )
        self._track(pause_hint)

    def update_hud(self, score: int, game_speed: float, energy: float):
        from constants import SPEEDOMETER_FACTOR
        if 'score' in self._hud:
            self._hud['score'].text = f'SCORE: {score}'
        if 'speed' in self._hud:
            mph = int(game_speed * SPEEDOMETER_FACTOR)
            self._hud['speed'].text = f'{mph} MPH'
        if 'energy_fill' in self._hud:
            ratio = max(0.0, energy / MAX_ENERGY)
            self._hud['energy_fill'].scale_x = 0.48 * ratio
            if ratio > 0.5:
                self._hud['energy_fill'].color = COL_LIME
            elif ratio > 0.25:
                self._hud['energy_fill'].color = COL_YELLOW
            else:
                self._hud['energy_fill'].color = color.Color(1, 0.1, 0.1, 1)

    # ── Pause overlay ─────────────────────────────────────────────────────────
    def show_pause(self):
        overlay = Entity(
            parent=camera.ui,
            model='quad',
            color=color.Color(0.0, 0.0, 0.1, 0.78),
            scale=(2, 1),
            z=0.5,
        )
        self._track(overlay)

        p_title = Text(
            parent=camera.ui,
            text='[ PAUSED ]',
            scale=3.0,
            position=(0, 0.12),
            origin=(0, 0),
            color=COL_CYAN,
            font=_FONT_MONO,
        )
        self._track(p_title)

        resume_btn = Button(
            parent=camera.ui,
            text='RESUME',
            scale=(0.22, 0.09),
            position=(0, -0.05),
            color=COL_MAGENTA,
            highlight_color=color.Color(1, 0.4, 1, 1),
            on_click=self._on_resume,
        )
        self._track(resume_btn)

    # ── Game-over overlay ─────────────────────────────────────────────────────
    def show_game_over(self, score: int, highscore: int):
        self.clear_all()

        bg = Entity(
            parent=camera.ui,
            model='quad',
            color=color.Color(0.06, 0, 0, 0.90),
            scale=(2, 1),
            z=0.5,
        )
        self._track(bg)

        err = Text(
            parent=camera.ui,
            text='CRASH — SYSTEM ERROR',
            scale=2.6,
            position=(0, 0.30),
            origin=(0, 0),
            color=color.Color(1, 0.05, 0.05, 1),
            font=_FONT_MONO,
        )
        self._track(err)

        score_txt = Text(
            parent=camera.ui,
            text=f'SCORE: {score}',
            scale=2.0,
            position=(0, 0.15),
            origin=(0, 0),
            color=COL_YELLOW,
            font=_FONT_MONO,
        )
        self._track(score_txt)

        hs_txt = Text(
            parent=camera.ui,
            text=f'LOCAL BEST: {highscore}',
            scale=1.4,
            position=(0, 0.05),
            origin=(0, 0),
            color=COL_LIME,
            font=_FONT_MONO,
        )
        self._track(hs_txt)

        if score >= highscore and score > 0:
            new_rec = Text(
                parent=camera.ui,
                text='★  NEW RECORD  ★',
                scale=1.6,
                position=(0, -0.06),
                origin=(0, 0),
                color=COL_MAGENTA,
                font=_FONT_MONO,
            )
            self._track(new_rec)

        restart_btn = Button(
            parent=camera.ui,
            text='↺  RESTART',
            scale=(0.24, 0.09),
            position=(0, -0.20),
            color=COL_ORANGE,
            highlight_color=color.Color(1, 0.7, 0.1, 1),
            on_click=self._on_restart,
        )
        self._track(restart_btn)

        garage_btn = Button(
            parent=camera.ui,
            text='⬡  GARAGE',
            scale=(0.24, 0.09),
            position=(0, -0.32),
            color=color.Color(0.1, 0.1, 0.35, 1),
            highlight_color=color.Color(0.3, 0.2, 0.8, 1),
            on_click=self._on_restart,   # GameManager will redirect to garage
        )
        self._track(garage_btn)
