import random
from ursina import *

# Initialize the game engine window
app = Ursina()

# --- GAME VARIABLES ---
game_speed = 35         # Starting speed
score = 0               # Score tracker
game_over = False       # Tracks game state
obstacles = []          # Active obstacle list
lasers = []             # Active laser projectile list
road_markers = []       # Scrolling neon lane line list

# Optimize lighting for a moody, neon sci-fi aesthetic
DirectionalLight(y=10, z=-10, rotation=(45, -45, 0))
AmbientLight(color=color.dark_gray)

# --- ADJUSTED CAMERA PERSPECTIVE ---
# Lowered height (Y=4 instead of 7) and reduced downward tilt (X=12 instead of 22)
# This lets you look "up" and down the highway toward the horizon properly
camera.position = (0, 4, -15)
camera.rotation_x = 12

# --- ENVIRONMENT & HIGHWAY ---
# Main highway deck
highway = Entity(model='cube', scale=(14, 0.1, 120), color=color.black, position=(0, 0, 50))

# Left and Right glowing borders
left_border = Entity(model='cube', scale=(0.3, 0.8, 120), color=color.cyan, position=(-7, 0.4, 50))
right_border = Entity(model='cube', scale=(0.3, 0.8, 120), color=color.cyan, position=(7, 0.4, 50))

# --- POPULATE SCROLLING NEON HIGHWAY MARKERS ---
for z_pos in range(0, 120, 15):
    marker_l = Entity(model='cube', scale=(0.15, 0.11, 4), color=color.lime, position=(-2.3, 0.01, z_pos))
    marker_r = Entity(model='cube', scale=(0.15, 0.11, 4), color=color.lime, position=(2.3, 0.01, z_pos))
    road_markers.extend([marker_l, marker_r])

# --- PLAYER VEHICLE ---
player = Entity(model='cube', color=color.magenta, scale=(1.4, 0.4, 2.2), position=(0, 0.25, -3), collider='box')
player_wing_l = Entity(parent=player, model='cube', color=color.violet, scale=(0.6, 0.2, 0.8), position=(-0.8, 0, -0.2))
player_wing_r = Entity(parent=player, model='cube', color=color.violet, scale=(0.6, 0.2, 0.8), position=(0.8, 0, -0.2))

# --- HUD & UI PANELS ---
score_panel = Entity(parent=camera.ui, model='quad', color=color.Color(0, 0, 0, 0.6), scale=(0.3, 0.1), position=(-0.7, 0.4))
score_text = Text(parent=score_panel, text=f'SCORE: {score}', scale=1.5, origin=(0, 0), color=color.white)

controls_panel = Text(
    text="[A/D or Arrows] Move  |  [Spacebar] Shoot Laser  |  [R] Restart", 
    position=(0, -0.45), scale=1.2, origin=(0, 0), color=color.light_gray
)

# --- GAME MECHANICS LOOPS ---

def spawn_obstacle():
    if game_over:
        return
    random_x = random.uniform(-4.5, 4.5)
    random_width = random.uniform(1.2, 3.2)
    
    obs = Entity(
        model='cube', 
        color=color.orange, 
        scale=(random_width, random.uniform(1, 2), 1.5), 
        position=(random_x, 0.5, 95), 
        collider='box'
    )
    obstacles.append(obs)
    
    delay_timer = max(0.3, random.uniform(0.4, 1.0) - (game_speed * 0.002))
    invoke(spawn_obstacle, delay=delay_timer)

spawn_obstacle()

def fire_laser():
    if game_over:
        return
    # Left Laser Barrel
    laser_l = Entity(model='cube', color=color.yellow, scale=(0.15, 0.15, 2.5), position=(player.x - 0.7, 0.3, player.z + 1.5), collider='box')
    # Right Laser Barrel
    laser_r = Entity(model='cube', color=color.yellow, scale=(0.15, 0.15, 2.5), position=(player.x + 0.7, 0.3, player.z + 1.5), collider='box')
    
    lasers.extend([laser_l, laser_r])
    
    # Tiny recoil shake visual animation effect
    player.z -= 0.15
    player.animate_z(-3, duration=0.1)

def trigger_explosion_effect(position):
    boom = Entity(model='sphere', color=color.yellow, position=position, scale=0.1)
    boom.animate_scale(4, duration=0.25, curve=curve.linear)
    boom.animate_color(color.clear, duration=0.25)
    destroy(boom, delay=0.3)

# --- ENGINE FRAME UPDATE ---
def update():
    global game_speed, score, game_over
    
    if game_over:
        return

    # 1. Player Navigation Control Mapping
    if held_keys['a'] or held_keys['left arrow']:
        player.x -= 18 * time.dt
    if held_keys['d'] or held_keys['right arrow']:
        player.x += 18 * time.dt
    player.x = clamp(player.x, -5.3, 5.3)

    # 2. Scrolling Neon Road Lines Effect Engine Loop
    for marker in road_markers:
        marker.z -= game_speed * time.dt
        if marker.z > 100:
            if laser in lasers: lasers.remove(laser)
            destroy(laser)

    # 4. Obstacle Lifetime Management and Collision Loops
    for obs in list(obstacles):
        obs.z -= game_speed * time.dt
        
        # Player Crash Check Routine
        if player.intersects(obs).hit:
            game_over = True
            Text(text='CRASH SYSTEM ERROR', origin=(0, -0.5), scale=3.5, color=color.red)
            Text(text='Press [ R ] to Boot Sequence Again', origin=(0, 1), scale=1.8, color=color.white)
            return

        # Safe Dodge clean loop validation pass verification check
        if obs.z < -10:
            if obs in obstacles: obstacles.remove(obs)
            destroy(obs)
            score += 5  
            score_text.text = f'SCORE: {score}'
            game_speed += 0.4

# --- INPUT CONTROLLER LISTENER INTERCEPTS ---
def input(key):
    if key == 'space':
        fire_laser()
        
    if key == 'r' and game_over:
        import sys
        import os
        os.execv(sys.executable, ['python'] + sys.argv)

app.run()
