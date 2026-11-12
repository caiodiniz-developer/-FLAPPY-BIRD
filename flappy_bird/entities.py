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

    def draw(self, surface, scene, scale=1.0):
        cell = 3
        mask = (
            "........#####.........",
            "......#########.......",
            "....#############.....",
            "...###############....",
            "..##################..",
            ".####################.",
            "######################",
            "#####################.",
            ".###################..",
            "..################....",
            "...############.......",
            ".....########.........",
        )
        base = self.bird_type.get("colors", (255, 214, 10))
        accent = self.bird_type.get("accent", (255, 146, 43))
        shadow = tuple(max(12, channel // 3) for channel in base)
        highlight = tuple(min(255, int(channel * 0.68 + 88)) for channel in base)
        sprite = pygame.Surface((28 * cell, 20 * cell), pygame.SRCALPHA)
        start_x, start_y = 2, 3

        # Expand the silhouette by one pixel to create a crisp arcade outline.
        for row, pattern in enumerate(mask):
            for column, pixel in enumerate(pattern):
                if pixel != "#":
                    continue
                x = start_x + column
                y = start_y + row
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    if not (0 <= row + dy < len(mask) and 0 <= column + dx < len(mask[row + dy])):
                        pygame.draw.rect(sprite, (17, 21, 39), ((x + dx) * cell, (y + dy) * cell, cell, cell))
                    elif mask[row + dy][column + dx] != "#":
                        pygame.draw.rect(sprite, (17, 21, 39), ((x + dx) * cell, (y + dy) * cell, cell, cell))

        wing_lift = int(math.sin(self.frame * 1.25) * 2)
        for row, pattern in enumerate(mask):
            for column, pixel in enumerate(pattern):
                if pixel != "#":
                    continue
                x = start_x + column
                y = start_y + row
                color = base
                if row < 4 and column > 9:
                    color = highlight
                elif row > 8 and column < 12:
                    color = shadow
                pygame.draw.rect(sprite, color, (x * cell, y * cell, cell, cell))

        crest = (255, 247, 224)
        pygame.draw.rect(sprite, crest, ((start_x + 10) * cell, (start_y + 1) * cell, 5 * cell, 2 * cell))
        pygame.draw.rect(sprite, crest, ((start_x + 8) * cell, (start_y + 2) * cell, 9 * cell, 2 * cell))
        pygame.draw.rect(sprite, (216, 229, 218), ((start_x + 8) * cell, (start_y + 4) * cell, 4 * cell, cell))

        # A layered wing, cream belly, bright beak and chunky pixel eye give
        # each unlockable bird a readable silhouette at gameplay scale.
        wing_x = (start_x + 4) * cell
        wing_y = (start_y + 6) * cell + wing_lift
        pygame.draw.rect(sprite, (17, 21, 39), (wing_x - cell, wing_y, 10 * cell, 5 * cell))
        pygame.draw.rect(sprite, shadow, (wing_x, wing_y + cell, 8 * cell, 3 * cell))
        pygame.draw.rect(sprite, highlight, (wing_x + cell, wing_y, 7 * cell, 3 * cell))
        pygame.draw.rect(sprite, base, (wing_x + 2 * cell, wing_y + cell, 6 * cell, cell))
        pygame.draw.rect(sprite, (255, 244, 216), ((start_x + 9) * cell, (start_y + 8) * cell, 7 * cell, 2 * cell))

        eye_x, eye_y = (start_x + 15) * cell, (start_y + 2) * cell
        pygame.draw.rect(sprite, (17, 21, 39), (eye_x - cell, eye_y - cell, 5 * cell, 6 * cell))
        pygame.draw.rect(sprite, (255, 250, 230), (eye_x, eye_y, 3 * cell, 4 * cell))
        pygame.draw.rect(sprite, (24, 31, 56), (eye_x + 2 * cell, eye_y + 2 * cell, cell, 2 * cell))
        pygame.draw.rect(sprite, (255, 255, 255), (eye_x, eye_y, cell, cell))
        beak_x, beak_y = (start_x + 21) * cell, (start_y + 6) * cell
        pygame.draw.rect(sprite, (49, 37, 45), (beak_x, beak_y, 5 * cell, 4 * cell))
        pygame.draw.rect(sprite, (242, 91, 40), (beak_x, beak_y + cell, 4 * cell, 2 * cell))
        pygame.draw.rect(sprite, (255, 189, 62), (beak_x, beak_y, 4 * cell, cell))
        pygame.draw.rect(sprite, (255, 223, 112), (beak_x + cell, beak_y, 2 * cell, cell))
        pygame.draw.rect(sprite, (175, 70, 53), (beak_x + cell, beak_y + 2 * cell, 2 * cell, cell))

        feet_y = (start_y + 12) * cell
        for foot_x in ((start_x + 7) * cell, (start_x + 13) * cell):
            pygame.draw.rect(sprite, (49, 37, 45), (foot_x, feet_y, cell, 2 * cell))
            pygame.draw.rect(sprite, (242, 130, 48), (foot_x - cell, feet_y + cell, 3 * cell, cell))

        bird_id = self.bird_type.get("id", "classic")
        if bird_id == "robot":
            pygame.draw.rect(sprite, (42, 226, 225), ((start_x + 4) * cell, (start_y + 4) * cell, 2 * cell, 2 * cell))
            pygame.draw.rect(sprite, (42, 226, 225), ((start_x + 7) * cell, (start_y + 3) * cell, cell, cell))
            pygame.draw.rect(sprite, (168, 193, 205), ((start_x + 5) * cell, (start_y + 8) * cell, 3 * cell, cell))
        elif bird_id == "ghost":
            pygame.draw.rect(sprite, (242, 251, 255), ((start_x + 4) * cell, (start_y + 5) * cell, 2 * cell, cell))
            pygame.draw.rect(sprite, (242, 251, 255), ((start_x + 6) * cell, (start_y + 4) * cell, cell, cell))
            pygame.draw.rect(sprite, (152, 165, 211), ((start_x + 5) * cell, (start_y + 9) * cell, 4 * cell, cell))
        elif bird_id == "space":
            pygame.draw.rect(sprite, (255, 245, 180), ((start_x + 6) * cell, (start_y + 3) * cell, cell, cell))
            pygame.draw.rect(sprite, (255, 245, 180), ((start_x + 8) * cell, (start_y + 5) * cell, cell, cell))
            pygame.draw.rect(sprite, (255, 245, 180), ((start_x + 4) * cell, (start_y + 8) * cell, cell, cell))
        elif bird_id == "fire":
            pygame.draw.rect(sprite, (255, 238, 92), ((start_x + 6) * cell, (start_y + 2) * cell, 2 * cell, 2 * cell))
            pygame.draw.rect(sprite, (255, 122, 42), ((start_x + 4) * cell, (start_y + 3) * cell, 2 * cell, 2 * cell))
        elif bird_id == "ice":
            pygame.draw.rect(sprite, (241, 255, 255), ((start_x + 7) * cell, (start_y + 2) * cell, 2 * cell, 2 * cell))
            pygame.draw.rect(sprite, (163, 243, 255), ((start_x + 5) * cell, (start_y + 3) * cell, 2 * cell, cell))
        elif bird_id == "golden":
            pygame.draw.rect(sprite, (255, 251, 189), ((start_x + 6) * cell, (start_y + 3) * cell, 3 * cell, cell))
            pygame.draw.rect(sprite, (255, 251, 189), ((start_x + 5) * cell, (start_y + 4) * cell, cell, cell))
        elif bird_id == "legend":
            pygame.draw.rect(sprite, (255, 232, 125), ((start_x + 7) * cell, (start_y + 1) * cell, cell, 3 * cell))
            pygame.draw.rect(sprite, (255, 232, 125), ((start_x + 5) * cell, (start_y + 3) * cell, 5 * cell, cell))

        pitch = max(-2, min(2, int(self.velocity / 240)))
        sprite = pygame.transform.rotate(sprite, -pitch * 7)
        if scale != 1.0:
            sprite = pygame.transform.scale(
                sprite,
                (round(sprite.get_width() * scale), round(sprite.get_height() * scale)),
            )
        surface.blit(sprite, sprite.get_rect(center=(round(self.x), round(self.y))))


class PipePair:
    def __init__(self, x, gap_y, gap_height, width=90, speed=PIPE_SPEED):
        self.x = x
        self.gap_y = gap_y
        self.gap_height = gap_height
        self.width = width
        self.speed = speed
        self.passed = False
        self.scored = False

    def update(self, dt):
        self.x -= self.speed * dt

    def draw(self, surface, scene):
        outline = (48, 39, 55)
        green = (45, 230, 64)
        light = (141, 255, 111)
        dark = (20, 156, 63)

        def draw_pipe_body(rect, cap_at_bottom):
            if rect.height <= 0:
                return
            pygame.draw.rect(surface, outline, rect.inflate(8, 0))
            pygame.draw.rect(surface, green, rect)
            pygame.draw.rect(surface, dark, (rect.right - 17, rect.y, 17, rect.height))
            pygame.draw.rect(surface, light, (rect.x + 8, rect.y, 12, rect.height))
            pygame.draw.rect(surface, (237, 255, 223), (rect.x + 26, rect.y, 8, rect.height))
            pygame.draw.rect(surface, (95, 250, 81), (rect.x + 38, rect.y, 5, rect.height))
            for segment_y in range(rect.y + 38, rect.bottom, 78):
                pygame.draw.rect(surface, (35, 185, 60), (rect.x + 43, segment_y, rect.width - 60, 4))
                pygame.draw.rect(surface, (141, 255, 111), (rect.x + 45, segment_y + 1, 8, 2))
            for detail_y in range(rect.y + 18, rect.bottom - 12, 72):
                pygame.draw.rect(surface, (13, 118, 54), (rect.right - 13, detail_y, 5, 5))
                pygame.draw.rect(surface, (190, 255, 154), (rect.x + 11, detail_y + 2, 4, 4))

            cap_y = rect.bottom - 24 if cap_at_bottom else rect.y
            cap = pygame.Rect(rect.x - 12, cap_y, rect.width + 24, 24)
            pygame.draw.rect(surface, outline, cap.inflate(8, 6))
            pygame.draw.rect(surface, green, cap)
            pygame.draw.rect(surface, light, (cap.x + 7, cap.y + 4, 17, cap.height - 8))
            pygame.draw.rect(surface, (237, 255, 223), (cap.x + 27, cap.y + 4, 8, cap.height - 8))
            pygame.draw.rect(surface, dark, (cap.right - 18, cap.y + 3, 10, cap.height - 6))
            pygame.draw.line(surface, (180, 255, 164), (cap.x + 4, cap.y + 3), (cap.right - 4, cap.y + 3), 2)
            pygame.draw.line(surface, (16, 123, 51), (cap.x + 3, cap.bottom - 3), (cap.right - 3, cap.bottom - 3), 2)
            for bolt_x in (cap.x + 6, cap.right - 10):
                pygame.draw.rect(surface, (34, 111, 58), (bolt_x, cap.y + 9, 4, 4))
                pygame.draw.rect(surface, (190, 255, 154), (bolt_x, cap.y + 9, 2, 2))

        top_rect = pygame.Rect(round(self.x), 0, self.width, max(0, self.gap_y))
        bottom_rect = pygame.Rect(
            round(self.x),
            self.gap_y + self.gap_height,
            self.width,
            max(0, SCREEN_HEIGHT - (self.gap_y + self.gap_height)),
        )
        draw_pipe_body(top_rect, True)
        draw_pipe_body(bottom_rect, False)

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
        color = tuple(max(0, min(255, channel + (24 if self.hovered else 0))) for channel in self.accent)
        shadow = self.rect.move(0, 5)
        pygame.draw.rect(surface, (20, 28, 46), shadow)
        pygame.draw.rect(surface, (17, 21, 39), self.rect.inflate(6, 6))
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, tuple(min(255, c + 55) for c in color), (self.rect.x + 4, self.rect.y + 4, self.rect.width - 8, 5))
        pygame.draw.rect(surface, tuple(max(0, c - 45) for c in color), (self.rect.x + 4, self.rect.bottom - 8, self.rect.width - 8, 4))
        text = font.render(self.label, True, self.text_color)
        text_rect = text.get_rect(center=self.rect.center)
        surface.blit(font.render(self.label, True, (17, 21, 39)), text_rect.move(2, 2))
        surface.blit(text, text_rect)
