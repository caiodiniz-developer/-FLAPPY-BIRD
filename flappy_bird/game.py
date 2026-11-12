import math
import random

import pygame

from flappy_bird.achievements import evaluate_achievements
from flappy_bird.config import (
    ACHIEVEMENTS,
    BIRD_TYPES,
    BIRD_OUTFITS,
    FPS,
    PIPE_GAP,
    SCENARIOS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    clamp,
    lerp,
)
from flappy_bird.entities import Bird, Button, Coin, Particle, PipePair, draw_coin_icon
from flappy_bird.save_data import load_state, save_state


DIFFICULTY_PRESETS = {
    "easy": {"label": "LEVE", "gap": 218, "speed": 230},
    "normal": {"label": "NORMAL", "gap": PIPE_GAP, "speed": 280},
    "hard": {"label": "DESAFIO", "gap": 150, "speed": 330},
}
FPS_PRESETS = (30, 60, 120, 0)


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
        self.save_data.setdefault("unlocked_outfits", ["none"])
        if "none" not in self.save_data["unlocked_outfits"]:
            self.save_data["unlocked_outfits"].append("none")
        self.current_outfit_id = self.save_data.get("selected_outfit", "none")
        self.current_outfit = self.outfit_by_id(self.current_outfit_id)
        if self.current_outfit_id not in self.save_data["unlocked_outfits"]:
            self.current_outfit_id = "none"
            self.current_outfit = self.outfit_by_id("none")
        self.shop_category = "birds"
        display_flags = pygame.SCALED | pygame.RESIZABLE
        if self.save_data["settings"].get("fullscreen", False):
            display_flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), display_flags)
        self.font = pygame.font.SysFont("Bahnschrift", 30)
        self.big_font = pygame.font.SysFont("Bahnschrift", 52, bold=True)
        self.small_font = pygame.font.SysFont("Bahnschrift", 22)
        self.arcade_font = pygame.font.SysFont("Bahnschrift", 58, bold=True)
        self.arcade_small_font = pygame.font.SysFont("Bahnschrift", 18, bold=True)
        self.hud_score_font = pygame.font.SysFont("Bahnschrift", 40, bold=True)
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
        self.settings_controls = {}
        self.pause_buttons = []
        self.game_over_buttons = []
        self.game_over_notification = ""
        self.warning_message = ""
        self.notice_message = ""
        self.notice_timer = 0.0
        self.transition_alpha = 0
        self.paused_from = "playing"
        self.settings_return_state = "menu"
        self.dragging_setting = None
        self.background_cache = {}
        self.stars = [
            (random.randrange(18, SCREEN_WIDTH - 18), random.randrange(18, SCREEN_HEIGHT // 2), random.choice((1, 1, 2)))
            for _ in range(90)
        ]

        self.reset_run()
        self.menu_bird = Bird(900, 375, self.bird_by_id(self.current_bird_id), self.current_outfit)
        self.loading_bird = Bird(300, 455, self.bird_by_id(self.current_bird_id), self.current_outfit)
        self.menu_elapsed = 0.0
        self.loading_elapsed = 0.0
        self.populate_menu_buttons()

    def bird_by_id(self, bird_id):
        for bird in BIRD_TYPES:
            if bird["id"] == bird_id:
                return bird
        return BIRD_TYPES[0]

    def outfit_by_id(self, outfit_id):
        for outfit in BIRD_OUTFITS:
            if outfit["id"] == outfit_id:
                return outfit
        return BIRD_OUTFITS[0]

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
        self.bird = Bird(220, SCREEN_HEIGHT // 2 - 40, self.bird_by_id(self.current_bird_id), self.current_outfit)
        self.pipes = []
        self.coins = []
        self.particles = []
        self.score = 0
        self.round_coins = 0
        self.streak = 0
        self.best_streak = 0
        self.pipes_spawned = 0
        self.perfect_timer = 0.0
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
        self.settings_return_state = self.state
        self.state = "settings"

    def back_to_menu(self):
        self.state = "menu"

    def back_from_settings(self):
        self.state = self.settings_return_state

    def show_notice(self, message):
        self.notice_message = message
        self.notice_timer = 2.0

    def resume_game(self):
        self.state = self.paused_from

    def pause_game(self):
        if self.state == "playing":
            self.paused_from = "playing"
            self.state = "paused"

    def toggle_fullscreen(self):
        settings = self.save_data["settings"]
        previous = settings.get("fullscreen", False)
        settings["fullscreen"] = not previous
        flags = pygame.SCALED | pygame.RESIZABLE
        if settings["fullscreen"]:
            flags |= pygame.FULLSCREEN
        try:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        except pygame.error as error:
            settings["fullscreen"] = previous
            self.show_notice("Não foi possível alterar o modo de tela.")
            print(f"Fullscreen toggle failed: {error}")
            return
        save_state(self.save_data)

    def cycle_setting(self, setting, values):
        current = self.save_data["settings"].get(setting, values[0])
        try:
            index = values.index(current)
        except ValueError:
            index = 0
        self.save_data["settings"][setting] = values[(index + 1) % len(values)]
        save_state(self.save_data)

    def restart_game(self):
        self.start_game()

    def buy_bird(self, bird_id):
        bird = self.bird_by_id(bird_id)
        if bird_id in self.save_data["unlocked_birds"]:
            self.save_data["selected_bird"] = bird_id
            self.current_bird_id = bird_id
            self.current_bird = bird
            self.menu_bird.bird_type = bird
            self.menu_bird.outfit = self.current_outfit
            self.loading_bird.bird_type = bird
            self.loading_bird.outfit = self.current_outfit
            self.show_notice("Personagem selecionado!")
            save_state(self.save_data)
            return
        if self.save_data["coins"] >= bird["price"]:
            self.save_data["coins"] -= bird["price"]
            self.save_data["unlocked_birds"].append(bird_id)
            self.save_data["selected_bird"] = bird_id
            self.current_bird_id = bird_id
            self.current_bird = bird
            self.menu_bird.bird_type = bird
            self.menu_bird.outfit = self.current_outfit
            self.loading_bird.bird_type = bird
            self.loading_bird.outfit = self.current_outfit
            self.show_notice("Novo personagem desbloqueado!")
            save_state(self.save_data)
        else:
            self.show_notice("Moedas insuficientes.")

    def buy_outfit(self, outfit_id):
        outfit = self.outfit_by_id(outfit_id)
        if outfit_id in self.save_data["unlocked_outfits"]:
            self.save_data["selected_outfit"] = outfit_id
            self.current_outfit_id = outfit_id
            self.current_outfit = outfit
            self.bird.outfit = outfit
            self.menu_bird.outfit = outfit
            self.loading_bird.outfit = outfit
            self.show_notice(f"{outfit['name']} equipado!")
            save_state(self.save_data)
            return
        if self.save_data["coins"] >= outfit["price"]:
            self.save_data["coins"] -= outfit["price"]
            self.save_data["unlocked_outfits"].append(outfit_id)
            self.save_data["selected_outfit"] = outfit_id
            self.current_outfit_id = outfit_id
            self.current_outfit = outfit
            self.bird.outfit = outfit
            self.menu_bird.outfit = outfit
            self.loading_bird.outfit = outfit
            self.show_notice("Novo visual desbloqueado!")
            save_state(self.save_data)
        else:
            self.show_notice("Moedas insuficientes para esse visual.")

    def buy_scene(self, scene_id):
        scene = self.scene_by_id(scene_id)
        if scene_id in self.save_data["unlocked_scenes"]:
            self.save_data["selected_scene"] = scene_id
            self.current_scene_id = scene_id
            self.current_scene = scene
            self.show_notice("Cenário selecionado!")
            save_state(self.save_data)
            return
        if self.save_data["coins"] >= scene["price"]:
            self.save_data["coins"] -= scene["price"]
            self.save_data["unlocked_scenes"].append(scene_id)
            self.save_data["selected_scene"] = scene_id
            self.current_scene_id = scene_id
            self.current_scene = scene
            self.show_notice("Novo cenário desbloqueado!")
            save_state(self.save_data)
        else:
            self.show_notice("Moedas insuficientes.")

    def save_current_progress(self):
        self.save_data["selected_bird"] = self.current_bird_id
        self.save_data["selected_scene"] = self.current_scene_id
        save_state(self.save_data)

    def spawn_pipe(self):
        gap_y = random.randint(140, SCREEN_HEIGHT - 220)
        preset = DIFFICULTY_PRESETS.get(self.save_data["settings"].get("difficulty"), DIFFICULTY_PRESETS["normal"])
        speed = preset["speed"] + min(self.score * 3, 120)
        pipe_x = SCREEN_WIDTH + 80
        gap_height = preset["gap"]
        self.pipes.append(PipePair(pipe_x, gap_y, gap_height, speed=speed))
        coin_y = gap_y + gap_height / 2
        coin_offsets = (-38, 0, 38) if (self.pipes_spawned + 1) % 4 == 0 else (0,)
        for offset in coin_offsets:
            self.coins.append(Coin(pipe_x + 45 + offset, coin_y, speed=speed))
        self.pipes_spawned += 1

    def update_particles(self, dt):
        for particle in self.particles[:]:
            particle.update(dt)
            if particle.life <= 0:
                self.particles.remove(particle)

    def add_particles(self, x, y, color):
        if not self.save_data["settings"].get("particles_enabled", True):
            return
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
                self.streak += 1
                self.best_streak = max(self.best_streak, self.streak)
                self.save_data["stats"]["total_obstacles_passed"] += 1
                self.add_particles(self.bird.x, 100, self.current_scene["accent"])
                gap_center = pipe.gap_y + pipe.gap_height / 2
                perfect_threshold = max(18, pipe.gap_height * 0.18)
                if abs(self.bird.y - gap_center) <= perfect_threshold:
                    self.round_coins += 1
                    self.perfect_timer = 1.4
                    self.add_particles(self.bird.x, self.bird.y, (255, 226, 117))
                if self.streak % 5 == 0:
                    self.round_coins += 2
                    self.add_particles(self.bird.x, 142, (255, 214, 100))

        self.update_particles(dt)

        if self.bird.y > SCREEN_HEIGHT - 90:
            self.bird.y = SCREEN_HEIGHT - 90
            self.bird.velocity = 0

        if self.state == "game_over":
            self.finish_round()

    def finish_round(self):
        previous_best = self.save_data["high_score"]
        self.save_data["high_score"] = max(self.save_data["high_score"], self.score)
        self.save_data["coins"] += self.round_coins
        self.save_data["stats"]["games_played"] += 1
        self.save_data["stats"]["total_coins_earned"] += self.round_coins
        self.save_data["stats"]["scenes_played"][self.current_scene_id] = self.save_data["stats"].get("scenes_played", {}).get(self.current_scene_id, 0) + 1
        self.game_over_notification = f"Pontuação: {self.score} | Moedas: {self.round_coins}"
        self.warning_message = "NOVO RECORDE!" if self.score > previous_best else ""
        reward_notifications = evaluate_achievements(self.save_data)
        if reward_notifications:
            self.warning_message = "Conquista desbloqueada!"
        save_state(self.save_data)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False

        if self.state == "loading":
            return

        if self.state == "menu":
            for button in self.menu_buttons:
                button.handle_event(event)

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.start_game()
                elif event.key == pygame.K_s:
                    self.open_shop()
                elif event.key == pygame.K_a:
                    self.open_achievements()
                elif event.key == pygame.K_c:
                    self.open_scenarios()
                elif event.key == pygame.K_o:
                    self.open_settings()

        if self.state == "shop" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if pygame.Rect(50, 630, 180, 60).collidepoint(event.pos):
                self.back_to_menu()
                return
            if pygame.Rect(100, 174, 170, 34).collidepoint(event.pos):
                self.shop_category = "birds"
                return
            if pygame.Rect(278, 174, 190, 34).collidepoint(event.pos):
                self.shop_category = "outfits"
                return
            for card in self.shop_cards:
                if card["rect"].collidepoint(event.pos):
                    if "bird_id" in card:
                        self.buy_bird(card["bird_id"])
                    else:
                        self.buy_outfit(card["outfit_id"])
        if self.state == "shop" and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.back_to_menu()
            elif event.key == pygame.K_b:
                self.shop_category = "birds"
            elif event.key == pygame.K_o:
                self.shop_category = "outfits"

        if self.state == "scenarios" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if pygame.Rect(50, 630, 180, 60).collidepoint(event.pos):
                self.back_to_menu()
                return
            for card in self.scenario_cards:
                if card["rect"].collidepoint(event.pos):
                    self.buy_scene(card["scene_id"])
        if self.state == "scenarios" and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back_to_menu()

        if self.state == "playing":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.pause_game()
                return
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                self.pause_game()
                return
            elif event.type == pygame.KEYDOWN and event.key in {pygame.K_SPACE, pygame.K_w, pygame.K_UP}:
                self.bird.jump()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if pygame.Rect(1156, 22, 88, 48).collidepoint(event.pos):
                    self.pause_game()
                    return
                else:
                    self.bird.jump()

        if self.state == "paused":
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    self.resume_game()
                elif event.key == pygame.K_r:
                    self.start_game()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in self.pause_buttons:
                    if button.rect.collidepoint(event.pos):
                        button.handle_event(event)
                        return

        if self.state == "settings":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = self.settings_return_state
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if pygame.Rect(50, 630, 180, 60).collidepoint(event.pos):
                    self.state = self.settings_return_state
                    return

                x, y = event.pos
                volume_rows = {
                    184: "master_volume",
                    254: "music_volume",
                    324: "sfx_volume",
                }
                for row_y, setting in volume_rows.items():
                    if 475 <= x <= 1000 and row_y - 20 <= y <= row_y + 24:
                        self.save_data["settings"][setting] = round(clamp((x - 500) / 460, 0, 1), 1)
                        self.dragging_setting = setting
                        save_state(self.save_data)
                        return
                if pygame.Rect(470, 385, 530, 48).collidepoint(event.pos):
                    self.cycle_setting("difficulty", ("easy", "normal", "hard"))
                elif pygame.Rect(470, 455, 530, 48).collidepoint(event.pos):
                    self.cycle_setting("fps_limit", FPS_PRESETS)
                elif pygame.Rect(470, 520, 530, 48).collidepoint(event.pos):
                    self.toggle_fullscreen()
                elif pygame.Rect(470, 580, 530, 44).collidepoint(event.pos):
                    self.save_data["settings"]["particles_enabled"] = not self.save_data["settings"].get("particles_enabled", True)
                    save_state(self.save_data)
            elif event.type == pygame.MOUSEMOTION and self.dragging_setting:
                x, y = event.pos
                row_positions = {
                    184: "master_volume",
                    254: "music_volume",
                    324: "sfx_volume",
                }
                for row_y, setting in row_positions.items():
                    if setting == self.dragging_setting and row_y - 20 <= y <= row_y + 24:
                        self.save_data["settings"][setting] = round(clamp((x - 500) / 460, 0, 1), 1)
                        break
            elif event.type == pygame.MOUSEBUTTONUP and self.dragging_setting:
                save_state(self.save_data)
                self.dragging_setting = None

        if self.state == "game_over":
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_r):
                    self.start_game()
                elif event.key == pygame.K_ESCAPE:
                    self.back_to_menu()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in self.game_over_buttons:
                    button.handle_event(event)

        if self.state == "achievements":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.back_to_menu()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and pygame.Rect(50, 630, 180, 60).collidepoint(event.pos):
                self.back_to_menu()

    def update(self, dt):
        self.notice_timer = max(0.0, self.notice_timer - dt)
        if self.state == "loading":
            self.loading_elapsed += dt
            self.loading_progress += dt
            if self.loading_progress >= 1.0 and self.loading_index < len(self.loading_steps):
                self.loading_index += 1
                self.loading_progress = 0.0
            progress = clamp((self.loading_index + self.loading_progress) / len(self.loading_steps), 0, 1)
            self.loading_bird.x = 230 + progress * 820
            self.loading_bird.y = 322 + math.sin(self.loading_elapsed * 4) * 14
            self.loading_bird.frame += dt * 14
            if self.loading_index >= len(self.loading_steps):
                self.state = "menu"
                return
            return

        if self.state == "playing":
            self.perfect_timer = max(0.0, self.perfect_timer - dt)
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
        scene_id = scene["id"]
        gradient = self.background_cache.get(scene_id)
        if gradient is None:
            gradient = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            for i in range(SCREEN_HEIGHT):
                t = i / SCREEN_HEIGHT
                color = (
                    int(lerp(scene["sky_top"][0], scene["sky_bottom"][0], t)),
                    int(lerp(scene["sky_top"][1], scene["sky_bottom"][1], t)),
                    int(lerp(scene["sky_top"][2], scene["sky_bottom"][2], t)),
                )
                pygame.draw.line(gradient, color, (0, i), (SCREEN_WIDTH, i))
            self.background_cache[scene_id] = gradient
        surface.blit(gradient, (0, 0))

        if scene["theme"] == "night":
            for x, y, radius in self.stars[:40]:
                pygame.draw.circle(surface, (255, 255, 255), (x, y), radius)
        elif scene["theme"] == "space":
            for x, y, radius in self.stars:
                pygame.draw.circle(surface, (255, 255, 255), (x, y), radius)
            pygame.draw.circle(surface, (240, 200, 130), (1030, 120), 35)
            pygame.draw.circle(surface, (160, 140, 255), (900, 170), 18)

        if scene["theme"] in ("day", "desert", "snow"):
            sun_x, sun_y = 1014, 116
            sun_rows = (24, 48, 64, 80, 80, 64, 48, 24)
            for row, width in enumerate(sun_rows):
                row_x = sun_x + (88 - width) // 2
                pygame.draw.rect(surface, (255, 203, 102), (row_x, sun_y + row * 8, width, 8))
            for row in range(1, 7):
                width = sun_rows[row] - 16
                pygame.draw.rect(surface, (255, 231, 153), (sun_x + (88 - width) // 2, sun_y + row * 8, width, 8))
            pygame.draw.rect(surface, (255, 247, 190), (sun_x + 28, sun_y + 28, 32, 32))
            for ray_x in (1002, 1106):
                pygame.draw.rect(surface, (255, 219, 132), (ray_x, 148, 8, 24))
            for ray_y in (100, 204):
                pygame.draw.rect(surface, (255, 219, 132), (1042, ray_y, 24, 8))
        elif scene["theme"] == "night":
            pygame.draw.rect(surface, (245, 239, 193), (1030, 122, 64, 64))
            pygame.draw.rect(surface, scene["sky_top"], (1052, 108, 48, 48))

        # Layered stepped ridges add depth behind the cloud band and foreground.
        ridge_a = scene.get("mountain_a", (90, 146, 104))
        ridge_b = scene.get("mountain_b", (63, 108, 82))
        pygame.draw.polygon(surface, ridge_a, [
            (0, 574), (0, 526), (80, 526), (80, 494), (150, 494),
            (150, 462), (228, 462), (228, 494), (310, 494), (310, 526),
            (420, 526), (420, 478), (520, 478), (520, 510), (610, 510),
            (610, 542), (760, 542), (760, 494), (840, 494), (840, 462),
            (930, 462), (930, 494), (1030, 494), (1030, 526),
            (1140, 526), (1140, 494), (1220, 494), (1220, 526),
            (SCREEN_WIDTH, 526), (SCREEN_WIDTH, 574),
        ])
        pygame.draw.polygon(surface, ridge_b, [
            (0, 608), (0, 568), (112, 568), (112, 536), (208, 536),
            (208, 568), (318, 568), (318, 536), (410, 536),
            (410, 568), (550, 568), (550, 584), (690, 584),
            (690, 552), (786, 552), (786, 568), (924, 568),
            (924, 536), (1020, 536), (1020, 568), (1136, 568),
            (1136, 536), (SCREEN_WIDTH, 536), (SCREEN_WIDTH, 608),
        ])

        # A low band of block-shaped clouds mirrors the hand-drawn pixel scenery.
        cloud_fill = (242, 255, 216) if scene["theme"] in ("day", "city") else scene["cloud"]
        cloud_shadow = tuple(max(0, channel - 32) for channel in cloud_fill)
        cloud_y = 445
        for i, cloud_x in enumerate(range(-48, SCREEN_WIDTH + 180, 206)):
            drift = int(pygame.time.get_ticks() * 0.009) % 206
            x = cloud_x - drift
            crown_y = cloud_y + (i % 3) * 18
            pygame.draw.rect(surface, cloud_shadow, (x, crown_y + 28, 180, 52))
            pygame.draw.rect(surface, cloud_fill, (x + 18, crown_y + 14, 145, 54))
            pygame.draw.rect(surface, cloud_fill, (x + 43, crown_y, 84, 34))
            pygame.draw.rect(surface, cloud_fill, (x + 124, crown_y + 8, 48, 34))
            pygame.draw.rect(surface, (255, 255, 240), (x + 34, crown_y + 18, 106, 10))

        horizon = 625
        building_outline = (67, 187, 200)
        building_fill = (157, 221, 193) if scene["theme"] != "night" else (57, 91, 126)
        building_specs = (
            (34, 86, 145), (117, 54, 206), (205, 120, 115), (345, 76, 158),
            (485, 115, 214), (660, 66, 132), (779, 108, 183), (945, 76, 162),
            (1098, 120, 220), (1222, 72, 156),
        )
        if scene["theme"] in ("day", "night", "city"):
            for index, (x, width, height) in enumerate(building_specs):
                top = horizon - height
                rect = pygame.Rect(x, top, width, height)
                pygame.draw.rect(surface, building_outline, rect.inflate(8, 8), 5)
                pygame.draw.rect(surface, building_fill, rect)
                pygame.draw.rect(surface, (209, 250, 224), (x + 8, top + 8, 7, height - 16))
                for window_y in range(top + 16, horizon - 14, 24):
                    for window_x in range(x + 20, x + width - 8, 22):
                        window_color = (116, 200, 185)
                        if scene["theme"] in ("night", "city") and (index + window_x // 22 + window_y // 24) % 3 == 0:
                            window_color = (255, 218, 124)
                        pygame.draw.rect(surface, window_color, (window_x, window_y, 8, 12))
                if index % 3 == 1:
                    pygame.draw.rect(surface, building_outline, (x + width // 2 - 12, top - 28, 24, 28), 4)

        if scene["theme"] == "forest":
            for x in range(0, SCREEN_WIDTH + 80, 105):
                pygame.draw.rect(surface, (75, 58, 50), (x + 34, horizon - 98, 18, 100))
                for tier in range(4):
                    tier_y = horizon - 58 - tier * 28
                    tier_w = 82 - tier * 15
                    pygame.draw.rect(surface, (36, 119 - tier * 7, 76 - tier * 5), (x + 43 - tier_w // 2, tier_y - 20, tier_w, 28))
        elif scene["theme"] == "desert":
            for x in range(-20, SCREEN_WIDTH + 100, 190):
                pygame.draw.rect(surface, (215, 164, 91), (x, horizon - 55, 96, 55))
                pygame.draw.rect(surface, (232, 191, 113), (x + 16, horizon - 76, 64, 24))
        elif scene["theme"] == "snow":
            for x in range(0, SCREEN_WIDTH + 60, 110):
                pygame.draw.rect(surface, (240, 250, 255), (x, horizon - 20, 42, 12))
                pygame.draw.rect(surface, (240, 250, 255), (x + 12, horizon - 32, 24, 12))
        elif scene["theme"] == "volcano":
            for x in range(-30, SCREEN_WIDTH + 80, 140):
                pygame.draw.polygon(surface, (92, 40, 37), [(x, horizon), (x + 48, horizon - 124), (x + 112, horizon)])
                pygame.draw.rect(surface, (255, 124, 48), (x + 45, horizon - 72, 12, 42))

        ground_y = SCREEN_HEIGHT - 90
        pygame.draw.rect(surface, (52, 126, 78), (0, ground_y, SCREEN_WIDTH, SCREEN_HEIGHT - ground_y))
        pygame.draw.rect(surface, (157, 219, 97), (0, ground_y, SCREEN_WIDTH, 11))
        pygame.draw.rect(surface, (227, 204, 139), (0, ground_y + 18, SCREEN_WIDTH, 26))
        pygame.draw.rect(surface, (155, 112, 95), (0, ground_y + 44, SCREEN_WIDTH, SCREEN_HEIGHT - ground_y - 44))
        for x in range(0, SCREEN_WIDTH, 32):
            pygame.draw.rect(surface, (73, 164, 87), (x, ground_y, 17, 5))
            pygame.draw.rect(surface, (127, 91, 87), (x + (16 if x % 64 else 0), ground_y + 49, 16, 9))
            pygame.draw.rect(surface, (190, 144, 115), (x, ground_y + 67, 16, 8))

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
        arcade_text("EDIÇÃO ARCADE PIXEL", (104, 235), (208, 226, 218), self.arcade_small_font)

        for button in self.menu_buttons:
            button.draw(self.screen, self.arcade_small_font)

        pygame.draw.rect(self.screen, (20, 26, 44), (766, 42, 212, 48))
        pygame.draw.rect(self.screen, (246, 190, 91), (766, 42, 212, 48), 3)
        pygame.draw.rect(self.screen, (20, 26, 44), (990, 42, 226, 48))
        pygame.draw.rect(self.screen, (246, 190, 91), (990, 42, 226, 48), 3)
        draw_coin_icon(self.screen, (790, 66), phase=math.pi / 2, radius=9)
        coin_display = self.arcade_small_font.render(f"MOEDAS  {self.save_data['coins']}", True, (255, 221, 130))
        best_score = self.arcade_small_font.render(f"RECORDE  {self.save_data['high_score']}", True, (234, 245, 227))
        self.screen.blit(coin_display, (806, 55))
        self.screen.blit(best_score, (1004, 55))

        pygame.draw.rect(self.screen, (18, 30, 52), (690, 265, 440, 250), 5)
        pygame.draw.rect(self.screen, (32, 75, 86), (704, 279, 412, 222))
        pygame.draw.rect(self.screen, (246, 190, 91), (700, 275, 420, 230), 2)
        player_label = self.arcade_small_font.render(self.current_bird["name"].upper(), True, (255, 224, 143))
        self.screen.blit(player_label, player_label.get_rect(center=(910, 296)))
        pygame.draw.rect(self.screen, (58, 106, 113), (804, 319, 212, 2))
        pygame.draw.rect(self.screen, (255, 232, 153), (808, 447, 184, 8))
        pygame.draw.rect(self.screen, (255, 232, 153), (832, 455, 136, 5))
        self.menu_bird.draw(self.screen, self.current_scene, scale=2.15)
        hint = self.arcade_small_font.render("TRILHA BÔNUS A CADA 4 CANOS", True, (255, 221, 130))
        self.screen.blit(hint, hint.get_rect(center=(910, 535)))
        control_hint = self.small_font.render("ESPAÇO / CLIQUE PARA VOAR", True, (244, 249, 229))
        self.screen.blit(control_hint, control_hint.get_rect(center=(910, 566)))
        footer = self.arcade_small_font.render("APERTE ESPAÇO  •  VAMOS VOAR", True, (48, 95, 72))
        self.screen.blit(footer, footer.get_rect(center=(910, 635)))

    def draw_page_frame(self, title, subtitle):
        self.draw_background(self.screen, self.current_scene)
        panel = pygame.Surface((1160, 620), pygame.SRCALPHA)
        panel.fill((17, 29, 49, 226))
        self.screen.blit(panel, (60, 35))
        pygame.draw.rect(self.screen, (16, 23, 40), (54, 29, 1172, 632), width=5)
        pygame.draw.rect(self.screen, (255, 207, 117), (62, 37, 1156, 616), width=2)
        pygame.draw.rect(self.screen, (255, 207, 117), (62, 37, 1156, 7))

        title_surface = self.big_font.render(title, True, (255, 226, 164))
        self.screen.blit(title_surface, (100, 68))
        subtitle_surface = self.small_font.render(subtitle, True, (196, 218, 222))
        self.screen.blit(subtitle_surface, (102, 127))

        wallet = self.arcade_small_font.render(f"MOEDAS  {self.save_data['coins']}", True, (255, 224, 146))
        wallet_rect = wallet.get_rect(topright=(1170, 79))
        self.screen.blit(wallet, wallet_rect)
        pygame.draw.line(self.screen, (255, 207, 117), (100, 165), (1180, 165), 2)

    def draw_back_button(self, action=None):
        action = action or self.back_to_menu
        Button(84, 635, 160, 42, "VOLTAR", action, accent=(221, 130, 113), text_color=(35, 28, 38)).draw(
            self.screen, self.arcade_small_font
        )

    def draw_notice(self):
        if self.notice_timer <= 0 or not self.notice_message:
            return
        rect = pygame.Rect(430, 648, 420, 42)
        pygame.draw.rect(self.screen, (12, 21, 38), rect.move(0, 4), border_radius=8)
        pygame.draw.rect(self.screen, (31, 57, 68), rect, border_radius=8)
        pygame.draw.rect(self.screen, (255, 207, 117), rect, width=2, border_radius=8)
        text = self.arcade_small_font.render(self.notice_message, True, (255, 234, 185))
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_shop(self):
        self.draw_page_frame("HANGAR & GUARDA-ROUPA", "Monte seu visual: escolha uma ave e equipe acessórios sem mudar a jogabilidade.")
        tab_specs = (
            ("birds", pygame.Rect(100, 174, 170, 34), "AVES"),
            ("outfits", pygame.Rect(278, 174, 190, 34), "ROUPAS"),
        )
        for category, rect, label in tab_specs:
            selected = category == self.shop_category
            fill = (255, 207, 117) if selected else (29, 49, 68)
            text_color = (25, 34, 48) if selected else (196, 218, 222)
            pygame.draw.rect(self.screen, (9, 18, 31), rect.move(0, 3))
            pygame.draw.rect(self.screen, fill, rect)
            pygame.draw.rect(self.screen, (255, 226, 164) if selected else (83, 115, 132), rect, width=2)
            tab_text = self.arcade_small_font.render(label, True, text_color)
            self.screen.blit(tab_text, tab_text.get_rect(center=rect.center))

        self.shop_cards = []
        if self.shop_category == "birds":
            rarity_colors = {
                "Comum": (179, 205, 194),
                "Raro": (119, 204, 255),
                "Épico": (204, 153, 255),
                "Lendário": (255, 190, 105),
                "Mitológico": (255, 132, 190),
            }
            for index, bird in enumerate(BIRD_TYPES):
                column = index % 5
                row = index // 5
                x = 100 + column * 218
                y = 218 + row * 186
                rect = pygame.Rect(x, y, 202, 170)
                self.shop_cards.append({"bird_id": bird["id"], "rect": rect})
                unlocked = bird["id"] in self.save_data["unlocked_birds"]
                selected = bird["id"] == self.save_data["selected_bird"]
                pygame.draw.rect(self.screen, (12, 21, 38), rect.move(0, 5), border_radius=12)
                pygame.draw.rect(self.screen, (31, 49, 70), rect, border_radius=12)
                pygame.draw.rect(self.screen, bird["accent"], rect, width=2, border_radius=12)
                if selected:
                    pygame.draw.rect(self.screen, (145, 216, 152), rect.inflate(-8, -8), width=2, border_radius=10)
                rarity = self.arcade_small_font.render(bird["rarity"].upper(), True, rarity_colors.get(bird["rarity"], (220, 226, 218)))
                self.screen.blit(rarity, rarity.get_rect(midtop=(rect.centerx, y + 7)))
                Bird(rect.centerx, y + 61, bird, self.current_outfit).draw(self.screen, self.current_scene, scale=0.72)
                label = self.small_font.render(bird["name"], True, (245, 245, 230))
                self.screen.blit(label, label.get_rect(center=(rect.centerx, y + 111)))
                status = f"{bird['price']} MOEDAS" if not unlocked else ("EM USO" if selected else "DESBLOQUEADO")
                status_color = (255, 215, 132) if not unlocked else ((164, 235, 169) if selected else (190, 215, 209))
                status_text = self.arcade_small_font.render(status, True, status_color)
                self.screen.blit(status_text, status_text.get_rect(center=(rect.centerx, y + 145)))
        else:
            for index, outfit in enumerate(BIRD_OUTFITS):
                column = index % 4
                row = index // 4
                x = 100 + column * 270
                y = 218 + row * 186
                rect = pygame.Rect(x, y, 250, 170)
                self.shop_cards.append({"outfit_id": outfit["id"], "rect": rect})
                unlocked = outfit["id"] in self.save_data["unlocked_outfits"]
                selected = outfit["id"] == self.current_outfit_id
                pygame.draw.rect(self.screen, (12, 21, 38), rect.move(0, 5), border_radius=12)
                pygame.draw.rect(self.screen, (31, 49, 70), rect, border_radius=12)
                pygame.draw.rect(self.screen, outfit["color"], rect, width=2, border_radius=12)
                if selected:
                    pygame.draw.rect(self.screen, (145, 216, 152), rect.inflate(-8, -8), width=2, border_radius=10)
                Bird(rect.centerx, y + 65, self.current_bird, outfit).draw(self.screen, self.current_scene, scale=1.0)
                name = self.small_font.render(outfit["name"], True, (245, 245, 230))
                self.screen.blit(name, name.get_rect(center=(rect.centerx, y + 113)))
                description = self.arcade_small_font.render(outfit["description"], True, (176, 199, 205))
                self.screen.blit(description, description.get_rect(center=(rect.centerx, y + 137)))
                status = f"{outfit['price']} MOEDAS" if not unlocked else ("EQUIPADO" if selected else "DESBLOQUEADO")
                status_color = (255, 215, 132) if not unlocked else ((164, 235, 169) if selected else (190, 215, 209))
                status_text = self.arcade_small_font.render(status, True, status_color)
                self.screen.blit(status_text, status_text.get_rect(center=(rect.centerx, y + 157)))

        self.draw_back_button()

    def draw_achievements(self):
        self.draw_page_frame("CONQUISTAS", "Complete objetivos em suas partidas para receber moedas de recompensa.")
        for index, item in enumerate(ACHIEVEMENTS):
            column = index // 5
            row = index % 5
            x = 96 + column * 548
            y = 185 + row * 84
            rect = pygame.Rect(x, y, 520, 72)
            unlocked = self.save_data["achievements"].get(item["id"], {}).get("unlocked", False)
            data = self.save_data["achievements"].get(item["id"], {})
            progress = min(item["requirement"], data.get("progress", 0))
            progress_ratio = progress / max(1, item["requirement"])
            card_color = (38, 67, 68) if unlocked else (31, 47, 66)
            pygame.draw.rect(self.screen, (12, 21, 38), rect.move(0, 4), border_radius=10)
            pygame.draw.rect(self.screen, card_color, rect, border_radius=10)
            pygame.draw.rect(self.screen, (142, 210, 145) if unlocked else (86, 118, 144), rect, width=2, border_radius=10)
            name = self.small_font.render(item["name"], True, (250, 238, 204))
            desc = self.arcade_small_font.render(item["description"], True, (196, 218, 222))
            self.screen.blit(name, (x + 16, y + 9))
            self.screen.blit(desc, (x + 16, y + 37))
            reward = self.arcade_small_font.render(f"+{item['reward']} COINS", True, (255, 215, 132))
            self.screen.blit(reward, reward.get_rect(topright=(rect.right - 14, y + 10)))
            bar = pygame.Rect(x + 16, y + 62, 488, 5)
            pygame.draw.rect(self.screen, (15, 25, 39), bar, border_radius=3)
            if progress_ratio:
                pygame.draw.rect(self.screen, (137, 217, 153), (bar.x, bar.y, max(5, int(bar.width * progress_ratio)), bar.height), border_radius=3)

        self.draw_back_button()

    def draw_scenarios(self):
        self.draw_page_frame("CENÁRIOS", "Escolha onde a próxima aventura vai acontecer.")
        self.scenario_cards = []
        for index, scene in enumerate(SCENARIOS):
            column = index % 4
            row = index // 4
            x = 100 + column * 270
            y = 190 + row * 205
            rect = pygame.Rect(x, y, 250, 188)
            self.scenario_cards.append({"scene_id": scene["id"], "rect": rect})
            unlocked = scene["id"] in self.save_data["unlocked_scenes"]
            selected = scene["id"] == self.save_data["selected_scene"]
            pygame.draw.rect(self.screen, (12, 21, 38), rect.move(0, 5), border_radius=12)
            pygame.draw.rect(self.screen, (28, 44, 64), rect, border_radius=12)
            pygame.draw.rect(self.screen, scene["accent"], rect, width=2, border_radius=12)
            preview = pygame.Rect(x + 12, y + 12, 226, 86)
            pygame.draw.rect(self.screen, scene["sky_top"], preview)
            pygame.draw.rect(self.screen, scene["sky_bottom"], (preview.x, preview.y + 43, preview.width, 43))
            pygame.draw.circle(self.screen, scene["accent"], (preview.right - 30, preview.y + 24), 13)
            pygame.draw.polygon(self.screen, scene["mountain_a"], [(preview.x, preview.bottom), (preview.x + 62, preview.y + 48), (preview.x + 112, preview.bottom), (preview.x + 162, preview.y + 52), (preview.right, preview.bottom)])
            pygame.draw.rect(self.screen, scene["ground_top"], (preview.x, preview.bottom - 8, preview.width, 8))
            label = self.small_font.render(scene["name"], True, (249, 242, 222))
            self.screen.blit(label, (x + 14, y + 108))
            status = "SELECIONADO" if selected else ("DESBLOQUEADO" if unlocked else f"{scene['price']} moedas")
            status_text = self.arcade_small_font.render(status, True, (165, 226, 169) if unlocked else (255, 215, 132))
            self.screen.blit(status_text, (x + 14, y + 138))
            if selected:
                pygame.draw.rect(self.screen, (160, 231, 167), rect.inflate(-8, -8), width=2, border_radius=10)

        self.draw_back_button()

    def draw_settings(self):
        self.draw_page_frame("CONFIGURAÇÕES", "Personalize os controles e a apresentação do jogo.")
        settings = self.save_data["settings"]

        def draw_slider(label, setting, y):
            pygame.draw.rect(self.screen, (29, 47, 66), (100, y - 16, 1080, 52), border_radius=8)
            self.screen.blit(self.small_font.render(label, True, (245, 242, 226)), (122, y - 7))
            track = pygame.Rect(500, y + 6, 460, 8)
            pygame.draw.rect(self.screen, (13, 23, 39), track, border_radius=4)
            fill = int(track.width * settings.get(setting, 0.8))
            pygame.draw.rect(self.screen, (112, 199, 183), (track.x, track.y, fill, track.height), border_radius=4)
            pygame.draw.circle(self.screen, (255, 218, 136), (track.x + fill, track.centery), 11)
            value = self.arcade_small_font.render(f"{settings.get(setting, 0.8):.1f}", True, (255, 221, 143))
            self.screen.blit(value, value.get_rect(midleft=(985, y - 1)))

        draw_slider("VOLUME GERAL", "master_volume", 184)
        draw_slider("MÚSICA", "music_volume", 254)
        draw_slider("EFEITOS", "sfx_volume", 324)

        difficulty = DIFFICULTY_PRESETS.get(settings.get("difficulty"), DIFFICULTY_PRESETS["normal"])["label"]
        rows = (
            (385, "DIFICULDADE", difficulty, "Altera a velocidade e o espaço entre os obstáculos."),
            (455, "LIMITE DE FPS", f"{settings.get('fps_limit', 60) or 'SEM LIMITE'}", "Ciclo: 30 / 60 / 120 / sem limite."),
            (520, "TELA", "INTEIRA" if settings.get("fullscreen", False) else "JANELA", "Clique para alternar o modo de exibição."),
            (580, "PARTÍCULAS", "ATIVADAS" if settings.get("particles_enabled", True) else "DESATIVADAS", "Desative para reduzir efeitos visuais."),
        )
        for y, label, value, description in rows:
            row_rect = pygame.Rect(100, y, 1080, 44)
            pygame.draw.rect(self.screen, (29, 47, 66), row_rect, border_radius=8)
            self.screen.blit(self.small_font.render(label, True, (245, 242, 226)), (122, y + 6))
            self.screen.blit(self.arcade_small_font.render(description, True, (163, 187, 196)), (430, y + 12))
            value_surface = self.arcade_small_font.render(value, True, (255, 221, 143))
            self.screen.blit(value_surface, value_surface.get_rect(midright=(1158, y + 22)))

        self.draw_back_button(self.back_from_settings)

    def draw_stat_card(self, rect, label, value, accent):
        pygame.draw.rect(self.screen, (8, 16, 31), rect.move(0, 4))
        pygame.draw.rect(self.screen, (23, 40, 59), rect)
        pygame.draw.rect(self.screen, accent, rect, width=2)
        pygame.draw.rect(self.screen, accent, (rect.x + 7, rect.y + 7, rect.width - 14, 3))
        label_surface = self.arcade_small_font.render(label, True, (183, 203, 210))
        self.screen.blit(label_surface, label_surface.get_rect(midtop=(rect.centerx, rect.y + 14)))
        value_surface = self.small_font.render(str(value), True, accent)
        self.screen.blit(value_surface, value_surface.get_rect(midbottom=(rect.centerx, rect.bottom - 9)))

    def draw_pause(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((9, 15, 29, 190))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(360, 105, 560, 520)
        pygame.draw.rect(self.screen, (7, 13, 27), panel.move(0, 9), border_radius=18)
        pygame.draw.rect(self.screen, (20, 37, 57), panel, border_radius=18)
        pygame.draw.rect(self.screen, (255, 207, 117), panel, width=3, border_radius=18)
        pygame.draw.rect(self.screen, (255, 207, 117), (panel.x + 5, panel.y + 5, panel.width - 10, 7))
        title = self.big_font.render("PAUSADO", True, (255, 226, 164))
        self.screen.blit(title, title.get_rect(center=(640, 174)))
        subtitle = self.small_font.render("Respire. O próximo voo começa quando quiser.", True, (196, 218, 222))
        self.screen.blit(subtitle, subtitle.get_rect(center=(640, 220)))
        self.draw_stat_card(pygame.Rect(408, 252, 136, 74), "PONTOS", self.score, (255, 218, 136))
        self.draw_stat_card(pygame.Rect(572, 252, 136, 74), "MOEDAS", f"+{self.round_coins}", (255, 218, 136))
        self.draw_stat_card(pygame.Rect(736, 252, 136, 74), "COMBO", f"x{self.streak}", (160, 226, 173))
        self.pause_buttons = [
            Button(490, 352, 300, 48, "CONTINUAR", self.resume_game, accent=(151, 211, 145), text_color=(25, 34, 52)),
            Button(490, 412, 300, 46, "RECOMEÇAR", self.start_game, accent=(255, 204, 112), text_color=(35, 28, 38)),
            Button(490, 470, 300, 46, "CONFIGURAÇÕES", self.open_settings, accent=(119, 190, 207), text_color=(25, 34, 52)),
            Button(490, 528, 300, 46, "MENU PRINCIPAL", self.back_to_menu, accent=(221, 130, 113), text_color=(35, 28, 38)),
        ]
        for button in self.pause_buttons:
            button.draw(self.screen, self.arcade_small_font)
        hint = self.arcade_small_font.render("ESC  •  CONTINUAR", True, (155, 181, 190))
        self.screen.blit(hint, hint.get_rect(center=(640, 596)))

    def draw_game(self):
        self.draw_background(self.screen, self.current_scene)

        for pipe in self.pipes:
            pipe.draw(self.screen, self.current_scene)
        for coin in self.coins:
            coin.draw(self.screen)

        self.bird.draw(self.screen, self.current_scene)
        for particle in self.particles:
            particle.draw(self.screen)

        def hud_panel(rect, accent):
            pygame.draw.rect(self.screen, (12, 21, 38), rect.move(0, 5))
            pygame.draw.rect(self.screen, (17, 34, 52), rect)
            pygame.draw.rect(self.screen, accent, rect, width=2)
            pygame.draw.rect(self.screen, accent, (rect.x + 7, rect.y + 7, rect.width - 14, 3))

        coin_panel = pygame.Rect(24, 18, 230, 72)
        hud_panel(coin_panel, (255, 207, 117))
        draw_coin_icon(self.screen, (51, 56), phase=math.pi / 2, radius=11)
        coin_label = self.arcade_small_font.render("MOEDAS", True, (197, 213, 215))
        coin_count = self.small_font.render(f"+{self.round_coins}", True, (255, 226, 148))
        self.screen.blit(coin_label, (76, 30))
        self.screen.blit(coin_count, (76, 54))

        score_panel = pygame.Rect(531, 14, 218, 82)
        hud_panel(score_panel, (255, 207, 117))
        score_label = self.arcade_small_font.render("PONTUAÇÃO", True, (197, 213, 215))
        score_text = self.hud_score_font.render(str(self.score), True, (255, 245, 220))
        self.screen.blit(score_label, score_label.get_rect(midtop=(640, 22)))
        self.screen.blit(score_text, score_text.get_rect(midtop=(640, 43)))

        streak_panel = pygame.Rect(956, 18, 184, 72)
        hud_panel(streak_panel, (145, 216, 152))
        streak_label = self.arcade_small_font.render("SEQUÊNCIA", True, (197, 213, 215))
        streak_count = self.small_font.render(f"x{self.streak}", True, (174, 241, 187))
        self.screen.blit(streak_label, streak_label.get_rect(midtop=(streak_panel.centerx, 30)))
        self.screen.blit(streak_count, streak_count.get_rect(midtop=(streak_panel.centerx, 54)))
        pause_button = Button(1156, 22, 88, 48, "II", None, accent=(255, 204, 112), text_color=(35, 28, 38))
        pause_button.draw(self.screen, self.arcade_small_font)

        if self.perfect_timer > 0 and self.state == "playing":
            banner = pygame.Rect(472, 112, 336, 42)
            pygame.draw.rect(self.screen, (9, 20, 34), banner.move(0, 4))
            pygame.draw.rect(self.screen, (31, 57, 68), banner)
            pygame.draw.rect(self.screen, (255, 218, 112), banner, width=2)
            perfect_label = self.arcade_small_font.render("VOO PERFEITO  +1 MOEDA", True, (255, 232, 150))
            self.screen.blit(perfect_label, perfect_label.get_rect(center=banner.center))
            bar_width = round(banner.width * self.perfect_timer / 1.4)
            pygame.draw.rect(self.screen, (255, 190, 70), (banner.x, banner.bottom - 3, bar_width, 3))

        if self.state == "game_over":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(overlay, (5, 12, 24, 205), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
            self.screen.blit(overlay, (0, 0))
            panel = pygame.Rect(340, 82, 600, 548)
            pygame.draw.rect(self.screen, (5, 12, 24), panel.move(0, 9), border_radius=18)
            pygame.draw.rect(self.screen, (20, 37, 57), panel, border_radius=18)
            pygame.draw.rect(self.screen, (255, 207, 117), panel, width=3, border_radius=18)
            pygame.draw.rect(self.screen, (255, 207, 117), (panel.x + 5, panel.y + 5, panel.width - 10, 7))
            title = self.big_font.render("FIM DE JOGO", True, (255, 226, 164))
            self.screen.blit(title, title.get_rect(center=(640, 148)))
            status_text = self.warning_message or "Mais um voo? Seu recorde espera."
            status_color = (160, 232, 165) if self.warning_message else (196, 218, 222)
            status = self.arcade_small_font.render(status_text, True, status_color)
            self.screen.blit(status, status.get_rect(center=(640, 193)))

            score_card = pygame.Rect(390, 220, 500, 102)
            pygame.draw.rect(self.screen, (8, 16, 31), score_card.move(0, 5))
            pygame.draw.rect(self.screen, (26, 48, 66), score_card)
            pygame.draw.rect(self.screen, (255, 207, 117), score_card, width=2)
            score_caption = self.arcade_small_font.render("PONTUAÇÃO DA PARTIDA", True, (193, 212, 214))
            score_value = self.hud_score_font.render(str(self.score), True, (255, 245, 220))
            self.screen.blit(score_caption, score_caption.get_rect(center=(640, 244)))
            self.screen.blit(score_value, score_value.get_rect(center=(640, 289)))

            self.draw_stat_card(pygame.Rect(390, 345, 150, 88), "RECORDE", self.save_data["high_score"], (255, 218, 136))
            self.draw_stat_card(pygame.Rect(565, 345, 150, 88), "GANHOS", f"+{self.round_coins}", (255, 218, 136))
            self.draw_stat_card(pygame.Rect(740, 345, 150, 88), "COMBO", f"x{self.best_streak}", (160, 226, 173))

            self.game_over_buttons = [
                Button(475, 465, 330, 52, "VOAR NOVAMENTE", self.start_game, accent=(151, 211, 145), text_color=(25, 34, 52)),
                Button(475, 530, 330, 48, "MENU PRINCIPAL", self.back_to_menu, accent=(119, 190, 207), text_color=(25, 34, 52)),
            ]
            for button in self.game_over_buttons:
                button.draw(self.screen, self.arcade_small_font)
            hint = self.arcade_small_font.render("ESPAÇO / ENTER  •  NOVA TENTATIVA", True, (155, 181, 190))
            self.screen.blit(hint, hint.get_rect(center=(640, 600)))

    def render_loading(self):
        self.draw_background(self.screen, self.current_scene)
        veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        veil.fill((7, 18, 33, 158))
        self.screen.blit(veil, (0, 0))

        frame = pygame.Rect(54, 35, 1172, 650)
        pygame.draw.rect(self.screen, (6, 14, 28), frame.move(0, 8))
        pygame.draw.rect(self.screen, (15, 31, 49), frame)
        pygame.draw.rect(self.screen, (255, 207, 117), frame, width=3)
        pygame.draw.rect(self.screen, (255, 207, 117), (frame.x + 5, frame.y + 5, frame.width - 10, 7))

        emblem = pygame.Rect(91, 67, 44, 44)
        pygame.draw.rect(self.screen, (255, 207, 117), emblem)
        pygame.draw.rect(self.screen, (19, 38, 57), emblem.inflate(-6, -6))
        pygame.draw.rect(self.screen, (7, 14, 26), (99, 79, 27, 19))
        pygame.draw.rect(self.screen, (255, 209, 46), (101, 81, 22, 14))
        pygame.draw.rect(self.screen, (255, 239, 191), (109, 82, 10, 4))
        pygame.draw.rect(self.screen, (255, 245, 219), (115, 82, 6, 8))
        pygame.draw.rect(self.screen, (22, 30, 45), (118, 85, 2, 4))
        pygame.draw.rect(self.screen, (242, 101, 54), (122, 85, 5, 6))
        pygame.draw.rect(self.screen, (255, 188, 58), (122, 83, 4, 3))
        pygame.draw.rect(self.screen, (237, 130, 48), (105, 97, 6, 2))
        pygame.draw.rect(self.screen, (237, 130, 48), (115, 97, 6, 2))
        brand = self.arcade_small_font.render("FLAPPY / ARCADE", True, (255, 222, 147))
        self.screen.blit(brand, (151, 68))
        title = self.big_font.render("PREPARANDO A PARTIDA", True, (246, 249, 232))
        self.screen.blit(title, (151, 88))

        scene_badge = pygame.Rect(914, 66, 259, 44)
        pygame.draw.rect(self.screen, (25, 47, 65), scene_badge)
        pygame.draw.rect(self.screen, self.current_scene["accent"], scene_badge, width=2)
        scene_label = self.arcade_small_font.render(f"MUNDO  /  {self.current_scene['name'].upper()}", True, (237, 241, 224))
        self.screen.blit(scene_label, scene_label.get_rect(center=scene_badge.center))

        viewport = pygame.Rect(91, 142, 1098, 334)
        pygame.draw.rect(self.screen, (5, 13, 26), viewport.inflate(12, 12))
        pygame.draw.rect(self.screen, (102, 143, 151), viewport.inflate(4, 4), width=2)
        self.screen.set_clip(viewport)

        for row in range(viewport.height):
            blend = row / max(1, viewport.height)
            color = tuple(
                round(lerp(self.current_scene["sky_top"][channel], self.current_scene["sky_bottom"][channel], blend))
                for channel in range(3)
            )
            pygame.draw.line(self.screen, color, (viewport.left, viewport.top + row), (viewport.right, viewport.top + row))

        if self.current_scene["theme"] in ("night", "space"):
            for index, (star_x, star_y, radius) in enumerate(self.stars):
                if star_y < viewport.height * 0.78:
                    twinkle = int((math.sin(self.loading_elapsed * 3 + index) + 1) * 35)
                    pygame.draw.rect(self.screen, (min(255, 185 + twinkle), min(255, 207 + twinkle), 255), (viewport.left + star_x % viewport.width, viewport.top + star_y % 220, radius + 1, radius + 1))

        drift = int(self.loading_elapsed * 16) % 260
        cloud_fill = self.current_scene["cloud"]
        for index, cloud_x in enumerate(range(-100, viewport.width + 260, 260)):
            x = viewport.left + cloud_x - drift
            y = viewport.top + 52 + (index % 2) * 35
            pygame.draw.rect(self.screen, tuple(max(0, channel - 25) for channel in cloud_fill), (x, y + 20, 118, 18))
            pygame.draw.rect(self.screen, cloud_fill, (x + 18, y + 10, 80, 28))
            pygame.draw.rect(self.screen, cloud_fill, (x + 37, y, 44, 18))

        pygame.draw.polygon(self.screen, self.current_scene["mountain_a"], [
            (viewport.left, viewport.top + 264), (viewport.left, viewport.top + 220),
            (viewport.left + 145, viewport.top + 166), (viewport.left + 260, viewport.top + 231),
            (viewport.left + 390, viewport.top + 180), (viewport.left + 535, viewport.top + 248),
            (viewport.left + 700, viewport.top + 171), (viewport.left + 850, viewport.top + 238),
            (viewport.right, viewport.top + 184), (viewport.right, viewport.bottom),
            (viewport.left, viewport.bottom),
        ])
        pygame.draw.polygon(self.screen, self.current_scene["mountain_b"], [
            (viewport.left, viewport.top + 284), (viewport.left + 190, viewport.top + 244),
            (viewport.left + 355, viewport.top + 275), (viewport.left + 520, viewport.top + 225),
            (viewport.left + 700, viewport.top + 278), (viewport.left + 890, viewport.top + 236),
            (viewport.right, viewport.top + 271), (viewport.right, viewport.bottom),
            (viewport.left, viewport.bottom),
        ])

        ground_y = viewport.top + 282
        pygame.draw.rect(self.screen, (35, 58, 68), (viewport.left, ground_y, viewport.width, 56))
        pygame.draw.rect(self.screen, self.current_scene["accent"], (viewport.left, ground_y, viewport.width, 5))
        for tile_x in range(viewport.left + 8, viewport.right, 42):
            pygame.draw.rect(self.screen, (53, 78, 83), (tile_x, ground_y + 18, 22, 7))
            pygame.draw.rect(self.screen, (53, 78, 83), (tile_x + 19, ground_y + 34, 22, 7))

        # A dotted flight route links the moving pilot to the gap and coin.
        route_y = viewport.top + 190
        for route_x in range(viewport.left + 90, viewport.right - 45, 28):
            pygame.draw.rect(self.screen, (228, 230, 185), (route_x, route_y, 9, 3))

        pipe = PipePair(viewport.left + 755, viewport.top + 112, 150, width=78, speed=0)
        pipe.draw(self.screen, self.current_scene)
        draw_coin_icon(self.screen, (viewport.left + 720, viewport.top + 188), self.loading_elapsed * 5, radius=10)
        draw_coin_icon(self.screen, (viewport.left + 760, viewport.top + 188), self.loading_elapsed * 5, radius=10)
        pygame.draw.circle(self.screen, (255, 236, 154), (round(self.loading_bird.x), round(self.loading_bird.y)), 29, width=1)
        pygame.draw.circle(self.screen, (255, 236, 154), (round(self.loading_bird.x), round(self.loading_bird.y)), 34, width=1)
        self.loading_bird.draw(self.screen, self.current_scene, scale=1.2)
        self.screen.set_clip(None)

        route_label = self.arcade_small_font.render("ROTA DE VOO  /  COLETE MOEDAS  /  EVITE OS CANOS", True, (194, 215, 213))
        self.screen.blit(route_label, (101, 493))
        phase = min(self.loading_index, len(self.loading_steps) - 1)
        phase_label = self.arcade_small_font.render(f"FASE {phase + 1:02d} / {len(self.loading_steps):02d}", True, (255, 220, 137))
        self.screen.blit(phase_label, phase_label.get_rect(topright=(1174, 493)))

        card = pygame.Rect(91, 520, 1098, 128)
        pygame.draw.rect(self.screen, (7, 17, 31), card.move(0, 5))
        pygame.draw.rect(self.screen, (21, 40, 58), card)
        pygame.draw.rect(self.screen, (78, 113, 127), card, width=2)

        progress = clamp((self.loading_index + self.loading_progress) / len(self.loading_steps), 0, 1)
        message = self.loading_steps[min(self.loading_index, len(self.loading_steps) - 1)]
        message_surface = self.small_font.render(message.upper(), True, (244, 247, 232))
        self.screen.blit(message_surface, (117, 535))
        percentage = self.arcade_font.render(f"{int(progress * 100):02d}%", True, (255, 224, 144))
        self.screen.blit(percentage, percentage.get_rect(topright=(1158, 522)))

        segment_width = 184
        segment_gap = 24
        segment_y = 572
        phase_names = ("BOOT", "MUNDO", "PILOTO", "SAVE", "GO!")
        for index, phase_name in enumerate(phase_names):
            x = 117 + index * (segment_width + segment_gap)
            segment = pygame.Rect(x, segment_y, segment_width, 13)
            pygame.draw.rect(self.screen, (7, 17, 31), segment)
            fill_ratio = clamp(progress * len(phase_names) - index, 0, 1)
            fill_width = round((segment.width - 4) * fill_ratio)
            if fill_width:
                pygame.draw.rect(self.screen, self.current_scene["accent"], (segment.x + 2, segment.y + 2, fill_width, segment.height - 4))
                pygame.draw.rect(self.screen, (255, 244, 200), (segment.x + 2, segment.y + 2, fill_width, 2))
            label_color = (255, 224, 144) if index <= self.loading_index else (128, 155, 166)
            label = self.arcade_small_font.render(phase_name, True, label_color)
            self.screen.blit(label, label.get_rect(midtop=(segment.centerx, 592)))

        tip = self.arcade_small_font.render("DICA  /  PASSE PELO CENTRO DO VÃO PARA GANHAR MOEDA EXTRA", True, (167, 200, 195))
        self.screen.blit(tip, tip.get_rect(center=(640, 627)))

    def run(self):
        while self.running:
            fps_limit = self.save_data["settings"].get("fps_limit", FPS)
            dt = min(self.clock.tick(fps_limit) / 1000.0, 0.05)
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
            elif self.state in {"playing", "paused", "game_over"}:
                self.draw_game()
                if self.state == "paused":
                    self.draw_pause()

            self.draw_notice()
            pygame.display.flip()

        pygame.quit()
