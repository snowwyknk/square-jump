import pygame
import random
import sys
from PIL import Image
import json
import os
import math
from pygame import mixer
from pygame. locals import *

#Инцилизация Pygame
pygame.init()
mixer.init()


#sound
crash_sound = pygame.mixer.Sound("sounds/crash.wav")


# Конвертация webp в png (если нужно) валюта
if not os.path.exists("skins/amethyst.png"):
    try:
        img = Image.open("skins/i.webp").convert("RGBA")
        img.save("skins/amethyst.png", "PNG")
    except:
        print("Не удалось конвертировать amethyst.webp")
        
# Конвертация WEBP в PNG фон меню
input_path = "menu/background.webp"
output_path = "menu/background.png"

try:
    img = Image.open(input_path)
    img.save(output_path, "PNG")
    print("Фон успешно конвертирован!")
except Exception as e:
    print(f"Ошибка конвертации: {e}")
    


#Константы
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
COLORS = [
    (255, 0, 0),    # RED
    (0, 255, 0),    # GREEN
    (0, 0, 255),    # BLUE
    (255, 255, 0),  # YELLOW
    (255, 0, 255)   # MAGENTA
]
PURPLE = (128, 0, 128)
GOLD = (255, 215, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

#Состояние игры
MENU = 0
PLAYING = 1
GAME_OVER = 2
SHOP = 3

#Игрок
class Player:
    def __init__(self, x, y):
        self.max_jumps = 1 
        self.jumps_left = 1
        self.x = x
        self.y = y
        self.size = 40
        self.speed = 5
        self.velocity_y = 0
        self.jump_force = -15
        self.gravity = 0.8
        self.is_jumping = False
        self.shape = 'cube'
        
        
        # Загрузка кастом скина
        try:
            self.skin = pygame.image.load("skins/cube01.png").convert_alpha()
            self.skin = pygame.transform.scale(self.skin, (self.size, self.size))
        except:
            self.skin = None
    
    def jump(self):
        if self.jumps_left > 0:
            self.velocity_y = self.jump_force
            self.is_jumping = True
            self.jumps_left -= 1

    def update(self):
        #Автоматическое движение
        self.x += self.speed

        #Гравитация и прыжок
        self.velocity_y += self.gravity
        self.y += self.velocity_y

        #Проверка земли
        if self.y >= SCREEN_HEIGHT - self.size:
            self.jumps_left = self.max_jumps
            self.y = SCREEN_HEIGHT - self.size
            self.velocity_y = 0
            self.is_jumping = False

    def draw(self, screen):
        if self.shape == 'cube':
            if self.skin:
                screen.blit(self.skin, (self.x, self.y))
            else:
                pygame.draw.rect(screen, WHITE, (self.x, self.y, self.size, self.size))
        elif self.shape == 'ball':
            pygame.draw.circle(screen, WHITE, (self.x + self.size // 2, self.y + self.size // 2), self.size // 2)

# Класс Препятствия
class Obstacle:
    def __init__(self, x, y, obstacle_type="spike"):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40
        self.type = obstacle_type  # "spike", "platform", "portal_cube", "portal_ball" 
        self.color = PURPLE if obstacle_type == "spike" else GOLD
        
        
    def update(self, speed):
        # Движение навстречу игроку
        self.x -= speed


    def draw(self, screen):
        if self.type == "spike":
            # шип
            pygame.draw.polygon(screen, self.color, [
                (self.x, self.y + self.height),
                (self.x + self.width // 2, self.y),
                (self.x + self.width, self.y + self.height)
            ])
        elif self.type == "platform":
            pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))

    def is_offscreen(self):
        return self.x + self.width < 0


    def check_collision(self, player):
        if self.type == "spike":
            # Проверка столкновения с шипом
            collision = (player.x < self.x + self.width and
                         player.x + player.size > self.x and
                         player.y < self.y + self.height and
                         player.y + player.size > self.y)
            if collision and crash_sound:
                crash_sound.play()
            return collision
        
        elif self.type == "platform":
            # Проверка стоит ли игрок на платформе
            return (player.x < self.x + self.width and
                    player.x + player.size > self.x and
                    player.y + player.size >= self.y and
                    player.y + player.size <= self.y + 10 )       

    
#Класс Анимаций
class Animation:
    def __init__(self, frames, speed = 0.1, loop = True):
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
        elif int(self.current_frame) >= len(self.frames) - 1:
            self.done = True
            self.current_frame = len(self.frames) - 1

    def get_current_frame(self):
        return self.frames[int(self.current_frame)]

#Класс Игры
class Game:
    def __init__(self):
        self.state = MENU
        if not os.path.exists("menu/background.png"):
            print("Ошибка: файл background.png не найден!")
            self.menu_bg = None
        else:
            try:
                self.menu_bg = pygame.image.load("menu/background.png").convert()
            except pygame.error as e:
                print(f"Ошибка загрузки изображения: {e}")
                self.menu_bg = None
            
        self.shop_items = [
            {"name": "Double Jump", "cost": 10, "owend": False},
            {"name": "Shield", "cost": 15, "owend": False},
            {"name": "Time Walk", "cost": 25, "owend": False},
        ]
        self.account_system = AccountSystem()
        self.promo_system = PromoSystem()
        self.amethysts = []
        self.total_amethysts = 0
        self.collect_sound = pygame.mixer.Sound("sounds/collect.wav")
        self.fullscreen = False
        self.menu_options = ['Start Jump', 'Lvl editor', "Exit jump", "Amethyst Shop"]
        self.selected_option = 0
        self.font = pygame.font.SysFont(None, 36)
        self.menu_font = pygame.font.SysFont(None, 48)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Square Jump v1.0")
        self.clock = pygame.time.Clock()
        self.running = True
        self.player = Player(100, SCREEN_HEIGHT - 100)
        self.obstacles = []
        self.score = 0
        self.font = pygame.font.SysFont(None, 36)
        self.obstacle_timer = 0
        self.obstacle_frequency = 1000  # Частота появления препятствий
        self.game_speed = 5
        # отрисовка меню игры
            
    def spawn_obstacles(self):
        if random.random() < 0.02 and self.state == PLAYING and len(self.obstacles) < 5: 
            obstacle_type = random.choice(["spike", "platform"])
            y = SCREEN_HEIGHT - 100 if obstacle_type == 'platform' else SCREEN_HEIGHT - 40
            self.obstacles.append(Obstacle(SCREEN_WIDTH, y, obstacle_type))
            
    def check_collisions(self):
        for obstacle in self.obstacles:
            if obstacle.check_collision(self.player):
                if obstacle.type == "spike":
                    if hasattr(self, 'player_has_shield') and self.player_has_shield:
                        self.player_has_shield = False  # Используем щит
                        print("Shield used!")
                    else:
                        self.state = GAME_OVER
                    
    def spawn_amethysts(self):
        if random.random() < 0.01 and len(self.amethysts) < 2:
            self.amethysts.append(Amethyst(
            SCREEN_WIDTH,
            random.randint(100, SCREEN_HEIGHT-100)
        ))
    def check_amethyst_collisions(self):
        for amethyst in self.amethysts[:]:
            if amethyst.check_collision(self.player) and not amethyst.collected:
                amethyst.collected = True
                self.total_amethysts += 1
                if self.collect_sound:
                    self.collect_sound.play()
                self.amethysts.remove(amethyst)
                    
                    
    def update(self):
        if self.state == PLAYING:
            self.player.update()
            self.spawn_amethysts()
            self.check_amethyst_collisions()
            # Обработка замедления времени
            if hasattr(self, 'time_slow_active') and self.time_slow_active:
                self.game_speed = max(2, self.game_speed * 0.5)  # Замедляем игру
                self.time_slow_duration -= self.clock.get_time()
                
                if self.time_slow_duration <= 0:
                    self.time_slow_active = False
                    self.time_slow_duration = 3000  # Сбрасываем таймер
            
            if self.player.x > SCREEN_WIDTH:
                self.player.x = -self.player.size

            self.spawn_obstacles()
            self.game_speed += 0.001
            for obstacle in self.obstacles[:]:
                obstacle.update(self.game_speed)
                if obstacle.is_offscreen():
                    self.obstacles.remove(obstacle)
            self.check_collisions()
            self.score += 1
            
    def draw(self):
        self.screen.fill(BLACK)
        if self.state == MENU:
            title = self.font.render("Press SPACE to Start", True, WHITE)
            self.draw_menu()
        elif self.state == PLAYING:
            offset_x = self.player.x - 100
            # отрисовка игрока
            self.player.draw(self.screen)
            for obstacle in self.obstacles:
                if obstacle.type == "spike":
                    pygame.draw.polygon(self.screen, obstacle.color, [
                        (obstacle.x - offset_x, obstacle.y + obstacle.height),
                        (obstacle.x - offset_x + obstacle.width // 2, obstacle.y),
                        (obstacle.x - offset_x + obstacle.width, obstacle.y + obstacle.height)
                    ])
                elif obstacle.type == "platform":
                    pygame.draw.rect(self.screen, obstacle.color,
                                     (obstacle.x - offset_x, obstacle.y, obstacle.width, obstacle.height))
                    
            #Аметист
            for amethyst in self.amethysts:
                amethyst.draw(self.screen)
            # текст
            score_text = self.font.render(f"Score: {self.score}", True, WHITE)
            amethyst_text = self.font.render(f"Amethysts: {self.total_amethysts}", True, (200, 0, 200))
            
            self.screen.blit(score_text, (20, 20))
        elif self.state == GAME_OVER:
            game_over_text = self.font.render("Dont give up! Press ENTER to Restart", True, WHITE)
            self.screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 2))
            
        pygame.display.flip()
        
        
    def draw_menu(self):
        if self.menu_bg:
            self.screen.blit(self.menu_bg, (0, 0))
        else:
            self.screen.fill(BLACK)
            
        # Отображение информации об аккаунте
        if self.account_system.current_account:
            account_text = self.font.render(
            f"Игрок: {self.account_system.current_account}", 
            True, 
            GOLD
            )
            self.screen.blit(account_text, (20, SCREEN_HEIGHT - 40))
        else:
            login_text = self.font.render("Нажмите L для входа", True, WHITE)
            self.screen.blit(login_text, (20, SCREEN_HEIGHT - 40))
            
            
        self.screen.fill(BLACK)
        title = self.menu_font.render('Square Jump', True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        
        mouse_pos = pygame.mouse.get_pos()
        for i, option in enumerate(self.menu_options):
            # Динамический цвет
            is_hovered = False
            text_rect = pygame.Rect(0, 0, 0, 0)  # Инициализация rect
            
            # Проверка наведения мыши
            text = self.menu_font.render(option, True, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH//2, 200 + i*60))
            
            if text_rect.collidepoint(mouse_pos):
                is_hovered = True
                self.selected_option = i
                
            color = GOLD if (i == self.selected_option or is_hovered) else WHITE
            text = self.menu_font.render(option, True, color)
            self.screen.blit(text, text_rect)
            
        # Отрисовка подсказок
        hints = [
            "Click options with mouse or use keyboard",
            "Press F11 to toggle fullscreen",
            "Press SPACE to Start"
        ]
        for i, hint in enumerate(hints):
            hint_text = self.font.render(hint, True, WHITE)
            self.screen.blit(hint_text, (SCREEN_WIDTH//2 - hint_text.get_width()//2, 400 + i*30))

            
    def run(self):
         while self.running:
             
            # Обработка событий для всех состояний
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    
                # Обработка событий в зависимости от состояния
                if self.state == MENU:
                    self.handle_menu_event(event)
                elif self.state == SHOP:
                    self.handle_shop_events(event)
                elif self.state in [PLAYING, GAME_OVER]:
                    self.handle_game_events(event)   
                        
            # Отрисовка
            if self.state == MENU:
                self.draw_menu()
            elif self.state == PLAYING:
                self.update()
                self.draw()
            elif self.state == GAME_OVER:
                self.draw_game_over()
            elif self.state == SHOP:
                self.draw_shop()
                
            pygame.display.flip()
            self.clock.tick(60)
            
    # метод игровых событий
    def handle_game_events(self, event):
        
        if event.type == pygame.QUIT:
            self.running = False
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self.fullscreen = not self.fullscreen
                if self.fullscreen:
                    self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
                else:
                    self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                    
            if event.key == pygame.K_SPACE:
                self.player.jump()
            
            if event.key == pygame.K_RETURN and self.state == GAME_OVER:
                self.reset_game()
                
    # очистка списков при смене состояния
    def change_state(self, new_state):
        self.state = new_state
        self.obstacles.clear()
        self.amethysts.clear()
        
    # аккаунт
    def show_login_screen(self):
        username = input("Введите имя пользователя: ")
        password = input("Введите пароль: ")
        
        if self.account_system.login(username, password):
            print("Успешный вход!")
            # Обновляем количество аметистов
            self.total_amethysts = self.account_system.get_current_account_data()["amethysts"]
        else:
            print("Неверные данные или создайте новый аккаунт")
            if input("Создать новый аккаунт? (y/n) ").lower() == "y":
                if self.account_system.create_account(username, password):
                    print("Аккаунт создан!")
                    self.account_system.login(username, password)
                
    # Метод для отрисовки экрана завершения игры            
    def draw_game_over(self):
        self.screen.fill(BLACK)
        game_over_text = self.font.render("Dont give up! Press ENTER to Restart", True, WHITE)
        self.screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 2))
        score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2 + 50))
                
                
                                
            
    def handle_menu_event(self, event):
            if event.type == pygame.QUIT:
                self.running = False
            # Инцилизация mouse_pos
            mouse_pos = pygame.mouse.get_pos() if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION) else (0, 0)
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.selected_option = (self.selected_option - 1) % len(self.menu_options)
                    
                elif event.key == pygame.K_DOWN:
                    self.selected_option = (self.selected_option + 1) % len(self.menu_options)
                    
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.execute_menu_action()
                    
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, option in enumerate(self.menu_options):
                    text = self.menu_font.render(option, True, WHITE)
                    text_rect = text.get_rect(center=(SCREEN_WIDTH//2, 200 + i*60))
                    
                    if text_rect.collidepoint(mouse_pos):
                        self.selected_option = i
                        self.execute_menu_action()
                        
            if  event.type == pygame.KEYDOWN:
                if event.key == pygame.K_l:
                    self.show_login_screen()
                elif event.key == pygame.K_p:
                    self.show_promo_screen()
                
                            
            # Подсветка при наведении
            if event.type == pygame.MOUSEMOTION:
                mouse_pos = pygame.mouse.get_pos()
            for i, option in enumerate(self.menu_options):
                text = self.menu_font.render(option, True, WHITE)
                text_rect = text.get_rect(center=(SCREEN_WIDTH//2, 200 + i*60))
                
                if text_rect.collidepoint(mouse_pos):
                    self.selected_option = i
                    self.execute_menu_action()
                    
                    
    def execute_menu_action(self):
        print(f"Selected option: {self.selected_option}")  # Отладочная информация
        if self.selected_option == 0:  # Start Jump
            self.reset_game()
            self.state = PLAYING
            print("Игра началась, Jump!")
        elif self.selected_option == 1:  # Lvl editor
            self.run_editor()
        elif self.selected_option == 2:  # Exit jump
            self.running = False
        elif self.selected_option == 3:  # Amethyst Shop
            self.state = SHOP
            print("Shop state activated!")  # Проверка перехода в магазин
             
                        
                        
                        
        
    def handle_events(self, event):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.fullscreen = not self.fullscreen
                    if self.fullscreen:
                        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
                    else:
                        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.state == MENU:
                        self.state = PLAYING
                    self.player.jump()
                if event.key == pygame.K_RETURN and self.state == GAME_OVER:
                    self.reset_game()
                    
    def reset_game(self):
        # Очищаем предыдущее состояние
        self.obstacles.clear()
        self.amethysts.clear()
        
        # Загружаем аметисты из аккаунта
        if self.account_system.current_account:
            account_data = self.account_system.get_current_account_data()
            self.total_amethysts = account_data["amethysts", 0]
            
        # Сбрасываем параметры
        self.player = Player(100, SCREEN_HEIGHT - 100)
        self.score = 0
        self.game_speed = 5
        
        
        
    def run_editor(self):
        print("Запуск редактора уровней")
        editor = LevelEditor(self)
        editor.run()
        print("Редактор закрыт")
       
        
    # Магазин
    def draw_shop(self):
        print("Drawing shop...")  # Проверка вызова метода
        self.screen.fill(BLACK)
        title = self.menu_font.render("Amethyst Shop", True, (200, 0, 200))
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        # Валюта
        currency = self.font.render(f"Your Amethysts: {self.total_amethysts}", True, WHITE)
        
        # Товары
        items = [
            {"name":"Double Jump", "cost": 10},
            {"name":"Shield", "cost": 15},
            {"name":"Time Walk", "cost": 25},
        ]
        
        for i, item in enumerate(self.shop_items):
            color = PURPLE if self.total_amethysts >= item["cost"] and not item["owend"] else (100, 100, 100)
            status = "OWNED" if item["owend"] else f"{item['cost']} Amethysts"
            text = self.font.render(f"{item['name']} - {item['cost']} Amethysts", True, color)
            self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, 200 + i*50))
            
        # Кнопка back
        back_text = self.font.render('Back to Menu (ESC)', True, WHITE)
        self.screen.blit(back_text, (SCREEN_WIDTH//2 - back_text.get_width()//2, 400))
        
    def handle_shop_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = MENU
                
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos() if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION) else (0, 0)
            
            # Кнопка назад
            back_rect = pygame.Rect(SCREEN_WIDTH//2 - 100, 400, 200, 40)
            if back_rect.collidepoint(mouse_pos):
                self.state = MENU
                return
            # Обработка покупок
            for i, item in enumerate(self.shop_items):
                item_rect = pygame.Rect(SCREEN_WIDTH//2 - 150, 150 + i*60, 300, 40)
                if item_rect.collidepoint(mouse_pos):
                    self.buy_item(i)
            
                    
    def buy_item(self, item_index):
        """Покупка предмета в магазине"""
        item = self.shop_items[item_index]
        
        if item["owend"] or self.total_amethysts < item["cost"]:
            return
        
        self.total_amethysts -= item["cost"]
        item["owend"] = True
        
        # Сохраняем в аккаунт
        if self.account_system.current_account:
            account_data = self.account_system.get_current_account_data()
            account_data["amethysts"] = self.total_amethysts
            self.account_system.save_accounts()
        
        # Покупка предметов
        if item["name"] == "Double Jump":
            self.player.max_jumps = 2
        elif item["name"] == "Shield":
            self.player_has_shield = True
        elif item["name"] == "Time Walk":
            self.time_slow_active = True
            self.time_slow_duration = 3000
            
        
        
        
# Класс Уровня
class LevelEditor:
    def __init__(self, game):
        self.game = game
        self.obstacles = []
        self.selected_type = 'spike'
        self.save_file = 'level1.json'
        self.editing = True
    
    def run(self):
        while self.editing:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.editing = False
                    self.game.running = False
               
            self.draw()
            pygame.display.flip()
            self.game.clock.tick(60)
        
        self.game.state = MENU
            
    def handle_events(self, event):
            if event.type == pygame.QUIT:
                return
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    self.selected_type = "spike"
                    print("Выбран тип: шипы")
                    
                elif event.key == pygame.K_2:
                    self.selected_type = "platform"
                    print("Выбран тип: платформа")
                    
                elif event.key == pygame.K_s: # Save lvl
                    self.save_level()
                    print("Уровень сохранен!")
                    
                elif event.key == pygame.K_ESCAPE: #EXIT
                    print("Выход из редактора")
                    self.editing = False 
                    
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                self.obstacles.append({
                    "x": x,
                    "y": y,
                    "type": self.selected_type
                })
                print(f"Добавлено препятствие в ({x}, {y})")
                
    def draw(self):
        self.game.screen.fill(BLACK)
        
        # рисуем препятствия
        for obs in self.obstacles:
            if obs["type"] == "spike":
                pygame.draw.polygon(self.game.screen, PURPLE, [
                    (obs['x'], obs['y'] + 40),
                    (obs['x'] + 20, obs['y']),
                    (obs['x'] + 40, obs['y'] + 40)
                ])
            else:
                pygame.draw.rect(self.game.screen, GOLD, (obs['x'], obs['y'], 40, 40))
                
        #Подсказки
        font = self.game.font
        help_text = [
            "1: Spike", "2: Platform",
            "LMB: Place", "S: Save",
            "ESC: Return to menu"
            f"Current: {self.selected_type}" 
        ]
        for i, text in enumerate(help_text):
            surf = font.render(text, True, WHITE)
            self.game.screen.blit(surf, (20, 20 + i*30))
            
    def save_level(self):
        with open(self.save_file, "w") as f:
            json.dump(self.obstacles, f)
        print(f"Level saved to {self.save_file}")
        
    def load_level(self, filename):
        try:
            with open(filename) as f:
                return json.load(f)
        except:
            return []
        
# Класс валюты
class Amethyst:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 30
        self.collected = False
        try:
            self.image = pygame.image.load("skins/amethyst.png").convert_alpha()
            self.image = pygame.transform.scale(self.image, (self.size, self.size))
        except:
            self.image = None
            
    def draw(self, screen):
        if not self.collected:
            if self.image:
                screen.blit(self.image, (self.x, self.y))
            else:
                pygame.draw.circle(screen, (148, 0, 211), 
                             (self.x + self.size//2, self.y + self.size//2), 
                             self.size//2)
                
    def check_collision(self, player):
        if not self.collected:
            return (player.x < self.x + self.size and
                    player.x + player.size > self.x and
                    player.y < self.y + self.size and
                    player.y + player.size > self.y)
            
# класс аккаунтов
class AccountSystem:
    def __init__(self):
        self.accounts_file = "accounts.json"
        self.current_account = None
        self.accounts = self.load_accounts()
        
    def load_accounts(self):
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, KeyError):
                return {}
            
        
    
    def save_accounts(self):
        with open(self.accounts_file, "w") as f:
            json.dump(self.accounts, f, indent=4)
            
    def create_account(self, username, password):
        if username in self.accounts:
            return False  # Аккаунт уже существует
        self.accounts[username] = {
            "password": password,
            "amethysts": 0,
            "unlocked_skins": ["default"],
            "promo_used": []
        }
        self.save_accounts()
        return True
    
    def login(self, username, password):
        if username in self.accounts and self.accounts[username]["password"] == password:
            self.current_account = username
            return True
        return False
    
    def logout(self):
        self.current_account = None
        
    def get_current_account_data(self):
        if self.current_account:
            return self.accounts[self.current_account]
        return None
    
        
                      
                  
    
# класс промиков)
class PromoSystem:
    PROMO_CODES = {
        "WELCOME10": {"amethysts": 10, "description": "Бонус за регистрацию"},
        "JUMP25": {"amethysts": 25, "description": "Подарок для игроков"},
        "SUMMERJUMP": {"amethysts": 38, "description": "Летний промокод"},
    }
    
    @classmethod
    def redeem_promo(cls, account_system, code):
        if not account_system.current_account:
            return "Войдите в аккаунт"
        
        account_data = account_system.get_current_account_data()
        
        if code in account_data["promo_used"]:
            return "Промокод уже использован"
        
        if code in cls.PROMO_CODES:
            reward = cls.PROMO_CODES[code]
            account_data["amethysts"] += reward["amethysts"]
            account_data["promo_used"].append(code)
            account_system.save_accounts()
            return f"Получено {reward['amethysts']} аметистов!"
        
        return "Неверный промокод"
    
    def show_promo_screen(self):
        if not self.account_system.current_account:
            print("Войдите в аккаунт для использования промокодов")
            return
        
        promo_code = input("Введите промокод: ").upper()
        result = self.promo_system.redeem_promo(self.account_system, promo_code)
        print(result)
        
        # Обновляем количество аметистов
        self.total_amethysts = self.account_system.get_current_account_data()["amethysts"]
    
         
            
        
    
if __name__ == "__main__":
    game = Game()
    game.run()




    

        





