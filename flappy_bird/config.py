import math

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GRAVITY = 1350
JUMP_FORCE = 430
PIPE_SPEED = 280
PIPE_WIDTH = 90
PIPE_GAP = 180
GROUND_HEIGHT = 100

BIRD_TYPES = [
    {"id": "classic", "name": "Pássaro Clássico", "price": 0, "rarity": "Comum", "description": "O pássaro original, balanceado e confiável.", "colors": (255, 214, 10), "accent": (255, 146, 43)},
    {"id": "golden", "name": "Pássaro Dourado", "price": 150, "rarity": "Raro", "description": "Brilha como ouro e vale cada moeda.", "colors": (255, 192, 0), "accent": (255, 240, 150)},
    {"id": "blue", "name": "Pássaro Azul", "price": 180, "rarity": "Raro", "description": "Veloz e elegante.", "colors": (85, 170, 255), "accent": (170, 220, 255)},
    {"id": "red", "name": "Pássaro Vermelho", "price": 220, "rarity": "Épico", "description": "Uma intensidade que não passa despercebida.", "colors": (255, 96, 96), "accent": (255, 180, 120)},
    {"id": "robot", "name": "Pássaro Robô", "price": 300, "rarity": "Épico", "description": "Precisão mecânica para voos exatos.", "colors": (120, 135, 155), "accent": (190, 210, 230)},
    {"id": "ghost", "name": "Pássaro Fantasma", "price": 350, "rarity": "Lendário", "description": "Leve como fumaça, impossível de rastrear.", "colors": (200, 200, 220), "accent": (240, 240, 255)},
    {"id": "space", "name": "Pássaro Espacial", "price": 420, "rarity": "Lendário", "description": "Aventureiro cósmico com energia estelar.", "colors": (140, 120, 255), "accent": (240, 140, 255)},
    {"id": "fire", "name": "Pássaro de Fogo", "price": 470, "rarity": "Lendário", "description": "Chamas límpidas em cada curva.", "colors": (255, 110, 50), "accent": (255, 210, 60)},
    {"id": "ice", "name": "Pássaro de Gelo", "price": 520, "rarity": "Lendário", "description": "Um voo frio e mortal.", "colors": (100, 220, 255), "accent": (220, 245, 255)},
    {"id": "legend", "name": "Pássaro Lendário", "price": 650, "rarity": "Mitológico", "description": "O campeão supremo da noite.", "colors": (255, 80, 180), "accent": (255, 225, 120)},
]

BIRD_OUTFITS = [
    {"id": "none", "name": "Sem acessório", "price": 0, "style": "none", "color": (225, 231, 220), "description": "Visual clássico."},
    {"id": "pilot", "name": "Boné de piloto", "price": 90, "style": "pilot", "color": (75, 145, 210), "description": "Pronto pra voar."},
    {"id": "bandana", "name": "Bandana turbo", "price": 120, "style": "bandana", "color": (232, 83, 77), "description": "Rápida em curvas."},
    {"id": "explorer", "name": "Chapéu explorador", "price": 180, "style": "explorer", "color": (180, 129, 72), "description": "Explore novos céus."},
    {"id": "crown", "name": "Coroa pixel", "price": 240, "style": "crown", "color": (255, 196, 60), "description": "Realeza dos ares."},
    {"id": "hero", "name": "Capa de herói", "price": 280, "style": "hero", "color": (187, 83, 220), "description": "Rastro de herói."},
    {"id": "space", "name": "Capacete orbital", "price": 320, "style": "space", "color": (76, 218, 228), "description": "Para outro mundo."},
]

SCENARIOS = [
    {"id": "classic", "name": "Campo Clássico", "price": 0, "unlock_text": "Disponível desde o início.", "sky_top": (111, 200, 255), "sky_bottom": (173, 227, 255), "ground_top": (21, 151, 81), "ground_bottom": (64, 189, 95), "cloud": (255, 255, 255), "mountain_a": (90, 146, 104), "mountain_b": (63, 108, 82), "accent": (255, 225, 120), "theme": "day"},
    {"id": "night", "name": "Noite", "price": 200, "unlock_text": "Desbloqueia com 200 moedas.", "sky_top": (8, 12, 35), "sky_bottom": (32, 50, 92), "ground_top": (23, 42, 68), "ground_bottom": (11, 22, 43), "cloud": (200, 220, 255), "mountain_a": (53, 63, 91), "mountain_b": (28, 39, 63), "accent": (255, 220, 130), "theme": "night"},
    {"id": "forest", "name": "Floresta", "price": 240, "unlock_text": "Desbloqueia com 240 moedas.", "sky_top": (94, 178, 126), "sky_bottom": (195, 230, 162), "ground_top": (50, 121, 72), "ground_bottom": (18, 75, 42), "cloud": (245, 250, 255), "mountain_a": (48, 101, 67), "mountain_b": (28, 74, 50), "accent": (255, 209, 102), "theme": "forest"},
    {"id": "desert", "name": "Deserto", "price": 260, "unlock_text": "Desbloqueia com 260 moedas.", "sky_top": (246, 183, 95), "sky_bottom": (255, 228, 160), "ground_top": (188, 139, 68), "ground_bottom": (134, 96, 54), "cloud": (255, 244, 206), "mountain_a": (183, 126, 63), "mountain_b": (119, 83, 42), "accent": (248, 214, 92), "theme": "desert"},
    {"id": "snow", "name": "Neve", "price": 340, "unlock_text": "Desbloqueia com 340 moedas.", "sky_top": (160, 205, 255), "sky_bottom": (230, 243, 255), "ground_top": (185, 212, 220), "ground_bottom": (118, 150, 178), "cloud": (245, 250, 255), "mountain_a": (172, 191, 210), "mountain_b": (116, 139, 166), "accent": (255, 235, 160), "theme": "snow"},
    {"id": "space", "name": "Espaço", "price": 420, "unlock_text": "Desbloqueia com 420 moedas.", "sky_top": (4, 8, 20), "sky_bottom": (16, 20, 55), "ground_top": (28, 26, 53), "ground_bottom": (13, 19, 38), "cloud": (255, 255, 255), "mountain_a": (81, 85, 130), "mountain_b": (50, 51, 88), "accent": (209, 167, 255), "theme": "space"},
    {"id": "volcano", "name": "Vulcão", "price": 480, "unlock_text": "Desbloqueia com 480 moedas.", "sky_top": (190, 30, 30), "sky_bottom": (118, 46, 32), "ground_top": (93, 19, 16), "ground_bottom": (57, 11, 12), "cloud": (255, 200, 150), "mountain_a": (106, 48, 32), "mountain_b": (60, 27, 16), "accent": (255, 150, 60), "theme": "volcano"},
    {"id": "city", "name": "Cidade", "price": 560, "unlock_text": "Desbloqueia com 560 moedas.", "sky_top": (58, 72, 120), "sky_bottom": (133, 158, 209), "ground_top": (80, 88, 95), "ground_bottom": (46, 52, 62), "cloud": (235, 242, 255), "mountain_a": (72, 85, 110), "mountain_b": (50, 62, 83), "accent": (255, 214, 120), "theme": "city"},
]

ACHIEVEMENTS = [
    {"id": "first_flight", "name": "Primeiro Voo", "description": "Jogue pela primeira vez.", "requirement": 1, "reward": 25, "kind": "games_played"},
    {"id": "rookie", "name": "Iniciante", "description": "Marque 5 pontos.", "requirement": 5, "reward": 40, "kind": "best_score"},
    {"id": "good_pilot", "name": "Bom Piloto", "description": "Marque 20 pontos.", "requirement": 20, "reward": 90, "kind": "best_score"},
    {"id": "professional", "name": "Profissional", "description": "Marque 50 pontos.", "requirement": 50, "reward": 150, "kind": "best_score"},
    {"id": "legend", "name": "Lenda", "description": "Marque 100 pontos.", "requirement": 100, "reward": 260, "kind": "best_score"},
    {"id": "collector", "name": "Colecionador", "description": "Colete 100 moedas.", "requirement": 100, "reward": 80, "kind": "coins_total"},
    {"id": "millionaire", "name": "Milionário", "description": "Acumule 1000 moedas.", "requirement": 1000, "reward": 150, "kind": "wallet"},
    {"id": "survivor", "name": "Sobrevivente", "description": "Passe por 30 obstáculos em uma partida.", "requirement": 30, "reward": 110, "kind": "pipes_passed"},
    {"id": "explorer", "name": "Explorador", "description": "Jogue em todos os cenários.", "requirement": 8, "reward": 200, "kind": "scenarios_played"},
    {"id": "persistent", "name": "Persistente", "description": "Jogue 100 partidas.", "requirement": 100, "reward": 250, "kind": "games_played"},
]

def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def lerp(a, b, t):
    return a + (b - a) * t
