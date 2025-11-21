import pygame
import random
import sys
import json
import os
import sqlite3
from hashlib import sha256
import logging
import datetime
import math

# Настройка логирования
logging.basicConfig(filename='game.log', level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        # Константы
        self.SCREEN_WIDTH = 800
        self.SCREEN_HEIGHT = 600
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GOLD = (255, 215, 0)
        self.PURPLE = (128, 0, 128)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.BLUE = (0, 0, 255)
        
        # Состояния игры
        self.MENU = 0
        self.PLAYING = 1
        self.GAME_OVER = 2
        self.SHOP = 3
        self.LOGIN = 4
        self.PROMO = 5
        self.EDITOR = 6
        self.PAUSED = 7
        self.INVENTORY = 8
        self.CHEST = 9
        
        # Режим экрана
        self.fullscreen = False
        self.original_size = (self.SCREEN_WIDTH, self.SCREEN_HEIGHT)
        
        # Инициализация экрана
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption("Square Jump")
        self.clock = pygame.time.Clock()
        
        # Системы
        self.account_system = AccountSystem()
        self.promo_system = PromoSystem(self.account_system)
        
        # Состояние игры
        self.state = self.MENU
        self.running = True
        self.score = 0
        self.total_amethysts = 0
        
        # Меню
        self.menu_options = ['Start Game', 'Shop', 'Level Editor', 'Inventory', 'Daily Chest', 'Exit']
        self.selected_option = 0
        
        # ШРИФТЫ
        try:
            self.font = pygame.font.SysFont('arial', 32)
            self.title_font = pygame.font.SysFont('arial', 48, bold=True)
            self.small_font = pygame.font.SysFont('arial', 24)
        except:
            self.font = pygame.font.Font(None, 32)
            self.title_font = pygame.font.Font(None, 48)
            self.small_font = pygame.font.Font(None, 24)
        
        # Логин система
        self.login_input = ""
        self.password_input = ""
        self.active_input = "login"
        self.login_message = ""
        
        # Автозаполнение логина последним пользователем
        last_user = self.account_system.get_last_username()
        if last_user:
            self.login_input = last_user
            self.login_message = f"Last user: {last_user} - Enter password"
        
        # Промокод система
        self.promo_input = ""
        self.promo_message = ""
        
        # Скины
        self.skins = self.load_skins()
        self.current_skin = "cube01"
        
        # Ежедневный сундук
        self.last_chest_date = None
        self.chest_rewards = []
        self.chest_animation_frame = 0
        
        # Загрузка ресурсов
        self.load_resources()
        
        # Игрок
        self.player = None
        self.obstacles = []
        self.amethysts = []
        self.game_speed = 5
        
         # Автоматическая загрузка данных если пользователь уже залогинен
        if self.account_system.current_account:
            self.load_player_data()
        
    def load_player_data(self):
        """Загрузка данных игрока после логина"""
        account_data = self.account_system.get_current_account_data()
        self.total_amethysts = account_data.get("amethysts", 0)
        self.load_player_skins()
        logging.info(f"Player data loaded for: {account_data['username']}")
        
        # Загружаем скины если пользователь уже залогинен
        if self.account_system.current_account:
            self.load_player_skins()
        
    def load_skins(self):
        """Загрузка информации о скинах"""
        return {
            "cube01": {"name": "Basic Cube", "cost": 0, "owned": True, "locked": False, "image": "cube01.png"},
            "cube02": {"name": "Gold Cube", "cost": 50, "owned": False, "locked": False, "image": "cube02.png"},
            "cube03": {"name": "Diamond Cube", "cost": 100, "owned": False, "locked": False, "image": "cube03.png"},
            "cube04": {"name": "Fire Cube", "cost": 150, "owned": False, "locked": True, "image": "cube04.png"},
            "cube05": {"name": "Ice Cube", "cost": 200, "owned": False, "locked": True, "image": "cube05.png"},
            "cube06": {"name": "Rainbow Cube", "cost": 300, "owned": False, "locked": True, "image": "cube06.png"}
        }
    
    def load_player_skins(self):
        """Загрузка скинов игрока из базы данных"""
        if not self.account_system.current_account:
            return
            
        try:
            cursor = self.account_system.conn.cursor()
            cursor.execute('''
                SELECT skin_id FROM player_skins 
                WHERE player_id = ? AND owned = 1
            ''', (self.account_system.current_account["id"],))
            
            owned_skins = [row[0] for row in cursor.fetchall()]
            
            # Обновляем статус скинов
            for skin_id in self.skins:
                if skin_id in owned_skins:
                    self.skins[skin_id]["owned"] = True
                elif skin_id == "cube01":
                    self.skins[skin_id]["owned"] = True
                else:
                    self.skins[skin_id]["owned"] = False
                    
        except sqlite3.Error as e:
            logging.error(f"Error loading player skins: {e}")

    def initialize_new_player_skins(self):
        """Инициализация скинов для нового игрока"""
        if not self.account_system.current_account:
            return
            
        try:
            cursor = self.account_system.conn.cursor()
            # Даем базовый скин новому игроку
            cursor.execute('''
                INSERT OR REPLACE INTO player_skins (player_id, skin_id, owned)
                VALUES (?, 'cube01', 1)
            ''', (self.account_system.current_account["id"],))
            
            self.account_system.conn.commit()
            
            # Обновляем локальные данные
            self.skins["cube01"]["owned"] = True
            self.current_skin = "cube01"
            
        except sqlite3.Error as e:
            logging.error(f"Error initializing player skins: {e}")

        
    def toggle_fullscreen(self):
        """Переключение полноэкранного режима"""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.SCREEN_WIDTH, self.SCREEN_HEIGHT = self.screen.get_size()
        else:
            self.screen = pygame.display.set_mode(self.original_size)
            self.SCREEN_WIDTH, self.SCREEN_HEIGHT = self.original_size
        
        # Перезагружаем ресурсы для нового размера экрана
        self.load_resources()
        
    def load_resources(self):
        """Загрузка всех ресурсов игры"""
        try:
            # Создаем базовые ресурсы если их нет
            folders = ["sounds", "skins", "backgrounds", "menu", "levels", "chests"]
            for folder in folders:
                if not os.path.exists(folder):
                    os.makedirs(folder)
                
            # Звуки
            sound_paths = [
                "sounds/crash.wav",
                "game project/sounds/crash.wav",
                "sounds/collect.wav", 
                "game project/sounds/collect.wav",
                "sounds/chest_open.wav"
            ]
            
            self.crash_sound = None
            self.collect_sound = None
            self.chest_sound = None
            
            for path in sound_paths:
                try:
                    if "crash" in path and not self.crash_sound:
                        if os.path.exists(path):
                            self.crash_sound = pygame.mixer.Sound(path)
                    elif "collect" in path and not self.collect_sound:
                        if os.path.exists(path):
                            self.collect_sound = pygame.mixer.Sound(path)
                    elif "chest" in path and not self.chest_sound:
                        if os.path.exists(path):
                            self.chest_sound = pygame.mixer.Sound(path)
                except Exception as e:
                    logging.warning(f"Failed to load sound {path}: {e}")
                    continue
            
            # Загрузка изображений
            image_paths = {
                'menu_bg': ["menu/background.png", "game project/menu/background.png"],
                'player_image': [f"skins/{self.skins[self.current_skin]['image']}", f"game project/skins/{self.skins[self.current_skin]['image']}"],
                'amethyst_image': ["skins/amethyst.png", "game project/skins/amethyst.png"],
                'chest_image': ["chestskins/amethystchest.png", "game project/chestskins/amethystchest.png"]
            }
            
            self.menu_bg = None
            self.player_image = None
            self.amethyst_image = None
            self.chest_image = None
            self.game_bg = None
            
            # Загрузка фона меню
            for path in image_paths['menu_bg']:
                try:
                    if os.path.exists(path):
                        self.menu_bg = pygame.image.load(path).convert()
                        self.menu_bg = pygame.transform.scale(self.menu_bg, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
                        break
                except Exception as e:
                    logging.warning(f"Failed to load menu background {path}: {e}")
                    continue
            
            # Загрузка игрового фона
            try:
                if os.path.exists("backgrounds/game_bg.png"):
                    self.game_bg = pygame.image.load("backgrounds/game_bg.png").convert()
                    self.game_bg = pygame.transform.scale(self.game_bg, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
            except Exception as e:
                logging.warning(f"Failed to load game background: {e}")
                pass
                
            if not self.game_bg:
                self.game_bg = self.create_gradient_bg()
            
            # Загрузка скина игрока
            for path in image_paths['player_image']:
                try:
                    if os.path.exists(path):
                        self.player_image = pygame.image.load(path).convert_alpha()
                        self.player_image = pygame.transform.scale(self.player_image, (40, 40))
                        break
                except Exception as e:
                    logging.warning(f"Failed to load player image {path}: {e}")
                    continue
            
            # Загрузка аметиста
            for path in image_paths['amethyst_image']:
                try:
                    if os.path.exists(path):
                        self.amethyst_image = pygame.image.load(path).convert_alpha()
                        self.amethyst_image = pygame.transform.scale(self.amethyst_image, (30, 30))
                        break
                except Exception as e:
                    logging.warning(f"Failed to load amethyst image {path}: {e}")
                    continue
                    
            # Загрузка сундука
            for path in image_paths['chest_image']:
                try:
                    if os.path.exists(path):
                        self.chest_image = pygame.image.load(path).convert_alpha()
                        self.chest_image = pygame.transform.scale(self.chest_image, (200, 200))
                        break
                except Exception as e:
                    logging.warning(f"Failed to load chest image {path}: {e}")
                    # Создаем простой сундук если файла нет
                    self.chest_image = self.create_default_chest()
                
        except Exception as e:
            logging.error(f"Error loading resources: {e}")
            print(f"Resource loading error: {e}")

    def create_default_chest(self):
        """Создание стандартного сундука если файла нет"""
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        # Основа сундука
        pygame.draw.rect(surf, (139, 69, 19), (50, 100, 100, 60))  # Коричневый
        pygame.draw.rect(surf, (160, 82, 45), (50, 80, 100, 30))   # Верх
        # Украшения
        pygame.draw.rect(surf, (255, 215, 0), (70, 85, 60, 20))    # Золотая полоса
        pygame.draw.circle(surf, (255, 215, 0), (100, 95), 8)      # Золотая ручка
        return surf

    def create_gradient_bg(self):
        """Создание градиентного фона если нет изображения"""
        surf = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        # Простой темный фон
        surf.fill((20, 20, 50))
        return surf

    def play_sound_safe(self, sound):
        """Безопасное воспроизведение звука"""
        if sound and pygame.mixer.get_init():
            try:
                sound.play()
            except pygame.error as e:
                logging.warning(f"Could not play sound: {e}")

    def handle_events(self):
        """Обработка всех событий игры"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            # Глобальные горячие клавиши
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_ESCAPE and self.state == self.PLAYING:
                    self.state = self.PAUSED
                elif event.key == pygame.K_ESCAPE and self.state == self.PAUSED:
                    self.state = self.PLAYING
                
            if self.state == self.MENU:
                self.handle_menu_events(event)
            elif self.state == self.PLAYING:
                self.handle_game_events(event)
            elif self.state == self.SHOP:
                self.handle_shop_events(event)
            elif self.state == self.GAME_OVER:
                self.handle_game_over_events(event)
            elif self.state == self.LOGIN:
                self.handle_login_events(event)
            elif self.state == self.PROMO:
                self.handle_promo_events(event)
            elif self.state == self.EDITOR:
                self.handle_editor_events(event)
            elif self.state == self.PAUSED:
                self.handle_pause_events(event)
            elif self.state == self.INVENTORY:
                self.handle_inventory_events(event)
            elif self.state == self.CHEST:
                self.handle_chest_events(event)

    def handle_menu_events(self, event):
        """События меню с обработкой выхода"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_option = (self.selected_option - 1) % len(self.menu_options)
            elif event.key == pygame.K_DOWN:
                self.selected_option = (self.selected_option + 1) % len(self.menu_options)
            elif event.key == pygame.K_RETURN:
                self.execute_menu_action()
            elif event.key == pygame.K_l:
                if self.account_system.current_account:
                    # Выход из аккаунта
                    self.account_system.current_account = None
                    self.total_amethysts = 0
                    self.login_input = ""
                    self.password_input = ""
                    self.login_message = "Logged out successfully"
                    logging.info("User logged out")
                else:
                    # Вход в аккаунт
                    self.state = self.LOGIN
                    # Автозаполнение логина последним пользователем
                    last_user = self.account_system.get_last_username()
                    if last_user and not self.login_input:
                        self.login_input = last_user
                        self.active_input = "password"
                        self.login_message = f"Last user: {last_user} - Enter password"
                    else:
                        self.login_input = ""
                        self.password_input = ""
                        self.active_input = "login"
                        self.login_message = ""
            elif event.key == pygame.K_p:
                self.state = self.PROMO
                self.promo_input = ""
                self.promo_message = ""
                
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            for i, option in enumerate(self.menu_options):
                text_rect = pygame.Rect(self.SCREEN_WIDTH//2 - 100, 200 + i*60, 200, 50)
                if text_rect.collidepoint(mouse_pos):
                    self.selected_option = i
                    self.execute_menu_action()
                    
    def execute_menu_action(self):
        """Выполнение действия в меню"""
        option = self.menu_options[self.selected_option]
        
        if option == 'Start Game':
            self.start_game()
        elif option == 'Shop':
            self.state = self.SHOP
        elif option == 'Level Editor':
            self.start_editor()
        elif option == 'Inventory':
            self.state = self.INVENTORY
        elif option == 'Daily Chest':
            self.open_daily_chest()
        elif option == 'Exit':
            self.running = False

    def open_daily_chest(self):
        """Открытие ежедневного сундука"""
        if not self.account_system.current_account:
            self.state = self.LOGIN
            return
            
        today = datetime.datetime.now().date()
        
        # Проверяем, открывали ли уже сундук сегодня
        try:
            cursor = self.account_system.conn.cursor()
            cursor.execute('''
                SELECT last_chest_date FROM players WHERE username = ?
            ''', (self.account_system.current_account['username'],))
            
            result = cursor.fetchone()
            last_date = result[0] if result else None
            
            if last_date:
                last_date = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()
                if last_date == today:
                    # Уже открывали сегодня
                    self.chest_rewards = [{"type": "message", "text": "You already opened chest today!"}]
                    self.state = self.CHEST
                    return
        except sqlite3.Error as e:
            logging.error(f"Database error in open_daily_chest: {e}")
            self.chest_rewards = [{"type": "message", "text": "Database error!"}]
            self.state = self.CHEST
            return
        
        # Генерируем награды
        self.generate_chest_rewards()
        self.state = self.CHEST
        self.chest_animation_frame = 0
        
        # Обновляем дату последнего открытия
        try:
            cursor.execute('''
                UPDATE players SET last_chest_date = ? WHERE username = ?
            ''', (today.strftime('%Y-%m-%d'), self.account_system.current_account['username']))
            self.account_system.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error updating chest date: {e}")
        
        self.play_sound_safe(self.chest_sound)

    def generate_chest_rewards(self):
        """Генерация наград из сундука"""
        rewards = []
        
        try:
            # Шансы на разные типы наград
            reward_chances = [
                ("amethyst", 10, 50),   # 50% шанс на 10 аметистов
                ("amethyst", 25, 30),   # 30% шанс на 25 аметистов
                ("amethyst", 50, 15),   # 15% шанс на 50 аметистов
                ("skin", None, 5)       # 5% шанс на скин
            ]
            
            # Основная награда
            main_reward = random.choices(
                reward_chances, 
                weights=[chance for _, _, chance in reward_chances]
            )[0]
            
            reward_type, amount, _ = main_reward
            
            if reward_type == "amethyst":
                rewards.append({"type": "amethyst", "amount": amount})
                # Добавляем аметисты к аккаунту
                self.total_amethysts += amount
                if self.account_system.conn:
                    cursor = self.account_system.conn.cursor()
                    cursor.execute('''
                        UPDATE players SET amethysts = amethysts + ? WHERE username = ?
                    ''', (amount, self.account_system.current_account['username']))
                    self.account_system.conn.commit()
                    
            elif reward_type == "skin":
                # Выбираем случайный заблокированный скин
                locked_skins = [skin_id for skin_id, skin in self.skins.items() 
                              if not skin["owned"] and not skin["locked"]]
                
                if locked_skins:
                    skin_id = random.choice(locked_skins)
                    self.skins[skin_id]["owned"] = True
                    rewards.append({"type": "skin", "skin_id": skin_id, "name": self.skins[skin_id]["name"]})
                    
                    # Сохраняем в базу
                    if self.account_system.conn:
                        cursor = self.account_system.conn.cursor()
                        cursor.execute('''
                            INSERT OR REPLACE INTO player_skins (player_id, skin_id, owned)
                            VALUES ((SELECT id FROM players WHERE username = ?), ?, 1)
                        ''', (self.account_system.current_account['username'], skin_id))
                        self.account_system.conn.commit()
                else:
                    # Если нет доступных скинов, даем аметисты
                    fallback_amount = 50
                    rewards.append({"type": "amethyst", "amount": fallback_amount})
                    self.total_amethysts += fallback_amount
            
            # Дополнительная маленькая награда
            if random.random() < 0.3:  # 30% шанс на дополнительную награду
                bonus_amount = 5
                rewards.append({"type": "amethyst", "amount": bonus_amount})
                self.total_amethysts += bonus_amount
                
        except Exception as e:
            logging.error(f"Error generating chest rewards: {e}")
            # Награда по умолчанию при ошибке
            rewards.append({"type": "amethyst", "amount": 10})
            self.total_amethysts += 10
        
        self.chest_rewards = rewards

    def start_game(self):
        """Начало новой игры"""
        # Загружаем текущий скин
        skin_image_path = f"skins/{self.skins[self.current_skin]['image']}"
        try:
            if os.path.exists(skin_image_path):
                player_image = pygame.image.load(skin_image_path).convert_alpha()
                player_image = pygame.transform.scale(player_image, (40, 40))
            else:
                player_image = None
        except Exception as e:
            logging.warning(f"Failed to load player skin: {e}")
            player_image = None
            
        self.player = Player(100, self.SCREEN_HEIGHT - 100, player_image)
        self.obstacles = []
        self.amethysts = []
        self.score = 0
        self.game_speed = 5
        self.state = self.PLAYING

    def handle_game_events(self, event):
        """События во время игры"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if self.player:
                    self.player.jump()
            elif event.key == pygame.K_p:  # Пауза на P
                self.state = self.PAUSED

    def handle_pause_events(self, event):
        """События во время паузы"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                self.state = self.PLAYING
            elif event.key == pygame.K_m:
                self.state = self.MENU

    def handle_inventory_events(self, event):
        """События инвентаря"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = self.MENU
                
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Обработка выбора скина
            skin_keys = list(self.skins.keys())
            skins_per_row = 3
            skin_width = 160
            start_x = (self.SCREEN_WIDTH - (skins_per_row * skin_width)) // 2
            
            for i, skin_id in enumerate(skin_keys):
                row = i // skins_per_row
                col = i % skins_per_row
                x = start_x + col * skin_width
                y = 150 + row * 120
                
                # Проверяем не вышли ли за пределы экрана
                if y > self.SCREEN_HEIGHT - 100:
                    break
                    
                skin_rect = pygame.Rect(x, y, 150, 100)
                if skin_rect.collidepoint(mouse_pos):
                    skin = self.skins[skin_id]
                    if skin["owned"]:
                        self.current_skin = skin_id
                        # Обновляем изображение игрока
                        self.load_resources()
                    elif not skin["locked"]:
                        # Покупка скина
                        if self.total_amethysts >= skin["cost"]:
                            self.total_amethysts -= skin["cost"]
                            skin["owned"] = True
                            self.current_skin = skin_id
                            
                            # Сохраняем в базу
                            try:
                                cursor = self.account_system.conn.cursor()
                                cursor.execute('''
                                    UPDATE players SET amethysts = ? WHERE username = ?
                                ''', (self.total_amethysts, self.account_system.current_account['username']))
                                
                                cursor.execute('''
                                    INSERT OR REPLACE INTO player_skins (player_id, skin_id, owned)
                                    VALUES ((SELECT id FROM players WHERE username = ?), ?, 1)
                                ''', (self.account_system.current_account['username'], skin_id))
                                
                                self.account_system.conn.commit()
                                self.load_resources()
                            except sqlite3.Error as e:
                                logging.error(f"Database error buying skin: {e}")

    def handle_chest_events(self, event):
        """События экрана сундука"""
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = self.MENU
            else:
                self.state = self.MENU

    def update_game(self):
        """Обновление игровой логики"""
        if self.state != self.PLAYING or not self.player:
            return
            
        # Обновление игрока
        self.player.update()
        
        # Сбрасываем флаг нахождения на платформе
        on_platform = False
        platform_collision = None
        
        # Сначала проверяем все столкновения
        for obstacle in self.obstacles[:]:
            if obstacle:
                obstacle.update(self.game_speed)
                if obstacle.is_offscreen():
                    self.obstacles.remove(obstacle)
                elif obstacle.type == "platform" and obstacle.check_collision(self.player):
                    on_platform = True
                    platform_collision = obstacle  # Запоминаем с какой платформой столкнулись
        
        # Корректируем позицию игрока относительно платформы
        if on_platform and platform_collision and self.player.velocity_y > 0:
            self.player.y = platform_collision.y - self.player.size
            self.player.velocity_y = 0
            self.player.jumps_left = self.player.max_jumps
        
        # Если игрок на земле, восстанавливаем прыжки
        if self.player.y >= self.SCREEN_HEIGHT - self.player.size:
            self.player.y = self.SCREEN_HEIGHT - self.player.size
            self.player.velocity_y = 0
            self.player.jumps_left = self.player.max_jumps
        elif on_platform:
            # Уже обработали выше
            pass
        
        # Генерация препятствий
        if random.random() < 0.02 and len(self.obstacles) < 5:
            self.spawn_obstacle()
            
        # Генерация аметистов
        if random.random() < 0.01 and len(self.amethysts) < 3:
            self.spawn_amethyst()
                
        # Обновление аметистов
        for amethyst in self.amethysts[:]:
            if amethyst:
                amethyst.update(self.game_speed)
                if amethyst.check_collision(self.player):
                    self.total_amethysts += 1
                    self.amethysts.remove(amethyst)
                    self.play_sound_safe(self.collect_sound)
                    
        # Проверка столкновений с шипами
        for obstacle in self.obstacles:
            if obstacle and obstacle.type == "spike" and obstacle.check_collision(self.player):
                self.play_sound_safe(self.crash_sound)
                self.state = self.GAME_OVER
                return
                
        # Увеличение сложности
        self.game_speed += 0.001
        self.score += 1

    def spawn_obstacle(self):
        """Создание препятствия"""
        obstacle_type = random.choice(["spike", "platform"])
        if obstacle_type == "platform":
            y = random.randint(200, self.SCREEN_HEIGHT - 150)
        else:
            y = self.SCREEN_HEIGHT - 40
            
        self.obstacles.append(Obstacle(self.SCREEN_WIDTH, y, obstacle_type))

    def spawn_amethyst(self):
        """Создание аметиста"""
        y = random.randint(100, self.SCREEN_HEIGHT - 150)
        self.amethysts.append(Amethyst(self.SCREEN_WIDTH, y, self.amethyst_image))

    def draw(self):
        """Отрисовка игры"""
        if self.state == self.MENU:
            self.draw_menu()
        elif self.state == self.PLAYING:
            self.draw_game()
        elif self.state == self.SHOP:
            self.draw_shop()
        elif self.state == self.GAME_OVER:
            self.draw_game_over()
        elif self.state == self.LOGIN:
            self.draw_login()
        elif self.state == self.PROMO:
            self.draw_promo()
        elif self.state == self.EDITOR:
            self.draw_editor()
        elif self.state == self.PAUSED:
            self.draw_pause()
        elif self.state == self.INVENTORY:
            self.draw_inventory()
        elif self.state == self.CHEST:
            self.draw_chest()
            
        pygame.display.flip()

    def draw_menu(self):
        """Отрисовка меню с информацией о пользователе"""
        # Фон
        if self.menu_bg:
            self.screen.blit(self.menu_bg, (0, 0))
        else:
            self.screen.fill(self.BLACK)
        
        # Заголовок
        title = self.title_font.render("SQUARE JUMP", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 80))
        
        # Опции меню
        for i, option in enumerate(self.menu_options):
            color = self.GOLD if i == self.selected_option else self.WHITE
            text = self.font.render(option, True, color)
            text_rect = text.get_rect(center=(self.SCREEN_WIDTH//2, 200 + i*50))
            
            # Простая подсветка выбранной опции
            if i == self.selected_option:
                pygame.draw.rect(self.screen, (50, 50, 50), 
                               (text_rect.x - 10, text_rect.y - 5, 
                                text_rect.width + 20, text_rect.height + 10))
            
            self.screen.blit(text, text_rect)
            
        # Подсказки
        hints = [
            "F11: Fullscreen",
            "L: Login/Logout | P: Promo Code",
            "ESC: Back to menu"
        ]
        for i, hint in enumerate(hints):
            hint_text = self.small_font.render(hint, True, self.WHITE)
            self.screen.blit(hint_text, (20, 20 + i*30))
            
        # Информация об аккаунте
        if self.account_system.current_account:
            username = self.account_system.current_account['username']
            account_text = self.small_font.render(
                f"Player: {username} | Amethysts: {self.total_amethysts}", 
                True, self.GREEN
            )
            self.screen.blit(account_text, (20, self.SCREEN_HEIGHT - 40))
            
            # Кнопка выхода
            logout_text = self.small_font.render("L: Logout", True, self.RED)
            self.screen.blit(logout_text, (self.SCREEN_WIDTH - 120, self.SCREEN_HEIGHT - 40))
        else:
            last_user = self.account_system.get_last_username()
            if last_user:
                login_text = self.small_font.render(f"Press L to login as {last_user}", True, self.GOLD)
            else:
                login_text = self.small_font.render("Press L to login", True, self.WHITE)
            self.screen.blit(login_text, (20, self.SCREEN_HEIGHT - 40))
            
    def draw_game(self):
        """Отрисовка игрового процесса"""
        # Фон
        if self.game_bg:
            self.screen.blit(self.game_bg, (0, 0))
        else:
            self.screen.fill(self.BLACK)
        
        # Препятствия
        for obstacle in self.obstacles:
            if obstacle:
                obstacle.draw(self.screen)
            
        # Аметисты
        for amethyst in self.amethysts:
            if amethyst and not amethyst.collected:
                amethyst.draw(self.screen)
            
        # Игрок
        if self.player:
            self.player.draw(self.screen)
            
        # Интерфейс
        score_text = self.font.render(f"Score: {self.score}", True, self.WHITE)
        amethyst_text = self.font.render(f"Amethysts: {self.total_amethysts}", True, self.PURPLE)
        speed_text = self.font.render(f"Speed: {self.game_speed:.1f}", True, self.WHITE)
        
        self.screen.blit(score_text, (20, 20))
        self.screen.blit(amethyst_text, (20, 60))
        self.screen.blit(speed_text, (20, 100))
        
        # Подсказки управления
        controls_text = self.small_font.render("SPACE: Jump | P: Pause | ESC: Menu", True, self.WHITE)
        self.screen.blit(controls_text, (20, self.SCREEN_HEIGHT - 30))

    def draw_inventory(self):
        """Отрисовка инвентаря скинов"""
        self.screen.fill(self.BLACK)
        
        title = self.title_font.render("SKIN INVENTORY", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        # Текущий игрок
        if self.account_system.current_account:
            player_text = self.font.render(
                f"Player: {self.account_system.current_account['username']}", 
                True, self.WHITE
            )
            self.screen.blit(player_text, (self.SCREEN_WIDTH//2 - player_text.get_width()//2, 100))
        
        # Скины
        skin_keys = list(self.skins.keys())
        skins_per_row = 3
        skin_width = 160
        skin_height = 110
        start_x = (self.SCREEN_WIDTH - (skins_per_row * skin_width)) // 2
        
        for i, skin_id in enumerate(skin_keys):
            row = i // skins_per_row
            col = i % skins_per_row
            
            x = start_x + col * skin_width
            y = 150 + row * 120
            
            # Проверяем не вышли ли за пределы экрана
            if y + skin_height > self.SCREEN_HEIGHT - 50:
                # Создаем прокрутку или предупреждение
                warning_text = self.small_font.render("... more skins available", True, self.WHITE)
                self.screen.blit(warning_text, (self.SCREEN_WIDTH//2 - warning_text.get_width()//2, self.SCREEN_HEIGHT - 40))
                break
            
            skin = self.skins[skin_id]
            
            # Рамка скина
            border_color = self.GREEN if skin_id == self.current_skin else self.GOLD
            pygame.draw.rect(self.screen, border_color, (x-5, y-5, skin_width-10, skin_height-10), 3)
            
            # Загрузка изображения скина
            try:
                skin_path = f"skins/{skin['image']}"
                if os.path.exists(skin_path):
                    skin_img = pygame.image.load(skin_path).convert_alpha()
                    skin_img = pygame.transform.scale(skin_img, (80, 80))
                    self.screen.blit(skin_img, (x + 35, y + 10))
            except Exception as e:
                logging.warning(f"Failed to load skin image {skin_path}: {e}")
                # Запасной вариант - цветной квадрат
                color = self.GREEN if skin["owned"] else (100, 100, 100)
                pygame.draw.rect(self.screen, color, (x + 35, y + 10, 80, 80))
            
            # Название скина
            name_text = self.small_font.render(skin["name"], True, self.WHITE)
            self.screen.blit(name_text, (x + 75 - name_text.get_width()//2, y + 5))
            
            # Статус скина
            if skin["owned"]:
                status_text = self.small_font.render("OWNED", True, self.GREEN)
            elif skin["locked"]:
                status_text = self.small_font.render("LOCKED", True, self.RED)
            else:
                status_text = self.small_font.render(f"{skin['cost']} AM", True, self.GOLD)
            
            self.screen.blit(status_text, (x + 75 - status_text.get_width()//2, y + 95))
        
        # Подсказки
        hint_text = self.small_font.render("Click to select/buy skin | ESC: Back", True, self.WHITE)
        self.screen.blit(hint_text, (self.SCREEN_WIDTH//2 - hint_text.get_width()//2, self.SCREEN_HEIGHT - 40))

    def draw_chest(self):
        """Отрисовка экрана сундука"""
        self.screen.fill(self.BLACK)
        
        # Анимация открытия сундука
        scale = 1.0 + 0.1 * math.sin(self.chest_animation_frame * 0.1)
        self.chest_animation_frame += 1
        
        if self.chest_image:
            scaled_chest = pygame.transform.scale(self.chest_image, 
                                                (int(200 * scale), int(200 * scale)))
            self.screen.blit(scaled_chest, (self.SCREEN_WIDTH//2 - 100, 150))
        else:
            pygame.draw.rect(self.screen, (139, 69, 19), 
                           (self.SCREEN_WIDTH//2 - 100, 150, 200, 200))
        
        title = self.title_font.render("DAILY CHEST", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        # Отображение наград
        y_offset = 370
        for reward in self.chest_rewards:
            if reward["type"] == "amethyst":
                reward_text = self.font.render(f"+{reward['amount']} Amethysts!", True, self.PURPLE)
                self.screen.blit(reward_text, (self.SCREEN_WIDTH//2 - reward_text.get_width()//2, y_offset))
                y_offset += 40
            elif reward["type"] == "skin":
                reward_text = self.font.render(f"New Skin: {reward['name']}!", True, self.GOLD)
                self.screen.blit(reward_text, (self.SCREEN_WIDTH//2 - reward_text.get_width()//2, y_offset))
                y_offset += 40
            elif reward["type"] == "message":
                reward_text = self.font.render(reward["text"], True, self.RED)
                self.screen.blit(reward_text, (self.SCREEN_WIDTH//2 - reward_text.get_width()//2, y_offset))
                y_offset += 40
        
        # Подсказка
        hint_text = self.small_font.render("Click anywhere to continue", True, self.WHITE)
        self.screen.blit(hint_text, (self.SCREEN_WIDTH//2 - hint_text.get_width()//2, self.SCREEN_HEIGHT - 50))
        
    def draw_pause(self):
        """Отрисовка экрана паузы"""
        # Полупрозрачный overlay
        overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        # Текст паузы
        pause_text = self.title_font.render("PAUSED", True, self.GOLD)
        continue_text = self.font.render("Press P or ESC to continue", True, self.WHITE)
        menu_text = self.font.render("Press M for main menu", True, self.WHITE)
        
        self.screen.blit(pause_text, (self.SCREEN_WIDTH//2 - pause_text.get_width()//2, 200))
        self.screen.blit(continue_text, (self.SCREEN_WIDTH//2 - continue_text.get_width()//2, 280))
        self.screen.blit(menu_text, (self.SCREEN_WIDTH//2 - menu_text.get_width()//2, 320))

    def draw_shop(self):
        """Отрисовка магазина"""
        self.screen.fill(self.BLACK)
        title = self.title_font.render("SHOP", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        # Список товаров
        items = [
            {"name": "Double Jump", "cost": 10, "description": "Jump twice in air"},
            {"name": "Shield", "cost": 15, "description": "Protection from one obstacle"},
            {"name": "Speed Boost", "cost": 20, "description": "Temporary speed increase"},
        ]
        
        for i, item in enumerate(items):
            can_afford = self.total_amethysts >= item["cost"]
            color = self.GOLD if can_afford else (100, 100, 100)
            text = self.font.render(f"{item['name']} - {item['cost']} Amethysts", True, color)
            desc = self.small_font.render(item["description"], True, self.WHITE)
            
            self.screen.blit(text, (self.SCREEN_WIDTH//2 - text.get_width()//2, 150 + i*80))
            self.screen.blit(desc, (self.SCREEN_WIDTH//2 - desc.get_width()//2, 180 + i*80))
            
        # Баланс
        balance_text = self.font.render(f"Your Amethysts: {self.total_amethysts}", True, self.PURPLE)
        self.screen.blit(balance_text, (self.SCREEN_WIDTH//2 - balance_text.get_width()//2, 400))
            
        # Кнопка назад
        back_text = self.font.render("Press ESC to return to menu", True, self.WHITE)
        self.screen.blit(back_text, (self.SCREEN_WIDTH//2 - back_text.get_width()//2, 500))

    def draw_game_over(self):
        """Отрисовка экрана завершения игры"""
        self.screen.fill(self.BLACK)
        
        game_over = self.title_font.render("GAME OVER", True, self.RED)
        score_text = self.font.render(f"Final Score: {self.score}", True, self.WHITE)
        restart_text = self.font.render("Press ENTER to restart or ESC for menu", True, self.WHITE)
        
        self.screen.blit(game_over, (self.SCREEN_WIDTH//2 - game_over.get_width()//2, 200))
        self.screen.blit(score_text, (self.SCREEN_WIDTH//2 - score_text.get_width()//2, 250))
        self.screen.blit(restart_text, (self.SCREEN_WIDTH//2 - restart_text.get_width()//2, 300))

    def draw_login(self):
        """Отрисовка экрана логина"""
        self.screen.fill(self.BLACK)
        
        title = self.title_font.render("LOGIN", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 100))
        
        # Поля ввода
        login_text = self.font.render("Username:", True, self.WHITE)
        password_text = self.font.render("Password:", True, self.WHITE)
        
        self.screen.blit(login_text, (200, 200))
        self.screen.blit(password_text, (200, 250))
        
        # Поле логина
        login_rect = pygame.Rect(350, 200, 250, 30)
        pygame.draw.rect(self.screen, self.WHITE if self.active_input == "login" else (100, 100, 100), login_rect, 2)
        login_input_text = self.font.render(self.login_input, True, self.WHITE)
        self.screen.blit(login_input_text, (355, 205))
        
        # Поле пароля
        password_rect = pygame.Rect(350, 250, 250, 30)
        pygame.draw.rect(self.screen, self.WHITE if self.active_input == "password" else (100, 100, 100), password_rect, 2)
        hidden_password = "*" * len(self.password_input)
        password_input_text = self.font.render(hidden_password, True, self.WHITE)
        self.screen.blit(password_input_text, (355, 255))
        
        # Сообщение
        if self.login_message:
            message_color = (100, 255, 100) if "success" in self.login_message.lower() else self.RED
            message_text = self.font.render(self.login_message, True, message_color)
            self.screen.blit(message_text, (self.SCREEN_WIDTH//2 - message_text.get_width()//2, 320))
        
        # Подсказки
        hint1 = self.small_font.render("TAB: Switch field, ENTER: Login, ESC: Back", True, self.WHITE)
        hint2 = self.small_font.render("New account will be created automatically", True, self.WHITE)
        
        self.screen.blit(hint1, (self.SCREEN_WIDTH//2 - hint1.get_width()//2, 400))
        self.screen.blit(hint2, (self.SCREEN_WIDTH//2 - hint2.get_width()//2, 430))

    def draw_promo(self):
        """Отрисовка экрана промокода"""
        self.screen.fill(self.BLACK)
        
        title = self.title_font.render("PROMO CODE", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 100))
        
        # Поле ввода
        promo_rect = pygame.Rect(200, 200, 400, 40)
        pygame.draw.rect(self.screen, self.WHITE, promo_rect, 2)
        promo_text = self.font.render(self.promo_input, True, self.WHITE)
        self.screen.blit(promo_text, (210, 210))
        
        # Сообщение
        if self.promo_message:
            message_color = (100, 255, 100) if "received" in self.promo_message.lower() else self.RED
            message_text = self.font.render(self.promo_message, True, message_color)
            self.screen.blit(message_text, (self.SCREEN_WIDTH//2 - message_text.get_width()//2, 280))
        
        # Подсказки
        hint1 = self.small_font.render("ENTER: Activate, ESC: Back", True, self.WHITE)
        available_codes = self.small_font.render("Available: WELCOME10, JUMP25", True, (100, 100, 255))
        
        self.screen.blit(hint1, (self.SCREEN_WIDTH//2 - hint1.get_width()//2, 350))
        self.screen.blit(available_codes, (self.SCREEN_WIDTH//2 - available_codes.get_width()//2, 380))

    # РЕДАКТОР УРОВНЕЙ
    def start_editor(self):
        """Запуск редактора уровней"""
        self.editor_obstacles = []
        self.editor_selected_type = "spike"
        self.state = self.EDITOR

    def handle_editor_events(self, event):
        """События редактора уровней"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = self.MENU
            elif event.key == pygame.K_1:
                self.editor_selected_type = "spike"
            elif event.key == pygame.K_2:
                self.editor_selected_type = "platform"
            elif event.key == pygame.K_s:  # Сохранить уровень
                self.save_level()
            elif event.key == pygame.K_l:  # Загрузить уровень
                self.load_level()
            elif event.key == pygame.K_c:  # Очистить
                self.editor_obstacles = []
            elif event.key == pygame.K_BACKSPACE:  # Удалить последний
                if self.editor_obstacles:
                    self.editor_obstacles.pop()
                    
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Левая кнопка - добавить
                x, y = event.pos
                self.editor_obstacles.append({
                    "x": x, 
                    "y": y, 
                    "type": self.editor_selected_type
                })
            elif event.button == 3:  # Правая кнопка - удалить ближайший
                x, y = event.pos
                for i, obs in enumerate(self.editor_obstacles):
                    if abs(obs["x"] - x) < 40 and abs(obs["y"] - y) < 40:
                        self.editor_obstacles.pop(i)
                        break

    def draw_editor(self):
        """Отрисовка редактора уровней"""
        self.screen.fill(self.BLACK)
        
        # Заголовок
        title = self.title_font.render("LEVEL EDITOR", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 20))
        
        # Отрисовка препятствий
        for obs in self.editor_obstacles:
            if obs["type"] == "spike":
                points = [
                    (obs["x"], obs["y"] + 40),
                    (obs["x"] + 20, obs["y"]),
                    (obs["x"] + 40, obs["y"] + 40)
                ]
                pygame.draw.polygon(self.screen, self.RED, points)
            else:
                pygame.draw.rect(self.screen, self.GOLD, (obs["x"], obs["y"], 40, 40))
        
        # Подсказки
        hints = [
            "1: Spike | 2: Platform",
            "LMB: Add obstacle | RMB: Remove",
            "S: Save | L: Load | C: Clear | BACKSPACE: Undo",
            f"Selected: {self.editor_selected_type}",
            "ESC: Back to menu"
        ]
        
        for i, hint in enumerate(hints):
            hint_text = self.small_font.render(hint, True, self.WHITE)
            self.screen.blit(hint_text, (20, 80 + i*25))

    def save_level(self):
        """Сохранение уровня в файл"""
        try:
            if not os.path.exists("levels"):
                os.makedirs("levels")
                
            filename = "levels/custom_level.json"
            with open(filename, "w") as f:
                json.dump(self.editor_obstacles, f, indent=4)
            
            print(f"Level saved to {filename}")
        except Exception as e:
            print(f"Error saving level: {e}")
            logging.error(f"Error saving level: {e}")

    def load_level(self):
        """Загрузка уровня из файла"""
        try:
            filename = "levels/custom_level.json"
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    self.editor_obstacles = json.load(f)
                print(f"Level loaded from {filename}")
            else:
                print("No saved level found")
        except Exception as e:
            print(f"Error loading level: {e}")
            logging.error(f"Error loading level: {e}")

    def handle_login_events(self, event):
        """События экрана логина"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = self.MENU
            elif event.key == pygame.K_TAB:
                self.active_input = "password" if self.active_input == "login" else "login"
            elif event.key == pygame.K_RETURN:
                self.process_login()
            elif event.key == pygame.K_BACKSPACE:
                if self.active_input == "login":
                    self.login_input = self.login_input[:-1]
                else:
                    self.password_input = self.password_input[:-1]
            else:
                # Ввод текста с ограничениями
                if event.unicode.isprintable():
                    if self.active_input == "login":
                        # Ограничение логина 15 символов
                        if len(self.login_input) < 15:
                            self.login_input += event.unicode
                    else:
                        # Ограничение пароля 20 символов
                        if len(self.password_input) < 20:
                            self.password_input += event.unicode

    def handle_promo_events(self, event):
        """События экрана промокода"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = self.MENU
            elif event.key == pygame.K_RETURN:
                self.process_promo()
            elif event.key == pygame.K_BACKSPACE:
                self.promo_input = self.promo_input[:-1]
            elif event.unicode.isprintable():
                # Ограничиваем ввод только буквами и цифрами
                if event.unicode.isalnum() and len(self.promo_input) < 20:
                    self.promo_input += event.unicode.upper()

    def process_login(self):
        """Обработка логина с улучшенной обработкой ошибок БД"""
        if not self.login_input or not self.password_input:
            self.login_message = "Please fill all fields"
            return
            
        logging.debug(f"Attempting login/registration for: {self.login_input}")
        
        # Проверяем подключение к БД
        if not self.account_system.conn:
            self.login_message = "Database connection failed - please restart game"
            logging.error("No database connection available")
            return
        
        # Сначала пробуем залогиниться
        login_success = self.account_system.login(self.login_input, self.password_input)
        
        if login_success:
            self.login_message = "Login successful!"
            self.load_player_data()
            logging.info(f"User {self.login_input} logged in successfully")
            self.state = self.MENU  # Возвращаем в меню после успешного логина
            return
            
        # Если логин не удался, пробуем создать аккаунт
        create_success = self.account_system.create_account(self.login_input, self.password_input)
        
        if create_success:
            # После создания пробуем снова залогиниться
            login_after_create = self.account_system.login(self.login_input, self.password_input)
            
            if login_after_create:
                self.login_message = "New account created and logged in!"
                self.load_player_data()
                logging.info(f"New account created and logged in: {self.login_input}")
                self.state = self.MENU 
            else:
                self.login_message = "Account created but login failed. Please try logging in again."
                logging.warning(f"Account created but login failed for: {self.login_input}")
        else:
            self.login_message = "Login failed! Username may be taken."
            logging.warning(f"Both login and account creation failed for: {self.login_input}")

    def process_promo(self):
        """Активация промокода"""
        if not self.account_system.current_account:
            self.promo_message = "Please login first!"
            return
            
        result = self.promo_system.redeem_promo(self.promo_input)
        self.promo_message = result
        
        # Обновляем количество аметистов
        if "received" in result.lower():
            account_data = self.account_system.get_current_account_data()
            self.total_amethysts = account_data.get("amethysts", 0)

    def handle_shop_events(self, event):
        """События магазина"""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = self.MENU

    def handle_game_over_events(self, event):
        """События экрана завершения игры"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.start_game()
            elif event.key == pygame.K_ESCAPE:
                self.state = self.MENU

    def run(self):
        """Главный игровой цикл"""
        while self.running:
            self.handle_events()
            if self.state == self.PLAYING:
                self.update_game()
            self.draw()
            self.clock.tick(60)
            
        pygame.quit()
        sys.exit()

# Базовые классы с улучшениями
class Player:
    def __init__(self, x, y, image=None):
        self.x = x
        self.y = y
        self.size = 40
        self.speed = 5
        self.velocity_y = 0
        self.jump_force = -15
        self.gravity = 0.8
        self.jumps_left = 1
        self.max_jumps = 1
        self.image = image

    def jump(self):
        if self.jumps_left > 0:
            self.velocity_y = self.jump_force
            self.jumps_left -= 1

    def update(self):
        self.velocity_y += self.gravity
        self.y += self.velocity_y

        # Проверка земли
        if self.y >= 600 - self.size:
            self.y = 600 - self.size
            self.velocity_y = 0
            self.jumps_left = self.max_jumps

    def draw(self, screen):
        if self.image:
            screen.blit(self.image, (self.x, self.y))
        else:
            pygame.draw.rect(screen, (255, 255, 255), (self.x, self.y, self.size, self.size))

class Obstacle:
    def __init__(self, x, y, obstacle_type):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40
        self.type = obstacle_type
        self.color = (255, 0, 0) if obstacle_type == "spike" else (255, 215, 0)

    def update(self, speed):
        self.x -= speed

    def draw(self, screen):
        if self.type == "spike":
            # Рисуем шип
            points = [
                (self.x, self.y + self.height),
                (self.x + self.width // 2, self.y),
                (self.x + self.width, self.y + self.height)
            ]
            pygame.draw.polygon(screen, self.color, points)
        else:
            # Рисуем платформу
            pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))

    def check_collision(self, player):
        if self.type == "spike":
            # Для шипов - обычное прямоугольное столкновение
            return (player.x < self.x + self.width and
                    player.x + player.size > self.x and
                    player.y < self.y + self.height and
                    player.y + player.size > self.y)
        else:
            # Для платформ - только сверху
            return (player.x < self.x + self.width and
                    player.x + player.size > self.x and
                    player.y + player.size >= self.y and
                    player.y + player.size <= self.y + 10 and
                    player.velocity_y > 0)

    def is_offscreen(self):
        return self.x + self.width < 0

class Amethyst:
    def __init__(self, x, y, image=None):
        self.x = x
        self.y = y
        self.size = 30
        self.collected = False
        self.image = image

    def update(self, speed):
        self.x -= speed

    def draw(self, screen):
        if not self.collected:
            if self.image:
                screen.blit(self.image, (self.x, self.y))
            else:
                pygame.draw.circle(screen, (148, 0, 211), 
                                 (self.x + self.size//2, self.y + self.size//2), 
                                 self.size//2)

    def check_collision(self, player):
        return (player.x < self.x + self.size and
                player.x + player.size > self.x and
                player.y < self.y + self.size and
                player.y + player.size > self.y)

# Система аккаунтов с улучшениями
class AccountSystem:
    def __init__(self):
        try:
            self.db_path = "game_accounts.db"
            self.conn = sqlite3.connect(self.db_path)
            self.current_account = None
            self.create_tables()
            self.update_database_schema()
            self.load_last_session()
            logging.info("Database initialized successfully")
        except sqlite3.Error as e:
            logging.error(f"Failed to initialize database: {e}")
            self.conn = None
            self.current_account = None

    def create_tables(self):
        if not self.conn:
            return
            
        try:
            cursor = self.conn.cursor()
            
            # Создаем таблицу players
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    amethysts INTEGER DEFAULT 0,
                    last_chest_date TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS promo_used (
                    player_id INTEGER,
                    promo_code TEXT,
                    FOREIGN KEY(player_id) REFERENCES players(id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_skins (
                    player_id INTEGER,
                    skin_id TEXT,
                    owned BOOLEAN DEFAULT 0,
                    FOREIGN KEY(player_id) REFERENCES players(id),
                    PRIMARY KEY (player_id, skin_id)
                )
            ''')
            
            # Таблица для хранения последней сессии
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_sessions (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_username TEXT,
                    last_login_date TEXT
                )
            ''')
            
            self.conn.commit()
            logging.info("Database tables created/verified")
        except sqlite3.Error as e:
            logging.error(f"Database error in create_tables: {e}")

    def update_database_schema(self):
        """Обновление схемы базы данных если нужно"""
        if not self.conn:
            return
            
        try:
            cursor = self.conn.cursor()
            
            # Проверяем существование колонки last_chest_date
            cursor.execute("PRAGMA table_info(players)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'last_chest_date' not in columns:
                logging.info("Adding missing column: last_chest_date")
                cursor.execute('''
                    ALTER TABLE players ADD COLUMN last_chest_date TEXT
                ''')
                self.conn.commit()
                logging.info("Database schema updated successfully")
                
        except sqlite3.Error as e:
            logging.error(f"Error updating database schema: {e}")

    def save_last_session(self, username):
        """Сохраняем информацию о последней сессии"""
        if not self.conn:
            return
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO game_sessions (id, last_username, last_login_date)
                VALUES (1, ?, ?)
            ''', (username, datetime.datetime.now().isoformat()))
            self.conn.commit()
            logging.info(f"Session saved for user: {username}")
        except sqlite3.Error as e:
            logging.error(f"Error saving session: {e}")

    def load_last_session(self):
        """Загружаем последнюю сессию и автоматически логинимся"""
        if not self.conn:
            return
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT last_username FROM game_sessions WHERE id = 1
            ''')
            
            result = cursor.fetchone()
            if result:
                last_username = result[0]
                logging.info(f"Found last session for user: {last_username}")
                self.last_username = last_username
            else:
                self.last_username = None
                
        except sqlite3.Error as e:
            logging.error(f"Error loading last session: {e}")
            self.last_username = None

    def hash_password(self, password):
        return sha256(password.encode()).hexdigest()

    def create_account(self, username, password):
        if not self.conn:
            logging.error("No database connection for account creation")
            return False
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO players (username, password, amethysts, last_chest_date) 
                VALUES (?, ?, 0, NULL)
            ''', (username, self.hash_password(password)))
            self.conn.commit()
            logging.info(f"Account created successfully: {username}")
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Account already exists: {username}")
            return False
        except sqlite3.Error as e:
            logging.error(f"Database error in create_account: {e}")
            return False

    def login(self, username, password):
        if not self.conn:
            logging.error("No database connection for login")
            return False
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, username, amethysts, last_chest_date FROM players 
                WHERE username = ? AND password = ?
            ''', (username, self.hash_password(password)))
            
            result = cursor.fetchone()
            if result:
                self.current_account = {
                    "id": result[0],
                    "username": result[1],
                    "amethysts": result[2] or 0,
                    "last_chest_date": result[3]
                }
                # Сохраняем сессию при успешном логине
                self.save_last_session(username)
                logging.info(f"Login successful: {username}")
                return True
            else:
                logging.warning(f"Login failed for: {username} - invalid credentials")
                return False
        except sqlite3.Error as e:
            logging.error(f"Database error in login: {e}")
            return False

    def get_current_account_data(self):
        return self.current_account

    def get_last_username(self):
        """Возвращает имя последнего залогиненного пользователя"""
        return getattr(self, 'last_username', None)

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            logging.info("Database connection closed")

class PromoSystem:
    PROMO_CODES = {
        "WELCOME10": {"amethysts": 10},
        "JUMP25": {"amethysts": 25},
    }

    def __init__(self, account_system):
        self.account_system = account_system

    def redeem_promo(self, code):
        if not self.account_system.current_account:
            return "Please login first"
            
        if not self.account_system.conn:
            return "Database error"
            
        code = code.upper()
        if code not in self.PROMO_CODES:
            return "Invalid promo code"
            
        try:
            cursor = self.account_system.conn.cursor()
            cursor.execute('''
                SELECT 1 FROM promo_used 
                WHERE player_id = ? AND promo_code = ?
            ''', (self.account_system.current_account["id"], code))
            
            if cursor.fetchone():
                return "Promo code already used"
                
            # Выдача награды
            reward = self.PROMO_CODES[code]
            cursor.execute('''
                UPDATE players SET amethysts = amethysts + ? 
                WHERE id = ?
            ''', (reward["amethysts"], self.account_system.current_account["id"]))
            
            cursor.execute('''
                INSERT INTO promo_used (player_id, promo_code) VALUES (?, ?)
            ''', (self.account_system.current_account["id"], code))
            
            self.account_system.conn.commit()
            self.account_system.current_account["amethysts"] += reward["amethysts"]
            
            logging.info(f"Promo code redeemed: {code} for user {self.account_system.current_account['username']}")
            return f"Received {reward['amethysts']} amethysts!"
        except sqlite3.Error as e:
            logging.error(f"Database error in redeem_promo: {e}")
            return "Database error"

if __name__ == "__main__":
    game = Game()
    game.run()