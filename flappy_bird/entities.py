import math
import random

import pygame

from flappy_bird.config import JUMP_FORCE, PIPE_SPEED, SCREEN_HEIGHT, SCREEN_WIDTH, GRAVITY


class Bird:
    def __init__(self, x, y, bird_type):
        self.x = x
        self.y = y
        self.velocity = 0.0
        self.radius = 22
        self.bird_type = bird_type
        self.alive = True
        self.frame = random.random() * 1000

    def jump(self):
        self.velocity = -JUMP_FORCE

    def update(self, dt):
        self.velocity += GRAVITY * dt
        self.y += self.velocity * dt
        self.frame += dt * 18

    def draw(self, surface, scene):
        color = self.bird_type.get("colors", (255, 214, 10))
        accent = self.bird_type.get("accent", (255, 146, 43))
        wing_phase = math.sin(self.frame) * 10
        angle = max(-1.2, min(1.4, self.velocity / 550))

        body_rect = pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)
        wing_rect = pygame.Rect(int(self.x - self.radius + 8), int(self.y - 6 + wing_phase), self.radius * 1.4, self.radius * 0.9)

        rotated = pygame.Surface((self.radius * 2 + 30, self.radius * 2 + 30), pygame.SRCALPHA)
        pygame.draw.ellipse(rotated, color, (15, 15, self.radius * 2, self.radius * 2))
        pygame.draw.ellipse(rotated, accent, (26, 22, self.radius, self.radius * 0.7))
        pygame.draw.ellipse(rotated, (255, 255, 255), (32, 22, 8, 8))
        pygame.draw.ellipse(rotated, (0, 0, 0), (35, 25, 4, 4))
        pygame.draw.ellipse(rotated, (255, 228, 100), (10, 10, 18, 18))
        pygame.draw.ellipse(rotated, color, (body_rect.left - 5, body_rect.top + 7, self.radius * 1.5, self.radius * 0.8))
        pygame.draw.polygon(rotated, accent, [(self.x - self.radius + 25, self.y), (self.x - self.radius + 50, self.y + 6), (self.x - self.radius + 25, self.y + 12)])
        pygame.draw.polygon(rotated, (255, 210, 130), [(self.x - self.radius + 25, self.y + 2), (self.x - self.radius + 40, self.y + 6), (self.x - self.radius + 25, self.y + 10)])

        rotated = pygame.transform.rotate(rotated, math.degrees(angle) * 20)
        rotated_rect = rotated.get_rect(center=(self.x, self.y))
        surface.blit(rotated, rotated_rect)


class PipePair:
    def __init__(self, x, gap_y, gap_height, width=90):
        self.x = x
        self.gap_y = gap_y
        self.gap_height = gap_height
        self.width = width
        self.passed = False
        self.scored = False

    def update(self, dt):
        self.x -= PIPE_SPEED * dt

    def draw(self, surface, scene):
        top_color = scene["mountain_a"]
        bottom_color = scene["mountain_b"]
        pipe_cap_color = scene["accent"]

        top_rect = pygame.Rect(self.x, 0, self.width, self.gap_y)
        bottom_rect = pygame.Rect(self.x, self.gap_y + self.gap_height, self.width, SCREEN_HEIGHT - (self.gap_y + self.gap_height))
        cap_top = pygame.Rect(self.x - 8, self.gap_y - 18, self.width + 16, 18)
        cap_bottom = pygame.Rect(self.x - 8, self.gap_y + self.gap_height, self.width + 16, 18)

        pygame.draw.rect(surface, top_color, top_rect)
        pygame.draw.rect(surface, bottom_color, bottom_rect)
        pygame.draw.rect(surface, pipe_cap_color, cap_top)
        pygame.draw.rect(surface, pipe_cap_color, cap_bottom)

    def collides_with(self, bird):
        if bird.x + bird.radius > self.x and bird.x - bird.radius < self.x + self.width:
            if bird.y - bird.radius < self.gap_y or bird.y + bird.radius > self.gap_y + self.gap_height:
                return True
        return False


class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 12
        self.value = 1
        self.phase = random.random() * math.tau
        self.collected = False

    def update(self, dt):
        self.phase += dt * 8

    def draw(self, surface):
        if self.collected:
            return
        center = (int(self.x), int(self.y))
        glow = 18 + int(math.sin(self.phase) * 6)
        pygame.draw.circle(surface, (255, 215, 90), center, self.radius + 6)
        pygame.draw.circle(surface, (255, 238, 159), center, self.radius + glow // 5)
        pygame.draw.circle(surface, (255, 190, 40), center, self.radius)
        pygame.draw.circle(surface, (255, 255, 255), center, self.radius * 0.35)
        pygame.draw.line(surface, (255, 240, 120), center, (center[0], center[1] - self.radius), 2)

    def collides_with(self, bird):
        distance = math.hypot(self.x - bird.x, self.y - bird.y)
        return distance < self.radius + bird.radius


class Particle:
    def __init__(self, x, y, color, speed, ttl=0.7):
        self.x = x
        self.y = y
        self.vx = random.uniform(-80, 80)
        self.vy = random.uniform(-110, 30)
        self.color = color
        self.life = ttl
        self.max_life = ttl
        self.size = random.randint(2, 5)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 250 * dt
        self.life -= dt

    def draw(self, surface):
        alpha = max(0, self.life / self.max_life)
        color = (*self.color, int(alpha * 255))
        if len(color) == 4:
            s = pygame.Surface((self.size * 4, self.size * 4), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (self.size * 2, self.size * 2), self.size)
            surface.blit(s, (self.x - self.size * 2, self.y - self.size * 2))
        else:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.size)


class Button:
    def __init__(self, x, y, w, h, label, action=None, accent=(255, 204, 102), text_color=(20, 20, 20), radius=18):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.action = action
        self.accent = accent
        self.text_color = text_color
        self.radius = radius
        self.hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            if self.action:
                self.action()

    def draw(self, surface, font):
        self.hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        color = tuple(max(0, min(255, c + (40 if self.hovered else 0))) for c in self.accent)
        inner = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(inner, (*color, 220), (0, 0, self.rect.width, self.rect.height), border_radius=self.radius)
        pygame.draw.rect(inner, (255, 255, 255, 80), (2, 2, self.rect.width - 4, self.rect.height - 4), border_radius=self.radius, width=2)
        surface.blit(inner, self.rect.topleft)

        text = font.render(self.label, True, self.text_color)
        text_rect = text.get_rect(center=self.rect.center)
        surface.blit(text, text_rect)
