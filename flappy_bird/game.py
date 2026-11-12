import math
import random
from typing import Iterable

import pygame

from flappy_bird.achievements import evaluate_achievements
from flappy_bird.config import (
    ACHIEVEMENTS,
    BIRD_TYPES,
    FPS,
    PIPE_GAP,
    SCENARIOS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    clamp,
    lerp,
)
from flappy_bird.entities import Bird, Button, Coin, Particle, PipePair
from flappy_bird.save_data import load_state, save_state


class FlappyGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Flappy Bird Deluxe")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "loading"
        self.save_data = load_state()
        self.current_scene_id = self.save_data["selected_scene"]
        self.current_bird_id = self.save_data["selected_bird"]
        self.current_scene = self.scene_by_id(self.current_scene_id)
        self.current_bird = self.bird_by_id(self.current_bird_id)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.font = pygame.font.SysFont("Arial", 30)
        self.big_font = pygame.font.SysFont("Arial", 52, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 22)
        self.arcade_font = pygame.font.SysFont("Courier New", 60, bold=True)
        self.arcade_small_font = pygame.font.SysFont("Courier New", 19, bold=True)
        self.loading_steps = [
            "Inicializando Pygame",
            "Carregando cenários",
            "Preparando personagens",
            "Configurando save data",
            "Conectando interface",
        ]
        self.loading_index = 0
        self.loading_progress = 0.0
        self.menu_buttons = []
        self.shop_cards = []
        self.scenario_cards = []
        self.game_over_notification = ""
        self.warning_message = ""
        self.transition_alpha = 0

        self.reset_run()
        self.menu_bird = Bird(900, 375, self.bird_by_id(self.current_bird_id))
        self.menu_elapsed = 0.0
        self.populate_menu_buttons()

    def bird_by_id(self, bird_id):
        for bird in BIRD_TYPES:
            if bird["id"] == bird_id:
                return bird
        return BIRD_TYPES[0]

    def scene_by_id(self, scene_id):
        for scene in SCENARIOS:
            if scene["id"] == scene_id:
                return scene
        return SCENARIOS[0]

    def populate_menu_buttons(self):
        self.menu_buttons = [
            Button(112, 292, 340, 52, "JOGAR", self.start_game, accent=(255, 190, 70), text_color=(35, 28, 38)),
            Button(112, 357, 340, 48, "LOJA", self.open_shop, accent=(102, 194, 214), text_color=(25, 34, 52)),
            Button(112, 417, 340, 48, "CONQUISTAS", self.open_achievements, accent=(157, 202, 116), text_color=(25, 34, 52)),
            Button(112, 477, 340, 48, "CENÁRIOS", self.open_scenarios, accent=(184, 150, 216), text_color=(25, 34, 52)),
            Button(112, 537, 340, 48, "CONFIGURAÇÕES", self.open_settings, accent=(223, 132, 112), text_color=(35, 28, 38)),
        ]

    def reset_run(self):
        self.bird = Bird(220, SCREEN_HEIGHT // 2 - 40, self.bird_by_id(self.current_bird_id))
        self.pipes = []
        self.coins = []
        self.particles = []
        self.score = 0
        self.round_coins = 0
        self.pipe_timer = 0.0
        self.sound_timer = 0.0
        self.started = False
        self.state = "menu" if self.state != "loading" else "loading"

    def start_game(self):
        self.state = "playing"
        self.started = True
        self.reset_run()
        self.state = "playing"

    def open_shop(self):
        self.state = "shop"

    def open_achievements(self):
        self.state = "achievements"

    def open_scenarios(self):
        self.state = "scenarios"

    def open_settings(self):
        self.state = "settings"

    def back_to_menu(self):
        self.state = "menu"

    def restart_game(self):
        self.start_game()

    def buy_bird(self, bird_id):
        bird = self.bird_by_id(bird_id)
        if bird_id in self.save_data["unlocked_birds"]:
            self.save_data["selected_bird"] = bird_id
            self.current_bird_id = bird_id
            self.current_bird = bird
            self.menu_bird.bird_type = bird
            save_state(self.save_data)
            return
        if self.save_data["coins"] >= bird["price"]:
            self.save_data["coins"] -= bird["price"]
            self.save_data["unlocked_birds"].append(bird_id)
            self.save_data["selected_bird"] = bird_id
            self.current_bird_id = bird_id
            self.current_bird = bird
            self.menu_bird.bird_type = bird
            save_state(self.save_data)

    def buy_scene(self, scene_id):
        scene = self.scene_by_id(scene_id)
        if scene_id in self.save_data["unlocked_scenes"]:
            self.save_data["selected_scene"] = scene_id
            self.current_scene_id = scene_id
            self.current_scene = scene
            save_state(self.save_data)
            return
        if self.save_data["coins"] >= scene["price"]:
            self.save_data["coins"] -= scene["price"]
            self.save_data["unlocked_scenes"].append(scene_id)
            self.save_data["selected_scene"] = scene_id
            self.current_scene_id = scene_id
            self.current_scene = scene
            save_state(self.save_data)

    def save_current_progress(self):
        self.save_data["selected_bird"] = self.current_bird_id
        self.save_data["selected_scene"] = self.current_scene_id
        save_state(self.save_data)

    def spawn_pipe(self):
        gap_y = random.randint(140, SCREEN_HEIGHT - 220)
        self.pipes.append(PipePair(SCREEN_WIDTH + 80, gap_y, PIPE_GAP))
        coin_y = gap_y + PIPE_GAP / 2
        self.coins.append(Coin(SCREEN_WIDTH + 80 + 30, coin_y))

    def update_particles(self, dt):
        for particle in self.particles[:]:
            particle.update(dt)
            if particle.life <= 0:
                self.particles.remove(particle)

    def add_particles(self, x, y, color):
        for _ in range(16):
            self.particles.append(Particle(x, y, color, 1.0))

    def update_game(self, dt):
        self.bird.update(dt)
        self.pipe_timer -= dt
        if self.pipe_timer <= 0:
            self.spawn_pipe()
            self.pipe_timer = random.uniform(1.15, 1.7)

        for pipe in self.pipes[:]:
            pipe.update(dt)
            if pipe.collides_with(self.bird):
                self.state = "game_over"
                self.current_scene = self.current_scene
            if pipe.x + pipe.width < 0:
                self.pipes.remove(pipe)

        for coin in self.coins[:]:
            coin.update(dt)
            if coin.collides_with(self.bird):
                coin.collected = True
                self.round_coins += coin.value
                self.add_particles(coin.x, coin.y, (255, 214, 100))
                self.save_data["stats"]["total_coins_collected"] += coin.value
                self.coins.remove(coin)
            elif coin.x + coin.radius < 0:
                self.coins.remove(coin)

        if self.bird.y - self.bird.radius < 0 or self.bird.y + self.bird.radius > SCREEN_HEIGHT - 90:
            self.state = "game_over"
        if self.bird.y > SCREEN_HEIGHT - 90:
            self.bird.y = SCREEN_HEIGHT - 90

        for pipe in self.pipes:
            if not pipe.scored and pipe.x + pipe.width < self.bird.x:
                pipe.scored = True
                self.score += 1
                self.save_data["stats"]["total_obstacles_passed"] += 1
                self.add_particles(self.bird.x, 100, self.current_scene["accent"])

        self.update_particles(dt)

        if self.bird.y > SCREEN_HEIGHT - 90:
            self.bird.y = SCREEN_HEIGHT - 90
            self.bird.velocity = 0

        if self.state == "game_over":
            self.finish_round()

    def finish_round(self):
        self.save_data["high_score"] = max(self.save_data["high_score"], self.score)
        self.save_data["coins"] += self.round_coins
        self.save_data["stats"]["games_played"] += 1
        self.save_data["stats"]["total_coins_earned"] += self.round_coins
        self.save_data["stats"]["scenes_played"][self.current_scene_id] = self.save_data["stats"].get("scenes_played", {}).get(self.current_scene_id, 0) + 1
        self.game_over_notification = f"Pontuação: {self.score} | Moedas: {self.round_coins}"
        self.warning_message = "Novo recorde!" if self.score >= self.save_data["high_score"] else ""
        reward_notifications = evaluate_achievements(self.save_data)
        if reward_notifications:
            self.warning_message = "Conquista desbloqueada!"
        save_state(self.save_data)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False

        if self.state == "loading":
            return

        if self.state in {"menu", "shop", "achievements", "scenarios", "settings"}:
            for button in self.menu_buttons:
                button.handle_event(event)

        if self.state == "shop" and event.type == pygame.MOUSEBUTTONDOWN:
            for card in self.shop_cards:
                if card["rect"].collidepoint(event.pos):
                    if event.button == 1:
                        self.buy_bird(card["bird_id"])

        if self.state == "scenarios" and event.type == pygame.MOUSEBUTTONDOWN:
            for card in self.scenario_cards:
                if card["rect"].collidepoint(event.pos):
                    if event.button == 1:
                        self.buy_scene(card["scene_id"])

        if self.state == "playing":
            if event.type == pygame.KEYDOWN and event.key in {pygame.K_SPACE, pygame.K_w, pygame.K_UP}:
                self.bird.jump()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.bird.jump()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "menu"

        if self.state == "game_over":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.start_game()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.start_game()

    def update(self, dt):
        if self.state == "loading":
            self.loading_progress += dt * 0.45
            if self.loading_progress >= 1.0 and self.loading_index < len(self.loading_steps):
                self.loading_index += 1
                self.loading_progress = 0.0
            if self.loading_index >= len(self.loading_steps):
                self.state = "menu"
                return
            return

        if self.state == "playing":
            self.update_game(dt)
            return

        if self.state == "game_over":
            self.update_particles(dt)
            return

        if self.state == "menu":
            self.menu_elapsed += dt
            self.menu_bird.frame += dt * 12
            self.menu_bird.y = 375 + math.sin(self.menu_elapsed * 2.2) * 10

    def draw_background(self, surface, scene):
        gradient = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for i in range(SCREEN_HEIGHT):
            t = i / SCREEN_HEIGHT
            color = (
                int(lerp(scene["sky_top"][0], scene["sky_bottom"][0], t)),
                int(lerp(scene["sky_top"][1], scene["sky_bottom"][1], t)),
                int(lerp(scene["sky_top"][2], scene["sky_bottom"][2], t)),
            )
            pygame.draw.line(gradient, color, (0, i), (SCREEN_WIDTH, i))
        surface.blit(gradient, (0, 0))

        if scene["theme"] == "night":
            for _ in range(40):
                x = random.randint(20, SCREEN_WIDTH - 20)
                y = random.randint(20, SCREEN_HEIGHT // 2)
                pygame.draw.circle(surface, (255, 255, 255), (x, y), 2)
        elif scene["theme"] == "space":
            for _ in range(60):
                x = random.randint(20, SCREEN_WIDTH - 20)
                y = random.randint(20, SCREEN_HEIGHT // 2)
                pygame.draw.circle(surface, (255, 255, 255), (x, y), 2)
            pygame.draw.circle(surface, (240, 200, 130), (1030, 120), 35)
            pygame.draw.circle(surface, (160, 140, 255), (900, 170), 18)

        for i in range(7):
            cloud_x = (i * 220 + pygame.time.get_ticks() * 0.03) % (SCREEN_WIDTH + 220) - 110
            cloud_y = 90 + (i % 3) * 55
            pygame.draw.ellipse(surface, scene["cloud"], (cloud_x, cloud_y, 100, 40))
            pygame.draw.ellipse(surface, scene["cloud"], (cloud_x + 28, cloud_y - 15, 90, 40))

        mountain_a = scene["mountain_a"]
        mountain_b = scene["mountain_b"]
        pygame.draw.polygon(surface, mountain_a, [(0, SCREEN_HEIGHT - 90), (180, 400), (350, SCREEN_HEIGHT - 120), (560, 330), (790, SCREEN_HEIGHT - 100), (950, 440), (SCREEN_WIDTH, SCREEN_HEIGHT - 90)])
        pygame.draw.polygon(surface, mountain_b, [(0, SCREEN_HEIGHT), (220, 430), (430, SCREEN_HEIGHT - 60), (690, 390), (980, SCREEN_HEIGHT - 80), (SCREEN_WIDTH, SCREEN_HEIGHT)])

        if scene["theme"] == "forest":
            for x in range(0, SCREEN_WIDTH + 80, 90):
                pygame.draw.rect(surface, (65, 42, 28), (x, SCREEN_HEIGHT - 110, 16, 80))
                pygame.draw.polygon(surface, (20, 110, 40), [(x - 25, SCREEN_HEIGHT - 110), (x + 20, SCREEN_HEIGHT - 180), (x + 65, SCREEN_HEIGHT - 110)])
        if scene["theme"] == "city":
            for x in range(0, SCREEN_WIDTH + 40, 110):
                building_h = 120 + (x % 180)
                pygame.draw.rect(surface, (60, 72, 90), (x, SCREEN_HEIGHT - 90 - building_h, 70, building_h))
                for wx in range(x + 10, x + 60, 16):
                    for wy in range(SCREEN_HEIGHT - 90 - building_h + 15, SCREEN_HEIGHT - 100, 26):
                        pygame.draw.rect(surface, (255, 220, 110), (wx, wy, 8, 12))
        if scene["theme"] == "desert":
            for x in range(0, SCREEN_WIDTH + 50, 150):
                pygame.draw.polygon(surface, (212, 172, 85), [(x, SCREEN_HEIGHT - 90), (x + 40, SCREEN_HEIGHT - 140), (x + 90, SCREEN_HEIGHT - 90)])
        if scene["theme"] == "snow":
            for x in range(0, SCREEN_WIDTH + 50, 100):
                pygame.draw.circle(surface, (255, 255, 255), (x, SCREEN_HEIGHT - 92), 15)
        if scene["theme"] == "volcano":
            for x in range(0, SCREEN_WIDTH + 60, 110):
                pygame.draw.polygon(surface, (140, 24, 16), [(x, SCREEN_HEIGHT - 90), (x + 50, SCREEN_HEIGHT - 220), (x + 100, SCREEN_HEIGHT - 90)])
                pygame.draw.circle(surface, (255, 110, 30), (x + 60, SCREEN_HEIGHT - 175), 8)

        ground_y = SCREEN_HEIGHT - 90
        pygame.draw.rect(surface, scene["ground_top"], (0, ground_y, SCREEN_WIDTH, 90))
        pygame.draw.rect(surface, scene["ground_bottom"], (0, ground_y + 40, SCREEN_WIDTH, 90))
        for x in range(0, SCREEN_WIDTH + 30, 20):
            pygame.draw.rect(surface, (255, 255, 255, 80), (x, ground_y + 40 + (x % 40), 10, 10), border_radius=4)

    def draw_menu(self):
        for y in range(0, SCREEN_HEIGHT, 8):
            blend = y / SCREEN_HEIGHT
            color = (
                int(lerp(49, 157, blend)),
                int(lerp(164, 217, blend)),
                int(lerp(205, 189, blend)),
            )
            pygame.draw.rect(self.screen, color, (0, y, SCREEN_WIDTH, 8))

        # Pixel clouds and distant pines give the title screen its own arcade stage.
        cloud_shift = int(pygame.time.get_ticks() * 0.012) % (SCREEN_WIDTH + 180)
        for cloud_x, cloud_y in ((95, 105), (495, 165), (930, 90), (1250, 190)):
            x = (cloud_x - cloud_shift) % (SCREEN_WIDTH + 180) - 90
            pygame.draw.rect(self.screen, (229, 248, 227), (x, cloud_y + 12, 118, 22))
            pygame.draw.rect(self.screen, (229, 248, 227), (x + 24, cloud_y, 64, 18))
            pygame.draw.rect(self.screen, (176, 224, 214), (x + 10, cloud_y + 32, 102, 8))

        pygame.draw.rect(self.screen, (255, 218, 112), (1020, 170, 70, 70))
        pygame.draw.rect(self.screen, (255, 237, 153), (1030, 160, 50, 90))
        for x, peak, color in ((-20, 468, (109, 186, 152)), (350, 438, (91, 166, 139)), (760, 455, (80, 148, 127)), (1110, 430, (70, 132, 119))):
            for step in range(0, 7):
                width = 90 + step * 36
                y = peak + step * 17
                pygame.draw.rect(self.screen, color, (x - step * 18, y, width, 18))

        for tree_x, tree_y, size in ((625, 490, 1), (760, 470, 1.2), (1030, 480, 1), (1170, 455, 1.25)):
            trunk_w = int(14 * size)
            trunk_h = int(56 * size)
            pygame.draw.rect(self.screen, (104, 75, 58), (tree_x, tree_y, trunk_w, trunk_h))
            for tier in range(4):
                tier_w = int((42 - tier * 6) * size)
                tier_h = int(24 * size)
                pygame.draw.rect(
                    self.screen,
                    (53 - tier * 4, 137 - tier * 6, 96 - tier * 4),
                    (tree_x - (tier_w - trunk_w) // 2, tree_y - 20 - tier * 21, tier_w, tier_h),
                )

        ground_y = 598
        pygame.draw.rect(self.screen, (49, 128, 83), (0, ground_y, SCREEN_WIDTH, SCREEN_HEIGHT - ground_y))
        pygame.draw.rect(self.screen, (126, 197, 104), (0, ground_y, SCREEN_WIDTH, 12))
        pygame.draw.rect(self.screen, (210, 178, 113), (0, ground_y + 18, SCREEN_WIDTH, SCREEN_HEIGHT - ground_y - 18))
        for x in range(0, SCREEN_WIDTH, 32):
            pygame.draw.rect(self.screen, (95, 147, 84), (x, ground_y, 16, 5))
            pygame.draw.rect(self.screen, (173, 133, 95), (x + (16 if x % 64 else 0), ground_y + 27, 16, 10))
            pygame.draw.rect(self.screen, (187, 147, 103), (x, ground_y + 51, 16, 10))

        # Chunky bordered panel, deliberately kept translucent over the scenery.
        panel = pygame.Surface((456, 574), pygame.SRCALPHA)
        panel.fill((18, 30, 52, 232))
        self.screen.blit(panel, (54, 44))
        pygame.draw.rect(self.screen, (20, 26, 44), (50, 40, 464, 582), 7)
        pygame.draw.rect(self.screen, (246, 190, 91), (58, 48, 448, 566), 3)
        pygame.draw.rect(self.screen, (255, 222, 130), (58, 48, 448, 8))

        def arcade_text(label, position, color, font):
            text = font.render(label, True, color)
            shadow = font.render(label, True, (15, 20, 37))
            self.screen.blit(shadow, (position[0] + 4, position[1] + 5))
            self.screen.blit(text, position)

        arcade_text("FLAPPY", (100, 84), (255, 205, 96), self.arcade_font)
        arcade_text("BIRD", (102, 143), (123, 214, 218), self.arcade_font)
        pygame.draw.rect(self.screen, (246, 190, 91), (100, 222, 348, 3))
        arcade_text("PIXEL ARCADE EDITION", (104, 235), (208, 226, 218), self.arcade_small_font)

        for button in self.menu_buttons:
            button.draw(self.screen, self.arcade_small_font)

        pygame.draw.rect(self.screen, (20, 26, 44), (766, 42, 212, 48))
        pygame.draw.rect(self.screen, (246, 190, 91), (766, 42, 212, 48), 3)
        pygame.draw.rect(self.screen, (20, 26, 44), (990, 42, 226, 48))
        pygame.draw.rect(self.screen, (246, 190, 91), (990, 42, 226, 48), 3)
        coin_display = self.arcade_small_font.render(f"MOEDAS  {self.save_data['coins']}", True, (255, 221, 130))
        best_score = self.arcade_small_font.render(f"RECORDE  {self.save_data['high_score']}", True, (234, 245, 227))
        self.screen.blit(coin_display, (780, 55))
        self.screen.blit(best_score, (1004, 55))

        pygame.draw.rect(self.screen, (18, 30, 52), (690, 265, 440, 250), 5)
        pygame.draw.rect(self.screen, (32, 75, 86), (704, 279, 412, 222))
        pygame.draw.rect(self.screen, (246, 190, 91), (700, 275, 420, 230), 2)
        self.screen.blit(self.arcade_small_font.render("PLAYER 01", True, (255, 224, 143)), (824, 284))
        pygame.draw.rect(self.screen, (255, 232, 153), (808, 447, 184, 8))
        pygame.draw.rect(self.screen, (255, 232, 153), (832, 455, 136, 5))
        self.menu_bird.draw(self.screen, self.current_scene, scale=2.15)
        hint = self.arcade_small_font.render("SPACE / CLICK TO FLAP", True, (244, 249, 229))
        self.screen.blit(hint, hint.get_rect(center=(910, 550)))
        footer = self.arcade_small_font.render("PRESS START  •  FLY YOUR WAY", True, (48, 95, 72))
        self.screen.blit(footer, footer.get_rect(center=(910, 635)))

    def draw_shop(self):
        self.draw_background(self.screen, self.current_scene)
        title = self.big_font.render("LOJA", True, (255, 255, 255))
        self.screen.blit(title, (560, 80))
        self.shop_cards = []
        x = 120
        y = 180
        for bird in BIRD_TYPES:
            rect = pygame.Rect(x, y, 180, 210)
            self.shop_cards.append({"bird_id": bird["id"], "rect": rect})
            unlocked = bird["id"] in self.save_data["unlocked_birds"]
            selected = bird["id"] == self.save_data["selected_bird"]
            pygame.draw.rect(self.screen, (27, 39, 58), rect, border_radius=22)
            pygame.draw.rect(self.screen, (255, 255, 255, 100), rect.inflate(-8, -8), border_radius=18, width=2)
            Bird(x + 90, y + 72, bird).draw(self.screen, self.current_scene, scale=0.9)
            label = self.small_font.render(bird["name"], True, (255, 255, 255))
            self.screen.blit(label, (x + 16, y + 120))
            price_text = self.small_font.render(f"{bird['price']} moedas" if not unlocked else "Comprado", True, (255, 210, 110))
            self.screen.blit(price_text, (x + 16, y + 150))
            if selected:
                pygame.draw.rect(self.screen, (120, 255, 150), rect.inflate(-18, -18), width=3, border_radius=18)
            button_label = "SELECIONAR" if unlocked else "COMPRAR"
            btn = Button(x + 18, y + 175, 144, 26, button_label, lambda bid=bird["id"]: self.buy_bird(bid), accent=(120, 220, 115) if unlocked else (255, 212, 90))
            btn.draw(self.screen, self.small_font)
            x += 210
            if x > 1000:
                x = 120
                y += 250

        back_button = Button(50, 640, 160, 40, "VOLTAR", self.back_to_menu, accent=(255, 144, 144))
        back_button.draw(self.screen, self.small_font)
        coin_display = self.small_font.render(f"Moedas: {self.save_data['coins']}", True, (255, 255, 255))
        self.screen.blit(coin_display, (1040, 80))

    def draw_achievements(self):
        self.draw_background(self.screen, self.current_scene)
        title = self.big_font.render("CONQUISTAS", True, (255, 255, 255))
        self.screen.blit(title, (470, 80))
        y = 170
        for item in ACHIEVEMENTS:
            unlocked = self.save_data["achievements"].get(item["id"], {}).get("unlocked", False)
            color = (70, 180, 120) if unlocked else (70, 90, 110)
            pygame.draw.rect(self.screen, color, (80, y, 1120, 50), border_radius=12)
            text = self.font.render(item["name"], True, (255, 255, 255))
            self.screen.blit(text, (110, y + 12))
            desc = self.small_font.render(item["description"], True, (230, 230, 230))
            self.screen.blit(desc, (500, y + 16))
            y += 60

        back_button = Button(50, 640, 160, 40, "VOLTAR", self.back_to_menu, accent=(255, 144, 144))
        back_button.draw(self.screen, self.small_font)

    def draw_scenarios(self):
        self.draw_background(self.screen, self.current_scene)
        title = self.big_font.render("CENÁRIOS", True, (255, 255, 255))
        self.screen.blit(title, (500, 80))
        self.scenario_cards = []
        x = 120
        y = 180
        for scene in SCENARIOS:
            rect = pygame.Rect(x, y, 220, 180)
            self.scenario_cards.append({"scene_id": scene["id"], "rect": rect})
            unlocked = scene["id"] in self.save_data["unlocked_scenes"]
            selected = scene["id"] == self.save_data["selected_scene"]
            pygame.draw.rect(self.screen, (22, 37, 59), rect, border_radius=18)
            pygame.draw.rect(self.screen, scene["accent"], rect.inflate(-15, -15), border_radius=12, width=2)
            label = self.small_font.render(scene["name"], True, (255, 255, 255))
            self.screen.blit(label, (x + 18, y + 18))
            if not unlocked:
                price = self.small_font.render(f"{scene['price']} moedas", True, (255, 214, 110))
                self.screen.blit(price, (x + 18, y + 120))
            if selected:
                pygame.draw.rect(self.screen, (120, 255, 150), rect.inflate(-10, -10), width=3, border_radius=18)
            button_label = "SELECIONAR" if unlocked else "COMPRAR"
            btn = Button(x + 18, y + 135, 184, 26, button_label, lambda sid=scene["id"]: self.buy_scene(sid), accent=(125, 175, 255) if unlocked else (255, 214, 90))
            btn.draw(self.screen, self.small_font)
            x += 250
            if x > 1000:
                x = 120
                y += 220

        back_button = Button(50, 640, 160, 40, "VOLTAR", self.back_to_menu, accent=(255, 144, 144))
        back_button.draw(self.screen, self.small_font)

    def draw_settings(self):
        self.draw_background(self.screen, self.current_scene)
        title = self.big_font.render("CONFIGURAÇÕES", True, (255, 255, 255))
        self.screen.blit(title, (430, 80))

        self.screen.blit(self.small_font.render("Volume Geral", True, (255, 255, 255)), (180, 190))
        self.screen.blit(self.small_font.render(f"{self.save_data['settings']['master_volume']:.1f}", True, (255, 255, 255)), (980, 190))
        self.screen.blit(self.small_font.render("Música", True, (255, 255, 255)), (180, 260))
        self.screen.blit(self.small_font.render(f"{self.save_data['settings']['music_volume']:.1f}", True, (255, 255, 255)), (980, 260))
        self.screen.blit(self.small_font.render("Efeitos", True, (255, 255, 255)), (180, 330))
        self.screen.blit(self.small_font.render(f"{self.save_data['settings']['sfx_volume']:.1f}", True, (255, 255, 255)), (980, 330))
        self.screen.blit(self.small_font.render("FPS", True, (255, 255, 255)), (180, 400))
        self.screen.blit(self.small_font.render(f"{self.save_data['settings']['fps_limit']}", True, (255, 255, 255)), (980, 400))
        back_button = Button(50, 640, 160, 40, "VOLTAR", self.back_to_menu, accent=(255, 144, 144))
        back_button.draw(self.screen, self.small_font)

    def draw_game(self):
        self.draw_background(self.screen, self.current_scene)

        for pipe in self.pipes:
            pipe.draw(self.screen, self.current_scene)
        for coin in self.coins:
            coin.draw(self.screen)

        self.bird.draw(self.screen, self.current_scene)
        for particle in self.particles:
            particle.draw(self.screen)

        score_text = self.big_font.render(str(self.score), True, (255, 255, 255))
        self.screen.blit(score_text, (SCREEN_WIDTH // 2 - 30, 40))
        coins_text = self.small_font.render(f"Moedas: {self.round_coins}", True, (255, 220, 110))
        self.screen.blit(coins_text, (70, 80))

        if self.state == "game_over":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(overlay, (0, 0, 0, 150), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
            self.screen.blit(overlay, (0, 0))
            game_over = self.big_font.render("GAME OVER", True, (255, 255, 255))
            self.screen.blit(game_over, (470, 180))
            points = self.font.render(f"Pontuação: {self.score}", True, (255, 255, 255))
            self.screen.blit(points, (520, 260))
            record = self.font.render(f"Recorde: {self.save_data['high_score']}", True, (255, 255, 255))
            self.screen.blit(record, (510, 310))
            coins = self.font.render(f"Moedas desta partida: {self.round_coins}", True, (255, 220, 110))
            self.screen.blit(coins, (430, 360))
            btn_restart = Button(460, 430, 190, 52, "JOGAR NOVAMENTE", self.start_game, accent=(120, 220, 135))
            btn_restart.draw(self.screen, self.small_font)
            btn_menu = Button(680, 430, 170, 52, "MENU", self.back_to_menu, accent=(255, 150, 150))
            btn_menu.draw(self.screen, self.small_font)

    def render_loading(self):
        self.draw_background(self.screen, self.current_scene)
        title = self.big_font.render("FLAPPY BIRD DELUXE", True, (255, 255, 255))
        self.screen.blit(title, (310, 120))

        msg = self.small_font.render(self.loading_steps[min(self.loading_index, len(self.loading_steps) - 1)], True, (255, 255, 255))
        self.screen.blit(msg, (500, 220))

        progress_rect = pygame.Rect(340, 300, 600, 28)
        fill_width = int((self.loading_progress) * 600)
        pygame.draw.rect(self.screen, (255, 255, 255), progress_rect, 3, border_radius=10)
        pygame.draw.rect(self.screen, (120, 220, 130), (progress_rect.x + 4, progress_rect.y + 4, fill_width - 8, 20), border_radius=10)

        percentage = self.font.render(f"{int((self.loading_index + self.loading_progress) / len(self.loading_steps) * 100)}%", True, (255, 255, 255))
        self.screen.blit(percentage, (590, 350))

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)

            self.screen.fill((0, 0, 0))
            if self.state == "loading":
                self.render_loading()
            elif self.state == "menu":
                self.draw_menu()
            elif self.state == "shop":
                self.draw_shop()
            elif self.state == "achievements":
                self.draw_achievements()
            elif self.state == "scenarios":
                self.draw_scenarios()
            elif self.state == "settings":
                self.draw_settings()
            elif self.state in {"playing", "game_over"}:
                self.draw_game()

            pygame.display.flip()

        pygame.quit()
