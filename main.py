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

# Spieler (Einzelnes Raumschiff)
player_img = pygame.Surface((50, 30))
player_img.fill(GREEN)
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
enemy_direction = 1
enemy_speed = 1

# Schüsse
bullets = []
bullet_img = pygame.Surface((5, 15))
bullet_img.fill(WHITE)
bullet_speed = -7

# Score
score = 0
font = pygame.font.SysFont(None, 36)

# Schussmodus
SINGLE_SHOT = 0
DOUBLE_SHOT = 1
shot_mode = SINGLE_SHOT

# Level
level = 1

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

def draw():
    screen.fill((0, 0, 0))
    screen.blit(player_img, player_rect)
    for enemy in enemies:
        screen.blit(enemy_img, enemy)
    for bullet in bullets:
        screen.blit(bullet_img, bullet)
    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (10, 10))
    mode_text = "Einfach Schuss" if shot_mode == SINGLE_SHOT else "Doppelkanone"
    mode_render = font.render(f"Modus: {mode_text}", True, WHITE)
    screen.blit(mode_render, (10, 50))
    level_text = font.render(f"Level: {level}", True, WHITE)
    screen.blit(level_text, (10, 90))
    pygame.display.flip()

def move_enemies():
    global enemy_direction
    move_down = False
    for enemy in enemies:
        enemy.x += enemy_direction * enemy_speed
        if enemy.right >= WIDTH or enemy.left <= 0:
            move_down = True
    if move_down:
        enemy_direction *= -1
        for enemy in enemies:
            enemy.y += 20

def check_collisions():
    global score
    for bullet in bullets[:]:
        for enemy in enemies[:]:
            if bullet.colliderect(enemy):
                bullets.remove(bullet)
                enemies.remove(enemy)
                score += 10
                break

def game_over():
    over_text = font.render("GAME OVER", True, RED)
    screen.blit(over_text, (WIDTH // 2 - 100, HEIGHT // 2))  # Position anpassen
    pygame.display.flip()
    pygame.time.wait(2000)
    pygame.quit()
    sys.exit()

# Hauptspiel-Schleife
while True:
    # Powerup: Schussmodus wechseln bei 200 Punkten
    if shot_mode == SINGLE_SHOT and score >= 200:
        shot_mode = DOUBLE_SHOT

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if shot_mode == SINGLE_SHOT:
                    bullet = bullet_img.get_rect(midbottom=(player_rect.centerx, player_rect.top))
                    bullets.append(bullet)
                elif shot_mode == DOUBLE_SHOT:
                    offset = 12
                    bullet_left = bullet_img.get_rect(midbottom=(player_rect.centerx - offset, player_rect.top))
                    bullet_right = bullet_img.get_rect(midbottom=(player_rect.centerx + offset, player_rect.top))
                    bullets.append(bullet_left)
                    bullets.append(bullet_right)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] and player_rect.left > 0:
        player_rect.x -= player_speed
    if keys[pygame.K_RIGHT] and player_rect.right < WIDTH:
        player_rect.x += player_speed

    # Schüsse bewegen
    for bullet in bullets[:]:
        bullet.y += bullet_speed
        if bullet.bottom < 0:
            bullets.remove(bullet)

    move_enemies()
    check_collisions()

    # Prüfe auf Game Over
    for enemy in enemies:
        if enemy.bottom >= HEIGHT - 50:
            game_over()

    # Prüfe auf Level-Wechsel
    if not enemies:
        level += 1
        spawn_enemies()

    draw()
    clock.tick(60)