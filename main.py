import pygame
import random
import sys

# Initialisierung
pygame.init()
WIDTH, HEIGHT = 1600, 1200  # Fenster doppelt so groß
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Invaders")
clock = pygame.time.Clock()

# Farben
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

# Spieler (Dreieck als Raumschiff)
def create_ship_surface(color):
    surf = pygame.Surface((50, 50), pygame.SRCALPHA)
    # Spitze oben, flache Seite unten
    pygame.draw.polygon(
        surf,
        color,
        [(25, 5), (45, 45), (5, 45)]
    )
    return surf

player_img = create_ship_surface(GREEN)
player_rect = player_img.get_rect(midbottom=(WIDTH // 2, HEIGHT - 10))
player_speed_base = 5  # Basisgeschwindigkeit
player_speed = player_speed_base
max_health = 10        # Maximale Lebenspunkte
player_health = max_health

homing_enabled = False  # NEU: Status für Lenkraketen
homing_missiles = []    # NEU: Liste für Raketen

# Gegner
enemy_img = pygame.Surface((40, 30))
enemy_img.fill(RED)
enemies = []
enemy_rows, enemy_cols = 5, 8
for row in range(enemy_rows):
    for col in range(enemy_cols):
        x = 160 + col * 160  # Abstand und Startposition anpassen
        y = 100 + row * 100
        rect = enemy_img.get_rect(topleft=(x, y))
        enemies.append(rect)
enemy_speed = 1

# Schüsse: Kugel statt Rechteck
bullet_radius = 8
bullet_img = pygame.Surface((bullet_radius * 2, bullet_radius * 2), pygame.SRCALPHA)
pygame.draw.circle(bullet_img, WHITE, (bullet_radius, bullet_radius), bullet_radius)
bullets = []

bullet_speed = 12  # <--- Definiere die Geschwindigkeit der Kugeln als positive Zahl

# Score
score = 0
font = pygame.font.SysFont(None, 36)

# Schussmodus
SINGLE_SHOT = 0
DOUBLE_SHOT = 1
shot_mode = SINGLE_SHOT

# Level
level = 1

# Schussrate
shoot_cooldown = 200  # Millisekunden zwischen Schüssen
last_shot_time = 0

# Explosionseinstellungen
explosion_radius = 100  # Pixel
explosion_color = (255, 200, 0)
explosion_duration = 300  # ms

explosion_active = False
explosion_time = 0
explosion_pos = (0, 0)

special_shot_counter = 0

# Powerup-Status
powerup_selected = False
powerup_exploding = False
powerup_double_shot = False  # NEU: Status für Doppelschuss

# Upgrade-Status für 500 Punkte
upgrade_selected_500 = False

# Spielerleben
player_health = 10  # Spieler startet mit 10 Leben

# Upgrade-Status
life_steal = False  # Upgrade-Status

next_powerup_score = 200  # Schwelle für das nächste Powerup-Popup

debug_mode = False
paused = False

Base_HP_Regular = 5

# Enemy spawning variables
enemies_to_spawn = []  # Queue of enemies to spawn
last_spawn_time = 0
spawn_interval = 150   # Milliseconds between enemy spawns (was 500)
wave_started = False

def spawn_enemies():
    global enemies, enemy_speed, enemies_to_spawn, wave_started
    enemies = []
    enemies_to_spawn = []
    wave_started = True
    
    enemy_rows, enemy_cols = 5, 8
    # HP pro Welle
    enemy_hp = int(Base_HP_Regular * (1 + 0.05 * (level - 1)))
    
    # Spawn-Radius um den Spieler (näher am Bildschirmrand)
    spawn_distance = max(WIDTH, HEIGHT) // 2 + 200  # Weniger weit weg
    
    # Prepare enemies to spawn over time
    total_enemies = enemy_rows * enemy_cols
    for i in range(total_enemies):
        # Berechne Position relativ zum Spieler
        offset_x = spawn_distance * (0.5 + 0.5 * (i % 3 - 1))  # Variiere Entfernung leicht
        offset_y = spawn_distance * (0.5 + 0.5 * (i % 3 - 1))
        
        x = player_rect.centerx + offset_x * (1 if (i % 4) < 2 else -1)
        y = player_rect.centery + offset_y * (1 if (i % 4) % 2 == 0 else -1)
        
        # Zusätzliche Streuung für natürlichere Verteilung
        x += random.randint(-300, 300)
        y += random.randint(-300, 300)
        
        rect = enemy_img.get_rect(center=(x, y))
        enemies_to_spawn.append({"rect": rect, "hp": enemy_hp})
    
    enemy_speed = 1 + (level - 1) * 0.15  # Weniger Steigerung pro Welle

def update_enemy_spawning():
    global last_spawn_time, wave_started
    current_time = pygame.time.get_ticks()
    
    if wave_started and enemies_to_spawn and current_time - last_spawn_time > spawn_interval:
        # Spawn next enemy from queue
        new_enemy = enemies_to_spawn.pop(0)
        # Spawn-Radius um den Spieler (näher am Bildschirmrand)
        spawn_distance = max(WIDTH, HEIGHT) // 2 + 200
        offset_x = random.choice([-spawn_distance, spawn_distance])
        offset_y = random.choice([-spawn_distance, spawn_distance])
        new_enemy["rect"].centerx = player_rect.centerx + offset_x + random.randint(-200, 200)
        new_enemy["rect"].centery = player_rect.centery + offset_y + random.randint(-200, 200)
        
        enemies.append(new_enemy)
        last_spawn_time = current_time
    
    # Check if wave is complete
    if not enemies_to_spawn and not enemies:
        wave_started = False

# Entferne diesen initialen Gegner-Spawn:
# spawn_enemies()

def trigger_explosion(center):
    global explosion_active, explosion_time, explosion_pos
    explosion_active = True
    explosion_time = pygame.time.get_ticks()
    explosion_pos = center
    # Flächenschaden an Gegnern
    for enemy in enemies[:]:
        dist = ((enemy["rect"].centerx - center[0]) ** 2 + (enemy["rect"].centery - center[1]) ** 2) ** 0.5
        if dist <= explosion_radius:
            enemy["hp"] -= 20  # Explosion-Schaden
    # Entferne Gegner mit HP <= 0
    enemies[:] = [e for e in enemies if e["hp"] > 0]

# Vorberechnete Schriftarten für Menüs und Anzeigen
button_font = pygame.font.SysFont(None, 120)
title_font = pygame.font.SysFont(None, 180)
font_big = pygame.font.SysFont(None, 48)
font_btn = pygame.font.SysFont(None, 36)

# Kamera-Variablen
camera_x = 0
camera_y = 0

def draw():
    global camera_x, camera_y, explosion_active
    screen.fill((0, 0, 0))
    
    # Kamera folgt dem Spieler (Spieler bleibt in der Bildschirmmitte)
    camera_x = player_rect.centerx - WIDTH // 2
    camera_y = player_rect.centery - HEIGHT // 2
    
    # Spieler-Rotation berechnen
    mouse_x, mouse_y = pygame.mouse.get_pos()
    # Mausposition in Weltkoordinaten umrechnen
    world_mouse_x = mouse_x + camera_x
    world_mouse_y = mouse_y + camera_y
    px, py = player_rect.centerx, player_rect.centery
    dx = world_mouse_x - px
    dy = world_mouse_y - py
    angle = pygame.math.Vector2(dx, dy).angle_to((0, 1))  # Korrekte Richtung
    rotated_img = pygame.transform.rotate(player_img, angle)
    # Spieler immer in der Bildschirmmitte zeichnen
    screen_player_rect = rotated_img.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(rotated_img, screen_player_rect)
    
    # Gegner zeichnen (mit Kamera-Offset)
    for enemy in enemies:
        screen_x = enemy["rect"].x - camera_x
        screen_y = enemy["rect"].y - camera_y
        # Nur zeichnen, wenn auf dem Bildschirm sichtbar
        if -50 <= screen_x <= WIDTH + 50 and -50 <= screen_y <= HEIGHT + 50:
            screen.blit(enemy_img, (screen_x, screen_y))
    
    # Kugeln zeichnen (mit Kamera-Offset)
    for bullet in bullets:
        rect, dx, dy = bullet[:3]
        screen_x = rect.centerx - camera_x
        screen_y = rect.centery - camera_y
        if -20 <= screen_x <= WIDTH + 20 and -20 <= screen_y <= HEIGHT + 20:
            bullet_rect = bullet_img.get_rect(center=(screen_x, screen_y))
            screen.blit(bullet_img, bullet_rect)
    
    # Raketen zeichnen (mit Kamera-Offset)
    for missile in homing_missiles:
        screen_x = missile["rect"].x - camera_x
        screen_y = missile["rect"].y - camera_y
        if -20 <= screen_x <= WIDTH + 20 and -20 <= screen_y <= HEIGHT + 20:
            screen_rect = pygame.Rect(screen_x, screen_y, missile["rect"].width, missile["rect"].height)
            pygame.draw.rect(screen, (255, 120, 0), screen_rect)
    
    # Explosion zeichnen (mit Kamera-Offset)
    if explosion_active:
        if pygame.time.get_ticks() - explosion_time < explosion_duration:
            screen_explosion_x = explosion_pos[0] - camera_x
            screen_explosion_y = explosion_pos[1] - camera_y
            if -explosion_radius <= screen_explosion_x <= WIDTH + explosion_radius and -explosion_radius <= screen_explosion_y <= HEIGHT + explosion_radius:
                pygame.draw.circle(screen, explosion_color, (screen_explosion_x, screen_explosion_y), explosion_radius, 4)
        else:
            explosion_active = False
    
    # UI-Elemente (bleiben an fester Position)
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (10, 10))
    # Modus-Anzeige anpassen
    mode_text = []
    if powerup_double_shot:
        mode_text.append("Doppelschuss")
    if powerup_exploding:
        mode_text.append("Explodierende Kugeln")
    if not mode_text:
        mode_text.append("Einfach Schuss")
    mode_render = font.render(f"Modus: {', '.join(mode_text)}", True, WHITE)
    screen.blit(mode_render, (10, 50))
    level_text = font.render(f"Level: {level}", True, WHITE)
    screen.blit(level_text, (10, 90))
    # Health bar anzeigen
    bar_width = 200
    bar_height = 30
    bar_x = 10
    bar_y = 130
    pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height), border_radius=8)
    health_fill = int(bar_width * (player_health / max_health))
    pygame.draw.rect(screen, GREEN, (bar_x, bar_y, health_fill, bar_height), border_radius=8)
    health_text = font.render(f"Health: {player_health}/{max_health}", True, WHITE)
    screen.blit(health_text, (bar_x + bar_width + 15, bar_y))
    # Gegner HP oben links anzeigen
    if enemies:
        hp_text = font.render(f"Gegner HP: {enemies[0]['hp']}", True, RED)
        screen.blit(hp_text, (10, 170))
    
    pygame.display.flip()

def move_enemies():
    for enemy in enemies:
        dx = player_rect.centerx - enemy["rect"].centerx
        dy = player_rect.centery - enemy["rect"].centery
        dist = max(1, (dx**2 + dy**2) ** 0.5)
        step_x = enemy_speed * dx / dist
        step_y = enemy_speed * dy / dist
        enemy["rect"].x += step_x
        enemy["rect"].y += step_y

def move_homing_missiles():
    for missile in homing_missiles[:]:
        # Finde den nächsten Gegner
        if not enemies:
            missile["rect"].y -= missile["speed"]
        else:
            nearest = min(
                enemies,
                key=lambda e: (e["rect"].centerx - missile["rect"].centerx) ** 2 + (e["rect"].centery - missile["rect"].centery) ** 2
            )
            dx = nearest["rect"].centerx - missile["rect"].centerx
            dy = nearest["rect"].centery - missile["rect"].centery
            dist = max(1, (dx**2 + dy**2)**0.5)
            missile["rect"].x += int(missile["speed"] * dx / dist)
            missile["rect"].y += int(missile["speed"] * dy / dist)
        # Entferne Rakete, wenn sie zu weit vom Spieler entfernt ist (statt Bildschirmgrenzen)
        distance_to_player = ((missile["rect"].centerx - player_rect.centerx) ** 2 + (missile["rect"].centery - player_rect.centery) ** 2) ** 0.5
        if distance_to_player > 2500:
            homing_missiles.remove(missile)

def check_collisions():
    global score, explosion_active, explosion_time, explosion_pos, special_shot_counter, player_health
    hit_enemies = []
    for bullet in bullets[:]:
        rect = bullet[0]
        special = bullet[3] if len(bullet) > 3 else False
        collided = False
        for enemy in enemies:
            if enemy in hit_enemies:
                continue
            if rect.colliderect(enemy["rect"]):
                if special and not explosion_active:
                    trigger_explosion(rect.center)
                # Schuss-Schaden
                enemy["hp"] -= 8
                bullets.remove(bullet)
                if enemy["hp"] <= 0:
                    hit_enemies.append(enemy)
                    score += 10
                    # Life Steal: 1% Chance bei Kill
                    if life_steal and random.random() < 0.01 and player_health < max_health:
                        player_health += 1
                collided = True
                break
        # Wenn ein Gegner getroffen wurde, keine weiteren Kollisionen für diesen Schuss prüfen
        if collided:
            continue
    # Entferne getroffene Gegner nach der Schleife
    for enemy in hit_enemies:
        if enemy in enemies:
            enemies.remove(enemy)

def check_homing_collisions():
    global score, player_health
    for missile in homing_missiles[:]:
        for enemy in enemies:
            if missile["rect"].colliderect(enemy["rect"]):
                enemy["hp"] -= 20  # Homing missile damage
                homing_missiles.remove(missile)
                if enemy["hp"] <= 0:
                    enemies.remove(enemy)
                    score += 10
                    # Life Steal: 1% Chance bei Kill
                    if life_steal and random.random() < 0.01 and player_health < max_health:
                        player_health += 1
                break

def menu_screen():
    global debug_mode
    play_text = button_font.render("PLAY", True, WHITE)
    quit_text = button_font.render("QUIT", True, WHITE)
    debug_text = button_font.render("Play_Debug_Mode", True, WHITE)
    play_rect = play_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100))
    debug_rect = debug_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 250))
    quit_rect = quit_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 400))
    title_text = title_font.render("Space Invaders", True, GREEN)
    title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 200))
    while True:
        screen.fill((0, 0, 0))
        screen.blit(title_text, title_rect)
        pygame.draw.rect(screen, GREEN, play_rect.inflate(60, 40), border_radius=20)
        screen.blit(play_text, play_rect)
        pygame.draw.rect(screen, (120, 120, 255), debug_rect.inflate(60, 40), border_radius=20)
        screen.blit(debug_text, debug_rect)
        pygame.draw.rect(screen, RED, quit_rect.inflate(60, 40), border_radius=20)
        screen.blit(quit_text, quit_rect)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if play_rect.collidepoint(event.pos):
                    debug_mode = False
                    return
                if debug_rect.collidepoint(event.pos):
                    debug_mode = True
                    return
                if quit_rect.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    debug_mode = False
                    return

def reset_game():
    global player_rect, score, level, shot_mode, last_shot_time, special_shot_counter
    global powerup_selected, powerup_exploding, powerup_double_shot, upgrade_selected_500, player_health, life_steal
    global player_speed, player_speed_base, homing_enabled, homing_missiles, max_health
    player_rect = player_img.get_rect(midbottom=(WIDTH // 2, HEIGHT - 10))
    score = 0
    level = 1
    shot_mode = SINGLE_SHOT
    last_shot_time = 0
    special_shot_counter = 0
    powerup_selected = False
    powerup_exploding = False
    powerup_double_shot = False
    upgrade_selected_500 = False
    max_health = 10
    player_health = max_health
    life_steal = False
    player_speed_base = 5
    player_speed = player_speed_base
    homing_enabled = False
    homing_missiles.clear()
    spawn_enemies()
    bullets.clear()

def game_over():
    over_text = font.render("GAME OVER", True, RED)
    screen.blit(over_text, (WIDTH // 2 - 100, HEIGHT // 2))
    pygame.display.flip()
    pygame.time.wait(2000)
    menu_screen()
    reset_game()

def damage_player(amount=1):
    global player_health
    player_health -= amount
    if player_health <= 0:
        game_over()

# Powerup-Funktionen
def set_powerup_exploding():
    global powerup_exploding
    powerup_exploding = True

def set_powerup_double_shot():
    global powerup_double_shot
    powerup_double_shot = True

def set_powerup_life_steal():
    global life_steal
    life_steal = True

def set_powerup_more_health():
    global max_health, player_health
    add_hp = max(1, int(max_health * 0.25))
    max_health += add_hp
    player_health += add_hp

def set_powerup_faster_ship():
    global player_speed_base
    player_speed_base *= 1.15  # float statt int!

def set_powerup_homing():
    global homing_enabled
    homing_enabled = True

powerup_pool = [
    {
        "name": "Explodierende Kugeln",
        "color": (255, 200, 0),
        "apply": lambda: set_powerup_exploding()
    },
    {
        "name": "Doppelschuss",
        "color": (0, 255, 255),
        "apply": lambda: set_powerup_double_shot()
    },
    {
        "name": "Life Steal",
        "color": (255, 0, 255),
        "apply": lambda: set_powerup_life_steal()
    },
    {
        "name": "Mehr Leben",
        "color": (0, 200, 0),
        "apply": lambda: set_powerup_more_health()
    },
    {
        "name": "Schnellerer Flug",
        "color": (0, 120, 255),
        "apply": lambda: set_powerup_faster_ship()
    },
    {
        "name": "Lenkraketen",
        "color": (255, 120, 0),
        "apply": lambda: set_powerup_homing()
    },
    # Hier können weitere Powerups hinzugefügt werden
]

def powerup_selection_pygame():
    global powerup_selected
    popup_width, popup_height = 500, 300
    popup_rect = pygame.Rect((WIDTH - popup_width)//2, (HEIGHT - popup_height)//2, popup_width, popup_height)
    button_w, button_h = 200, 60
    options = random.sample(powerup_pool, 2)
    btn1_rect = pygame.Rect(popup_rect.centerx - button_w - 20, popup_rect.centery, button_w, button_h)
    btn2_rect = pygame.Rect(popup_rect.centerx + 20, popup_rect.centery, button_w, button_h)

    txt = font_big.render("Wähle dein Powerup!", True, WHITE)
    txt1 = font_btn.render(options[0]["name"], True, WHITE)
    txt2 = font_btn.render(options[1]["name"], True, WHITE)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn1_rect.collidepoint(event.pos):
                    options[0]["apply"]()
                    powerup_selected = True
                    running = False
                if btn2_rect.collidepoint(event.pos):
                    options[1]["apply"]()
                    powerup_selected = True
                    running = False
        pygame.draw.rect(screen, (30,30,30), popup_rect, border_radius=20)
        pygame.draw.rect(screen, options[0]["color"], btn1_rect, border_radius=10)
        pygame.draw.rect(screen, options[1]["color"], btn2_rect, border_radius=10)
        screen.blit(txt, (popup_rect.centerx - txt.get_width()//2, popup_rect.top + 40))
        screen.blit(txt1, (btn1_rect.centerx - txt1.get_width()//2, btn1_rect.centery - txt1.get_height()//2))
        screen.blit(txt2, (btn2_rect.centerx - txt2.get_width()//2, btn2_rect.centery - txt2.get_height()//2))
        pygame.display.flip()
        clock.tick(60)

def upgrade_selection_pygame():
    popup_width, popup_height = 500, 300
    popup_rect = pygame.Rect((WIDTH - popup_width)//2, (HEIGHT - popup_height)//2, popup_width, popup_height)
    button_w, button_h = 200, 60
    options = random.sample(powerup_pool, 2)
    btn1_rect = pygame.Rect(popup_rect.centerx - button_w - 20, popup_rect.centery, button_w, button_h)
    btn2_rect = pygame.Rect(popup_rect.centerx + 20, popup_rect.centery, button_w, button_h)

    txt = font_big.render("Wähle ein Upgrade!", True, WHITE)
    txt1 = font_btn.render(options[0]["name"], True, WHITE)
    txt2 = font_btn.render(options[1]["name"], True, WHITE)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn1_rect.collidepoint(event.pos):
                    options[0]["apply"]()
                    running = False
                if btn2_rect.collidepoint(event.pos):
                    options[1]["apply"]()
                    running = False
        pygame.draw.rect(screen, (30,30,30), popup_rect, border_radius=20)
        pygame.draw.rect(screen, options[0]["color"], btn1_rect, border_radius=10)
        pygame.draw.rect(screen, options[1]["color"], btn2_rect, border_radius=10)
        screen.blit(txt, (popup_rect.centerx - txt.get_width()//2, popup_rect.top + 40))
        screen.blit(txt1, (btn1_rect.centerx - txt1.get_width()//2, btn1_rect.centery - txt1.get_height()//2))
        screen.blit(txt2, (btn2_rect.centerx - txt2.get_width()//2, btn2_rect.centery - txt2.get_height()//2))
        pygame.display.flip()
        clock.tick(60)

# --- Die folgenden Funktionen müssen VOR der Hauptspiel-Schleife stehen ---
def shoot_bullet(special=False):
    # Mausposition in Weltkoordinaten umrechnen
    mouse_x, mouse_y = pygame.mouse.get_pos()
    world_mouse_x = mouse_x + camera_x
    world_mouse_y = mouse_y + camera_y
    px, py = player_rect.centerx, player_rect.centery
    dx = world_mouse_x - px
    dy = world_mouse_y - py
    dist = max(1, (dx**2 + dy**2) ** 0.5)
    speed = abs(bullet_speed)
    dir_x = speed * dx / dist
    dir_y = speed * dy / dist
    bullet_rect = bullet_img.get_rect(center=(px, py))
    # Spezialschuss-Flag nur, wenn powerup_exploding aktiv ist
    return (bullet_rect, dir_x, dir_y, special if powerup_exploding else False)

def shoot_double_bullet(special=False):
    # Mausposition in Weltkoordinaten umrechnen
    mouse_x, mouse_y = pygame.mouse.get_pos()
    world_mouse_x = mouse_x + camera_x
    world_mouse_y = mouse_y + camera_y
    px, py = player_rect.centerx, player_rect.centery
    dx = world_mouse_x - px
    dy = world_mouse_y - py
    dist = max(1, (dx**2 + dy**2) ** 0.5)
    speed = abs(bullet_speed)
    dir_x = speed * dx / dist
    dir_y = speed * dy / dist
    offset = 12
    bullet_left = bullet_img.get_rect(center=(px - offset, py))
    bullet_right = bullet_img.get_rect(center=(px + offset, py))
    # Spezialschuss-Flag nur, wenn powerup_exploding aktiv ist
    return [
        (bullet_left, dir_x, dir_y, special if powerup_exploding else False),
        (bullet_right, dir_x, dir_y, special if powerup_exploding else False)
    ]

def shoot_homing_missile():
    px, py = player_rect.centerx, player_rect.centery
    missile_rect = pygame.Rect(px-8, py-24, 16, 32)
    homing_missiles.append({"rect": missile_rect, "speed": 16})

def check_enemy_player_collision():
    for enemy in enemies[:]:
        if enemy["rect"].colliderect(player_rect):
            damage_player(1)
            # Gegner nach Kollision entfernen (optional, falls sie nicht mehrfach treffen sollen)
            enemies.remove(enemy)
            break

# --- Spiel startet immer mit Menü ---
menu_screen()
reset_game()

# Hauptspiel-Schleife
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        # Schießen mit rechter Maustaste für Lenkraketen
        if homing_enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            shoot_homing_missile()
        # Debug Mode: Pause/Unpause mit Leertaste
        if debug_mode and event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            paused = not paused

    if debug_mode and paused:
        # Powerup-Spam: Zeige endlos Popups bis Leertaste erneut gedrückt wird
        while paused:
            # Powerup-Auswahl und Anwendung
            popup_width, popup_height = 500, 300
            popup_rect = pygame.Rect((WIDTH - popup_width)//2, (HEIGHT - popup_height)//2, popup_width, popup_height)
            button_w, button_h = 200, 60
            options = random.sample(powerup_pool, 2)
            btn1_rect = pygame.Rect(popup_rect.centerx - button_w - 20, popup_rect.centery, button_w, button_h)
            btn2_rect = pygame.Rect(popup_rect.centerx + 20, popup_rect.centery, button_w, button_h)
            txt = font_big.render("DEBUG: Wähle Powerup!", True, WHITE)
            txt1 = font_btn.render(options[0]["name"], True, WHITE)
            txt2 = font_btn.render(options[1]["name"], True, WHITE)
            selected = None
            while selected is None and paused:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                        paused = False
                        break
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if btn1_rect.collidepoint(event.pos):
                            selected = options[0]
                        if btn2_rect.collidepoint(event.pos):
                            selected = options[1]
                screen.fill((0,0,0))
                pygame.draw.rect(screen, (30,30,30), popup_rect, border_radius=20)
                pygame.draw.rect(screen, options[0]["color"], btn1_rect, border_radius=10)
                pygame.draw.rect(screen, options[1]["color"], btn2_rect, border_radius=10)
                screen.blit(txt, (popup_rect.centerx - txt.get_width()//2, popup_rect.top + 40))
                screen.blit(txt1, (btn1_rect.centerx - txt1.get_width()//2, btn1_rect.centery - txt1.get_height()//2))
                screen.blit(txt2, (btn2_rect.centerx - txt2.get_width()//2, btn2_rect.centery - txt2.get_height()//2))
                pygame.display.flip()
                clock.tick(60)
            if selected is not None:
                selected["apply"]()
        continue

    # Powerup-Popup bei Erreichen der Schwelle
    if score >= next_powerup_score:
        if next_powerup_score == 200 and not powerup_selected:
            powerup_selection_pygame()
            powerup_selected = True
            next_powerup_score = 500
        elif next_powerup_score == 500 and not upgrade_selected_500:
            upgrade_selection_pygame()
            upgrade_selected_500 = True
            next_powerup_score = 1000
        else:
            upgrade_selection_pygame()
            # Nächste Schwelle: +1000 + 25% der letzten Schwelle
            next_powerup_score += 1000 + int(next_powerup_score * 0.25)

    # Powerup-Auswahl bei 200 Punkten
    if not powerup_selected and score >= 200:
        powerup_selection_pygame()

    # Upgrade-Auswahl bei 500 Punkten
    if not upgrade_selected_500 and score >= 500:
        upgrade_selection_pygame()
        upgrade_selected_500 = True

    current_time = pygame.time.get_ticks()
    keys = pygame.key.get_pressed()

    # Geschwindigkeit immer aktuell setzen
    player_speed = player_speed_base

    # Bewegung mit WASD statt Pfeiltasten
    if keys[pygame.K_a]:
        player_rect.x -= round(player_speed)
    if keys[pygame.K_d]:
        player_rect.x += round(player_speed)
    if keys[pygame.K_w]:
        player_rect.y -= round(player_speed)
    if keys[pygame.K_s]:
        player_rect.y += round(player_speed)

    # Schießen mit linker Maustaste
    if pygame.mouse.get_pressed()[0]:
        if current_time - last_shot_time > shoot_cooldown:
            special = False
            if powerup_exploding:
                special_shot_counter += 1
                if special_shot_counter % 10 == 0:
                    special = True
            # Doppelschuss unabhängig von Explodierende Kugeln
            if powerup_double_shot:
                bullets.extend(shoot_double_bullet(special))
            else:
                bullets.append(shoot_bullet(special))
            last_shot_time = current_time

    # Schüsse bewegen
    for bullet in bullets[:]:
        rect, dx, dy = bullet[:3]
        rect.x += dx
        rect.y += dy
        # Entferne Kugeln basierend auf Entfernung zum Spieler statt fixen Bildschirmgrenzen
        distance_to_player = ((rect.centerx - player_rect.centerx) ** 2 + (rect.centery - player_rect.centery) ** 2) ** 0.5
        if distance_to_player > 2000:  # Entferne Kugeln wenn sie zu weit vom Spieler entfernt sind
            bullets.remove(bullet)

    move_enemies()
    move_homing_missiles()
    check_collisions()
    check_homing_collisions()
    check_enemy_player_collision()

    # Prüfe auf Game Over durch Gegner-Kollision
    # for enemy in enemies:
    #     if enemy["rect"].colliderect(player_rect):
    #         damage_player(1)
    #         if enemy in enemies:
    #             enemies.remove(enemy)
    #         break

    # Prüfe auf Level-Wechsel
    if not enemies and not enemies_to_spawn and not wave_started:
        level += 1
        spawn_enemies()
    
    # Update enemy spawning
    update_enemy_spawning()

    draw()
    clock.tick(60)