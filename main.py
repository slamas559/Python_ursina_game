"""
╔══════════════════════════════════════════════════════╗
║   CYBERPUNK NEON INFINITE RACER  —  main.py          ║
║   Entry point. Boots the Ursina app & GameManager.   ║
╚══════════════════════════════════════════════════════╝
"""

from ursina import Ursina, window, color
from managers.game_manager import GameManager

if __name__ == '__main__':
    app = Ursina(
        title='Cyberpunk Neon Racer',
        borderless=False,
        fullscreen=False,
        development_mode=False,
    )

    window.size       = (1280, 720)
    window.color      = color.Color(0.02, 0.02, 0.06, 1)   # near-black indigo
    window.exit_button.visible = False

    gm = GameManager()

    # Ursina routes keyboard events to a module-level `input()` function.
    # We delegate straight to GameManager so no logic lives here.
    def input(key):          # noqa: A001
        gm.input(key)

    # Ursina calls a module-level update() every frame.
    def update():
        gm.update()

    app.run()
