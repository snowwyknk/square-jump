import pygame
import pygame_menu
import random
import sys
import json
import os
import sqlite3
from hashlib import sha256
import logging
import datetime
import math
import time

# Настройка логирования
logging.basicConfig(filename='game.log', level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# ============================================================================
# КОНСТАНТЫ ДЛЯ СИСТЕМЫ ПРОКАЧКИ СКИНОВ (НОВОЕ)
# ============================================================================
MAX_SKIN_LEVEL = 15
EXP_PER_LEVEL = [0, 100, 250, 500, 1000, 1500, 2200, 3000, 4000, 5000, 
                 6100, 7300, 8600, 10000, 11500, 13000]

# ============================================================================
# КЛАССЫ ИГРОВЫХ ОБЪЕКТОВ (С УЛУЧШЕНИЯМИ)
# ============================================================================
class Player:
    def __init__(self, x, y, size=55):
        self.x = x
        self.y = y
        self.size = size
        self.vy = 0
        self.on_ground = False
        self.jumps_left = 2
        self.alive = True
        self.invincible = False
        self.invincible_timer = 0
        self.has_double_jump = True
        self.has_shield = False
        self.speed_boost_timer = 0
        
    # ====================================================================
        # НОВОЕ: АТРИБУТЫ ДЛЯ ПРОКАЧКИ СКИНОВ
        # ====================================================================
        self.skin_level = 1          # Текущий уровень скина (1-15)
        self.skin_exp = 0            # Опыт текущего уровня
        self.total_exp = 0           # Общий накопленный опыт
        self.completed_levels = 0    # Количество пройденных кастомных уровней
        
    def update(self, gravity, max_fall_speed, air_resistance=0.98):
        # Применяем гравитацию с сопротивлением воздуха
        self.vy += gravity
        self.vy *= air_resistance
        
        # Ограничиваем максимальную скорость падения
        if self.vy > max_fall_speed:
            self.vy = max_fall_speed
        elif self.vy < -max_fall_speed * 1.5:
            self.vy = -max_fall_speed * 1.5
            
        self.y += self.vy
        
        # Обновление таймеров
        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= 1
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        else:
            self.invincible = False
            
    def jump(self, jump_force):
        """Выполнение прыжка"""
        if self.jumps_left > 0:
            self.vy = jump_force
            self.jumps_left -= 1
            self.on_ground = False
            
            # ================================================================
            # НОВОЕ: Визуальный эффект при прыжке в зависимости от уровня скина
            # ================================================================
            effect_size = min(10, 5 + self.skin_level // 3)
            return True, effect_size
        return False, 0
        
    def get_rect(self):
        """Получение прямоугольника игрока для коллизий"""
        return pygame.Rect(self.x, self.y, self.size, self.size)
        
    def activate_shield(self):
        """Активация щита"""
        if self.has_shield:
            self.invincible = True
            self.invincible_timer = 300
            self.has_shield = False
            return True
        return False
        
    def activate_speed_boost(self):
        """Активация ускорения"""
        self.speed_boost_timer = 180
        return True
    
    # ========================================================================
    # НОВЫЕ МЕТОДЫ ДЛЯ СИСТЕМЫ ПРОКАЧКИ
    # ========================================================================
    def add_exp(self, amount):
        """
        Добавление опыта скину
        amount: количество опыта для добавления
        """
        self.skin_exp += amount
        self.total_exp += amount
        
        # Проверяем, не пора ли повысить уровень
        while (self.skin_level < MAX_SKIN_LEVEL and 
               self.skin_exp >= EXP_PER_LEVEL[self.skin_level]):
            self.level_up()
            
    def level_up(self):
        """
        Повышение уровня скина
        Вызывается автоматически при накоплении достаточного опыта
        """
        self.skin_level += 1
        logging.info(f"Skin leveled up to {self.skin_level}!")
        
        # Можно добавить бонусы при повышении уровня
        if self.skin_level % 5 == 0:  # Каждые 5 уровней
            self.size += 2  # Небольшое увеличение размера
            logging.info(f"Player size increased to {self.size}")
            
    def get_exp_percentage(self):
        """
        Получение процента заполнения текущего уровня
        Возвращает: процент от 0 до 100
        """
        if self.skin_level >= MAX_SKIN_LEVEL:
            return 100  # Максимальный уровень
        
        current_level_exp = EXP_PER_LEVEL[self.skin_level - 1]
        next_level_exp = EXP_PER_LEVEL[self.skin_level]
        exp_in_current = self.skin_exp - current_level_exp
        exp_needed = next_level_exp - current_level_exp
        
        if exp_needed == 0:
            return 0
            
        percentage = (exp_in_current / exp_needed) * 100
        return min(100, max(0, percentage))  # Ограничиваем 0-100
    
    def add_completed_level(self):
        """Увеличивает счетчик пройденных кастомных уровней"""
        self.completed_levels += 1
            
class Obstacle:
    def __init__(self, x, y, obstacle_type, width=60, height=60, color=None):
        self.x = x
        self.y = y
        self.type = obstacle_type
        self.w = width
        self.h = height
        self.color = color or (255, 0, 0)
        
    # Дополнительные свойства для движущихся шипов
        self.move_speed = 0
        self.move_direction = 1
        self.original_y = y
        
        # ====================================================================
        # НОВОЕ: СВОЙСТВА ДЛЯ УЛУЧШЕННОЙ ГЕНЕРАЦИИ
        # ====================================================================
        self.bounce_power = 1.0           # Для прыгучих платформ
        self.disappear_timer = 0          # Для исчезающих платформ
        self.visible = True               # Видимость объекта
        self.pulse_phase = random.random() * math.pi * 2  # Для анимации
        
    def update(self, game_speed):
        """
        УЛУЧШЕННОЕ обновление позиции препятствия
        Добавлена поддержка новых типов препятствий
        """
        # Основное движение
        self.x -= game_speed
        
        # Анимация пульсации для визуального эффекта
        self.pulse_phase += 0.05
        
        # Движение для движущихся шипов
        if self.type == "moving_spike":
            self.y += self.move_speed * self.move_direction
            if self.y > self.original_y + 50 or self.y < self.original_y - 50:
                self.move_direction *= -1
        
        # НОВОЕ: Обновление таймера для исчезающих платформ
        if self.type == "disappearing_platform" and self.visible:
            self.disappear_timer -= 1
            if self.disappear_timer <= 0:
                self.visible = False
                
    def get_rect(self):
        """Получение прямоугольника препятствия для коллизий"""
        return pygame.Rect(self.x, self.y, self.w, self.h)
        
    def is_off_screen(self):
        """Проверка, вышло ли препятствие за экран"""
        return self.x < -100
    
    # ========================================================================
    # НОВЫЕ МЕТОДЫ ДЛЯ УЛУЧШЕННОЙ ГЕНЕРАЦИИ
    # ========================================================================
    def get_pulse_offset(self):
        """
        Возвращает смещение для анимации пульсации
        Используется для визуальных эффектов
        """
        return math.sin(self.pulse_phase) * 2

class Amethyst:
    def __init__(self, x, y, size=30):
        self.x = x
        self.y = y
        self.size = size
        self.collected = False
        self.float_offset = random.random() * math.pi * 2  # Для плавающей анимации
        self.rotation = 0  # Для вращения
        
    def update(self, game_speed):
        """УЛУЧШЕННОЕ обновление позиции аметиста с анимацией"""
        self.x -= game_speed
        
        # Анимация плавания
        self.float_offset += 0.05
        self.rotation += 2
        
    def get_rect(self):
        """Получение прямоугольника аметиста для коллизий"""
        # Немного увеличиваем хитбокс для удобства сбора
        return pygame.Rect(self.x - 2, self.y - 2, self.size + 4, self.size + 4)
        
    def is_off_screen(self):
        """Проверка, вышел ли аметист за экран"""
        return self.x < -50
    
    # ========================================================================
    # НОВЫЕ МЕТОДЫ ДЛЯ УЛУЧШЕННОЙ АНИМАЦИИ
    # ========================================================================
    def get_float_y(self):
        """Возвращает Y позицию с учетом плавающей анимации"""
        return self.y + math.sin(self.float_offset) * 3
    
    def get_current_size(self):
        """Возвращает размер с учетом пульсации"""
        pulse = math.sin(self.float_offset * 2) * 2
        return self.size + pulse

class ShopItem:
    def __init__(self, name, description, cost, effect_type):
        self.name = name
        self.description = description
        self.cost = cost
        self.effect_type = effect_type

class ParticleSystem:
    """УЛУЧШЕННАЯ система частиц для визуальных эффектов"""
    def __init__(self):
        self.particles = []
        self.max_particles = 200  # Ограничение для производительности
        
    def add_particles(self, x, y, color, count=5, speed=2, lifetime=30, size_variation=3):
        """
        УЛУЧШЕННОЕ добавление частиц
        size_variation: вариация размера частиц
        """
        # Проверяем, не превышен ли лимит частиц
        if len(self.particles) > self.max_particles - count:
            # Удаляем самые старые частицы
            self.particles = self.particles[count:]
            
        for _ in range(count):
            particle = {
                'x': x,
                'y': y,
                'vx': random.uniform(-speed, speed),
                'vy': random.uniform(-speed, speed),
                'color': color,
                'lifetime': lifetime,
                'max_lifetime': lifetime,
                'size': random.randint(2, 2 + size_variation),
                'gravity': random.uniform(0.05, 0.15)
            }
            self.particles.append(particle)
            
    def update(self):
        """УЛУЧШЕННОЕ обновление частиц"""
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += particle['gravity']
            particle['lifetime'] -= 1
            
            if particle['lifetime'] <= 0:
                self.particles.remove(particle)
                
    def draw(self, screen):
        """УЛУЧШЕННАЯ отрисовка частиц с плавным исчезновением"""
        for particle in self.particles:
            # Плавное изменение альфа-канала
            alpha = int(255 * (particle['lifetime'] / particle['max_lifetime']))
            color = list(particle['color'])
            
            if len(color) == 3:
                color.append(alpha)
            else:
                color[3] = alpha
            
            # Создаем поверхность с альфа-каналом
            size = particle['size']
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            
            # Рисуем частицу как размытый круг
            pygame.draw.circle(surf, color, (size, size), size)
            
            # Добавляем свечение для эффектных частиц
            if alpha > 150:
                glow_color = list(color[:3]) + [alpha // 3]
                pygame.draw.circle(surf, glow_color, (size, size), size * 1.5)
            
            screen.blit(surf, (particle['x'] - size, particle['y'] - size))

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
        self.ORANGE = (255, 165, 0)
        self.CYAN = (0, 255, 255)
        self.PINK = (255, 105, 180)
        self.LIME = (50, 205, 50)
        
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
        self.LEVEL_SELECT = 10
        self.LEVEL_COMPLETE = 11
        self.SKIN_PROGRESSION = 12
        
        # Режим экрана
        self.fullscreen = False
        self.original_size = (self.SCREEN_WIDTH, self.SCREEN_HEIGHT)
        
        # Инициализация экрана
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption("Square Jump - Ultimate Edition v2.0")
        self.clock = pygame.time.Clock()
        
        # Сначала создаем пустого игрока, чтобы избежать ошибок
        self.player = Player(0, 0)
        self.player.skin_level = 1
        self.player.skin_exp = 0
        self.player.total_exp = 0
        self.player.completed_levels = 0
        
        # Системы
        self.account_system = AccountSystem()
        self.promo_system = PromoSystem(self.account_system)
        self.particle_system = ParticleSystem()
        
        # ====================================================================
        # УЛУЧШЕННЫЕ ПАРАМЕТРЫ ФИЗИКИ
        self.gravity = 0.5            
        self.jump_force = -16         
        self.max_fall_speed = 15      
        self.air_resistance = 0.98    
        self.bounce_multiplier = 1.5 
        self.acceleration_rate = 0.002
        
        # Состояние игры
        self.state = self.MENU
        self.running = True
        self.score = 0
        self.total_amethysts = 0
        self.level_complete = False
        
         # Меню (старая система для совместимости)
        self.menu_options = ['Start Game', 'Level Select', 'Level Editor', 'Shop', 
                            'Inventory', 'Daily Chest', 'Login/Logout', 'Promo Codes', 
                            'Settings', 'Skin Progression', 'Exit']
        self.selected_option = 0
        
        # Флаг использования pygame-menu
        self.use_pygame_menu = True
        
        # Сначала создаем градиентный фон
        self.menu_bg_surface = self.create_gradient_menu_bg()
        
        # Меню (pygame-menu)
        self.menu = None
        self.create_menus()
        
        # Устанавливаем активное меню при запуске
        self.state = self.MENU
        if self.use_pygame_menu:
            self.menu = self.main_menu
            self.menu.enable()
        
        # ШРИФТЫ
        try:
            self.font = pygame.font.SysFont('arial', 32)
            self.title_font = pygame.font.SysFont('arial', 48, bold=True)
            self.small_font = pygame.font.SysFont('arial', 24)
            self.tiny_font = pygame.font.SysFont('arial', 18)
        except:
            self.font = pygame.font.Font(None, 32)
            self.title_font = pygame.font.Font(None, 48)
            self.small_font = pygame.font.Font(None, 24)
            self.tiny_font = pygame.font.Font(None, 18)
        
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
        self.player_image = None
        
        
        # Магазин
        self.shop_items = [
            ShopItem("Shield", "Protection from one obstacle", 30, "shield"),
            ShopItem("Speed Boost", "Temporary speed increase", 25, "speed_boost"),
            ShopItem("Extra Life", "One extra life per game", 40, "extra_life"),
            ShopItem("Double Jump", "Jump twice in the air", 50, "double_jump"),
            ShopItem("EXP Booster", "+20% EXP for 3 levels", 75, "exp_booster")  # НОВЫЙ товар
        ]
        self.selected_shop_item = 0
        
        # Ежедневный сундук
        self.last_chest_date = None
        self.chest_rewards = []
        self.chest_animation_frame = 0
        
        # Загрузка ресурсов
        self.load_resources()
        
        # Игрок и игровые объекты
        self.obstacles = []
        self.amethysts = []
        self.game_speed = 5
        self.base_speed = 5
        self.camera_x = 0
        self.spawn_timer = 0
        self.percent = 0
        self.distance_traveled = 0
        self.level_end_x = 5000
        
        
        # РЕДАКТОР УРОВНЕЙ
        self.editor_obstacles = []
        self.editor_amethysts = []
        self.editor_selected_type = "spike"
        self.editor_brush_size = 1
        self.editor_grid_snap = True
        self.editor_show_grid = True
        self.editor_camera_x = 0
        self.editor_camera_y = 0
        self.editor_dragging = False
        self.editor_drag_start = (0, 0)
        self.editor_selected_object = None
        self.editor_level_name = "my_level"
        self.editor_message = ""
        self.editor_message_timer = 0
        
         # ====================================================================
        # НОВОЕ: СИСТЕМА ПРОКАЧКИ И УРОВНЕЙ
        # ====================================================================
        self.exp_message = ""          # Сообщение о полученном опыте
        self.exp_message_timer = 0     # Таймер отображения сообщения
        self.exp_boost_active = False  # Активен ли буст опыта
        self.exp_boost_timer = 0       # Таймер буста опыта
        
        # Загрузка доступных уровней (теперь с 10 пресет-уровнями)
        self.available_levels = self.load_available_levels()
        self.selected_level_index = 0
        
        # Прогресс по уровням
        self.completed_levels = []  # Список пройденных уровней
        self.level_progress = {}    # Статистика по уровням
        self.load_level_progress()
        
        # Генерация 10 пресет-уровней
        self.preset_levels = self.generate_preset_levels()
        
        # Автоматическая загрузка данных если пользователь уже залогинен
        if self.account_system.current_account:
            self.load_player_data()
            
         # Создаем меню (теперь после инициализации всего остального)
        self.create_menus()
    
        # Устанавливаем активное меню при запуске
        if self.use_pygame_menu:
            self.menu = self.main_menu
            self.menu.enable()
            
        # ВЫБОР УРОВНЕЙ
        self.available_levels = self.load_available_levels()
        self.selected_level_index = 0
        

    def create_gradient_menu_bg(self):
        surf = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
    
        # Цвет градиента зависит от уровня скина
        if self.player and hasattr(self.player, 'skin_level'):
            base_hue = (self.player.skin_level * 24) % 360
        else:
            base_hue = 240  # Значение по умолчанию
        
        start_color = self.hsv_to_rgb(base_hue, 0.8, 0.2)
        end_color = self.hsv_to_rgb((base_hue + 60) % 360, 0.9, 0.4)
        
        # Создаем вертикальный градиент
        for y in range(self.SCREEN_HEIGHT):
            t = y / self.SCREEN_HEIGHT
            r = self.lerp(start_color[0], end_color[0], t)
            g = self.lerp(start_color[1], end_color[1], t)
            b = self.lerp(start_color[2], end_color[2], t)
            pygame.draw.line(surf, (int(r), int(g), int(b)), (0, y), (self.SCREEN_WIDTH, y))
        
        # Добавляем звезды/частицы для красоты
        for _ in range(50):
            x = random.randint(0, self.SCREEN_WIDTH)
            y = random.randint(0, self.SCREEN_HEIGHT)
            size = random.randint(1, 3)
            brightness = random.randint(150, 255)
            pygame.draw.circle(surf, (brightness, brightness, brightness), (x, y), size)
        
        return surf
        
    def update_menu_theme(self):
        """Обновление темы меню с градиентным фоном"""
        theme = pygame_menu.themes.THEME_DARK.copy()
        
        # Настраиваем тему
        theme.title_background_color = (40, 40, 80, 180)
        theme.title_font_color = self.GOLD
        theme.widget_font_color = self.WHITE
        theme.background_color = (0, 0, 0, 0)
        theme.title_font_size = 48
        theme.widget_font_size = 32
        theme.widget_margin = (0, 15)
        theme.widget_padding = 15
        
        # Убедимся, что градиентный фон создан
        if not hasattr(self, 'menu_bg_surface'):
            self.menu_bg_surface = self.create_gradient_menu_bg()
        elif self.menu_bg_surface.get_size() != (self.SCREEN_WIDTH, self.SCREEN_HEIGHT):
            self.menu_bg_surface = self.create_gradient_menu_bg()
        
        return theme

    def create_menus(self):
        """
        УЛУЧШЕННОЕ создание меню с использованием pygame-menu
        Все кнопки теперь работают правильно
        """
        theme = self.update_menu_theme()
        
        # Главное меню
        self.main_menu = pygame_menu.Menu(
            'Square Jump Ultimate v2.0',
            self.SCREEN_WIDTH,
            self.SCREEN_HEIGHT,
            theme=theme,
            onclose=pygame_menu.events.EXIT
        )
        
        # ИСПРАВЛЕННЫЕ КНОПКИ - все используют правильные методы
        self.main_menu.add.button('Start Game', self.start_game_from_menu)
        self.main_menu.add.button('Level Select', self.show_level_select_menu)
        self.main_menu.add.button('Level Editor', self.start_editor_from_menu)
        self.main_menu.add.button('Shop', self.show_shop_menu)
        self.main_menu.add.button('Inventory', self.show_inventory_menu)
        self.main_menu.add.button('Daily Chest', self.open_daily_chest_from_menu)
        self.main_menu.add.button('Login/Logout', self.toggle_login_from_menu)
        self.main_menu.add.button('Promo Codes', self.show_promo_menu)
        self.main_menu.add.button('Settings', self.show_settings_menu)
        self.main_menu.add.button('Skin Progression', self.show_skin_progression_menu)
        self.main_menu.add.button('Switch to Old Menu', self.toggle_menu_system)
        self.main_menu.add.button('Exit', self.exit_game)
        
        # Меню выбора уровня
        self.level_select_menu = pygame_menu.Menu(
            'Select Level',
            self.SCREEN_WIDTH,
            self.SCREEN_HEIGHT,
            theme=theme
        )
        
        # Меню магазина
        self.shop_menu = pygame_menu.Menu(
            'Shop',
            self.SCREEN_WIDTH,
            self.SCREEN_HEIGHT,
            theme=theme
        )
        
        # Меню инвентаря
        self.inventory_menu = pygame_menu.Menu(
            'Inventory',
            self.SCREEN_WIDTH,
            self.SCREEN_HEIGHT,
            theme=theme
        )
        
        # Меню настроек
        self.settings_menu = pygame_menu.Menu(
            'Settings',
            self.SCREEN_WIDTH,
            self.SCREEN_HEIGHT,
            theme=theme
        )
        
        self.settings_menu.add.selector('Resolution: ', 
            [('800x600', 0), ('1024x768', 1), ('1280x720', 2)], 
            onchange=self.change_resolution)
        self.settings_menu.add.selector('Fullscreen: ', 
            [('Off', False), ('On', True)], 
            onchange=self.toggle_fullscreen_setting)
        self.settings_menu.add.range_slider('Music Volume', 50, (0, 100), 1, 
            onchange=self.change_music_volume)
        self.settings_menu.add.range_slider('SFX Volume', 70, (0, 100), 1, 
            onchange=self.change_sfx_volume)
        self.settings_menu.add.button('Back', self.return_to_main_menu)
        
        # Меню промокодов
        self.promo_menu = pygame_menu.Menu(
            'Promo Codes',
            self.SCREEN_WIDTH,
            self.SCREEN_HEIGHT,
            theme=theme
        )
        
        self.promo_input_widget = self.promo_menu.add.text_input('Code: ', 
            default='', maxchar=20)
        self.promo_menu.add.button('Redeem', self.redeem_promo_from_menu)
        self.promo_menu.add.button('Back', self.return_to_main_menu)
        
        # Меню прокачки скинов (обновляется динамически)
        self.skin_progression_menu = pygame_menu.Menu(
            'Skin Progression',
            self.SCREEN_WIDTH,
            self.SCREEN_HEIGHT,
            theme=theme
        )
        
        # Добавляем кнопку "Назад" в меню прокачки
        self.skin_progression_menu.add.button('Back', self.return_to_main_menu)
    
    # ИСПРАВЛЕННЫЕ МЕТОДЫ ДЛЯ РАБОТЫ PYGAME-MENU
    # ========================================================================
    def start_game_from_menu(self):
        """Запуск игры из меню (исправленная версия)"""
        if self.menu and self.menu.is_enabled():
            self.menu.disable()
        self.start_game()
    
    def start_editor_from_menu(self):
        """Запуск редактора из меню (исправленная версия)"""
        if self.menu and self.menu.is_enabled():
            self.menu.disable()
        self.start_editor()
    
    def open_daily_chest_from_menu(self):
        """Открытие сундука из меню (исправленная версия)"""
        self.open_daily_chest()
    
    def toggle_login_from_menu(self):
        """Переключение логина из меню (исправленная версия)"""
        self.toggle_login()
    
    def show_skin_progression_menu(self):
        """Показать меню прокачки скинов (НОВОЕ)"""
        self.update_skin_progression_menu()
        self.state = self.MENU
        self.menu = self.skin_progression_menu
        
    def update_skin_progression_menu(self):
        """Обновление меню прокачки скинов"""
        self.skin_progression_menu.clear()
        
        self.skin_progression_menu.add.label('SKIN PROGRESSION', font_color=self.GOLD)
        
        if self.account_system.current_account:
            self.skin_progression_menu.add.label(
                f'Player: {self.account_system.current_account["username"]}',
                font_color=self.WHITE
            )
        
        # Информация о текущем скине
        skin = self.skins.get(self.current_skin, {})
        self.skin_progression_menu.add.label(
            f'Current Skin: {skin.get("name", "Unknown")}',
            font_color=self.CYAN
        )
        
        # ПРОВЕРЯЕМ, ЧТО ИГРОК СУЩЕСТВУЕТ И ИМЕЕТ АТРИБУТЫ ПРОКАЧКИ
        if self.player and hasattr(self.player, 'skin_level'):
            # Уровень скина
            level_text = f'Level: {self.player.skin_level}/{MAX_SKIN_LEVEL}'
            self.skin_progression_menu.add.label(level_text, font_color=self.GREEN)
            
            # Опыт текущего уровня
            if self.player.skin_level < len(EXP_PER_LEVEL):
                next_level_exp = EXP_PER_LEVEL[self.player.skin_level]
                current_level_exp = EXP_PER_LEVEL[self.player.skin_level - 1]
                exp_in_current = self.player.skin_exp - current_level_exp
                exp_needed = next_level_exp - current_level_exp
                exp_text = f'EXP: {exp_in_current}/{exp_needed}'
            else:
                exp_text = f'EXP: {self.player.skin_exp} (MAX LEVEL)'
            self.skin_progression_menu.add.label(exp_text, font_color=self.PURPLE)
            
            # Общий опыт
            total_exp_text = f'Total EXP: {self.player.total_exp}'
            self.skin_progression_menu.add.label(total_exp_text, font_color=self.GOLD)
            
            # Прогресс бар
            progress = self.player.get_exp_percentage()
            progress_text = f'Progress: {progress:.1f}%'
            self.skin_progression_menu.add.label(progress_text, font_color=self.WHITE)
            
            # Пройденные уровни
            completed_text = f'Custom Levels Completed: {self.get_completed_custom_levels()}'
            self.skin_progression_menu.add.label(completed_text, font_color=self.LIME)
        else:
            # Если игрок не создан, показываем базовую информацию
            self.skin_progression_menu.add.label('Player data not loaded', font_color=self.RED)
        
        # Разделитель
        self.skin_progression_menu.add.label("─" * 30, font_color=self.WHITE)
        self.skin_progression_menu.add.label("LEVEL REWARDS", font_color=self.GOLD)
        
        # Показываем информацию о первых 5 уровнях
        for level in range(1, min(6, MAX_SKIN_LEVEL + 1)):
            # Проверяем уровень с учетом наличия игрока
            if self.player and hasattr(self.player, 'skin_level') and self.player.skin_level >= level:
                status = "✓ UNLOCKED"
                color = self.GREEN
            else:
                if level < len(EXP_PER_LEVEL):
                    status = f"Requires {EXP_PER_LEVEL[level]} EXP"
                else:
                    status = "MAX LEVEL"
                color = self.WHITE
            
            self.skin_progression_menu.add.label(
                f'Level {level}: {status}',
                font_color=color,
                font_size=20
            )
        
        self.skin_progression_menu.add.button('Back', self.return_to_main_menu)

    def exit_game(self):
        """Выход из игры"""
        self.running = False

    def toggle_menu_system(self):
        """Переключение между старой и новой системой меню"""
        self.use_pygame_menu = not self.use_pygame_menu
        
        # Явно сбрасываем состояние
        self.state = self.MENU
        
        if self.use_pygame_menu:
            self.menu = self.main_menu
            if self.menu:
                self.menu.enable()
        else:
            if self.menu:
                self.menu.disable()
            self.menu = None
            self.selected_option = 0  # Сброс выбора в старом меню

    def show_level_select_menu(self):
        """Показать меню выбора уровня"""
        self.level_select_menu.clear()
        self.level_select_menu.add.label('SELECT LEVEL', font_color=self.GOLD)
        
        for i, level in enumerate(self.available_levels):
            self.level_select_menu.add.button(
                f"{level['name']} - {level['description']}", 
                lambda idx=i: self.start_selected_level(idx)
            )
        
        self.level_select_menu.add.button('Back', self.return_to_main_menu)
        self.state = self.MENU
        self.menu = self.level_select_menu

    def show_shop_menu(self):
        """Показать меню магазина"""
        self.shop_menu.clear()
        self.shop_menu.add.label('SHOP', font_color=self.GOLD)
        
        # Сначала показываем баланс
        balance_text = f'Your Amethysts: {self.total_amethysts}'
        self.shop_menu.add.label(balance_text, font_color=self.PURPLE, font_size=24)
        
        # Добавляем разделитель
        self.shop_menu.add.label("─" * 40, font_color=self.WHITE)
        
        # Отображаем товары без фреймов
        for i, item in enumerate(self.shop_items):
            can_afford = self.total_amethysts >= item.cost
            color = self.GREEN if can_afford else self.RED
            
            # Создаем строку с информацией о товаре
            item_info = f"{item.name} - {item.cost} AM"
            self.shop_menu.add.label(item_info, font_color=color, font_size=22)
            
            # Описание товара
            self.shop_menu.add.label(item.description, font_color=self.WHITE, font_size=18)
            
            # Кнопка покупки
            btn_text = 'Buy' if can_afford else 'Cannot afford'
            self.shop_menu.add.button(
                btn_text,
                lambda i=item: self.buy_shop_item_from_menu(i),
                background_color=color if can_afford else (100, 100, 100),
                font_color=self.BLACK if can_afford else self.WHITE,
                font_size=20
            )
            
            # Добавляем отступ между товарами
            if i < len(self.shop_items) - 1:
                self.shop_menu.add.label("", font_color=self.WHITE)  # Пустая строка для отступа
        
        self.shop_menu.add.button('Back', self.return_to_main_menu)
        self.state = self.MENU
        self.menu = self.shop_menu

    def show_inventory_menu(self):
        """Показать меню инвентаря"""
        self.inventory_menu.clear()
        
        self.inventory_menu.add.label('SKIN INVENTORY', font_color=self.GOLD)
        
        if self.account_system.current_account:
            self.inventory_menu.add.label(
                f'Player: {self.account_system.current_account["username"]}',
                font_color=self.WHITE
            )
        
        # Создаем сетку для скинов простым способом
        # Добавляем все скины как кнопки
        for skin_id, skin in self.skins.items():
            skin_color = self.GREEN if skin["owned"] else (100, 100, 100)
            border_color = self.GOLD if skin_id == self.current_skin else skin_color
            
            # Создаем кнопку для скина
            self.inventory_menu.add.button(
                skin["name"],
                lambda sid=skin_id: self.select_skin_from_menu(sid),
                background_color=border_color,
                font_color=self.BLACK if skin["owned"] else self.WHITE,
                font_size=20
            )
        
        # Добавляем разделитель
        self.inventory_menu.add.label("─" * 40, font_color=self.WHITE)
        
        # Информация о текущем скине
        skin = self.skins.get(self.current_skin, {})
        self.inventory_menu.add.label(
            f'Selected: {skin.get("name", "Unknown")}',
            font_color=self.CYAN
        )
        
        # Баланс
        self.inventory_menu.add.label(
            f'Your Amethysts: {self.total_amethysts}',
            font_color=self.PURPLE
        )
        
        self.inventory_menu.add.button('Back', self.return_to_main_menu)
        
        self.state = self.MENU
        self.menu = self.inventory_menu
    
    def show_settings_menu(self):
        """Показать меню настроек"""
        self.state = self.MENU
        self.menu = self.settings_menu

    def show_promo_menu(self):
        """Показать меню промокодов"""
        self.state = self.MENU
        self.menu = self.promo_menu

    def toggle_login(self):
        """Переключение логина/логаута"""
        if self.account_system.current_account:
            self.account_system.current_account = None
            self.total_amethysts = 0
            self.login_message = "Logged out successfully"
            self.state = self.MENU
            if self.use_pygame_menu:
                self.menu = self.main_menu
        else:
            self.state = self.LOGIN
            self.menu = None

    def change_resolution(self, value, index):
        """Изменение разрешения экрана"""
        resolutions = [(800, 600), (1024, 768), (1280, 720)]
        new_size = resolutions[index]
        
        if not self.fullscreen:
            self.SCREEN_WIDTH, self.SCREEN_HEIGHT = new_size
            self.screen = pygame.display.set_mode(new_size)
            self.create_menus()

    def toggle_fullscreen_setting(self, value, fullscreen):
        """Переключение полноэкранного режима из настроек"""
        self.toggle_fullscreen()

    def change_music_volume(self, value):
        """Изменение громкости музыки"""
        pygame.mixer.music.set_volume(value / 100)

    def change_sfx_volume(self, value):
        """Изменение громкости звуковых эффектов"""
        # Здесь можно добавить установку громкости для звуковых эффектов
        pass

    def buy_shop_item_from_menu(self, item):
        """Покупка товара из меню магазина"""
        success = self.buy_shop_item(item)
        if success:
            # Обновляем данные игрока после покупки
            account_data = self.account_system.get_current_account_data()
            self.total_amethysts = account_data.get("amethysts", 0)
            # Показываем сообщение об успешной покупке
            success_menu = pygame_menu.Menu(
                'Success',
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=self.update_menu_theme()
            )
            success_menu.add.label(f'Purchased {item.name}!', font_color=self.GREEN)
            success_menu.add.button('Back to Shop', self.show_shop_menu)
            self.menu = success_menu
        else:
            # Показываем сообщение об ошибке
            error_menu = pygame_menu.Menu(
                'Error',
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=self.update_menu_theme()
            )
            if self.login_message:
                error_menu.add.label(self.login_message, font_color=self.RED)
            else:
                error_menu.add.label('Purchase failed!', font_color=self.RED)
            error_menu.add.button('Back to Shop', self.show_shop_menu)
            self.menu = error_menu
        
    def select_skin_from_menu(self, skin_id):
        skin = self.skins[skin_id]
        
        if skin["owned"]:
            # Используем новый метод с сохранением прогресса
            self.switch_skin_with_progress(skin_id)
            # Обновляем меню инвентаря
            self.show_inventory_menu()
        elif not skin["locked"] and self.total_amethysts >= skin["cost"]:
            # Покупка скина
            self.total_amethysts -= skin["cost"]
            skin["owned"] = True
            
            try:
                if self.account_system.current_account and self.account_system.conn:
                    cursor = self.account_system.conn.cursor()
                    cursor.execute('UPDATE players SET amethysts = ? WHERE username = ?',
                                (self.total_amethysts, self.account_system.current_account['username']))
                    cursor.execute('INSERT OR REPLACE INTO player_skins (player_id, skin_id, owned) VALUES ((SELECT id FROM players WHERE username = ?), ?, 1)',
                                (self.account_system.current_account['username'], skin_id))
                    self.account_system.conn.commit()
                
                # Переключаемся на новый скин
                self.switch_skin_with_progress(skin_id)
                # Обновляем меню инвентаря
                self.show_inventory_menu()
            except sqlite3.Error as e:
                logging.error(f"Database error buying skin: {e}")
                # Показываем ошибку
                error_menu = pygame_menu.Menu(
                    'Error',
                    self.SCREEN_WIDTH,
                    self.SCREEN_HEIGHT,
                    theme=self.update_menu_theme()
                )
                error_menu.add.label("Purchase failed!", font_color=self.RED)
                error_menu.add.button('Back', self.show_inventory_menu)
                self.menu = error_menu
        else:
            # Нельзя купить
            error_menu = pygame_menu.Menu(
                'Cannot Buy',
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=self.update_menu_theme()
            )
            error_menu.add.label(f"Need {skin['cost']} amethysts!", font_color=self.RED)
            error_menu.add.button('Back', self.show_inventory_menu)
            self.menu = error_menu

    def redeem_promo_from_menu(self):
        """Активация промокода из меню"""
        code = self.promo_input_widget.get_value()
        if code:
            result = self.promo_system.redeem_promo(code)
            # Создаем временный виджет для отображения сообщения
            self.promo_menu.add.label(result, font_color=self.GREEN if "received" in result.lower() else self.RED, label_id="promo_result")
            
            if "received" in result.lower():
                account_data = self.account_system.get_current_account_data()
                self.total_amethysts = account_data.get("amethysts", 0)
                
            

    # ОСНОВНЫЕ МЕТОДЫ ИГРЫ (ОБНОВЛЕННЫЕ)
    # ========================================================================
    def load_available_levels(self):
        """
        УЛУЧШЕННАЯ загрузка списка доступных уровней
        Теперь включает 10 пресет-уровней
        """
        levels = [
            {"name": "Random Generation", "file": "random", "description": "Бесконечная случайная генерация"},
            {"name": "Tutorial", "file": "levels/tutorial.json", "description": "Обучение для новичков"},
            {"name": "Easy Run", "file": "levels/easy.json", "description": "Простой уровень с платформами"},
            {"name": "Platform Paradise", "file": "levels/platforms.json", "description": "Много платформ и прыжков"},
            {"name": "Spike Challenge", "file": "levels/spikes.json", "description": "Сложный уровень с шипами"},
        ]
        
        # Добавляем пользовательские уровни
        custom_levels_folder = "levels"
        if os.path.exists(custom_levels_folder):
            for filename in os.listdir(custom_levels_folder):
                if filename.endswith(".json") and filename not in ["tutorial.json", "easy.json", "platforms.json", "spikes.json"]:
                    level_name = filename.replace(".json", "").replace("_", " ").title()
                    levels.append({
                        "name": f"Custom: {level_name}",
                        "file": f"{custom_levels_folder}/{filename}",
                        "description": "Пользовательский уровень"
                    })
        
        return levels
    
    def show_level_select_menu(self):
        """Показать меню выбора уровня с пресет-уровнями"""
        self.level_select_menu.clear()
        self.level_select_menu.add.label('SELECT LEVEL', font_color=self.GOLD)
        
        # Добавляем стандартные уровни
        for i, level in enumerate(self.available_levels):
            self.level_select_menu.add.button(
                f"{level['name']} - {level['description']}", 
                lambda idx=i: self.start_selected_level(idx)
            )
        
        # Добавляем разделитель
        self.level_select_menu.add.label("─" * 30, font_color=self.WHITE)
        self.level_select_menu.add.label("PRESET LEVELS (1-10)", font_color=self.CYAN)
        
        # Добавляем пресет-уровни
        for i, level in enumerate(self.preset_levels):
            # Проверяем, пройден ли уровень
            is_completed = level["name"] in self.completed_levels
            status = "✓ " if is_completed else ""
            
            self.level_select_menu.add.button(
                f"{status}Level {i+1}: {level['name'].split(': ')[1]}", 
                lambda idx=i: self.start_preset_level(idx)
            )
        
        self.level_select_menu.add.button('Back', self.return_to_main_menu)
        self.state = self.MENU
        self.menu = self.level_select_menu
    
    def start_preset_level(self, index):
        """
        Запуск пресет-уровня
        index: индекс уровня в списке preset_levels
        """
        if 0 <= index < len(self.preset_levels):
            level_data = self.preset_levels[index]
            self.start_game_with_level(level_data)
            self.state = self.PLAYING
            
            # Запоминаем имя уровня для награды опытом
            self.current_level_name = level_data["name"]
    
    def hsv_to_rgb(self, h, s, v):
        """
        Конвертация HSV в RGB цвет
        h: оттенок (0-360)
        s: насыщенность (0-1)
        v: яркость (0-1)
        """
        h = h % 360
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        
        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
            
        return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)
    
    def lerp(self, start, end, t):
        """
        Линейная интерполяция между двумя значениями
        start: начальное значение
        end: конечное значение
        t: коэффициент интерполяции (0-1)
        """
        return start + (end - start) * t
    
    def ease_out_quad(self, x):
        """
        Функция easing для плавных анимаций
        x: входное значение (0-1)
        """
        return 1 - (1 - x) * (1 - x)
    
    def create_gradient_surface(self, width, height, start_color, end_color):
        """
        Создание градиентной поверхности
        width, height: размеры поверхности
        start_color, end_color: начальный и конечный цвета (R, G, B)
        """
        surf = pygame.Surface((width, height))
        
        for y in range(height):
            t = y / height
            r = self.lerp(start_color[0], end_color[0], t)
            g = self.lerp(start_color[1], end_color[1], t)
            b = self.lerp(start_color[2], end_color[2], t)
            
            pygame.draw.line(surf, (int(r), int(g), int(b)), (0, y), (width, y))
        
        return surf
    
    # ========================================================================
    # СИСТЕМА ПРОКАЧКИ СКИНОВ - НОВЫЕ МЕТОДЫ
    # ========================================================================
    
    def calculate_level_exp(self, amethysts_collected, score, custom_levels_completed):
        # Более сбалансированная формула
        base_exp = (amethysts_collected * 15) + (score // 2) + 50
        
        # Бонус за пройденные уровни
        bonus_exp = custom_levels_completed * 25  # 25 опыта за каждый пройденный уровень
        
        total_exp = int(base_exp + bonus_exp)
        
        # Применяем буст опыта если активен
        if self.exp_boost_active:
            total_exp = int(total_exp * 1.2)
            self.exp_boost_timer -= 1
            if self.exp_boost_timer <= 0:
                self.exp_boost_active = False
        
        return max(10, total_exp)  # Минимум 10 опыта
    
    def calculate_level_progress(self):
        if self.enable_random_generation:
            # Для случайной генерации используем стандартную логику
            return min(100, int(self.distance_traveled / 15))
        else:
            # Для кастомных уровней считаем прогресс на основе пройденного пути
            if self.level_end_x > 0 and self.player:
                # Прогресс по расстоянию
                if self.player.x >= self.level_end_x:
                    return 100
                progress = (self.player.x / self.level_end_x) * 100
                return min(100, int(progress))
            # Если level_end_x не установлен, используем дистанцию
            return min(100, int(self.player.x / 50)) if self.player else 0
    
    def award_exp_on_level_complete(self, level_name):
        if not self.player or not hasattr(self.player, 'skin_level'):
            logging.error("Cannot award EXP: player not initialized")
            return
            
        # Отмечаем уровень как пройденный
        if level_name not in self.completed_levels:
            self.completed_levels.append(level_name)
            self.player.add_completed_level()
            
            # Сохраняем статистику
            collected_amethysts = len([a for a in self.amethysts if a.collected])
            self.level_progress[level_name] = {
                "score": self.score,
                "amethysts": collected_amethysts,
                "date": datetime.datetime.now().isoformat()
            }
            
            self.save_level_progress()
        
        # Считаем сколько аметистов собрано в этом уровне
        collected_amethysts = len([a for a in self.amethysts if a.collected])
        
        # Получаем количество пройденных кастомных уровней
        custom_levels_completed = self.get_completed_custom_levels()
        
        # Рассчитываем опыт
        exp_earned = self.calculate_level_exp(
            collected_amethysts,
            self.score,
            custom_levels_completed
        )
        
        logging.info(f"Awarding {exp_earned} EXP for level {level_name}")
        logging.info(f"  Amethysts: {collected_amethysts}, Score: {self.score}")
        
        # Добавляем опыт игроку
        old_level = self.player.skin_level
        self.player.add_exp(exp_earned)
        
        # Сохраняем в БД
        if self.account_system.conn and self.account_system.current_account:
            success = self.account_system.save_skin_progression(
                self.account_system.current_account["id"],
                self.current_skin,
                self.player.skin_level,
                self.player.skin_exp,
                self.player.total_exp,
                self.player.completed_levels
            )
            
            if not success:
                logging.error("Failed to save skin progression to database")
        
        # Показываем сообщение о полученном опыте
        level_up_msg = ""
        if old_level < self.player.skin_level:
            level_up_msg = f" LEVEL UP! {old_level}→{self.player.skin_level}"
        
        self.exp_message = f"+{exp_earned} Square-EXP!{level_up_msg}"
        self.exp_message_timer = 180  # 3 секунды при 60 FPS
        
        # Эффект частиц
        self.particle_system.add_particles(
            self.SCREEN_WIDTH // 2,
            self.SCREEN_HEIGHT // 2,
            self.GOLD,
            count=20,
            speed=2,
            size_variation=5
        )
        
        # Звуковой эффект
        self.play_sound_safe(self.powerup_sound)
        
    def debug_skin_progression(self):
        print("\n=== SKIN PROGRESSION DEBUG ===")
        print(f"Player exists: {self.player is not None}")
        if self.player:
            print(f"Player skin level: {self.player.skin_level}")
            print(f"Player skin EXP: {self.player.skin_exp}")
            print(f"Player total EXP: {self.player.total_exp}")
            print(f"Completed levels: {self.player.completed_levels}")
            
            # Проверка EXP таблицы
            if self.player.skin_level < len(EXP_PER_LEVEL):
                needed = EXP_PER_LEVEL[self.player.skin_level] - EXP_PER_LEVEL[self.player.skin_level - 1]
                current = self.player.skin_exp - EXP_PER_LEVEL[self.player.skin_level - 1]
                print(f"Progress to next level: {current}/{needed} ({current/needed*100:.1f}%)")
        else:
            print("ERROR: Player is None!")
        
        print(f"Current skin: {self.current_skin}")
        print(f"Account logged in: {self.account_system.current_account is not None}")
        print("==============================\n")
        
    def switch_skin_with_progress(self, new_skin_id):
        
        if new_skin_id not in self.skins:
            logging.error(f"Unknown skin: {new_skin_id}")
            return False
        
        # Если игрока нет, просто меняем скин
        if not self.player:
            self.current_skin = new_skin_id
            self.safe_load_skin()
            return True
        
        # 1. Сохраняем прогресс текущего скина
        if self.account_system.current_account and self.account_system.conn:
            try:
                self.account_system.save_skin_progression(
                    self.account_system.current_account["id"],
                    self.current_skin,
                    self.player.skin_level,
                    self.player.skin_exp,
                    self.player.total_exp,
                    self.player.completed_levels
                )
            except Exception as e:
                logging.error(f"Error saving skin progression: {e}")
        
        # 2. Загружаем прогресс нового скина
        old_skin = self.current_skin
        self.current_skin = new_skin_id
        
        if self.account_system.current_account and self.account_system.conn:
            progression = self.account_system.load_skin_progression(
                self.account_system.current_account["id"],
                new_skin_id
            )
            
            if progression:
                self.player.skin_level = progression["level"]
                self.player.skin_exp = progression["exp"]
                self.player.total_exp = progression["total_exp"]
                self.player.completed_levels = progression.get("completed_levels", 0)
                logging.info(f"Loaded progression for skin {new_skin_id}: level {self.player.skin_level}")
            else:
                # Новый скин - начинаем с 1 уровня
                self.player.skin_level = 1
                self.player.skin_exp = 0
                # total_exp и completed_levels сохраняем - это общие показатели игрока
                logging.info(f"New skin {new_skin_id}, starting at level 1")
        
        # 3. Загружаем изображение
        self.safe_load_skin()
        
        logging.info(f"Switched skin from {old_skin} to {new_skin_id}")
        return True
        
    def get_completed_custom_levels(self):
        """
        Получение количества пройденных кастомных уровней
        Возвращает: количество уровней
        """
        if not self.player:
            return 0
        return self.player.completed_levels
    
    def load_level_progress(self):
        """Загрузка прогресса по уровням из файла"""
        try:
            if os.path.exists("level_progress.json"):
                with open("level_progress.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.completed_levels = data.get("completed_levels", [])
                    self.level_progress = data.get("level_progress", {})
                    
                    # Обновляем счетчик у игрока если он существует
                    if self.player:
                        self.player.completed_levels = len([
                            lvl for lvl in self.completed_levels 
                            if lvl.startswith("Custom:") or lvl.startswith("Challenge") or lvl.startswith("Preset")
                        ])
        except Exception as e:
            logging.error(f"Error loading level progress: {e}")
            self.completed_levels = []
            self.level_progress = {}
    
    def save_level_progress(self):
        """Сохранение прогресса по уровням в файл"""
        try:
            data = {
                "completed_levels": self.completed_levels,
                "level_progress": self.level_progress
            }
            
            with open("level_progress.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving level progress: {e}")
            
    # СИСТЕМА 10 ПРЕСЕТ-УРОВНЕЙ - НОВЫЕ МЕТОДЫ
    # ========================================================================
    def generate_preset_levels(self):
        """
        Создание 10 предустановленных уровней разной сложности
        Возвращает: список уровней
        """
        preset_levels = []
        
        # Уровень 1: Обучение
        level1 = {
            "name": "Preset 1: Tutorial",
            "player_start_x": 150,
            "player_start_y": 400,
            "speed": 5,
            "level_end_x": 2000,
            "obstacles": [
                {"x": 500, "y": 450, "w": 60, "h": 100, "type": "spike", "color": [220, 20, 60]},
                {"x": 800, "y": 350, "w": 150, "h": 25, "type": "platform", "color": [70, 130, 180]},
                {"x": 1200, "y": 400, "w": 60, "h": 100, "type": "spike", "color": [220, 20, 60]},
            ],
            "amethysts": [
                {"x": 600, "y": 300, "size": 30},
                {"x": 900, "y": 280, "size": 30},
                {"x": 1400, "y": 300, "size": 30}
            ],
            "random_generation": False
        }
        
        # Уровень 2: Платформенный рай
        level2 = {
            "name": "Preset 2: Platform Paradise",
            "player_start_x": 150,
            "player_start_y": 400,
            "speed": 6,
            "level_end_x": 2500,
            "obstacles": [
                {"x": 400, "y": 380, "w": 120, "h": 20, "type": "platform", "color": [100, 200, 100]},
                {"x": 600, "y": 330, "w": 120, "h": 20, "type": "platform", "color": [100, 200, 100]},
                {"x": 800, "y": 280, "w": 120, "h": 20, "type": "platform", "color": [100, 200, 100]},
                {"x": 1000, "y": 230, "w": 120, "h": 20, "type": "platform", "color": [100, 200, 100]},
                {"x": 1200, "y": 180, "w": 120, "h": 20, "type": "platform", "color": [100, 200, 100]},
                {"x": 1500, "y": 450, "w": 60, "h": 100, "type": "spike", "color": [220, 20, 60]},
            ],
            "amethysts": [
                {"x": 450, "y": 320, "size": 25},
                {"x": 650, "y": 270, "size": 25},
                {"x": 850, "y": 220, "size": 25},
                {"x": 1050, "y": 170, "size": 25},
                {"x": 1250, "y": 120, "size": 25}
            ],
            "random_generation": False
        }
        
        # Уровень 3: Шиповая арена
        level3 = {
            "name": "Preset 3: Spike Arena",
            "player_start_x": 150,
            "player_start_y": 400,
            "speed": 7,
            "level_end_x": 3000,
            "obstacles": [
                {"x": 500, "y": 450, "w": 60, "h": 100, "type": "spike", "color": [255, 50, 50]},
                {"x": 700, "y": 450, "w": 60, "h": 100, "type": "spike", "color": [255, 50, 50]},
                {"x": 900, "y": 450, "w": 60, "h": 100, "type": "spike", "color": [255, 50, 50]},
                {"x": 1100, "y": 450, "w": 60, "h": 100, "type": "spike", "color": [255, 50, 50]},
                {"x": 1300, "y": 350, "w": 200, "h": 25, "type": "platform", "color": [70, 130, 180]},
                {"x": 1600, "y": 450, "w": 60, "h": 100, "type": "spike", "color": [255, 50, 50]},
                {"x": 1800, "y": 450, "w": 60, "h": 100, "type": "spike", "color": [255, 50, 50]},
            ],
            "amethysts": [
                {"x": 1350, "y": 280, "size": 35},
                {"x": 1450, "y": 280, "size": 35}
            ],
            "random_generation": False
        }
        
        # Уровень 4: Прыгучий мир
        level4 = {
            "name": "Preset 4: Bounce World",
            "player_start_x": 150,
            "player_start_y": 400,
            "speed": 6,
            "level_end_x": 2800,
            "obstacles": [
                {"x": 400, "y": 400, "w": 100, "h": 25, "type": "bouncing_platform", "color": [0, 200, 100]},
                {"x": 600, "y": 350, "w": 100, "h": 25, "type": "bouncing_platform", "color": [0, 200, 100]},
                {"x": 800, "y": 300, "w": 100, "h": 25, "type": "bouncing_platform", "color": [0, 200, 100]},
                {"x": 1000, "y": 250, "w": 100, "h": 25, "type": "bouncing_platform", "color": [0, 200, 100]},
                {"x": 1200, "y": 200, "w": 100, "h": 25, "type": "bouncing_platform", "color": [0, 200, 100]},
            ],
            "amethysts": [
                {"x": 450, "y": 320, "size": 30},
                {"x": 650, "y": 270, "size": 30},
                {"x": 850, "y": 220, "size": 30},
                {"x": 1050, "y": 170, "size": 30},
                {"x": 1250, "y": 120, "size": 30}
            ],
            "random_generation": False
        }
        
        # Уровень 5: Исчезающие платформы
        level5 = {
            "name": "Preset 5: Disappearing Act",
            "player_start_x": 150,
            "player_start_y": 400,
            "speed": 7,
            "level_end_x": 3200,
            "obstacles": [
                {"x": 400, "y": 400, "w": 120, "h": 25, "type": "disappearing_platform", "color": [255, 165, 0]},
                {"x": 600, "y": 350, "w": 120, "h": 25, "type": "disappearing_platform", "color": [255, 165, 0]},
                {"x": 800, "y": 300, "w": 120, "h": 25, "type": "disappearing_platform", "color": [255, 165, 0]},
                {"x": 1000, "y": 250, "w": 120, "h": 25, "type": "disappearing_platform", "color": [255, 165, 0]},
                {"x": 1200, "y": 200, "w": 120, "h": 25, "type": "disappearing_platform", "color": [255, 165, 0]},
            ],
            "amethysts": [
                {"x": 460, "y": 320, "size": 35},
                {"x": 660, "y": 270, "size": 35},
                {"x": 860, "y": 220, "size": 35},
                {"x": 1060, "y": 170, "size": 35},
                {"x": 1260, "y": 120, "size": 35}
            ],
            "random_generation": False
        }
        
        # Добавляем первые 5 уровней
        preset_levels.extend([level1, level2, level3, level4, level5])
        
        # Генерация остальных 5 уровней (6-10)
        for i in range(6, 11):
            level = self.generate_random_preset_level(i)
            preset_levels.append(level)
        
        return preset_levels
    
    def generate_random_preset_level(self, level_num):
        """
        Генерация случайного пресет-уровня
        level_num: номер уровня (6-10)
        """
        # Сложность увеличивается с каждым уровнем
        difficulty = min(1.0, (level_num - 1) / 10)
        
        # Определяем длину уровня в зависимости от сложности
        level_length = int(2000 + difficulty * 3000)
        
        level_data = {
            "name": f"Preset {level_num}: Challenge",
            "player_start_x": 150,
            "player_start_y": 400,
            "speed": int(5 + difficulty * 5),  # Скорость от 5 до 10
            "level_end_x": level_length,
            "obstacles": [],
            "amethysts": [],
            "random_generation": False
        }
        
        # Генерация препятствий (количество зависит от сложности)
        num_obstacles = int(8 + difficulty * 12)  # От 8 до 20
        
        for i in range(num_obstacles):
            x = 300 + (i * level_length) // num_obstacles + random.randint(-100, 100)
            
            # Выбор типа препятствия в зависимости от сложности
            rand_type = random.random()
            
            if rand_type < 0.4:  # 40% шипы
                height = random.randint(80, 120)
                level_data["obstacles"].append({
                    "x": x,
                    "y": 500 - height,
                    "w": 60,
                    "h": height,
                    "type": "spike",
                    "color": [220, 20, 60]
                })
            elif rand_type < 0.65:  # 25% платформы
                width = random.randint(100, 200)
                y = random.randint(300, 450)
                level_data["obstacles"].append({
                    "x": x,
                    "y": y,
                    "w": width,
                    "h": 25,
                    "type": "platform",
                    "color": [70, 130, 180]
                })
                
                # Добавляем аметист на платформу с шансом 50%
                if random.random() < 0.5:
                    level_data["amethysts"].append({
                        "x": x + width // 2 - 15,
                        "y": y - 50,
                        "size": random.randint(25, 35)
                    })
            elif rand_type < 0.85:  # 20% прыгучие платформы
                width = random.randint(100, 180)
                y = random.randint(300, 450)
                level_data["obstacles"].append({
                    "x": x,
                    "y": y,
                    "w": width,
                    "h": 25,
                    "type": "bouncing_platform",
                    "color": [0, 200, 100]
                })
            else:  # 15% исчезающие платформы
                width = random.randint(100, 180)
                y = random.randint(300, 450)
                level_data["obstacles"].append({
                    "x": x,
                    "y": y,
                    "w": width,
                    "h": 25,
                    "type": "disappearing_platform",
                    "color": [255, 165, 0]
                })
        
        # Добавляем дополнительные аметисты
        num_amethysts = int(5 + difficulty * 15)  # От 5 до 20
        for i in range(num_amethysts):
            if len(level_data["amethysts"]) >= num_amethysts:
                break
                
            x = random.randint(500, level_data["level_end_x"] - 500)
            y = random.randint(200, 450)
            level_data["amethysts"].append({
                "x": x,
                "y": y,
                "size": random.randint(25, 40)
            })
        
        return level_data
    
    # УЛУЧШЕННАЯ ГЕНЕРАЦИЯ ПРЕПЯТСТВИЙ - НОВЫЕ МЕТОДЫ
    # ========================================================================
    def spawn_random_obstacle(self):
        """
        УЛУЧШЕННАЯ генерация случайных препятствий
        Использует систему весов для разнообразия
        """
        # Веса для разных типов препятствий (сумма = 1.0)
        obstacle_types = [
            ("spike", 0.35),           # 35% - обычные шипы
            ("platform", 0.25),        # 25% - обычные платформы
            ("moving_spike", 0.15),    # 15% - движущиеся шипы
            ("spike_cluster", 0.10),   # 10% - кластер шипов
            ("bouncing_platform", 0.08), # 8% - прыгучие платформы
            ("disappearing_platform", 0.07) # 7% - исчезающие платформы
        ]
        
        # Выбираем тип с учетом весов
        types, weights = zip(*obstacle_types)
        obstacle_type = random.choices(types, weights=weights)[0]
        
        # Спавним выбранный тип
        if obstacle_type == "spike":
            self.spawn_spike()
        elif obstacle_type == "platform":
            self.spawn_platform()
        elif obstacle_type == "moving_spike":
            self.spawn_moving_spike()
        elif obstacle_type == "spike_cluster":
            self.spawn_spike_cluster()
        elif obstacle_type == "bouncing_platform":
            self.spawn_bouncing_platform()
        elif obstacle_type == "disappearing_platform":
            self.spawn_disappearing_platform()
    
    def spawn_spike(self):
        """Спавн обычного шипа"""
        height = random.choice([80, 100, 120, 150])
        spike_color = random.choice([
            (220, 20, 60),    # Красный
            (255, 69, 0),     # Оранжево-красный
            (199, 21, 133),   # Розовый
            (178, 34, 34)     # Огненно-красный
        ])
        
        self.obstacles.append(Obstacle(
            self.SCREEN_WIDTH + 50,
            self.SCREEN_HEIGHT - height,
            "spike",
            60, height,
            spike_color
        ))
    
    def spawn_platform(self):
        """Спавн обычной платформы"""
        width = random.randint(120, 250)
        height = 25
        y_pos = random.randint(300, 450)
        
        platform_color = random.choice([
            (70, 130, 180),   # Стальной синий
            (100, 149, 237),  # Кукурузно-синий
            (30, 144, 255),   # Доджер-синий
            (0, 191, 255)     # Глубокий небесный
        ])
        
        platform = Obstacle(
            self.SCREEN_WIDTH + 50,
            y_pos,
            "platform",
            width, height,
            platform_color
        )
        self.obstacles.append(platform)
        
        # 40% шанс добавить аметист на платформу
        if random.random() < 0.4:
            self.amethysts.append(Amethyst(
                platform.x + width // 2 - 15,
                y_pos - 40,
                size=random.randint(25, 35)
            ))
    
    def spawn_moving_spike(self):
        """Спавн движущегося шипа"""
        height = random.choice([60, 80, 100])
        spike_color = (255, 69, 0)  # Оранжево-красный
        
        spike = Obstacle(
            self.SCREEN_WIDTH + 50,
            self.SCREEN_HEIGHT - height,
            "moving_spike",
            50, height,
            spike_color
        )
        spike.move_speed = random.uniform(1.0, 3.0)
        spike.original_y = spike.y
        self.obstacles.append(spike)
    
    def spawn_spike_cluster(self):
        """Спавн кластера шипов"""
        cluster_width = random.randint(200, 350)
        spike_count = random.randint(3, 6)
        spike_width = cluster_width // spike_count
        
        for i in range(spike_count):
            spike_height = random.choice([70, 90, 110, 130])
            self.obstacles.append(Obstacle(
                self.SCREEN_WIDTH + 50 + i * spike_width,
                self.SCREEN_HEIGHT - spike_height,
                "spike",
                spike_width - 10, spike_height,
                (178, 34, 34)  # Огненно-красный
            ))
    
    def spawn_bouncing_platform(self):
        """Спавн прыгучей платформы"""
        width = random.randint(120, 200)
        height = 25
        y_pos = random.randint(300, 450)
        
        platform = Obstacle(
            self.SCREEN_WIDTH + 50,
            y_pos,
            "bouncing_platform",
            width, height,
            (0, 200, 100)  # Зеленый
        )
        platform.bounce_power = random.uniform(1.3, 1.8)  # Сила отскока
        self.obstacles.append(platform)
        
        # 50% шанс добавить аметист
        if random.random() < 0.5:
            self.amethysts.append(Amethyst(
                platform.x + width // 2 - 15,
                y_pos - 40,
                size=random.randint(25, 35)
            ))
    
    def spawn_disappearing_platform(self):
        """Спавн исчезающей платформы"""
        width = random.randint(100, 180)
        height = 25
        y_pos = random.randint(300, 450)
        
        platform = Obstacle(
            self.SCREEN_WIDTH + 50,
            y_pos,
            "disappearing_platform",
            width, height,
            (255, 165, 0)  # Оранжевый
        )
        platform.disappear_timer = random.randint(45, 90)  # Исчезает через 0.75-1.5 секунды
        platform.visible = True
        self.obstacles.append(platform)
        
        # 60% шанс добавить аметист (рискованно, но награда больше)
        if random.random() < 0.6:
            self.amethysts.append(Amethyst(
                platform.x + width // 2 - 15,
                y_pos - 40,
                size=random.randint(30, 40)  # Большие аметисты
                
            ))
    def handle_collisions(self):
        """
        УЛУЧШЕННАЯ обработка коллизий
        Поддержка новых типов препятствий
        """
        if not self.player:
            return
            
        player_rect = self.player.get_rect()
        
        for obj in self.obstacles:
            # Пропускаем невидимые исчезающие платформы
            if not obj.visible and obj.type == "disappearing_platform":
                continue
                
            obj_rect = obj.get_rect()
            
            if player_rect.colliderect(obj_rect):
                if obj.type in ["spike", "moving_spike"]:
                    self.handle_spike_collision(obj)
                elif obj.type == "platform":
                    self.handle_platform_collision(obj)
                elif obj.type == "bouncing_platform":
                    self.handle_bouncing_platform_collision(obj)
                elif obj.type == "disappearing_platform":
                    self.handle_disappearing_platform_collision(obj)
                elif obj.type == "spike_cluster":
                    self.handle_spike_collision(obj)  # Обрабатываем как обычный шип
    
    def handle_spike_collision(self, spike):
        """Обработка коллизии с шипом"""
        if self.player.invincible:
            return
            
        self.state = self.GAME_OVER
        self.play_sound_safe(self.crash_sound)
        
        # Эффект разрушения с учетом уровня скина
        particle_count = min(50, 30 + self.player.skin_level * 2)
        self.particle_system.add_particles(
            self.player.x + self.player.size//2,
            self.player.y + self.player.size//2,
            self.RED,
            count=particle_count,
            speed=5,
            size_variation=4
        )
    
    def handle_platform_collision(self, platform):
        """Обработка коллизии с платформой"""
        if self.player.vy > 0 and self.player.y < platform.y:
            # Мягкое приземление с буферной зоной
            self.player.y = platform.y - self.player.size
            self.player.vy = 0
            self.player.on_ground = True
            self.player.jumps_left = 2 + (1 if self.player.has_double_jump else 0)
            
            # Визуальный эффект приземления
            self.particle_system.add_particles(
                self.player.x + self.player.size//2,
                self.player.y + self.player.size,
                (150, 150, 255, 180),
                count=5,
                speed=1,
                size_variation=2
            )
    
    def handle_bouncing_platform_collision(self, platform):
        """Обработка коллизии с прыгучей платформой"""
        if self.player.vy > 0:  # Падает вниз
            # Приземление на платформу
            self.player.y = platform.y - self.player.size
            
            # Усиленный отскок с учетом силы платформы
            bounce_strength = self.jump_force * platform.bounce_power
            self.player.vy = bounce_strength
            
            # Сбрасываем состояние прыжков
            self.player.on_ground = False
            self.player.jumps_left = 1 + (1 if self.player.has_double_jump else 0)
            
            # Эффект отскока
            self.particle_system.add_particles(
                self.player.x + self.player.size//2,
                self.player.y + self.player.size,
                (0, 255, 100, 200),
                count=10,
                speed=2,
                size_variation=3
            )
            
            # Звуковой эффект
            self.play_sound_safe(self.powerup_sound)
    
    def handle_disappearing_platform_collision(self, platform):
        """Обработка коллизии с исчезающей платформой"""
        if self.player.vy > 0 and self.player.y < platform.y:
            # Приземление
            self.player.y = platform.y - self.player.size
            self.player.vy = 0
            self.player.on_ground = True
            self.player.jumps_left = 2 + (1 if self.player.has_double_jump else 0)
            
            # Платформа начинает быстро исчезать
            platform.disappear_timer = 20  # Быстрее исчезает при касании
            
            # Визуальный эффект
            self.particle_system.add_particles(
                platform.x + platform.w//2,
                platform.y,
                (255, 165, 0, 150),
                count=8,
                speed=1,
                size_variation=2
            )
    
    def safe_load_skin(self):
        """Безопасная загрузка скина с обработкой ошибок"""
        try:
            if self.current_skin not in self.skins:
                self.current_skin = "cube01"

            filename = self.skins[self.current_skin]["image"]
            path1 = f"game project/skins/{filename}"
            path2 = f"skins/{filename}"

            if os.path.exists(path1):
                img = pygame.image.load(path1).convert_alpha()
            elif os.path.exists(path2):
                img = pygame.image.load(path2).convert_alpha()
            else:
                raise FileNotFoundError(f"Skin file not found: {filename}")

            # Масштабируем с учетом уровня скина (ИСПРАВЛЕНО)
            base_size = 60
            # Безопасная проверка наличия игрока и его уровня
            if self.player and hasattr(self.player, 'skin_level'):
                size_increase = min(20, (self.player.skin_level - 1) * 2)
            else:
                size_increase = 0
            final_size = base_size + size_increase
            
            self.player_image = pygame.transform.scale(img, (final_size, final_size))
            logging.info(f"Skin loaded successfully: {self.current_skin}, size: {final_size}")
        except Exception as e:
            logging.warning(f"Скин не загрузился: {e}")
            self.create_default_skin()
        
    def create_default_skin(self, skin_info=None):
        """Создание стандартного скина если файл не найден"""
        base_size = 60
        size_increase = min(20, (self.player.skin_level - 1) * 2) if self.player else 0
        final_size = base_size + size_increase
        
        surf = pygame.Surface((final_size, final_size), pygame.SRCALPHA)
        
        if skin_info:
            skin_name = skin_info["name"].lower()
            if "gold" in skin_name:
                color = self.GOLD
            elif "diamond" in skin_name:
                color = (185, 242, 255)
            elif "fire" in skin_name:
                color = (255, 69, 0)
            elif "ice" in skin_name:
                color = (173, 216, 230)
            elif "rainbow" in skin_name:
                for i in range(final_size):
                    hue = (i * 6) % 360
                    color = self.hsv_to_rgb(hue, 1.0, 1.0)
                    pygame.draw.line(surf, color, (i, 0), (i, final_size))
                self.player_image = surf
                return
            else:
                color = self.WHITE
        else:
            color = self.WHITE
        
        pygame.draw.rect(surf, color, (0, 0, final_size, final_size))
        pygame.draw.rect(surf, (50, 50, 50), (0, 0, final_size, final_size), 4)
        self.player_image = surf
        
    def load_player_data(self):
        """Загрузка данных игрока после логина"""
        try:
            account_data = self.account_system.get_current_account_data()
            if account_data:
                self.total_amethysts = account_data.get("amethysts", 0)
                self.load_player_skins()
                self.load_player_upgrades()
                
                # Загрузка прогресса прокачки скина (ИСПРАВЛЕНО)
                if self.current_skin and self.account_system.current_account and self.player:
                    progression = self.account_system.load_skin_progression(
                        self.account_system.current_account["id"],
                        self.current_skin
                    )
                    
                    if progression:
                        self.player.skin_level = progression["level"]
                        self.player.skin_exp = progression["exp"]
                        self.player.total_exp = progression["total_exp"]
                        self.player.completed_levels = progression.get("completed_levels", 0)
                        logging.info(f"Loaded skin progression: level {self.player.skin_level}, EXP {self.player.skin_exp}")
                    else:
                        # Если прогресса нет, устанавливаем значения по умолчанию
                        self.player.skin_level = 1
                        self.player.skin_exp = 0
                        self.player.total_exp = 0
                        self.player.completed_levels = 0
                        logging.info(f"No progression found for skin {self.current_skin}, starting fresh")
                
                logging.info(f"Player data loaded for: {account_data['username']}")
        except Exception as e:
            logging.error(f"Error loading player data: {e}")
        
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
            cursor.execute('SELECT skin_id FROM player_skins WHERE player_id = ? AND owned = 1', 
                         (self.account_system.current_account["id"],))
            
            owned_skins = [row[0] for row in cursor.fetchall()]
            
            for skin_id in self.skins:
                if skin_id in owned_skins:
                    self.skins[skin_id]["owned"] = True
                elif skin_id == "cube01":
                    self.skins[skin_id]["owned"] = True
                else:
                    self.skins[skin_id]["owned"] = False
                    
        except sqlite3.Error as e:
            logging.error(f"Error loading player skins: {e}")

    def load_player_upgrades(self):
        """ИСПРАВЛЕНО: Загрузка улучшений игрока"""
        if not self.account_system.current_account:
            return
            
        try:
            cursor = self.account_system.conn.cursor()
            cursor.execute('SELECT upgrade_type FROM player_upgrades WHERE player_id = ?', 
                         (self.account_system.current_account["id"],))
            
            owned_upgrades = [row[0] for row in cursor.fetchall()]
            
            # Сохраняем улучшения для применения при создании игрока
            self.player_upgrades = owned_upgrades
            
            # Применяем улучшения только если игрок существует
            if self.player:
                if 'shield' in owned_upgrades:
                    self.player.has_shield = True
                if 'double_jump' in owned_upgrades:
                    self.player.has_double_jump = True
                    self.player.jumps_left = 3  # Двойной прыжок + обычный
                if 'exp_booster' in owned_upgrades:
                    self.exp_boost_active = True
                    self.exp_boost_timer = 3  # 3 уровня с бустом
                
        except sqlite3.Error as e:
            logging.error(f"Error loading player upgrades: {e}")

    def initialize_new_player_skins(self):
        """Инициализация скинов для нового игрока"""
        if not self.account_system.current_account:
            return
            
        try:
            cursor = self.account_system.conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO player_skins (player_id, skin_id, owned) VALUES (?, "cube01", 1)',
                         (self.account_system.current_account["id"],))
            
            self.account_system.conn.commit()
            self.skins["cube01"]["owned"] = True
            self.current_skin = "cube01"
            self.safe_load_skin()
            
        except sqlite3.Error as e:
            logging.error(f"Error initializing player skins: {e}")
        
    def toggle_fullscreen(self):
        """Переключение полноэкранного режима"""
        self.fullscreen = not self.fullscreen
        try:
            if self.fullscreen:
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                self.screen = pygame.display.set_mode(self.original_size)
            
            self.SCREEN_WIDTH, self.SCREEN_HEIGHT = self.screen.get_size()
            
            # Пересоздаем меню с новым размером
            self.menu_bg_surface = self.create_gradient_menu_bg()
            self.create_menus()
            self.safe_load_skin()
            
        except pygame.error as e:
            logging.error(f"Error switching fullscreen: {e}")
            self.fullscreen = not self.fullscreen  # Откатываем изменение
        
    def load_resources(self):
        """Загрузка всех ресурсов игры"""
        try:
            folders = ["sounds", "skins", "backgrounds", "menu", "levels", "chests"]
            for folder in folders:
                if not os.path.exists(folder):
                    os.makedirs(folder)
                    logging.info(f"Created folder: {folder}")

            # Создаем градиентный фон для меню
            self.menu_bg_surface = self.create_gradient_menu_bg()

            # Звуки
            sound_paths = [
                "sounds/crash.wav", "game project/sounds/crash.wav",
                "sounds/collect.wav", "game project/sounds/collect.wav",
                "sounds/chest_open.wav", "sounds/level_complete.wav",
                "sounds/powerup.wav"
            ]
            
            self.crash_sound = None
            self.collect_sound = None
            self.chest_sound = None
            self.level_complete_sound = None
            self.powerup_sound = None
            
            for path in sound_paths:
                try:
                    if "crash" in path and not self.crash_sound and os.path.exists(path):
                        self.crash_sound = pygame.mixer.Sound(path)
                    elif "collect" in path and not self.collect_sound and os.path.exists(path):
                        self.collect_sound = pygame.mixer.Sound(path)
                    elif "chest" in path and not self.chest_sound and os.path.exists(path):
                        self.chest_sound = pygame.mixer.Sound(path)
                    elif "level_complete" in path and not self.level_complete_sound and os.path.exists(path):
                        self.level_complete_sound = pygame.mixer.Sound(path)
                    elif "powerup" in path and not self.powerup_sound and os.path.exists(path):
                        self.powerup_sound = pygame.mixer.Sound(path)
                except Exception as e:
                    continue

            self.safe_load_skin()
        
            # Загрузка изображений
            image_paths = {
                'menu_bg': ["menu/background.png", "game project/menu/background.png"],
                'amethyst_image': ["skins/amethyst.png", "game project/skins/amethyst.png"],
                'chest_image': ["chestskins/amethystchest.png", "game project/chestskins/amethystchest.png"]
            }
            
            self.menu_bg = None
            self.amethyst_image = None
            self.chest_image = None
            self.game_bg = None
            
            for path in image_paths['menu_bg']:
                try:
                    if os.path.exists(path):
                        self.menu_bg = pygame.image.load(path).convert()
                        self.menu_bg = pygame.transform.scale(self.menu_bg, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
                        break
                except Exception as e:
                    continue
            
            try:
                if os.path.exists("backgrounds/game_bg.png"):
                    self.game_bg = pygame.image.load("backgrounds/game_bg.png").convert()
                    self.game_bg = pygame.transform.scale(self.game_bg, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
            except Exception as e:
                pass
                
            if not self.game_bg:
                self.game_bg = self.create_gradient_bg()
            
            for path in image_paths['amethyst_image']:
                try:
                    if os.path.exists(path):
                        self.amethyst_image = pygame.image.load(path).convert_alpha()
                        self.amethyst_image = pygame.transform.scale(self.amethyst_image, (30, 30))
                        break
                except Exception as e:
                    continue
                    
            for path in image_paths['chest_image']:
                try:
                    if os.path.exists(path):
                        self.chest_image = pygame.image.load(path).convert_alpha()
                        self.chest_image = pygame.transform.scale(self.chest_image, (200, 200))
                        break
                except Exception as e:
                    continue
                    
            if not self.chest_image:
                self.chest_image = self.create_default_chest()
                
        except Exception as e:
            logging.error(f"Error loading resources: {e}")
            # Создаем fallback фон
            self.menu_bg_surface = self.create_gradient_menu_bg()

    def create_default_chest(self):
        """Создание стандартного сундука"""
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        pygame.draw.rect(surf, (139, 69, 19), (50, 100, 100, 60))
        pygame.draw.rect(surf, (160, 82, 45), (50, 80, 100, 30))
        pygame.draw.rect(surf, (255, 215, 0), (70, 85, 60, 20))
        pygame.draw.circle(surf, (255, 215, 0), (100, 95), 8)
        return surf

    def create_gradient_bg(self):
        """Создание градиентного фона"""
        surf = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        for y in range(self.SCREEN_HEIGHT):
            color_value = 20 + int(30 * (y / self.SCREEN_HEIGHT))
            pygame.draw.line(surf, (color_value, color_value, 80), (0, y), (self.SCREEN_WIDTH, y))
        return surf

    def play_sound_safe(self, sound):
        """Безопасное воспроизведение звука"""
        if sound and pygame.mixer.get_init():
            try:
                sound.set_volume(0.3)
                sound.play()
            except pygame.error as e:
                logging.warning(f"Could not play sound: {e}")

    # ОСНОВНЫЕ МЕТОДЫ (без изменений, но сохранены для полноты)
    # ========================================================================
    def handle_events(self):
        """Обработка всех событий игры"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_ESCAPE:
                    self.handle_escape_key()
                elif event.key == pygame.K_TAB and self.state == self.MENU:
                    self.toggle_menu_system()
            
            # Обработка событий pygame-menu
            if (self.state == self.MENU and self.use_pygame_menu and 
                self.menu and self.menu.is_enabled()):
                self.menu.update([event])
                
            # Обработка для старой системы меню
            elif self.state == self.MENU and not self.use_pygame_menu:
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
            elif self.state == self.LEVEL_SELECT:
                self.handle_level_select_events(event)
            elif self.state == self.LEVEL_COMPLETE:
                self.handle_level_complete_events(event)
            elif self.state == self.SKIN_PROGRESSION:
                self.handle_skin_progression_events(event)
                
    def handle_skin_progression_events(self, event):
        """Обработка событий в меню прокачки скинов"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_to_main_menu()

    def handle_escape_key(self):
        """Обработка клавиши ESC в разных состояниях"""
        if self.state == self.PLAYING:
            self.state = self.PAUSED
        elif self.state == self.PAUSED:
            self.state = self.PLAYING
        elif self.state in [self.SHOP, self.INVENTORY, self.LEVEL_SELECT, 
                           self.LOGIN, self.PROMO, self.CHEST, self.LEVEL_COMPLETE]:
            self.return_to_main_menu()
        elif self.state == self.GAME_OVER:
            self.return_to_main_menu()
        elif self.state == self.EDITOR:
            self.return_to_main_menu()

    def return_to_main_menu(self):
        """Возврат в главное меню"""
        self.state = self.MENU
        if self.use_pygame_menu:
            self.menu = self.main_menu
            if self.menu:
                self.menu.enable()
        else:
            self.menu = None

    def handle_menu_events(self, event):
        """События старого меню (если pygame-menu не используется)"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_option = (self.selected_option - 1) % len(self.menu_options)
            elif event.key == pygame.K_DOWN:
                self.selected_option = (self.selected_option + 1) % len(self.menu_options)
            elif event.key == pygame.K_RETURN:
                self.execute_menu_action()
            elif event.key == pygame.K_l:
                self.toggle_login()
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
        """Выполнение действия в старом меню"""
        option = self.menu_options[self.selected_option]
        
        if option == 'Start Game':
            self.start_game()
        elif option == 'Level Select':
            self.state = self.LEVEL_SELECT
            self.selected_level_index = 0
        elif option == 'Level Editor':
            self.start_editor()
        elif option == 'Shop':
            self.state = self.SHOP
            self.selected_shop_item = 0
        elif option == 'Inventory':
            self.state = self.INVENTORY
        elif option == 'Daily Chest':
            self.open_daily_chest()
        elif option == 'Login/Logout':
            self.toggle_login()
        elif option == 'Promo Codes':
            self.state = self.PROMO
            self.promo_input = ""
            self.promo_message = ""
        elif option == 'Settings':
            self.show_settings_menu()
        elif option == 'Exit':
            self.running = False

    def handle_level_select_events(self, event):
        """События выбора уровня"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_to_main_menu()
            elif event.key == pygame.K_UP:
                self.selected_level_index = (self.selected_level_index - 1) % len(self.available_levels)
            elif event.key == pygame.K_DOWN:
                self.selected_level_index = (self.selected_level_index + 1) % len(self.available_levels)
            elif event.key == pygame.K_RETURN:
                self.start_selected_level()
                
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            for i, level in enumerate(self.available_levels):
                level_rect = pygame.Rect(100, 150 + i*80, 600, 70)
                if level_rect.collidepoint(mouse_pos):
                    self.selected_level_index = i
                    if event.button == 1:
                        self.start_selected_level()

    def start_selected_level(self, index=None):
        """Запуск выбранного уровня"""
        if index is None:
            index = self.selected_level_index
            
        selected_level = self.available_levels[index]
        
        if selected_level["file"] == "random":
            self.start_game()
        else:
            self.load_custom_level(selected_level["file"])
        self.state = self.PLAYING

    def load_custom_level(self, filename):
        """Загрузка кастомного уровня"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    level_data = json.load(f)
                self.start_game_with_level(level_data)
            else:
                self.create_default_level(filename)
                
        except Exception as e:
            logging.error(f"Error loading level {filename}: {e}")
            self.create_default_level(filename)

    def create_default_level(self, filename):
        """Создание базового уровня"""
        level_data = {
            "name": "Default Level",
            "player_start_x": 150,
            "player_start_y": 400,
            "speed": 8,
            "level_end_x": 3000,
            "obstacles": [
                {"x": 500, "y": 450, "w": 60, "h": 100, "type": "spike", "color": [220, 20, 60]},
                {"x": 800, "y": 350, "w": 150, "h": 25, "type": "platform", "color": [70, 130, 180]},
            ],
            "amethysts": [
                {"x": 850, "y": 300, "size": 30},
                {"x": 1500, "y": 300, "size": 30}
            ],
            "random_generation": False
        }
        
        try:
            os.makedirs("levels", exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(level_data, f, indent=4, ensure_ascii=False)
            self.start_game_with_level(level_data)
        except Exception as e:
            self.start_game()

    def open_daily_chest(self):
        """Открытие ежедневного сундука"""
        if not self.account_system.current_account:
            self.state = self.LOGIN
            return
            
        today = datetime.datetime.now().date()
        
        try:
            cursor = self.account_system.conn.cursor()
            cursor.execute('SELECT last_chest_date FROM players WHERE username = ?',
                         (self.account_system.current_account['username'],))
            
            result = cursor.fetchone()
            last_date = result[0] if result else None
            
            if last_date:
                last_date = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()
                if last_date == today:
                    self.chest_rewards = [{"type": "message", "text": "You already opened chest today!"}]
                    self.state = self.CHEST
                    return
        except sqlite3.Error as e:
            self.chest_rewards = [{"type": "message", "text": "Database error!"}]
            self.state = self.CHEST
            return
        
        self.generate_chest_rewards()
        self.state = self.CHEST
        self.chest_animation_frame = 0
        
        try:
            cursor.execute('UPDATE players SET last_chest_date = ? WHERE username = ?',
                         (today.strftime('%Y-%m-%d'), self.account_system.current_account['username']))
            self.account_system.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error updating chest date: {e}")
        
        self.play_sound_safe(self.chest_sound)

    def generate_chest_rewards(self):
        """Генерация наград из сундука"""
        rewards = []
        
        try:
            reward_chances = [
                ("amethyst", 10, 50),
                ("amethyst", 25, 30),
                ("amethyst", 50, 15),
                ("skin", None, 5)
            ]
            
            main_reward = random.choices(reward_chances, weights=[chance for _, _, chance in reward_chances])[0]
            reward_type, amount, _ = main_reward
            
            if reward_type == "amethyst":
                rewards.append({"type": "amethyst", "amount": amount})
                self.total_amethysts += amount
                if self.account_system.conn:
                    cursor = self.account_system.conn.cursor()
                    cursor.execute('UPDATE players SET amethysts = amethysts + ? WHERE username = ?',
                                 (amount, self.account_system.current_account['username']))
                    self.account_system.conn.commit()
                    
            elif reward_type == "skin":
                locked_skins = [skin_id for skin_id, skin in self.skins.items() 
                              if not skin["owned"] and not skin["locked"]]
                
                if locked_skins:
                    skin_id = random.choice(locked_skins)
                    self.skins[skin_id]["owned"] = True
                    rewards.append({"type": "skin", "skin_id": skin_id, "name": self.skins[skin_id]["name"]})
                    
                    if self.account_system.conn:
                        cursor = self.account_system.conn.cursor()
                        cursor.execute('INSERT OR REPLACE INTO player_skins (player_id, skin_id, owned) VALUES ((SELECT id FROM players WHERE username = ?), ?, 1)',
                                     (self.account_system.current_account['username'], skin_id))
                        self.account_system.conn.commit()
                else:
                    fallback_amount = 50
                    rewards.append({"type": "amethyst", "amount": fallback_amount})
                    self.total_amethysts += fallback_amount
            
            if random.random() < 0.3:
                bonus_amount = 5
                rewards.append({"type": "amethyst", "amount": bonus_amount})
                self.total_amethysts += bonus_amount
                
        except Exception as e:
            rewards.append({"type": "amethyst", "amount": 10})
            self.total_amethysts += 10
        
        self.chest_rewards = rewards

    def start_game(self):
        """Запуск случайной генерации"""
        if self.menu and self.menu.is_enabled():
            self.menu.disable()
        self.start_game_with_level({
            "player_start_x": 150,
            "player_start_y": 400,
            "speed": 8,
            "level_end_x": 0,
            "obstacles": [],
            "amethysts": [],
            "random_generation": True
        })

    def start_game_with_level(self, level_data):
        """Запуск игры с уровнем"""
        self.state = self.PLAYING
        self.score = 0
        self.base_speed = level_data.get("speed", 8)
        self.game_speed = self.base_speed
        self.camera_x = 0
        self.spawn_timer = 0
        self.percent = 0
        self.distance_traveled = 0
        self.level_complete = False
        self.level_end_x = level_data.get("level_end_x", 5000)

        # Создаем игрока
        self.player = Player(
            level_data.get("player_start_x", 150),
            level_data.get("player_start_y", 400)
        )
        
        # Применяем улучшения
        if hasattr(self, 'account_system') and self.account_system.current_account:
            self.load_player_upgrades()

        # Создаем препятствия
        self.obstacles = []
        for obs_data in level_data.get("obstacles", []):
            obstacle = Obstacle(
                obs_data["x"], 
                obs_data["y"], 
                obs_data["type"],
                obs_data.get("w", 60),
                obs_data.get("h", 60),
                obs_data.get("color", (255, 0, 0))
            )
            if obstacle.type == "moving_spike":
                obstacle.move_speed = obs_data.get("move_speed", 2.0)
                obstacle.move_direction = obs_data.get("move_direction", 1)
                obstacle.original_y = obs_data.get("original_y", obstacle.y)
            self.obstacles.append(obstacle)

        # Создаем аметисты
        self.amethysts = []
        for amethyst_data in level_data.get("amethysts", []):
            self.amethysts.append(Amethyst(
                amethyst_data["x"],
                amethyst_data["y"],
                amethyst_data.get("size", 30)
            ))

        self.enable_random_generation = level_data.get("random_generation", False)

    def handle_game_events(self, event):
        """События во время игры"""
        if event.type == pygame.KEYDOWN and self.player:
            if event.key == pygame.K_SPACE or event.key == pygame.K_UP:
                success, effect_size = self.player.jump(self.jump_force)
                if success:
                    self.particle_system.add_particles(
                        self.player.x + self.player.size//2,
                        self.player.y + self.player.size,
                        (200, 200, 255),
                        count=effect_size,
                        speed=2
                    )
            elif event.key == pygame.K_p:
                self.state = self.PAUSED
            elif event.key == pygame.K_h and self.player.has_shield:
                self.player.activate_shield()
            elif event.key == pygame.K_b:
                self.player.activate_speed_boost()
            elif event.key == pygame.K_F10:
                self.force_complete_level()
            elif event.key == pygame.K_F9:
                self.debug_skin_progression()
            

    def handle_pause_events(self, event):
        """События паузы"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                self.state = self.PLAYING
            elif event.key == pygame.K_m:
                self.return_to_main_menu()

    def handle_shop_events(self, event):
        """События магазина"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_to_main_menu()
            elif event.key == pygame.K_UP:
                self.selected_shop_item = (self.selected_shop_item - 1) % len(self.shop_items)
            elif event.key == pygame.K_DOWN:
                self.selected_shop_item = (self.selected_shop_item + 1) % len(self.shop_items)
            elif event.key == pygame.K_RETURN:
                self.buy_shop_item()
                
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            for i, item in enumerate(self.shop_items):
                item_rect = pygame.Rect(200, 150 + i*100, 400, 80)
                if item_rect.collidepoint(mouse_pos):
                    self.selected_shop_item = i
                    if event.button == 1:
                        self.buy_shop_item()

    def buy_shop_item(self):
        """Покупка товара в магазине"""
        if not self.account_system.current_account:
            self.login_message = "Please login first!"
            self.state = self.LOGIN
            return False
            
        item = self.shop_items[self.selected_shop_item]
        
        if self.total_amethysts < item.cost:
            self.login_message = f"Not enough amethysts! Need {item.cost}"
            return False
            
        try:
            cursor = self.account_system.conn.cursor()
            
            # Проверяем, есть ли уже это улучшение
            cursor.execute('SELECT 1 FROM player_upgrades WHERE player_id = ? AND upgrade_type = ?',
                        (self.account_system.current_account["id"], item.effect_type))
            
            if cursor.fetchone():
                self.login_message = "You already have this upgrade!"
                return False
            
            # Покупаем улучшение
            self.total_amethysts -= item.cost
            cursor.execute('UPDATE players SET amethysts = ? WHERE username = ?',
                        (self.total_amethysts, self.account_system.current_account['username']))
            
            cursor.execute('INSERT INTO player_upgrades (player_id, upgrade_type) VALUES (?, ?)',
                        (self.account_system.current_account["id"], item.effect_type))
            
            self.account_system.conn.commit()
            
            # Применяем улучшение
            if item.effect_type == "shield":
                if self.player:
                    self.player.has_shield = True
            elif item.effect_type == "speed_boost":
                # Это одноразовое улучшение, применяется в игре
                pass
            elif item.effect_type == "double_jump":
                if self.player:
                    self.player.has_double_jump = True
                    self.player.jumps_left = 3
            elif item.effect_type == "exp_booster":
                if self.player:
                    self.exp_boost_active = True
                    self.exp_boost_timer = 3  # 3 уровня с бустом
                
            self.login_message = f"Purchased {item.name}!"
            self.play_sound_safe(self.powerup_sound)
            return True
            
        except sqlite3.Error as e:
            self.login_message = "Database error!"
            logging.error(f"Error buying shop item: {e}")
            return False
        
    def handle_inventory_events(self, event):
        """События инвентаря"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_to_main_menu()
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            skin_keys = list(self.skins.keys())
            skins_per_row = 3
            skin_width = 160
            start_x = (self.SCREEN_WIDTH - (skins_per_row * skin_width)) // 2
            
            for i, skin_id in enumerate(skin_keys):
                row = i // skins_per_row
                col = i % skins_per_row
                x = start_x + col * skin_width
                y = 150 + row * 120
                
                if y > self.SCREEN_HEIGHT - 100:
                    break
                    
                skin_rect = pygame.Rect(x, y, 150, 100)
                if skin_rect.collidepoint(mouse_pos):
                    skin = self.skins[skin_id]
                    if skin["owned"]:
                        self.current_skin = skin_id
                        self.safe_load_skin()
                    elif not skin["locked"]:
                        if self.total_amethysts >= skin["cost"]:
                            self.total_amethysts -= skin["cost"]
                            skin["owned"] = True
                            self.current_skin = skin_id
                            
                            try:
                                cursor = self.account_system.conn.cursor()
                                cursor.execute('UPDATE players SET amethysts = ? WHERE username = ?',
                                             (self.total_amethysts, self.account_system.current_account['username']))
                                cursor.execute('INSERT OR REPLACE INTO player_skins (player_id, skin_id, owned) VALUES ((SELECT id FROM players WHERE username = ?), ?, 1)',
                                             (self.account_system.current_account['username'], skin_id))
                                self.account_system.conn.commit()
                                self.safe_load_skin()
                            except sqlite3.Error as e:
                                logging.error(f"Database error buying skin: {e}")

    def handle_chest_events(self, event):
        """События сундука"""
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            self.return_to_main_menu()

    def handle_level_complete_events(self, event):
        """События завершения уровня"""
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            self.return_to_main_menu()

    def update_game(self):
        if not self.player or not self.player.alive:
            return

        if self.level_complete:
            self.handle_level_complete()
            return

        # Обновление игрока с улучшенной физикой
        self.player.update(self.gravity, self.max_fall_speed, self.air_resistance)

        # Проверка земли с буферной зоной
        GROUND_Y = 500
        GROUND_BUFFER = 8
        
        if self.player.y >= GROUND_Y - GROUND_BUFFER:
            self.player.y = GROUND_Y
            self.player.vy = 0
            
            # Плавное приземление
            if not self.player.on_ground:
                self.player.on_ground = True
                self.player.jumps_left = 2 + (1 if self.player.has_double_jump else 0)
                
                # Эффект приземления
                self.particle_system.add_particles(
                    self.player.x + self.player.size//2,
                    self.player.y + self.player.size,
                    (150, 150, 255),
                    count=5,
                    speed=1
                )

        # Смерть от падения
        if self.player.y > 700:
            self.state = self.GAME_OVER
            self.play_sound_safe(self.crash_sound)
            self.particle_system.add_particles(
                self.player.x + self.player.size//2,
                self.player.y + self.player.size//2,
                self.RED,
                count=30,
                speed=5
            )
            return

        # Проверка завершения уровня
        if not self.enable_random_generation:
            # Обновляем прогресс
            self.percent = self.calculate_level_progress()
            # Проверяем, достигли ли мы 100%
            if self.percent >= 100 and not self.level_complete:
                self.level_complete = True
                self.play_sound_safe(self.level_complete_sound or self.chest_sound)
                self.particle_system.add_particles(
                    self.player.x + self.player.size//2,
                    self.player.y + self.player.size//2,
                    self.GOLD,
                    count=50,
                    speed=4
                )
            
                # Награда за завершение уровня
                completion_bonus = 20
                self.total_amethysts += completion_bonus
                
                # НАГРАЖДАЕМ ОПЫТОМ при завершении уровня
                if hasattr(self, 'current_level_name'):
                    self.award_exp_on_level_complete(self.current_level_name)
                else:
                    self.award_exp_on_level_complete("Unknown Level")
                
                if self.account_system.current_account and self.account_system.conn:
                    try:
                        cursor = self.account_system.conn.cursor()
                        cursor.execute('UPDATE players SET amethysts = amethysts + ? WHERE username = ?',
                                    (completion_bonus, self.account_system.current_account['username']))
                        self.account_system.conn.commit()
                    except sqlite3.Error as e:
                        logging.error(f"Database error updating completion bonus: {e}")

        # Случайная генерация для бесконечного режима
        if self.enable_random_generation:
            # Восстанавливаем базовую скорость если буст закончился
            if self.player.speed_boost_timer == 0 and self.game_speed > self.base_speed:
                self.game_speed = self.base_speed
                
            self.game_speed += self.acceleration_rate
            self.distance_traveled += self.game_speed * 0.1
            
            if self.enable_random_generation:
                self.percent = min(100, int(self.distance_traveled / 15))
        
            self.spawn_timer += 1
            spawn_interval = max(20, 60 - int(self.game_speed * 2))
            
            if self.spawn_timer > spawn_interval:
                self.spawn_timer = 0
                self.spawn_random_obstacle()

        # Обновление объектов
        for obj in self.obstacles[:]:
            obj.update(self.game_speed)
            if obj.is_off_screen():
                self.obstacles.remove(obj)
                self.score += 1

        for amethyst in self.amethysts[:]:
            amethyst.update(self.game_speed)
            if amethyst.is_off_screen():
                self.amethysts.remove(amethyst)

        # Обновление частиц
        self.particle_system.update()

        # Проверка коллизий
        self.handle_collisions()

        # Сбор аметистов
        player_rect = self.player.get_rect()
        for amethyst in self.amethysts[:]:
            if not amethyst.collected:
                if player_rect.colliderect(amethyst.get_rect()):
                    amethyst.collected = True
                    self.total_amethysts += 1
                    self.play_sound_safe(self.collect_sound)
                    
                    # Эффект сбора с учетом уровня скина
                    particle_count = min(20, 10 + self.player.skin_level)
                    self.particle_system.add_particles(
                        amethyst.x + amethyst.size//2,
                        amethyst.y + amethyst.size//2,
                        self.PURPLE,
                        count=particle_count,
                        speed=3
                    )
                    
                    if self.account_system.current_account and self.account_system.conn:
                        try:
                            cursor = self.account_system.conn.cursor()
                            cursor.execute('UPDATE players SET amethysts = amethysts + 1 WHERE username = ?',
                                         (self.account_system.current_account['username'],))
                            self.account_system.conn.commit()
                        except sqlite3.Error as e:
                            logging.error(f"Database error updating amethysts: {e}")

        # Камера
        target_camera_x = self.player.x - 250
        self.camera_x += (target_camera_x - self.camera_x) * 0.1

        # Прогресс для кастомных уровней
        if not self.enable_random_generation:
            progress = min(100, int((self.player.x / self.level_end_x) * 100))
            self.percent = progress

    def handle_level_complete(self):
        """Обработка завершения уровня"""
        # ИСПРАВЛЕНО: Проверка существования игрока
        if self.player:
            self.player.y += 5
            self.player.x += 3
            
            if self.player.y > self.SCREEN_HEIGHT + 100:
                self.show_level_complete_screen()

    def show_level_complete_screen(self):
        """Показ экрана завершения уровня"""
        self.state = self.LEVEL_COMPLETE

    def spawn_random_obstacle(self):
        """Спавн случайного препятствия"""
        obstacle_type = random.choices(
            ["spike", "platform", "moving_spike", "spike_cluster"],
            weights=[0.4, 0.3, 0.2, 0.1]
        )[0]
        
        if obstacle_type == "spike":
            height = random.choice([80, 100, 120, 150])
            self.obstacles.append(Obstacle(
                self.SCREEN_WIDTH + 50,
                self.SCREEN_HEIGHT - height,
                "spike",
                60, height,
                (220, 20, 60)
            ))
            
        elif obstacle_type == "platform":
            width = random.randint(120, 250)
            height = 25
            y_pos = random.randint(300, 450)
            platform = Obstacle(
                self.SCREEN_WIDTH + 50,
                y_pos,
                "platform",
                width, height,
                (70, 130, 180)
            )
            self.obstacles.append(platform)
            
            if random.random() < 0.3:
                self.amethysts.append(Amethyst(
                    platform.x + width // 2 - 15,
                    y_pos - 40
                ))
                
        elif obstacle_type == "moving_spike":
            height = random.choice([60, 80, 100])
            spike = Obstacle(
                self.SCREEN_WIDTH + 50,
                self.SCREEN_HEIGHT - height,
                "moving_spike",
                50, height,
                (255, 69, 0)
            )
            spike.move_speed = random.uniform(1.0, 3.0)
            spike.original_y = spike.y
            self.obstacles.append(spike)
            
        elif obstacle_type == "spike_cluster":
            cluster_width = random.randint(200, 350)
            spike_count = random.randint(3, 6)
            spike_width = cluster_width // spike_count
            
            for i in range(spike_count):
                spike_height = random.choice([70, 90, 110, 130])
                self.obstacles.append(Obstacle(
                    self.SCREEN_WIDTH + 50 + i * spike_width,
                    self.SCREEN_HEIGHT - spike_height,
                    "spike",
                    spike_width - 10, spike_height,
                    (178, 34, 34)
                ))

    # РЕДАКТОР УРОВНЕЙ
    def start_editor(self):
        self.editor_obstacles = []
        self.editor_amethysts = []
        self.editor_selected_type = "spike"
        self.editor_brush_size = 1
        self.editor_grid_snap = True
        self.editor_show_grid = True
        self.editor_camera_x = 0
        self.editor_camera_y = 0
        self.editor_dragging = False
        self.editor_drag_start = (0, 0)
        self.editor_selected_object = None
        self.editor_level_name = "my_level"
        self.editor_message = ""
        self.editor_message_timer = 0
        self.state = self.EDITOR

    def handle_editor_events(self, event):
        mx, my = pygame.mouse.get_pos()
        wx = mx + self.editor_camera_x
        wy = my + self.editor_camera_y

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                clicked = None
                for obj in self.editor_obstacles:
                    obj_rect = self.get_editor_object_rect(obj)
                    if obj_rect.collidepoint(mx, my):
                        clicked = obj
                        break

                if clicked:
                    self.editor_selected_object = clicked
                    self.editor_dragging = True
                    self.editor_drag_start = (mx, my)
                else:
                    if self.editor_grid_snap:
                        wx = round(wx / 40) * 40
                        wy = round(wy / 40) * 40

                    obj = Obstacle(wx, wy, self.editor_selected_type)
                    if self.editor_selected_type == "spike":
                        obj.w = 60
                        obj.h = 80
                        obj.color = (220, 20, 60)
                    elif self.editor_selected_type == "platform":
                        obj.w = 120
                        obj.h = 25
                        obj.color = (70, 130, 180)
                    elif self.editor_selected_type == "moving_spike":
                        obj.w = 50
                        obj.h = 80
                        obj.color = (255, 69, 0)
                        obj.move_speed = 2.0
                        obj.original_y = wy
                    
                    self.editor_obstacles.append(obj)
                    self.editor_selected_object = obj

            elif event.button == 3:
                for i in range(len(self.editor_obstacles)-1, -1, -1):
                    obj = self.editor_obstacles[i]
                    obj_rect = self.get_editor_object_rect(obj)
                    if obj_rect.collidepoint(mx, my):
                        if self.editor_selected_object == obj:
                            self.editor_selected_object = None
                        del self.editor_obstacles[i]
                        break

            elif event.button == 4: 
                self.editor_brush_size = min(8, self.editor_brush_size + 1)
            elif event.button == 5: 
                self.editor_brush_size = max(1, self.editor_brush_size - 1)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.editor_dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.editor_dragging and self.editor_selected_object:
                dx = mx - self.editor_drag_start[0]
                dy = my - self.editor_drag_start[1]
                if self.editor_grid_snap:
                    dx = round(dx / 40) * 40
                    dy = round(dy / 40) * 40
                self.editor_selected_object.x += dx
                self.editor_selected_object.y += dy
                if self.editor_selected_object.type == "moving_spike":
                    self.editor_selected_object.original_y = self.editor_selected_object.y
                self.editor_drag_start = (mx, my)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_to_main_menu()
            elif event.key == pygame.K_g:
                self.editor_grid_snap = not self.editor_grid_snap
            elif event.key == pygame.K_h:
                self.editor_show_grid = not self.editor_show_grid
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self.editor_selected_type = "spike"
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.editor_selected_type = "platform"
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self.editor_selected_type = "moving_spike"
            elif event.key == pygame.K_DELETE and self.editor_selected_object:
                self.editor_obstacles.remove(self.editor_selected_object)
                self.editor_selected_object = None
            elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                self.save_level()
            elif event.key == pygame.K_l and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                self.load_level()
            elif event.key == pygame.K_a:
                if self.editor_grid_snap:
                    wx = round(wx / 40) * 40
                    wy = round(wy / 40) * 40
                self.editor_amethysts.append(Amethyst(wx, wy))
            elif event.key == pygame.K_c:
                self.editor_obstacles = []
                self.editor_amethysts = []
                self.editor_selected_object = None

        if event.type == pygame.MOUSEBUTTONDOWN and pygame.key.get_mods() & pygame.KMOD_SHIFT:
            if event.button == 4:
                self.editor_camera_y -= 80
            elif event.button == 5:
                self.editor_camera_y += 80

    def get_editor_object_rect(self, obj):
        x = obj.x - self.editor_camera_x
        y = obj.y - self.editor_camera_y
        return pygame.Rect(x, y, obj.w, obj.h)

    def draw_editor(self):
        self.screen.fill((15, 15, 35))

        if self.editor_show_grid:
            grid = 40
            offset_x = self.editor_camera_x % grid
            offset_y = self.editor_camera_y % grid
            for x in range(offset_x, self.SCREEN_WIDTH, grid):
                pygame.draw.line(self.screen, (60, 60, 80), (x, 0), (x, self.SCREEN_HEIGHT))
            for y in range(offset_y, self.SCREEN_HEIGHT, grid):
                pygame.draw.line(self.screen, (60, 60, 80), (0, y), (self.SCREEN_WIDTH, y))

        for obj in self.editor_obstacles:
            x = obj.x - self.editor_camera_x
            y = obj.y - self.editor_camera_y

            if -100 < x < self.SCREEN_WIDTH + 100 and -100 < y < self.SCREEN_HEIGHT + 100:
                if obj.type == "spike":
                    points = [(x+20, y+60), (x+40, y), (x+60, y+60)]
                    color = (255, 80, 80) if obj == self.editor_selected_object else self.RED
                    pygame.draw.polygon(self.screen, color, points)
                    pygame.draw.polygon(self.screen, self.WHITE, points, 2)

                elif obj.type == "platform":
                    rect = (x, y, obj.w, obj.h)
                    color = self.GOLD if obj == self.editor_selected_object else (200, 160, 40)
                    pygame.draw.rect(self.screen, color, rect)
                    pygame.draw.rect(self.screen, self.WHITE, rect, 3)

                elif obj.type == "moving_spike":
                    points = [(x+20, y+60), (x+40, y), (x+60, y+60)]
                    color = (255, 140, 0) if obj == self.editor_selected_object else (255, 100, 0)
                    pygame.draw.polygon(self.screen, color, points)
                    pygame.draw.polygon(self.screen, self.WHITE, points, 2)

        for amethyst in self.editor_amethysts:
            x = amethyst.x - self.editor_camera_x
            y = amethyst.y - self.editor_camera_y
            if -50 < x < self.SCREEN_WIDTH + 50:
                pygame.draw.circle(self.screen, self.PURPLE, (int(x + 15), int(y + 15)), 15)
                pygame.draw.circle(self.screen, self.WHITE, (int(x + 15), int(y + 15)), 15, 2)

        if self.editor_selected_object:
            sx = self.editor_selected_object.x - self.editor_camera_x
            sy = self.editor_selected_object.y - self.editor_camera_y
            if self.editor_selected_object.type == "platform":
                sx += self.editor_selected_object.w // 2
                sy += self.editor_selected_object.h // 2
            else:
                sx += 40
                sy += 30
            pygame.draw.circle(self.screen, self.CYAN, (int(sx), int(sy)), 50, 3)

        lines = [
            "LEVEL EDITOR PRO",
            f"Объектов: {len(self.editor_obstacles)} | Аметистов: {len(self.editor_amethysts)} | Тип: {self.editor_selected_type.upper()}",
            f"Сетка: {'ВКЛ' if self.editor_grid_snap else 'ВЫКЛ'} (G) | Показывать: {'ВКЛ' if self.editor_show_grid else 'ВЫКЛ'} (H)",
            "1/2/3 — смена типа | A — добавить аметист | ЛКМ — поставить/выбрать | ПКМ — удалить",
            "DEL — удалить выбранный | C — очистить | Ctrl+S — сохранить | Ctrl+L — загрузить",
            "Shift+Колёсико — прокрутка | ESC — выход"
        ]
        
        for i, text in enumerate(lines):
            color = self.CYAN if i == 0 else self.WHITE
            surf = self.small_font.render(text, True, color)
            self.screen.blit(surf, (10, 10 + i*25))

        if self.editor_message and self.editor_message_timer > 0:
            msg_surf = self.font.render(self.editor_message, True, self.GREEN)
            self.screen.blit(msg_surf, (self.SCREEN_WIDTH//2 - msg_surf.get_width()//2, self.SCREEN_HEIGHT - 50))

    def save_level(self):
        try:
            os.makedirs("levels", exist_ok=True)
            name = self.editor_level_name.strip() or "custom_level"
            filename = f"levels/{name}.json"
            
            counter = 1
            original_filename = filename
            while os.path.exists(filename):
                filename = f"levels/{name}_{counter}.json"
                counter += 1
            
            # Конвертируем объекты в словари для сохранения
            obstacles_data = []
            for obj in self.editor_obstacles:
                obj_data = {
                    "x": obj.x, "y": obj.y, "type": obj.type,
                    "w": obj.w, "h": obj.h, "color": obj.color
                }
                if obj.type == "moving_spike":
                    obj_data.update({
                        "move_speed": obj.move_speed,
                        "move_direction": obj.move_direction,
                        "original_y": obj.original_y
                    })
                obstacles_data.append(obj_data)
                
            amethysts_data = [{"x": a.x, "y": a.y, "size": a.size} for a in self.editor_amethysts]
            
            level_data = {
                "name": name,
                "player_start_x": 150,
                "player_start_y": 400,
                "speed": 8,
                "level_end_x": 3000,
                "obstacles": obstacles_data,
                "amethysts": amethysts_data,
                "random_generation": False
            }
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(level_data, f, indent=4, ensure_ascii=False)
            
            self.available_levels = self.load_available_levels()
            self.editor_message = f"Уровень сохранен: {os.path.basename(filename)}"
            self.editor_message_timer = 180
            
        except Exception as e:
            self.editor_message = f"Ошибка сохранения: {e}"
            self.editor_message_timer = 180

    def load_level(self):
        try:
            filename = f"levels/{self.editor_level_name}.json"
            if not os.path.exists(filename):
                files = [f for f in os.listdir("levels") if f.endswith(".json")]
                if files:
                    filename = f"levels/{files[0]}"
                else:
                    self.editor_message = "Нет сохраненных уровней"
                    self.editor_message_timer = 180
                    return
            
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Конвертируем словари обратно в объекты
            self.editor_obstacles = []
            for obs_data in data.get("obstacles", []):
                obj = Obstacle(obs_data["x"], obs_data["y"], obs_data["type"])
                obj.w = obs_data.get("w", 60)
                obj.h = obs_data.get("h", 60)
                obj.color = obs_data.get("color", (255, 0, 0))
                if obj.type == "moving_spike":
                    obj.move_speed = obs_data.get("move_speed", 2.0)
                    obj.move_direction = obs_data.get("move_direction", 1)
                    obj.original_y = obs_data.get("original_y", obj.y)
                self.editor_obstacles.append(obj)
                
            self.editor_amethysts = []
            for amethyst_data in data.get("amethysts", []):
                self.editor_amethysts.append(Amethyst(
                    amethyst_data["x"],
                    amethyst_data["y"],
                    amethyst_data.get("size", 30)
                ))
                
            self.editor_level_name = data.get("name", "my_level")
            self.editor_message = f"Уровень загружен: {os.path.basename(filename)}"
            self.editor_message_timer = 180
            
        except Exception as e:
            self.editor_message = f"Ошибка загрузки: {e}"
            self.editor_message_timer = 180

    # УЛУЧШЕННАЯ ОТРИСОВКА
    # ========================================================================
    def draw_game(self):
        # ФОН с параллакс-эффектом
        parallax_offset = self.camera_x * 0.3 % self.SCREEN_WIDTH
        for i in range(self.SCREEN_HEIGHT):
            color_value = 10 + int(40 * (i / self.SCREEN_HEIGHT))
            base_color = (color_value, color_value, 60 + color_value)
            
            # Добавляем параллакс полосы
            if int(i / 20) % 2 == 0:
                stripe_color = (color_value + 10, color_value + 10, 70 + color_value)
            else:
                stripe_color = base_color
            
            pygame.draw.line(self.screen, stripe_color, 
                           (0 - parallax_offset, i), 
                           (self.SCREEN_WIDTH - parallax_offset, i))
            pygame.draw.line(self.screen, stripe_color, 
                           (self.SCREEN_WIDTH - parallax_offset, i), 
                           (self.SCREEN_WIDTH * 2 - parallax_offset, i))

        # ЗЕМЛЯ с текстурой
        for i in range(0, self.SCREEN_WIDTH, 40):
            color_variation = random.randint(-10, 10)
            ground_color = (50 + color_variation, 50 + color_variation, 90 + color_variation)
            pygame.draw.rect(self.screen, ground_color, (i, 550, 40, 50))
            pygame.draw.line(self.screen, (70, 70, 110), (i, 550), (i, 600), 2)

        # ФИНИШНЫЙ ПОРТАЛ с улучшенной анимацией
        if not self.enable_random_generation:
            portal_x = self.level_end_x - self.camera_x
            if -100 < portal_x < self.SCREEN_WIDTH + 100:
                time_ms = pygame.time.get_ticks()
                pulse = math.sin(time_ms * 0.01) * 15 + math.sin(time_ms * 0.005) * 8
                portal_width = 100 + pulse
                portal_rect = pygame.Rect(portal_x, 300, portal_width, 200)
                
                # Многослойный портал
                for layer in range(3):
                    layer_offset = layer * 20
                    for i in range(200):
                        color_value = int(128 + 127 * math.sin(i * 0.1 + time_ms * 0.005 + layer * 0.5))
                        alpha = 255 - layer * 80
                        color = (color_value, 0, color_value, alpha)
                        
                        # Создаем поверхность с альфа-каналом
                        line_surf = pygame.Surface((portal_width, 1), pygame.SRCALPHA)
                        line_surf.fill(color)
                        self.screen.blit(line_surf, (portal_x, 300 + i + layer_offset))
                
                pygame.draw.rect(self.screen, self.GOLD, portal_rect, 6)
                
                if portal_x < self.SCREEN_WIDTH - 100:
                    finish_text = self.font.render("FINISH", True, self.GOLD)
                    text_shadow = self.font.render("FINISH", True, (0, 0, 0, 128))
                    
                    # Тень текста
                    self.screen.blit(text_shadow, (portal_x + 12, 272))
                    self.screen.blit(finish_text, (portal_x + 10, 270))
                    
        # ФИНИШНАЯ ЛИНИЯ для кастомных уровней
        if not self.enable_random_generation and self.level_end_x > 0:
            finish_x = self.level_end_x - self.camera_x
            if -100 < finish_x < self.SCREEN_WIDTH + 100:
                # Анимированная финишная линия
                pulse = math.sin(pygame.time.get_ticks() * 0.01) * 10
                pygame.draw.line(self.screen, self.GOLD,
                            (finish_x, 100),
                            (finish_x, 500), 6 + int(pulse))
                
                # Текст "SQUARE COMPLETE"
                if finish_x < self.SCREEN_WIDTH - 50:
                    finish_text = self.font.render("SQUARE COMPLETE", True, self.GOLD)
                    text_rect = finish_text.get_rect(center=(finish_x + 50, 80))
                    self.screen.blit(finish_text, text_rect)

        # ПРЕПЯТСТВИЯ с улучшенной графикой
        for obj in self.obstacles:
            x = obj.x - self.camera_x
            if -100 < x < self.SCREEN_WIDTH + 100:
                if obj.type == "spike":
                    # Шипы с градиентом
                    points = [(x + obj.w//2, obj.y), (x, obj.y + obj.h), (x + obj.w, obj.y + obj.h)]
                    pygame.draw.polygon(self.screen, obj.color, points)
                    
                    # Внутренний градиент
                    for i in range(obj.h // 2):
                        shade = int(150 * (i / (obj.h // 2)))
                        inner_color = (min(255, obj.color[0] + shade), 
                                      max(0, obj.color[1] - shade), 
                                      max(0, obj.color[2] - shade))
                        inner_points = [
                            (x + obj.w//2, obj.y + i),
                            (x + i * obj.w//obj.h, obj.y + obj.h - i),
                            (x + obj.w - i * obj.w//obj.h, obj.y + obj.h - i)
                        ]
                        pygame.draw.polygon(self.screen, inner_color, inner_points)
                    
                    pygame.draw.polygon(self.screen, (150, 0, 0), points, 3)
                    
                elif obj.type == "moving_spike":
                    points = [(x + obj.w//2, obj.y), (x, obj.y + obj.h), (x + obj.w, obj.y + obj.h)]
                    pygame.draw.polygon(self.screen, obj.color, points)
                    pygame.draw.polygon(self.screen, (200, 50, 0), points, 3)
                    
                elif obj.type == "platform":
                    # Платформы с текстурой
                    pygame.draw.rect(self.screen, obj.color, (x, obj.y, obj.w, obj.h))
                    
                    # Текстура платформы
                    for i in range(0, obj.w, 10):
                        line_color = (40, 80, 120) if i % 20 == 0 else (60, 100, 140)
                        pygame.draw.line(self.screen, line_color, 
                                       (x + i, obj.y), 
                                       (x + i, obj.y + obj.h), 2)
                    
                    pygame.draw.rect(self.screen, (40, 80, 120), (x, obj.y, obj.w, obj.h), 3)
                    
                elif obj.type == "bouncing_platform":
                    # Прыгучие платформы с анимацией
                    pulse = math.sin(pygame.time.get_ticks() * 0.02) * 3
                    pygame.draw.rect(self.screen, obj.color, 
                                   (x, obj.y + pulse, obj.w, obj.h))
                    
                    # Эффект отскока
                    bounce_lines = int(obj.bounce_power * 5)
                    for i in range(bounce_lines):
                        line_y = obj.y + obj.h + i * 3
                        alpha = 255 - i * 40
                        line_surf = pygame.Surface((obj.w, 1), pygame.SRCALPHA)
                        line_surf.fill((0, 255, 100, alpha))
                        self.screen.blit(line_surf, (x, line_y))
                    
                    pygame.draw.rect(self.screen, (0, 150, 50), 
                                   (x, obj.y + pulse, obj.w, obj.h), 3)
                    
                elif obj.type == "disappearing_platform":
                    # Исчезающие платформы с мерцанием
                    if obj.visible:
                        alpha = max(100, min(255, obj.disappear_timer * 4))
                        platform_surf = pygame.Surface((obj.w, obj.h), pygame.SRCALPHA)
                        pygame.draw.rect(platform_surf, (*obj.color, alpha), (0, 0, obj.w, obj.h))
                        self.screen.blit(platform_surf, (x, obj.y))
                        
                        # Мерцание при исчезновении
                        if obj.disappear_timer < 30:
                            blink = math.sin(pygame.time.get_ticks() * 0.1) > 0
                            if blink:
                                pygame.draw.rect(self.screen, (255, 255, 255, 100), 
                                               (x, obj.y, obj.w, obj.h), 2)
                        
                        pygame.draw.rect(self.screen, (200, 100, 0), 
                                       (x, obj.y, obj.w, obj.h), 3)

        # АМЕТИСТЫ с улучшенной анимацией
        for amethyst in self.amethysts:
            if not amethyst.collected:
                x = amethyst.x - self.camera_x
                if -50 < x < self.SCREEN_WIDTH + 50:
                    # Плавающая анимация
                    float_y = amethyst.get_float_y()
                    current_size = amethyst.get_current_size()
                    
                    if self.amethyst_image:
                        # Вращающийся аметист
                        rotated_image = pygame.transform.rotate(self.amethyst_image, amethyst.rotation)
                        scaled_size = int(current_size * 1.5)
                        scaled_image = pygame.transform.scale(rotated_image, (scaled_size, scaled_size))
                        
                        # Свечение
                        glow_size = int(scaled_size * 1.3)
                        glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                        pygame.draw.circle(glow_surf, (148, 0, 211, 100), 
                                         (glow_size//2, glow_size//2), glow_size//2)
                        self.screen.blit(glow_surf, 
                                       (x - (glow_size - scaled_size)//2 + 15, 
                                        float_y - (glow_size - scaled_size)//2 + 15))
                        
                        self.screen.blit(scaled_image, 
                                       (x - (scaled_size - amethyst.size)//2 + 15, 
                                        float_y - (scaled_size - amethyst.size)//2 + 15))
                    else:
                        # Запасной вариант рисования
                        pygame.draw.circle(self.screen, (148, 0, 211), 
                                         (int(x + 15), int(float_y + 15)), int(current_size//2))
                        pygame.draw.circle(self.screen, (255, 255, 255), 
                                         (int(x + 15), int(float_y + 15)), int(current_size//2), 2)

        # ИГРОК с улучшенной графикой
        if self.player:
            px = self.player.x - self.camera_x
            py = self.player.y
            
            # Эффект щита с анимацией
            if self.player.invincible:
                shield_radius = self.player.size + 5 + math.sin(pygame.time.get_ticks() * 0.05) * 3
                shield_surf = pygame.Surface((shield_radius*2, shield_radius*2), pygame.SRCALPHA)
                
                # Концентрические круги щита
                for i in range(3):
                    radius = shield_radius - i * 3
                    alpha = 100 - i * 30
                    pygame.draw.circle(shield_surf, (0, 255, 255, alpha), 
                                     (shield_radius, shield_radius), radius, 2)
                
                self.screen.blit(shield_surf, (px - shield_radius + self.player.size//2, 
                                             py - shield_radius + self.player.size//2))
            
            # Тень под игроком
            if not self.player.on_ground:
                shadow_size = max(20, 40 - abs(self.player.vy) * 2)
                shadow_alpha = max(50, 150 - abs(self.player.vy) * 10)
                shadow_surf = pygame.Surface((shadow_size, 10), pygame.SRCALPHA)
                shadow_surf.fill((0, 0, 0, shadow_alpha))
                self.screen.blit(shadow_surf, 
                               (px + (self.player.size - shadow_size)//2, 560))
            
            # Отображение игрока с учетом уровня скина
            if self.player_image:
                # Эффект свечения для высоких уровней
                if self.player.skin_level >= 10:
                    glow_size = self.player.size + 10
                    glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                    glow_color = self.hsv_to_rgb((self.player.skin_level * 30) % 360, 0.7, 1.0)
                    pygame.draw.circle(glow_surf, (*glow_color, 100), 
                                     (glow_size//2, glow_size//2), glow_size//2)
                    self.screen.blit(glow_surf, (px - 5, py - 5))
                
                self.screen.blit(self.player_image, (px, py))
            else:
                pygame.draw.rect(self.screen, self.WHITE, 
                               (px, py, self.player.size, self.player.size))
                pygame.draw.rect(self.screen, (150, 150, 150), 
                               (px, py, self.player.size, self.player.size), 4)
            
            # Индикатор прыжков
            if self.player.jumps_left > 0:
                jump_indicator_size = 10
                for i in range(self.player.jumps_left):
                    indicator_x = px + i * (jump_indicator_size + 5)
                    indicator_y = py - 20
                    pygame.draw.circle(self.screen, self.GREEN, 
                                     (int(indicator_x + jump_indicator_size//2), 
                                      int(indicator_y + jump_indicator_size//2)), 
                                     jump_indicator_size//2)

        # ИНТЕРФЕЙС с информацией о прокачке
        percent_text = self.title_font.render(f"{self.percent}%", True, self.GOLD)
        percent_rect = percent_text.get_rect(center=(self.SCREEN_WIDTH//2, 30))
        
        # Фон для процентов
        pygame.draw.rect(self.screen, (0, 0, 0, 180), 
                        (percent_rect.x - 15, percent_rect.y - 10, 
                         percent_rect.width + 30, percent_rect.height + 20), 
                        border_radius=10)
        self.screen.blit(percent_text, percent_rect)
        
        # Прогресс бар уровня
        progress_width = 300
        pygame.draw.rect(self.screen, (50, 50, 50), 
                        (self.SCREEN_WIDTH//2 - progress_width//2, 70, progress_width, 12),
                        border_radius=6)
        pygame.draw.rect(self.screen, self.GOLD, 
                        (self.SCREEN_WIDTH//2 - progress_width//2, 70, 
                         progress_width * self.percent / 100, 12),
                        border_radius=6)

        # Статистика слева
        score_text = self.small_font.render(f"Score: {self.score}", True, self.WHITE)
        speed_text = self.small_font.render(f"Speed: {int(self.game_speed)}", True, self.WHITE)
        amethyst_text = self.small_font.render(f"Amethysts: {self.total_amethysts}", True, self.PURPLE)
        
        self.screen.blit(score_text, (20, 20))
        self.screen.blit(speed_text, (20, 50))
        self.screen.blit(amethyst_text, (20, 80))
        
        # Информация о прокачке скина справа
        if self.player:
            # Уровень и опыт
            level_text = self.small_font.render(f"Lvl {self.player.skin_level}", True, self.GOLD)
            exp_text = self.small_font.render(f"EXP: {self.player.skin_exp}", True, self.PURPLE)
            
            self.screen.blit(level_text, (self.SCREEN_WIDTH - 120, 20))
            self.screen.blit(exp_text, (self.SCREEN_WIDTH - 120, 50))
            
            # Прогресс бар опыта
            progress = self.player.get_exp_percentage()
            bar_width = 100
            bar_height = 8
            bar_x = self.SCREEN_WIDTH - bar_width - 30
            bar_y = 80
            
            # Фон прогресс бара
            pygame.draw.rect(self.screen, (50, 50, 50), 
                            (bar_x, bar_y, bar_width, bar_height),
                            border_radius=4)
            
            # Заполненная часть
            filled_width = int(bar_width * progress / 100)
            pygame.draw.rect(self.screen, self.GREEN, 
                            (bar_x, bar_y, filled_width, bar_height),
                            border_radius=4)
            
            # Граница
            pygame.draw.rect(self.screen, self.WHITE, 
                            (bar_x, bar_y, bar_width, bar_height), 1,
                            border_radius=4)
            
            # Процент текстом
            percent_text = f"{progress:.0f}%"
            percent_surf = self.tiny_font.render(percent_text, True, self.WHITE)
            self.screen.blit(percent_surf, (bar_x + bar_width + 5, bar_y - 3))
            
            # Индикатор буста опыта
            if self.exp_boost_active:
                boost_text = self.tiny_font.render("EXP+20%", True, self.LIME)
                self.screen.blit(boost_text, (self.SCREEN_WIDTH - 80, 95))

        # Улучшения игрока
        if self.player:
            upgrades_text = []
            if self.player.has_double_jump:
                upgrades_text.append("DJ")
            if self.player.has_shield:
                upgrades_text.append("SH")
            if self.player.speed_boost_timer > 0:
                upgrades_text.append("SP")
            if self.player.invincible:
                upgrades_text.append("INV")
                
            if upgrades_text:
                upgrades_display = self.small_font.render("Upgrades: " + ", ".join(upgrades_text), True, self.CYAN)
                self.screen.blit(upgrades_display, (20, 110))

        # Сообщение о полученном опыте
        if self.exp_message and self.exp_message_timer > 0:
            alpha = min(255, self.exp_message_timer * 2)
            exp_surf = self.font.render(self.exp_message, True, self.GOLD)
            exp_surf.set_alpha(alpha)
            
            # Тень сообщения
            shadow_surf = self.font.render(self.exp_message, True, (0, 0, 0, alpha//2))
            shadow_rect = shadow_surf.get_rect(center=(self.SCREEN_WIDTH//2 + 2, 102))
            self.screen.blit(shadow_surf, shadow_rect)
            
            exp_rect = exp_surf.get_rect(center=(self.SCREEN_WIDTH//2, 100))
            self.screen.blit(exp_surf, exp_rect)
        
        # Управление
        controls_text = self.small_font.render("SPACE: Jump | H: Shield | B: Boost | P: Pause", True, self.WHITE)
        controls_shadow = self.small_font.render("SPACE: Jump | H: Shield | B: Boost | P: Pause", True, (0, 0, 0, 128))
        
        # Тень текста управления
        self.screen.blit(controls_shadow, 
                        (self.SCREEN_WIDTH//2 - controls_text.get_width()//2 + 1, 
                         self.SCREEN_HEIGHT - 29))
        
        self.screen.blit(controls_text, 
                        (self.SCREEN_WIDTH//2 - controls_text.get_width()//2, 
                         self.SCREEN_HEIGHT - 30))
        
        # Экран завершения уровня
        if self.level_complete:
            overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
            
            complete_text = self.title_font.render("LEVEL COMPLETE!", True, self.GOLD)
            text_shadow = self.title_font.render("LEVEL COMPLETE!", True, (0, 0, 0, 128))
            
            # Тень текста
            self.screen.blit(text_shadow, 
                           (self.SCREEN_WIDTH//2 - complete_text.get_width()//2 + 3, 
                            self.SCREEN_HEIGHT//2 - complete_text.get_height()//2 + 3))
            
            self.screen.blit(complete_text, 
                           (self.SCREEN_WIDTH//2 - complete_text.get_width()//2, 
                            self.SCREEN_HEIGHT//2 - complete_text.get_height()//2))
            
            # Дополнительная информация
            if hasattr(self, 'exp_message') and self.exp_message:
                bonus_text = self.font.render(self.exp_message, True, self.PURPLE)
                self.screen.blit(bonus_text, 
                               (self.SCREEN_WIDTH//2 - bonus_text.get_width()//2, 
                                self.SCREEN_HEIGHT//2 + 50))
                
    def force_complete_level(self):
        if not self.level_complete and self.player:
            self.level_complete = True
            self.percent = 100
            if hasattr(self, 'current_level_name'):
                self.award_exp_on_level_complete(self.current_level_name)
            logging.info(f"Level {getattr(self, 'current_level_name', 'Unknown')} force-completed")

    def draw_shop(self):
        """Отрисовка магазина с информацией о прокачке"""
        self.screen.fill(self.BLACK)
        title = self.title_font.render("SHOP", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        # Информация о прокачке в магазине
        if self.player:
            exp_info = self.small_font.render(
                f"Skin Level: {self.player.skin_level} | EXP: {self.player.skin_exp}", 
                True, self.PURPLE
            )
            self.screen.blit(exp_info, (self.SCREEN_WIDTH//2 - exp_info.get_width()//2, 100))
        
        for i, item in enumerate(self.shop_items):
            y_pos = 150 + i * 100
            is_selected = i == self.selected_shop_item
            
            # Фон товара
            bg_color = (50, 50, 80) if is_selected else (30, 30, 50)
            pygame.draw.rect(self.screen, bg_color, (200, y_pos, 400, 80))
            pygame.draw.rect(self.screen, self.GOLD if is_selected else self.WHITE, (200, y_pos, 400, 80), 3)
            
            can_afford = self.total_amethysts >= item.cost
            color = self.GOLD if can_afford else (100, 100, 100)
            
            # Название и цена
            name_text = self.font.render(item.name, True, color)
            cost_text = self.font.render(f"{item.cost} AM", True, self.PURPLE)
            desc_text = self.small_font.render(item.description, True, self.WHITE)
            
            self.screen.blit(name_text, (220, y_pos + 10))
            self.screen.blit(cost_text, (500, y_pos + 10))
            self.screen.blit(desc_text, (220, y_pos + 45))
            
        # Баланс
        balance_text = self.font.render(f"Your Amethysts: {self.total_amethysts}", True, self.PURPLE)
        self.screen.blit(balance_text, (self.SCREEN_WIDTH//2 - balance_text.get_width()//2, 500))
            
        # Подсказки
        back_text = self.font.render("UP/DOWN: Select | ENTER: Buy | ESC: Back", True, self.WHITE)
        self.screen.blit(back_text, (self.SCREEN_WIDTH//2 - back_text.get_width()//2, 550))
        
    def draw_level_complete(self):
        """Отрисовка завершения уровня"""
        self.screen.fill(self.BLACK)
        
        scale = 1.0 + 0.1 * math.sin(pygame.time.get_ticks() * 0.01)
        complete_text = self.title_font.render("SQUARE COMPLETE!", True, self.GOLD)
        complete_text = pygame.transform.scale(complete_text, 
                                             (int(complete_text.get_width() * scale),
                                              int(complete_text.get_height() * scale)))
        
        self.screen.blit(complete_text, 
                        (self.SCREEN_WIDTH//2 - complete_text.get_width()//2, 
                         self.SCREEN_HEIGHT//2 - 100))
        
        collected_amethysts = len([a for a in self.amethysts if a.collected])
        total_amethysts = len(self.amethysts)
        
        stats = [
            f"Final Score: {self.score}",
            f"Amethysts Collected: {collected_amethysts}/{total_amethysts}",
            f"Progress: {self.percent}%",
            f"Completion Bonus: +20 Amethysts!",
            f"Level Completed!"
        ]
        
        for i, stat in enumerate(stats):
            stat_text = self.font.render(stat, True, self.WHITE)
            self.screen.blit(stat_text, (self.SCREEN_WIDTH//2 - stat_text.get_width()//2, 
                                       self.SCREEN_HEIGHT//2 + i*40 - 20))
        
        hint_text = self.small_font.render("Press any key to continue", True, self.WHITE)
        self.screen.blit(hint_text, (self.SCREEN_WIDTH//2 - hint_text.get_width()//2, 
                                   self.SCREEN_HEIGHT - 100))

    def draw_menu(self):
        """Отрисовка старого меню с информацией о прокачке"""
        if self.menu_bg:
            self.screen.blit(self.menu_bg, (0, 0))
        else:
            self.screen.fill(self.BLACK)
        
        title = self.title_font.render("SQUARE JUMP ULTIMATE v2.0", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 80))
        
        for i, option in enumerate(self.menu_options):
            color = self.GOLD if i == self.selected_option else self.WHITE
            text = self.font.render(option, True, color)
            text_rect = text.get_rect(center=(self.SCREEN_WIDTH//2, 200 + i*50))
            
            if i == self.selected_option:
                pygame.draw.rect(self.screen, (50, 50, 50, 180), 
                               (text_rect.x - 10, text_rect.y - 5, 
                                text_rect.width + 20, text_rect.height + 10))
            
            self.screen.blit(text, text_rect)
            
        hints = [
            "F11: Fullscreen | L: Login/Logout | P: Promo Code | TAB: Switch Menu",
            "NEW: Skin Progression, 10 Preset Levels, Improved Physics!",
            "Complete levels to earn Square-EXP and level up your skin!"
        ]
        
        for i, hint in enumerate(hints):
            hint_text = self.small_font.render(hint, True, self.WHITE)
            self.screen.blit(hint_text, (20, 20 + i*30))
            
        if self.account_system.current_account:
            username = self.account_system.current_account['username']
            
            # Информация о прокачке
            if self.player:
                skin_info = f" | Skin: Lvl {self.player.skin_level}"
            else:
                skin_info = ""
                
            account_text = self.small_font.render(
                f"Player: {username}{skin_info} | Amethysts: {self.total_amethysts}", 
                True, self.GREEN
            )
            self.screen.blit(account_text, (20, self.SCREEN_HEIGHT - 40))
        else:
            login_text = self.small_font.render("Press L to login", True, self.WHITE)
            self.screen.blit(login_text, (20, self.SCREEN_HEIGHT - 40))

    def draw_inventory(self):
        self.screen.fill(self.BLACK)
        title = self.title_font.render("SKIN INVENTORY", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        if self.account_system.current_account:
            player_text = self.font.render(f"Player: {self.account_system.current_account['username']}", True, self.WHITE)
            self.screen.blit(player_text, (self.SCREEN_WIDTH//2 - player_text.get_width()//2, 100))
        
        skin_keys = list(self.skins.keys())
        skins_per_row = 3
        skin_width = 160
        start_x = (self.SCREEN_WIDTH - (skins_per_row * skin_width)) // 2
        
        for i, skin_id in enumerate(skin_keys):
            row = i // skins_per_row
            col = i % skins_per_row
            x = start_x + col * skin_width
            y = 150 + row * 120
            
            if y + 110 > self.SCREEN_HEIGHT - 50:
                warning_text = self.small_font.render("... more skins available", True, self.WHITE)
                self.screen.blit(warning_text, (self.SCREEN_WIDTH//2 - warning_text.get_width()//2, self.SCREEN_HEIGHT - 40))
                break
            
            skin = self.skins[skin_id]
            border_color = self.GREEN if skin_id == self.current_skin else self.GOLD
            pygame.draw.rect(self.screen, border_color, (x-5, y-5, skin_width-10, 110), 3)
            
            try:
                skin_path = f"skins/{skin['image']}"
                if os.path.exists(skin_path):
                    skin_img = pygame.image.load(skin_path).convert_alpha()
                    skin_img = pygame.transform.scale(skin_img, (80, 80))
                    self.screen.blit(skin_img, (x + 35, y + 10))
                else:
                    color = self.GREEN if skin["owned"] else (100, 100, 100)
                    pygame.draw.rect(self.screen, color, (x + 35, y + 10, 80, 80))
            except Exception as e:
                color = self.GREEN if skin["owned"] else (100, 100, 100)
                pygame.draw.rect(self.screen, color, (x + 35, y + 10, 80, 80))
            
            name_text = self.small_font.render(skin["name"], True, self.WHITE)
            self.screen.blit(name_text, (x + 75 - name_text.get_width()//2, y + 5))
            
            if skin["owned"]:
                status_text = self.small_font.render("OWNED", True, self.GREEN)
            elif skin["locked"]:
                status_text = self.small_font.render("LOCKED", True, self.RED)
            else:
                status_text = self.small_font.render(f"{skin['cost']} AM", True, self.GOLD)
            
            self.screen.blit(status_text, (x + 75 - status_text.get_width()//2, y + 95))
        
        hint_text = self.small_font.render("Click to select/buy skin | ESC: Back", True, self.WHITE)
        self.screen.blit(hint_text, (self.SCREEN_WIDTH//2 - hint_text.get_width()//2, self.SCREEN_HEIGHT - 40))

    def draw_chest(self):
        self.screen.fill(self.BLACK)
        scale = 1.0 + 0.1 * math.sin(self.chest_animation_frame * 0.1)
        self.chest_animation_frame += 1
        
        if self.chest_image:
            scaled_chest = pygame.transform.scale(self.chest_image, (int(200 * scale), int(200 * scale)))
            self.screen.blit(scaled_chest, (self.SCREEN_WIDTH//2 - 100, 150))
        else:
            pygame.draw.rect(self.screen, (139, 69, 19), (self.SCREEN_WIDTH//2 - 100, 150, 200, 200))
        
        title = self.title_font.render("DAILY CHEST", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
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
        
        hint_text = self.small_font.render("Click anywhere to continue", True, self.WHITE)
        self.screen.blit(hint_text, (self.SCREEN_WIDTH//2 - hint_text.get_width()//2, self.SCREEN_HEIGHT - 50))

    def draw_pause(self):
        overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        pause_text = self.title_font.render("PAUSED", True, self.GOLD)
        continue_text = self.font.render("Press P or ESC to continue", True, self.WHITE)
        menu_text = self.font.render("Press M for main menu", True, self.WHITE)
        
        self.screen.blit(pause_text, (self.SCREEN_WIDTH//2 - pause_text.get_width()//2, 200))
        self.screen.blit(continue_text, (self.SCREEN_WIDTH//2 - continue_text.get_width()//2, 280))
        self.screen.blit(menu_text, (self.SCREEN_WIDTH//2 - menu_text.get_width()//2, 320))

    def draw_game_over(self):
        self.screen.fill(self.BLACK)
        game_over = self.title_font.render("GAME OVER", True, self.RED)
        score_text = self.font.render(f"Final Score: {self.score}", True, self.WHITE)
        percent_text = self.font.render(f"Progress: {self.percent}%", True, self.GOLD)
        restart_text = self.font.render("Press ENTER to restart or ESC for menu", True, self.WHITE)
        
        self.screen.blit(game_over, (self.SCREEN_WIDTH//2 - game_over.get_width()//2, 150))
        self.screen.blit(score_text, (self.SCREEN_WIDTH//2 - score_text.get_width()//2, 220))
        self.screen.blit(percent_text, (self.SCREEN_WIDTH//2 - percent_text.get_width()//2, 260))
        self.screen.blit(restart_text, (self.SCREEN_WIDTH//2 - restart_text.get_width()//2, 320))

    def draw_login(self):
        self.screen.fill(self.BLACK)
        title = self.title_font.render("LOGIN", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 100))
        
        login_text = self.font.render("Username:", True, self.WHITE)
        password_text = self.font.render("Password:", True, self.WHITE)
        self.screen.blit(login_text, (200, 200))
        self.screen.blit(password_text, (200, 250))
        
        login_rect = pygame.Rect(350, 200, 250, 30)
        pygame.draw.rect(self.screen, self.WHITE if self.active_input == "login" else (100, 100, 100), login_rect, 2)
        login_input_text = self.font.render(self.login_input, True, self.WHITE)
        self.screen.blit(login_input_text, (355, 205))
        
        password_rect = pygame.Rect(350, 250, 250, 30)
        pygame.draw.rect(self.screen, self.WHITE if self.active_input == "password" else (100, 100, 100), password_rect, 2)
        hidden_password = "*" * len(self.password_input)
        password_input_text = self.font.render(hidden_password, True, self.WHITE)
        self.screen.blit(password_input_text, (355, 255))
        
        if self.login_message:
            message_color = self.GREEN if "success" in self.login_message.lower() else self.RED
            message_text = self.font.render(self.login_message, True, message_color)
            self.screen.blit(message_text, (self.SCREEN_WIDTH//2 - message_text.get_width()//2, 320))
        
        hint1 = self.small_font.render("TAB: Switch field, ENTER: Login, ESC: Back", True, self.WHITE)
        hint2 = self.small_font.render("New account will be created automatically", True, self.WHITE)
        self.screen.blit(hint1, (self.SCREEN_WIDTH//2 - hint1.get_width()//2, 400))
        self.screen.blit(hint2, (self.SCREEN_WIDTH//2 - hint2.get_width()//2, 430))

    def draw_promo(self):
        self.screen.fill(self.BLACK)
        title = self.title_font.render("PROMO CODE", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 100))
        
        promo_rect = pygame.Rect(200, 200, 400, 40)
        pygame.draw.rect(self.screen, self.WHITE, promo_rect, 2)
        promo_text = self.font.render(self.promo_input, True, self.WHITE)
        self.screen.blit(promo_text, (210, 210))
        
        if self.promo_message:
            message_color = self.GREEN if "received" in self.promo_message.lower() else self.RED
            message_text = self.font.render(self.promo_message, True, message_color)
            self.screen.blit(message_text, (self.SCREEN_WIDTH//2 - message_text.get_width()//2, 280))
        
        hint1 = self.small_font.render("ENTER: Activate, ESC: Back", True, self.WHITE)
        available_codes = self.small_font.render("Available: WELCOME10, JUMP25, GAMER50, ULTIMATE100", True, (100, 100, 255))
        self.screen.blit(hint1, (self.SCREEN_WIDTH//2 - hint1.get_width()//2, 350))
        self.screen.blit(available_codes, (self.SCREEN_WIDTH//2 - available_codes.get_width()//2, 380))

    def draw_level_select(self):
        self.screen.fill(self.BLACK)
        title = self.title_font.render("SELECT LEVEL", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        for i, level in enumerate(self.available_levels):
            y_pos = 150 + i * 80
            is_selected = i == self.selected_level_index
            
            level_color = self.GOLD if is_selected else self.WHITE
            bg_color = (50, 50, 80) if is_selected else (30, 30, 50)
            pygame.draw.rect(self.screen, bg_color, (100, y_pos, 600, 70))
            pygame.draw.rect(self.screen, level_color, (100, y_pos, 600, 70), 3)
            
            name_text = self.font.render(level["name"], True, level_color)
            self.screen.blit(name_text, (120, y_pos + 15))
            
            desc_text = self.small_font.render(level["description"], True, self.WHITE)
            self.screen.blit(desc_text, (120, y_pos + 45))
        
        hint_text = self.small_font.render("UP/DOWN: Select | ENTER: Play | ESC: Back", True, self.WHITE)
        self.screen.blit(hint_text, (self.SCREEN_WIDTH//2 - hint_text.get_width()//2, self.SCREEN_HEIGHT - 50))

    def draw(self):
        self.screen.fill(self.BLACK)
        
        if self.state == self.MENU and self.use_pygame_menu and self.menu:
            # Для pygame-menu рисуем градиентный фон и меню
            self.screen.blit(self.menu_bg_surface, (0, 0))
            if self.menu.is_enabled():
                self.menu.draw(self.screen)
        elif self.state == self.MENU and not self.use_pygame_menu:
            # Для старого меню используем стандартный фон
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
        elif self.state == self.LEVEL_SELECT:
            self.draw_level_select()
        elif self.state == self.LEVEL_COMPLETE:
            self.draw_level_complete()
        
        # Отрисовка частиц поверх всего
        if self.state in [self.PLAYING, self.LEVEL_COMPLETE, self.GAME_OVER]:
            self.particle_system.draw(self.screen)
            
        pygame.display.flip()

    def handle_login_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_to_main_menu()
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
                if event.unicode.isprintable():
                    if self.active_input == "login":
                        if len(self.login_input) < 15:
                            self.login_input += event.unicode
                    else:
                        if len(self.password_input) < 20:
                            self.password_input += event.unicode

    def handle_promo_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_to_main_menu()
            elif event.key == pygame.K_RETURN:
                self.process_promo()
            elif event.key == pygame.K_BACKSPACE:
                self.promo_input = self.promo_input[:-1]
            elif event.unicode.isprintable():
                if event.unicode.isalnum() and len(self.promo_input) < 20:
                    self.promo_input += event.unicode.upper()

    def process_login(self):
        if not self.login_input or not self.password_input:
            self.login_message = "Please fill all fields"
            return
            
        if not self.account_system.conn:
            self.login_message = "Database connection failed - please restart game"
            return
        
        login_success = self.account_system.login(self.login_input, self.password_input)
        
        if login_success:
            self.login_message = "Login successful!"
            self.load_player_data()
            self.return_to_main_menu()
            return
            
        create_success = self.account_system.create_account(self.login_input, self.password_input)
        
        if create_success:
            login_after_create = self.account_system.login(self.login_input, self.password_input)
            
            if login_after_create:
                self.login_message = "New account created and logged in!"
                self.load_player_data()
                self.initialize_new_player_skins()
                self.return_to_main_menu()
            else:
                self.login_message = "Account created but login failed. Please try logging in again."
        else:
            self.login_message = "Login failed! Username may be taken."

    def process_promo(self):
        if not self.account_system.current_account:
            self.promo_message = "Please login first!"
            return
            
        result = self.promo_system.redeem_promo(self.promo_input)
        self.promo_message = result
        
        if "received" in result.lower():
            account_data = self.account_system.get_current_account_data()
            self.total_amethysts = account_data.get("amethysts", 0)

    def handle_game_over_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.start_game()
            elif event.key == pygame.K_ESCAPE:
                self.return_to_main_menu()

    def run(self):
        fps_counter = 0
        fps_time = time.time()
        fps_display = ""
        
        # Таймер для автосохранения
        autosave_timer = 0
        
        while self.running:
            self.handle_events()
            
            if self.state == self.PLAYING and self.player:
                self.update_game()
                
                # Автосохранение каждые 30 секунд
                autosave_timer += 1
                if autosave_timer >= 1800:  # 30 секунд при 60 FPS
                    self.auto_save_progress()
                    autosave_timer = 0
            
            if self.state == self.EDITOR and self.editor_message_timer > 0:
                self.editor_message_timer -= 1
                if self.editor_message_timer == 0:
                    self.editor_message = ""
            
            # Обновляем таймер сообщения об опыте
            if self.exp_message_timer > 0:
                self.exp_message_timer -= 1
            
            self.draw()
            
            # FPS счетчик (опционально)
            fps_counter += 1
            if time.time() - fps_time >= 1.0:
                fps_display = f"FPS: {fps_counter}"
                fps_counter = 0
                fps_time = time.time()
                
                # Простая оптимизация: очистка старых объектов
                if len(self.obstacles) > 50:
                    self.obstacles = self.obstacles[-30:]
                if len(self.amethysts) > 30:
                    self.amethysts = self.amethysts[-20:]
            
            if self.state == self.PLAYING and fps_display:
                fps_text = self.small_font.render(fps_display, True, (100, 255, 100, 180))
                self.screen.blit(fps_text, (10, self.SCREEN_HEIGHT - 30))
            
            self.clock.tick(60)
        
        # Сохраняем прогресс при выходе
        self.save_on_exit()
        pygame.quit()
        sys.exit()
    
    def auto_save_progress(self):
        """Автосохранение прогресса прокачки"""
        if (self.account_system.current_account and self.player and 
            hasattr(self, 'current_skin')):
            
            try:
                self.account_system.save_skin_progression(
                    self.account_system.current_account["id"],
                    self.current_skin,
                    self.player.skin_level,
                    self.player.skin_exp,
                    self.player.total_exp,
                    self.player.completed_levels
                )
                logging.info("Auto-save completed")
            except Exception as e:
                logging.error(f"Auto-save error: {e}")
                
    def save_on_exit(self):
        """Сохранение всех данных при выходе из игры"""
        self.auto_save_progress()
        self.save_level_progress()

# КЛАССЫ ДЛЯ БАЗЫ ДАННЫХ
class AccountSystem:
    def __init__(self):
        try:
            self.db_path = "game_accounts.db"
            self.conn = sqlite3.connect(self.db_path)
            self.current_account = None
            self.create_tables()
            self.update_database_schema()
            self.load_last_session()
        except sqlite3.Error as e:
            logging.error(f"Failed to initialize database: {e}")
            self.conn = None
            self.current_account = None

    def create_tables(self):
        if not self.conn:
            return
            
        try:
            cursor = self.conn.cursor()
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_upgrades (
                    player_id INTEGER,
                    upgrade_type TEXT,
                    FOREIGN KEY(player_id) REFERENCES players(id),
                    PRIMARY KEY (player_id, upgrade_type)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_sessions (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_username TEXT,
                    last_login_date TEXT
                )
            ''')
            
            # ================================================================
            # НОВАЯ ТАБЛИЦА: Прогресс прокачки скинов
            # ================================================================
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS skin_progression (
                    player_id INTEGER,
                    skin_id TEXT,
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    total_exp INTEGER DEFAULT 0,
                    completed_levels INTEGER DEFAULT 0,
                    FOREIGN KEY(player_id) REFERENCES players(id),
                    PRIMARY KEY (player_id, skin_id)
                )
            ''')
            
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error in create_tables: {e}")

    def update_database_schema(self):
        if not self.conn:
            return
            
        try:
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(players)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'last_chest_date' not in columns:
                cursor.execute('ALTER TABLE players ADD COLUMN last_chest_date TEXT')
                self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error updating database schema: {e}")

    def save_last_session(self, username):
        if not self.conn:
            return
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO game_sessions (id, last_username, last_login_date) VALUES (1, ?, ?)',
                         (username, datetime.datetime.now().isoformat()))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error saving session: {e}")

    def load_last_session(self):
        if not self.conn:
            return
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT last_username FROM game_sessions WHERE id = 1')
            result = cursor.fetchone()
            if result:
                self.last_username = result[0]
            else:
                self.last_username = None
        except sqlite3.Error as e:
            self.last_username = None

    def hash_password(self, password):
        return sha256(password.encode()).hexdigest()

    def create_account(self, username, password):
        if not self.conn:
            return False
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('INSERT INTO players (username, password, amethysts, last_chest_date) VALUES (?, ?, 0, NULL)',
                         (username, self.hash_password(password)))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except sqlite3.Error as e:
            logging.error(f"Database error in create_account: {e}")
            return False

    def login(self, username, password):
        if not self.conn:
            return False
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT id, username, amethysts, last_chest_date FROM players WHERE username = ? AND password = ?',
                         (username, self.hash_password(password)))
            
            result = cursor.fetchone()
            if result:
                self.current_account = {
                    "id": result[0],
                    "username": result[1],
                    "amethysts": result[2] or 0,
                    "last_chest_date": result[3]
                }
                self.save_last_session(username)
                return True
            else:
                return False
        except sqlite3.Error as e:
            logging.error(f"Database error in login: {e}")
            return False

    def get_current_account_data(self):
        if not self.current_account or not self.conn:
            return self.current_account or {}
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT amethysts, last_chest_date FROM players WHERE id = ?',
                         (self.current_account["id"],))
            
            result = cursor.fetchone()
            if result:
                self.current_account["amethysts"] = result[0] or 0
                self.current_account["last_chest_date"] = result[1]
        except sqlite3.Error as e:
            logging.error(f"Error updating account data: {e}")
        return self.current_account

    def get_last_username(self):
        return getattr(self, 'last_username', None)

    # ========================================================================
    # НОВЫЕ МЕТОДЫ ДЛЯ СИСТЕМЫ ПРОКАЧКИ
    # ========================================================================
    def save_skin_progression(self, player_id, skin_id, level, exp, total_exp, completed_levels):
        """
        Сохранение прогресса прокачки скина
        Возвращает: True если успешно, False если ошибка
        """
        if not self.conn:
            return False
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO skin_progression 
                (player_id, skin_id, level, exp, total_exp, completed_levels)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (player_id, skin_id, level, exp, total_exp, completed_levels))
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"Error saving skin progression: {e}")
            return False
    
    def load_skin_progression(self, player_id, skin_id):
        """
        Загрузка прогресса прокачки скина
        Возвращает: словарь с данными или None если ошибка
        """
        if not self.conn:
            return None
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT level, exp, total_exp, completed_levels FROM skin_progression
                WHERE player_id = ? AND skin_id = ?
            ''', (player_id, skin_id))
            
            result = cursor.fetchone()
            if result:
                return {
                    "level": result[0],
                    "exp": result[1],
                    "total_exp": result[2],
                    "completed_levels": result[3]
                }
            return None
        except sqlite3.Error as e:
            logging.error(f"Error loading skin progression: {e}")
            return None

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

class PromoSystem:
    PROMO_CODES = {
        "WELCOME10": {"amethysts": 10},
        "JUMP25": {"amethysts": 25},
        "GAMER50": {"amethysts": 50},
        "ULTIMATE100": {"amethysts": 100},
        "EXPPOWER": {"amethysts": 30, "message": "+1 EXP Boost token!"},
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
            cursor.execute('SELECT 1 FROM promo_used WHERE player_id = ? AND promo_code = ?',
                         (self.account_system.current_account["id"], code))
            
            if cursor.fetchone():
                return "Promo code already used"
                
            reward = self.PROMO_CODES[code]
            cursor.execute('UPDATE players SET amethysts = amethysts + ? WHERE id = ?',
                         (reward["amethysts"], self.account_system.current_account["id"]))
            cursor.execute('INSERT INTO promo_used (player_id, promo_code) VALUES (?, ?)',
                         (self.account_system.current_account["id"], code))
            
            self.account_system.conn.commit()
            self.account_system.current_account["amethysts"] += reward["amethysts"]
            
            message = f"Received {reward['amethysts']} amethysts!"
            if "message" in reward:
                message += f" {reward['message']}"
                
            return message
        except sqlite3.Error as e:
            return "Database error"

if __name__ == "__main__":
    game = Game()
    game.run()