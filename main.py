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
player_speed = 5

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

# Upgrade-Status für 500 Punkte
upgrade_selected_500 = False

# Spielerleben
player_health = 10  # Spieler startet mit 10 Leben

# Upgrade-Status
life_steal = False  # Upgrade-Status

def spawn_enemies():
    global enemies, enemy_speed
    enemies = []
    enemy_rows, enemy_cols = 5, 8
    for row in range(enemy_rows):
        for col in range(enemy_cols):
            x = 160 + col * 160
            y = 100 + row * 100
            rect = enemy_img.get_rect(topleft=(x, y))
            enemies.append(rect)
    enemy_speed = 1 + (level - 1) * 0.5  # Geschwindigkeit steigt mit Level

# Initialer Gegner-Spawn
spawn_enemies()

def trigger_explosion(center):
    global explosion_active, explosion_time, explosion_pos
    explosion_active = True
    explosion_time = pygame.time.get_ticks()
    explosion_pos = center
    # Flächenschaden an Gegnern
    for enemy in enemies[:]:
        dist = ((enemy.centerx - center[0]) ** 2 + (enemy.centery - center[1]) ** 2) ** 0.5
        if dist <= explosion_radius:
            enemies.remove(enemy)

# Vorberechnete Schriftarten für Menüs und Anzeigen
button_font = pygame.font.SysFont(None, 120)
title_font = pygame.font.SysFont(None, 180)
font_big = pygame.font.SysFont(None, 48)
font_btn = pygame.font.SysFont(None, 36)

def draw():
    screen.fill((0, 0, 0))
    # Spieler-Rotation berechnen
    mouse_x, mouse_y = pygame.mouse.get_pos()
    px, py = player_rect.centerx, player_rect.centery
    dx = mouse_x - px
    dy = mouse_y - py
    angle = pygame.math.Vector2(dx, dy).angle_to((0, 1))  # Korrekte Richtung
    rotated_img = pygame.transform.rotate(player_img, angle)
    rotated_rect = rotated_img.get_rect(center=player_rect.center)
    screen.blit(rotated_img, rotated_rect)
    for enemy in enemies:
        screen.blit(enemy_img, enemy)
    for bullet in bullets:
        rect, dx, dy = bullet[:3]  # Nur die ersten drei Werte entpacken
        bullet_rect = bullet_img.get_rect(center=rect.center)
        screen.blit(bullet_img, bullet_rect)
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (10, 10))
    mode_text = "Einfach Schuss" if shot_mode == SINGLE_SHOT else "Doppelkanone"
    mode_render = font.render(f"Modus: {mode_text}", True, WHITE)
    screen.blit(mode_render, (10, 50))
    level_text = font.render(f"Level: {level}", True, WHITE)
    screen.blit(level_text, (10, 90))
    # Health bar anzeigen
    max_health = 10
    bar_width = 200
    bar_height = 30
    bar_x = 10
    bar_y = 130
    pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height), border_radius=8)
    health_fill = int(bar_width * (player_health / max_health))
    pygame.draw.rect(screen, GREEN, (bar_x, bar_y, health_fill, bar_height), border_radius=8)
    health_text = font.render(f"Health: {player_health}/{max_health}", True, WHITE)
    screen.blit(health_text, (bar_x + bar_width + 15, bar_y))
    # Explosion zeichnen
    global explosion_active  # Fix: global muss außerhalb von if stehen
    if explosion_active:
        if pygame.time.get_ticks() - explosion_time < explosion_duration:
            pygame.draw.circle(screen, explosion_color, explosion_pos, explosion_radius, 4)
        else:
            explosion_active = False
    pygame.display.flip()

def move_enemies():
    for enemy in enemies:
        dx = player_rect.centerx - enemy.centerx
        dy = player_rect.centery - enemy.centery
        dist = max(1, (dx**2 + dy**2) ** 0.5)
        # Schrittgröße pro Frame (enemy_speed bleibt als Basis)
        step_x = enemy_speed * dx / dist
        step_y = enemy_speed * dy / dist
        enemy.x += step_x
        enemy.y += step_y

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
            if rect.colliderect(enemy):
                if special and not explosion_active:
                    trigger_explosion(rect.center)
                bullets.remove(bullet)
                hit_enemies.append(enemy)
                score += 10
                # Life Steal: 1% Chance bei Kill
                if life_steal and random.random() < 0.01 and player_health < 10:
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

def menu_screen():
    play_text = button_font.render("PLAY", True, WHITE)
    quit_text = button_font.render("QUIT", True, WHITE)
    play_rect = play_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100))
    quit_rect = quit_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 300))
    title_text = title_font.render("Space Invaders", True, GREEN)
    title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 200))
    while True:
        screen.fill((0, 0, 0))
        screen.blit(title_text, title_rect)
        pygame.draw.rect(screen, GREEN, play_rect.inflate(60, 40), border_radius=20)
        screen.blit(play_text, play_rect)
        pygame.draw.rect(screen, RED, quit_rect.inflate(60, 40), border_radius=20)
        screen.blit(quit_text, quit_rect)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if play_rect.collidepoint(event.pos):
                    return
                if quit_rect.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    return

def reset_game():
    global player_rect, score, level, shot_mode, last_shot_time, special_shot_counter, powerup_selected, powerup_exploding, upgrade_selected_500, player_health, life_steal
    player_rect = player_img.get_rect(midbottom=(WIDTH // 2, HEIGHT - 10))
    score = 0
    level = 1
    shot_mode = SINGLE_SHOT
    last_shot_time = 0
    special_shot_counter = 0
    powerup_selected = False
    powerup_exploding = False
    upgrade_selected_500 = False
    player_health = 10  # Leben zurücksetzen
    life_steal = False  # Upgrade zurücksetzen
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

def powerup_selection_pygame():
    global powerup_selected, powerup_exploding, shot_mode
    popup_width, popup_height = 500, 300
    popup_rect = pygame.Rect((WIDTH - popup_width)//2, (HEIGHT - popup_height)//2, popup_width, popup_height)
    button_w, button_h = 200, 60
    btn1_rect = pygame.Rect(popup_rect.centerx - button_w - 20, popup_rect.centery, button_w, button_h)
    btn2_rect = pygame.Rect(popup_rect.centerx + 20, popup_rect.centery, button_w, button_h)
    
    # Vorberechnung der Texte
    txt = font_big.render("Wähle dein Powerup!", True, WHITE)
    txt1 = font_btn.render("Explodierende Kugeln", True, WHITE)
    txt2 = font_btn.render("Doppelschuss", True, WHITE)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn1_rect.collidepoint(event.pos):
                    powerup_selected = True
                    powerup_exploding = True
                    shot_mode = SINGLE_SHOT
                    running = False
                if btn2_rect.collidepoint(event.pos):
                    powerup_selected = True
                    powerup_exploding = False
                    shot_mode = DOUBLE_SHOT
                    running = False
        # Zeichne Popup
        pygame.draw.rect(screen, (30,30,30), popup_rect, border_radius=20)
        pygame.draw.rect(screen, GREEN, btn1_rect, border_radius=10)
        pygame.draw.rect(screen, RED, btn2_rect, border_radius=10)
        screen.blit(txt, (popup_rect.centerx - txt.get_width()//2, popup_rect.top + 40))
        screen.blit(txt1, (btn1_rect.centerx - txt1.get_width()//2, btn1_rect.centery - txt1.get_height()//2))
        screen.blit(txt2, (btn2_rect.centerx - txt2.get_width()//2, btn2_rect.centery - txt2.get_height()//2))
        pygame.display.flip()
        clock.tick(60)

def shoot_bullet(special=False):
    mouse_x, mouse_y = pygame.mouse.get_pos()
    px, py = player_rect.centerx, player_rect.centery
    dx = mouse_x - px
    dy = mouse_y - py
    dist = max(1, (dx**2 + dy**2) ** 0.5)
    speed = abs(bullet_speed)
    dir_x = speed * dx / dist
    dir_y = speed * dy / dist
    bullet_rect = bullet_img.get_rect(center=(px, py))
    # Spezialschuss-Flag nur, wenn powerup_exploding aktiv ist
    return (bullet_rect, dir_x, dir_y, special if powerup_exploding else False)

def shoot_double_bullet(special=False):
    mouse_x, mouse_y = pygame.mouse.get_pos()
    px, py = player_rect.centerx, player_rect.centery
    dx = mouse_x - px
    dy = mouse_y - py
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

def upgrade_selection_pygame():
    global powerup_exploding, shot_mode, life_steal
    popup_width, popup_height = 500, 300
    popup_rect = pygame.Rect((WIDTH - popup_width)//2, (HEIGHT - popup_height)//2, popup_width, popup_height)
    button_w, button_h = 200, 60
    btn1_rect = pygame.Rect(popup_rect.centerx - button_w - 20, popup_rect.centery, button_w, button_h)
    btn2_rect = pygame.Rect(popup_rect.centerx + 20, popup_rect.centery, button_w, button_h)

    # Bestimme Optionen basierend auf vorherigem Powerup
    if powerup_exploding:
        option1_text = "Doppelschuss"
        option2_text = "Life Steal"
    else:
        option1_text = "Explodierende Kugeln"
        option2_text = "Life Steal"

    txt = font_big.render("Wähle ein Upgrade!", True, WHITE)
    txt1 = font_btn.render(option1_text, True, WHITE)
    txt2 = font_btn.render(option2_text, True, WHITE)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn1_rect.collidepoint(event.pos):
                    # Option 1: Das andere Powerup aktivieren
                    if powerup_exploding:
                        shot_mode = DOUBLE_SHOT
                    else:
                        powerup_exploding = True
                    running = False
                if btn2_rect.collidepoint(event.pos):
                    # Option 2: Life Steal aktivieren
                    life_steal = True
                    running = False
        pygame.draw.rect(screen, (30,30,30), popup_rect, border_radius=20)
        screen.blit(txt, (popup_rect.centerx - txt.get_width()//2, popup_rect.top + 40))
        pygame.draw.rect(screen, GREEN, btn1_rect, border_radius=10)
        pygame.draw.rect(screen, RED, btn2_rect, border_radius=10)
        screen.blit(txt1, (btn1_rect.centerx - txt1.get_width()//2, btn1_rect.centery - txt1.get_height()//2))
        screen.blit(txt2, (btn2_rect.centerx - txt2.get_width()//2, btn2_rect.centery - txt2.get_height()//2))
        pygame.display.flip()
        clock.tick(60)

# Menü vor Spielstart
menu_screen()
reset_game()

# Hauptspiel-Schleife
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    # Powerup-Auswahl bei 200 Punkten
    if not powerup_selected and score >= 200:
        powerup_selection_pygame()

    # Upgrade-Auswahl bei 500 Punkten
    if not upgrade_selected_500 and score >= 500:
        upgrade_selection_pygame()
        upgrade_selected_500 = True

    current_time = pygame.time.get_ticks()
    keys = pygame.key.get_pressed()
    # Bewegung mit WASD statt Pfeiltasten
    if keys[pygame.K_a] and player_rect.left > 0:
        player_rect.x -= player_speed
    if keys[pygame.K_d] and player_rect.right < WIDTH:
        player_rect.x += player_speed
    if keys[pygame.K_w] and player_rect.top > 0:
        player_rect.y -= player_speed
    if keys[pygame.K_s] and player_rect.bottom < HEIGHT:
        player_rect.y += player_speed

    # Dauerfeuer bei gedrückter Leertaste
    if keys[pygame.K_SPACE]:
        if current_time - last_shot_time > shoot_cooldown:
            special = False
            if powerup_exploding:
                special_shot_counter += 1
                if special_shot_counter % 10 == 0:
                    special = True
            if shot_mode == SINGLE_SHOT:
                bullets.append(shoot_bullet(special))
            elif shot_mode == DOUBLE_SHOT:
                bullets.extend(shoot_double_bullet(special))
            last_shot_time = current_time

    # Schüsse bewegen
    for bullet in bullets[:]:
        rect, dx, dy = bullet[:3]
        rect.x += dx
        rect.y += dy
        if rect.bottom < 0 or rect.top > HEIGHT or rect.right < 0 or rect.left > WIDTH:
            bullets.remove(bullet)

    move_enemies()
    check_collisions()

    # Prüfe auf Game Over durch Gegner-Kollision
    for enemy in enemies:
        if enemy.colliderect(player_rect):
            damage_player(1)
            # Gegner nach Kollision entfernen (optional, falls sie nicht mehrfach treffen sollen)
            enemies.remove(enemy)
            break

    # Prüfe auf Level-Wechsel
    if not enemies:
        level += 1
        spawn_enemies()

    draw()
    clock.tick(60)