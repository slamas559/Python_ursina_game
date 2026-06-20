"""
entities/garage_preview.py
Renders a spinning 3-D preview of the currently selected ship in the garage.
"""

from ursina import Entity, Vec3, color, time, destroy
from constants import COL_YELLOW
from entities.player_ship import SHIP_BLUEPRINTS


class GaragePreview:
    """
    A decorative spinning ship model displayed in world-space during the
    Garage state. Call update() every frame; call set_ship() to switch.
    """

    _PREVIEW_POS = Vec3(0, 1.8, 8)     # World position the preview floats at
    _SPIN_SPEED  = 55                   # Degrees per second

    def __init__(self, ship_key: str = 'interceptor'):
        self._parts = []
        self._build(ship_key)

    # ─────────────────────────────────────────────────────────────────────────
    def _build(self, ship_key: str):
        bp = SHIP_BLUEPRINTS[ship_key]
        cx, cy, cz = (
            self._PREVIEW_POS.x,
            self._PREVIEW_POS.y,
            self._PREVIEW_POS.z,
        )
        scale_factor = 1.6

        # Body
        body = Entity(
            model='cube',
            color=bp['body_color'],
            scale=Vec3(*(s * scale_factor for s in bp['body_scale'])),
            position=self._PREVIEW_POS,
        )
        self._parts.append(body)

        # Wings relative to body
        for side, pos_key in [(-1, 'wing_l_pos'), (1, 'wing_r_pos')]:
            wpos = bp[pos_key]
            wing = Entity(
                model='cube',
                color=bp['wing_color'],
                scale=Vec3(*(s * scale_factor for s in bp['wing_scale'])),
                position=Vec3(
                    cx + wpos.x * scale_factor,
                    cy + wpos.y * scale_factor,
                    cz + wpos.z * scale_factor,
                ),
            )
            self._parts.append(wing)

        # Nose cone
        n = bp['nose_scale']
        nose = Entity(
            model='cube',
            color=bp['nose_color'],
            scale=Vec3(n.x * scale_factor, n.y * scale_factor, n.z * scale_factor),
            position=Vec3(cx, cy + 0.1 * scale_factor, cz + 1.4 * scale_factor),
        )
        self._parts.append(nose)

    # ─────────────────────────────────────────────────────────────────────────
    def set_ship(self, ship_key: str):
        """Rebuild the preview for a different ship."""
        self._destroy_parts()
        self._build(ship_key)

    def update(self):
        """Spin all parts around Y axis each frame."""
        delta = self._SPIN_SPEED * time.dt
        pivot = self._PREVIEW_POS
        for part in self._parts:
            part.rotation_y += delta

    def destroy_all(self):
        self._destroy_parts()

    def _destroy_parts(self):
        for p in self._parts:
            destroy(p)
        self._parts.clear()
