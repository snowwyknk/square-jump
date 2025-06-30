import pygame
import random
import sys
from PIL import Image
# Инициализация Pygame
pygame.inut()

#Ангел талисман(26.07.???)
phatom cube_frames = [
    pygame.image.load('phantomcube. jpeg').convert_alpha()
]

phatom_quotes = [
    'Добро пожаловать в Squre jump!',
    'Я Phatom, твой путеводитель в игре.',
    'Кто знает, кто разработчки... Может, под ними скрываются юнцы?'
]
class Phatomcube:
    def _init_(self):
        self.frames = phatom.frames
        self.quotes = phatom.quotes
        self.current_frame = 0
        self.current_quote = 0
        self.animation_speed = 0.1
        self.x = WIDTH - 150
        self.y = HEIGHT//2
        self.show_text = False
        self.text_timer = 0
        self.font = pygame.font.SysFont('Arial', 24, italic = True)

def update(self):
    #Анимация крыльев


    


#Настройка окна
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('square jump')
obstacle_gap = 200
obstacles = []
BASE_SPEED = 5
obstacle_speed = BASE_SPEED
frame_count = 0
obstacle_width = 30

# спрайт куб
player_frames = [
    pygame.image.load('player_frame1.png').convert_alpha(),
    pygame.image.load('player_frame2.png').convert_alpha(),
    pygame.image.load('player_frame3.png').convert_alpha()
]




#класс анимаций
class Animation:
    def _init_(self, frames, speed=0.1, loop=True):
        self.frames = frames
        self.speed = speed
        self.loop = loop
        self.current_frame = 0
        self.playing = True
        self.done = False

    def update(self):
        if not self.playing:
            return
        
        self.current_frame += self.speed
        if self.loop:
            self.current_frame %= len(self.frames)
        elif int(self. current_frame) >= len(self.frames) - 1:
            self.done = True
            self.current_frame = len(self.frames) - 1

    def get_current_frame(self):
        return self.frames[int(self.current_frame)]

player_animatons = {
    'idle': Animaton(player_frame[0:1]),
    'jump': Animation(plater_frame[1:3], 0.2),
    'death': Animation(player_frame[3:6], 0.3, loop=False)
}
current_animation = player_animation['idle']
def load_spritesheet(filename, frame_width, frame_height, cols):
    sheet = pygame.image.load(filename).convert_alpha()
    frames = []
    for i in range(cols):
        frame = sheet.subsurface(pygame.Rect(i * frame_width, frame_height))
        frames.append(frame)
    return frames

#Смена анимации
if is_jumping:
    current_animmation = player_animations['jump']
elif is_dead:
    current_animation = player_animations['death']
else:
    current_animation = player_animations['idle']

# Обновление кадра
current_animation.update()

#Отрисовка
screen.blit(current_animations.get_current_frame(), (player_x, player_y))

#Анимация взрыва
explosion_frames = [pygame.image.load(f'explosion_{i}.png') for i in range(4)]
explosion = Animation(explosion_frames, 0.5, loop=False)

#Момент смерти
explosion.playing = True
explosion.current_frame = 0

#игровой цикл
if explosion.playing:
    screen.blit(explosion.get_current_frame(), (explosion_x, explosion_y))
    explosion.update()





#Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]

#Состояние игры
MENU = 0
PLAYING = 1
game_start = MENU

#Шрифты
font_large = pygame. font.SysFont(' Masquerade Toy Store Stuff', 50)
font_small = pygame. font.SysFont(' Masquerade Toy Store Stuff', 30)

#Параметры игрока
player_size = 40
player_x = 100
player_y = HEIGHT//2
player_color = WHITE
gravity = 1
jump_force = -20
player_velocity = 0
is_jumping = False


#Параметры препятствий
obstracles = []
obstracle_width = 30
obsracle_gap = 300
obstracle_speed = 5
score = 0
font = pygame.font.SysFont(None, 36)

#Кнопки меню
start_button = pygame.Rect(WIDTH//2 - 100, HEIGHT//2, 200, 50)

def create_obstacle():
    height = random.randint(50, HEIGHT - 200)
    color = random.choice(COLORS)
    obstacles.append({
        'x': WIDTH,
        'height': height,
        'color': color,
        'passed': False
    })

def draw_player():
    pygame.draw.rect(screen, player_color, (player_x, player_y, player_size))
def draw_obstacles():
    for obstacle in obstacles:
        pygame.draw.rect(screen, obstacle['color'], (obstacle['x'], 0, obstacle_width, obstacle['height']))
        bottom_y = obstacle['height'] + obstacle_gap
        pygame.draw.rect(screen, obstacle['color'], (obstacle['x'], bottom_y, obstracle_width, HEIGHT - bottom_y))
def check_collision():
    player_rect = pygame.Rect(player_x, player_y, player_size)
    for obstacle in obstacles:
        top_rect = pygame.Rect(obstacle['x'], 0, obstracle_width, obstacle['height'])
        bottom_rect = pygame.Rect(obstacle['x'], obstacle['height'] + obstacle_gap, obstacle_width, HEIGHT - (obstacle['height'] + obstacle_gap))
    if player_rect.colliderect(top_rect) or player_rect.colliderect(bottom_rect):
        return True
    return False

def update_score():
    global score
    for obstacle in obstacles:
        if obstacle['x'] + obstacle_width < player_x and not obstacle['passed']:
            obstacle['passed'] = True
            score += 1

def draw_menu():
    screen.fill(BLACK)
    title = font_large.render('SQUARE JUMP', True, WHITE)
    start_text = font_small.render('START (SPACE/MOUSE)', True, BLACK)

    screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3))
    pygame.draw.rect(screen, GREEN, start_button)
    screen.blit(start_text, (start_button.x + 10, start_button.y + 10))

def reset_game():
    global player_y, player_velocity, is_jumping, obstacles, score, obstacle_timer
    player_y = HEIGHT // 2
    player_velocity = 0
    is_jumping = False
    obstacles = []
    score = 0
    obstacle_timer = 0

    #Основной игровой цикл
    clock = pygame. time.Clock()
    running = True

    while running:
        #Обработка событий
        for event in pygame.event.get():
            if  event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                if game_state == MENU and start_button.collidepoint(mouse_pos):
                    game_state = PLAYING
                    reset_game()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if game_state == MENU:
                        game_state = PLAYING
                        reset_game()
                    elif game_state == PLAYING and not is_jumping:
                        player_velocity = jump_force
                        is_jumping = True





#часы для управления FPS
clock = pygame.time.Clock()
FPS = 60
class Game:
    def _init_(self):
        self.obstacles = []

def create_obstacle(self):
    height = random.randint(50, HEIGHT - 200)
    color = random.choice(COLORS)
    self.obstacles.append({
        'x': WIDTH,
        'height': height,
        'color': color,
        'passed': False
    })
    
def draw_player():
    pygame.draw.rect(screen, player_color, (player_x, player_y, player_size, player_size))
    global anim_frame, current_anim

    if is_jumping:
        current_anim = 'jump'
    else:
        current_anim = 'default'

    #кадр анимации
    anim_progress = anim_frame % len(player_animation_frames[current_anim])
    current_rect = player_animation_frames[current_anim][int(anim_progress)]

    #Русием игрока
    pygame.draw.rect(screen, player_color, (player_x, player_x, player_y, current_rect.width, current_rect.height))

    #обновыление счетчка кадров анимации
    anim_frame += anim_speed
    anim_speed = 0.15
    
    

def draw_obstacles():
    global obstacle_width
    for obstacle in obstacles:
        #Верхнее препятствие
        pygame.draw.rect(screen, obstacle['color'],(obstacle['x'], 0, obstacle_width, obstacle['height']))
        #Нижнее препятствие
        bottom_y = obstacle['height']  +  obstacle_gap
        pygame.draw.rect(screen, obstacle['color'],(obstacle['x'], bottom_y, obstacle_width, HEIGHT - bottom_y))

def check_collision():
    player_rect = pygame.Rect(player_x, player_y, player_size)

    for obstacle in obstacles:
        #Верхнее препятствие
        top_rect = pygame.Rect(obstacle['x'], 0, obstacle_width, obstacle['height'])
        #Нижнее препятствие
        bottom_rect = pygame.Rect(obstacle['x'], obstacle['height'] + obstacle_gap, obstacle_width, HEIGHT - (obstacle['height'] + obstacle_gap))

        if player_rect.colliderect(top_rect) or player_rect.colliderect(bottom_rect):
            return True
    if player_y <= 0 or player_y + player_size >= HEIGHT:
        return True
    return False
def update_score():
    global score
    for obstacle in obstacles:
        if obstacle['x'] + obstacle_width < player_x and not obstacle['passed']:
            obstacle['passed'] = True
            score += 1
#Oсновной игровой цикл
running = True
obstacle_timer = 0

while running:
    #Обработка событий
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and not is_jumping:
                player_velocity = jump_force
                is_jumping = True


#Гравитция
player_velocity += gravity
player_y += player_velocity

#Проверка Земли
if player_y + player_size >= HEIGHT:
    player_y = HEIGHT - player_size
    player_velocity = 0
    is_jumping = False

# Генерация препятствий
obstacle_timer += 1
if obstacle_timer >= 90:
    create_obstacle()
    obstacle_timer = 0

#Движения препятствий
for obstacle in obstacles[:]:
    obstacle['x'] -= obstacle_speed
    if obstacle['x'] + obstacle_width < 0:
        obstacles.remove(obstacle)
        while running:
            frame_count += 1
    if frame_count % 1000 == 0:
        obstacle_speed += 1

#обновление счета
update_score()

#ПРОВЕРКА СТЛОКНОВЕНИЙ
if check_collision():
    running = False

#отрисовка
screen.fill(BLACK)
draw_player()
draw_obstacles()

#Отображения счета
score_text = font.render(f"Score: {score}", True, WHITE)
screen.blit(score_text, (10,10))

pygame.display.flip()
clock.tick(FPS)

#Завершение игры
pygame.guit()
sys.exit()





    

        



