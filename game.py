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
from enum import Enum
import numpy as np

# Настройка логирования
logging.basicConfig(filename='game.log', level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# ============================================================================
# КОНСТАНТЫ ДЛЯ СИСТЕМЫ ПРОКАЧКИ СКИНОВ
# ============================================================================
MAX_SKIN_LEVEL = 15
EXP_PER_LEVEL = [0, 100, 250, 500, 1000, 1500, 2200, 3000, 4000, 5000, 
                 6100, 7300, 8600, 10000, 11500, 13000]

# ============================================================================
# констаты для заданий и комбо(holy shit!)
# ============================================================================
DAILY_QUESTS = [
    {"id": "collect_amethysts", "description_ru": "Собрать 10 аметистов", "description_en": "Collect 10 amethysts", "target": 10, "reward": 15},
    {"id": "complete_level", "description_ru": "Пройдите 1 уровень", "description_en": "Complete 1 level", "target": 1, "reward": 25},
    {"id": "score_points", "description_ru": "Набрать 500 очков", "description_en": "Score 500 points", "target": 500, "reward": 20},
    {"id": "jump_count", "description_ru": "Сделать 50 прыжков", "description_en": "Make 50 jumps", "target": 50, "reward": 10},
    {"id": "avoid_obstacles", "description_ru": "Избежать 20 препятствий", "description_en": "Avoid 20 obstacles", "target": 20, "reward": 30},
    {"id": "fast_complete", "description_ru": "Пройдите уровень менее чем за 60 секунд", "description_en": "Complete level in under 60 seconds", "target": 60, "reward": 40},
]

HERO_PHRASES = {
    'greetings': [
        "Приветствую, герой! Готов к новым вызовам?",
        "С возвращением! У меня для тебя новые задания!",
        "Отлично выглядишь! Проверим твои навыки?",
        "Эй, путник! Не хочешь заработать аметистов?",
        "Здравствуй! Как насчёт испытаний на сегодня?"
    ],
    'praise': [
        "Великолепно! Ты справляешься лучше всех!",
        "Невероятно! Ты настоящий мастер прыжков!",
        "Потрясающе! Так держать!",
        "Ты делаешь успехи! Продолжай в том же духе!",
        "Просто фантастика! Я тобой горжусь!"
    ],
    'quest_complete': [
        "Задание выполнено! Награда твоя!",
        "Отличная работа! Забирай награду!",
        "Молодец! Ты заслужил эту награду!",
        "Идеально! Вот твоя награда!",
        "Превосходно! Ты выполнил задание!"
    ],
    'motivation': [
        "Не сдавайся! У тебя всё получится!",
        "Продолжай в том же духе! Ты близок к цели!",
        "Каждый прыжок приближает тебя к победе!",
        "Соберись! Ты можешь больше, чем думаешь!",
        "Верь в себя! Ты рождён для великих дел!"
    ]
}

HERO_PHRASES_EN = {
    'greetings': [
        "Greetings, hero! Ready for new challenges?",
        "Welcome back! I have new quests for you!",
        "Looking good! Shall we test your skills?",
        "Hey, traveler! Want to earn some amethysts?",
        "Hello! How about today's challenges?"
    ],
    'praise': [
        "Excellent! You're doing better than anyone!",
        "Incredible! You're a true jumping master!",
        "Amazing! Keep it up!",
        "You're making progress! Keep going!",
        "Fantastic! I'm proud of you!"
    ],
    'quest_complete': [
        "Quest complete! Your reward!",
        "Great job! Take your reward!",
        "Well done! You've earned this reward!",
        "Perfect! Here's your reward!",
        "Superb! You completed the quest!"
    ],
    'motivation': [
        "Don't give up! You can do it!",
        "Keep going! You're close to the goal!",
        "Every jump brings you closer to victory!",
        "Hang in there! You can do more than you think!",
        "Believe in yourself! You're born for great deeds!"
    ]
}


# ============================================================================
# ПЕРЕЧИСЛЕНИЯ (ENUMS)
# ============================================================================

class GameState(Enum):
    """Состояния игры"""
    INTRO = 0
    MENU = 1
    PLAYING = 2
    GAME_OVER = 3
    SHOP = 4
    LOGIN = 5
    PROMO = 6
    EDITOR = 7
    PAUSED = 8
    INVENTORY = 9
    CHEST = 10
    LEVEL_SELECT = 11
    LEVEL_COMPLETE = 12
    SKIN_PROGRESSION = 13
    OTHER = 13
    ACHIEVEMENTS = 14


class ObstacleType(Enum):
    """Типы препятствий"""
    SPIKE = "spike"
    PLATFORM = "platform"
    MOVING_SPIKE = "moving_spike"
    SPIKE_CLUSTER = "spike_cluster"
    BOUNCING_PLATFORM = "bouncing_platform"
    DISAPPEARING_PLATFORM = "disappearing_platform"
    ROTATING_SPIKE = "rotating_spike"
    ICE_PLATFORM = "ice_platform"


class BonusType(Enum):
    """Типы бонусов"""
    MAGNET = "magnet"
    SLOW_TIME = "slow_time"
    SHIELD = "shield"
    SPEED_BOOST = "speed_boost"


class EffectType(Enum):
    """Типы эффектов в магазине"""
    SHIELD = "shield"
    SPEED_BOOST = "speed_boost"
    EXTRA_LIFE = "extra_life"
    DOUBLE_JUMP = "double_jump"
    EXP_BOOSTER = "exp_booster"


class QuestType(Enum):
    """Типы заданий"""
    COLLECT_AMETHYSTS = "collect_amethysts"
    COMPLETE_LEVEL = "complete_level"
    SCORE_POINTS = "score_points"
    JUMP_COUNT = "jump_count"
    AVOID_OBSTACLES = "avoid_obstacles"
    FAST_COMPLETE = "fast_complete"


# ============================================================================
# КЛАСС ДЛЯ ЛОКАЛИЗАЦИИ
# ============================================================================
class Localization:
    def __init__(self, language='ru'):
        self.language = language
        self.texts = self.load_texts()
        
    def load_texts(self):
        """Загрузка текстов для текущего языка"""
        texts = {
            'ru': self.get_russian_texts(),
            'en': self.get_english_texts()
        }
        return texts.get(self.language, texts['ru'])
    
    def get_russian_texts(self):
        """Русские тексты"""
        return {
            # Основные заголовки
            'game_title': "Square Jump - Ultimate Edition v2.0",
            'main_menu': "Главное меню",
            'level_select': "Выбор уровня",
            'shop': "Магазин",
            'inventory': "Инвентарь",
            'settings': "Настройки",
            'promo_codes': "Промокоды",
            'skin_progression': "Прогресс скина",
            'achievements': "Достижения",
            'level_editor': "Редактор уровней",
            'daily_chest': "Ежедневный сундук",
            'login': "Вход",
            
            # Кнопки меню
            'start_game': "Начать игру",
            'level_select_btn': "Выбор уровня",
            'level_editor_btn': "Редактор уровней",
            'shop_btn': "Магазин",
            'inventory_btn': "Инвентарь",
            'daily_chest_btn': "Ежедневный сундук",
            'other_menu': "Прочее",
            'login_logout': "Вход/Выход",
            'promo_codes_btn': "Промокоды",
            'settings_btn': "Настройки",
            'skin_progression_btn': "Прогресс скина",
            'switch_menu': "Старое меню",
            'exit': "Выход",
            'back': "Назад",
            
            # Сообщения игры
            'game_over': "ИГРА ОКОНЧЕНА",
            'level_complete': "УРОВЕНЬ ПРОЙДЕН!",
            'paused': "ПАУЗА",
            'login_success': "Вход выполнен успешно!",
            'logout_success': "Выход выполнен успешно!",
            'purchase_success': "Покупка успешна!",
            'purchase_failed': "Ошибка покупки!",
            'chest_opened': "Сундук открыт!",
            'chest_already_opened': "Вы уже открывали сундук сегодня!",
            'promo_success': "Промокод активирован!",
            'promo_invalid': "Неверный промокод",
            'promo_used': "Промокод уже использован",
            
            # Товары магазина
            'shield': "Щит",
            'shield_desc': "Защита от одного препятствия",
            'speed_boost': "Ускорение",
            'speed_boost_desc': "Временное увеличение скорости",
            'extra_life': "Дополнительная жизнь",
            'extra_life_desc': "Одна дополнительная жизнь за игру",
            'double_jump': "Двойной прыжок",
            'double_jump_desc': "Прыжок дважды в воздухе",
            'exp_booster': "Буст опыта",
            'exp_booster_desc': "+20% опыта на 3 уровня",
            
            # Скины
            'basic_cube': "Базовый куб",
            'gold_cube': "Золотой куб",
            'diamond_cube': "Алмазный куб",
            'fire_cube': "Огненный куб",
            'ice_cube': "Ледяной куб",
            'rainbow_cube': "Радужный куб",
            'owned': "ВЛАДЕЕТЕ",
            'locked': "ЗАБЛОКИРОВАНО",
            
            # Система прокачки
            'level': "Уровень",
            'exp': "Опыт",
            'total_exp': "Всего опыта",
            'progress': "Прогресс",
            'level_up': "ПОВЫШЕНИЕ УРОВНЯ!",
            'completed_levels': "Пройдено уровней",
            'skin_progress': "Прогресс скина",
            
            # Статистика игры
            'score': "Счёт",
            'speed': "Скорость",
            'amethysts': "Аметисты",
            'distance': "Дистанция",
            'percentage': "Процент",
            
            # Управление
            'controls_jump': "ПРОБЕЛ: Прыжок",
            'controls_shield': "H: Щит",
            'controls_boost': "B: Ускорение",
            'controls_pause': "P: Пауза",
            'controls_editor': "1-3: Тип | ЛКМ: Поставить | ПКМ: Удалить",
            
            # Промокоды
            'enter_promo': "Введите промокод:",
            'available_codes': "Доступные коды: WELCOME10, JUMP25, GAMER50, ULTIMATE100",
            
            # Редактор уровней
            'editor_title': "РЕДАКТОР УРОВНЕЙ PRO",
            'objects_count': "Объектов",
            'amethysts_count': "Аметистов",
            'object_type': "Тип",
            'grid': "Сетка",
            'show_grid': "Показать сетку",
            
            # Настройки
            'resolution': "Разрешение",
            'fullscreen': "Полный экран",
            'music_volume': "Громкость музыки",
            'sfx_volume': "Громкость эффектов",
            'language': "Язык",
            'particle_cap': "Лимит частиц",
            
            # Состояния
            'on': "ВКЛ",
            'off': "ВЫКЛ",
            'yes': "Да",
            'no': "Нет"
        }
    
    def get_english_texts(self):
        """Английские текстa"""
        return {
            # Main titles
            'game_title': "Square Jump - Ultimate Edition v2.0",
            'main_menu': "Main Menu",
            'level_select': "Level Select",
            'shop': "Shop",
            'inventory': "Inventory",
            'settings': "Settings",
            'promo_codes': "Promo Codes",
            'skin_progression': "Skin Progression",
            'achievements': "Achievements",
            'level_editor': "Level Editor",
            'daily_chest': "Daily Chest",
            'login': "Login",
            
            # Menu buttons
            'start_game': "Start Game",
            'level_select_btn': "Level Select",
            'level_editor_btn': "Level Editor",
            'shop_btn': "Shop",
            'inventory_btn': "Inventory",
            'daily_chest_btn': "Daily Chest",
            'login_logout': "Login/Logout",
            'promo_codes_btn': "Promo Codes",
            'settings_btn': "Settings",
            'skin_progression_btn': "Skin Progression",
            'switch_menu': "Switch to Old Menu",
            'exit': "Exit",
            'back': "Back",
            
            # Game messages
            'game_over': "GAME OVER",
            'level_complete': "LEVEL COMPLETE!",
            'paused': "PAUSED",
            'login_success': "Login successful!",
            'logout_success': "Logout successful!",
            'purchase_success': "Purchase successful!",
            'purchase_failed': "Purchase failed!",
            'chest_opened': "Chest opened!",
            'chest_already_opened': "You already opened chest today!",
            'promo_success': "Promo code activated!",
            'promo_invalid': "Invalid promo code",
            'promo_used': "Promo code already used",
            
            # Shop items
            'shield': "Shield",
            'shield_desc': "Protection from one obstacle",
            'speed_boost': "Speed Boost",
            'speed_boost_desc': "Temporary speed increase",
            'extra_life': "Extra Life",
            'extra_life_desc': "One extra life per game",
            'double_jump': "Double Jump",
            'double_jump_desc': "Jump twice in the air",
            'exp_booster': "EXP Booster",
            'exp_booster_desc': "+20% EXP for 3 levels",
            
            # Skins
            'basic_cube': "Basic Cube",
            'gold_cube': "Gold Cube",
            'diamond_cube': "Diamond Cube",
            'fire_cube': "Fire Cube",
            'ice_cube': "Ice Cube",
            'rainbow_cube': "Rainbow Cube",
            'owned': "OWNED",
            'locked': "LOCKED",
            
            # Progression system
            'level': "Level",
            'exp': "EXP",
            'total_exp': "Total EXP",
            'progress': "Progress",
            'level_up': "LEVEL UP!",
            'completed_levels': "Completed Levels",
            'skin_progress': "Skin Progress",
            
            # Game stats
            'score': "Score",
            'speed': "Speed",
            'amethysts': "Amethysts",
            'distance': "Distance",
            'percentage': "Percentage",
            
            # Controls
            'controls_jump': "SPACE: Jump",
            'controls_shield': "H: Shield",
            'controls_boost': "B: Boost",
            'controls_pause': "P: Pause",
            'controls_editor': "1-3: Type | LMB: Place | RMB: Delete",
            
            # Promo codes
            'enter_promo': "Enter promo code:",
            'available_codes': "Available codes: WELCOME10, JUMP25, GAMER50, ULTIMATE100",
            
            # Level editor
            'editor_title': "LEVEL EDITOR PRO",
            'objects_count': "Objects",
            'amethysts_count': "Amethysts",
            'object_type': "Type",
            'grid': "Grid",
            'show_grid': "Show grid",
            
            # Settings
            'resolution': "Resolution",
            'fullscreen': "Fullscreen",
            'music_volume': "Music Volume",
            'sfx_volume': "SFX Volume",
            'language': "Language",
            'particle_cap': "Particle cap",
            
            # States
            'on': "ON",
            'off': "OFF",
            'yes': "Yes",
            'no': "No"
        }
    
    def get(self, key, default=None):
        """Получение текста по ключу"""
        return self.texts.get(key, default or key)
    
    def set_language(self, language):
        """Установка языка"""
        if language in ['ru', 'en']:
            self.language = language
            self.texts = self.load_texts()
            
    def get_language_name(self, code):
        """Получение названия языка по коду"""
        names = {
            'ru': 'Русский',
            'en': 'English'
        }
        return names.get(code, code)

# ============================================================================
# КЛАССЫ ИГРОВЫХ ОБЪЕКТОВ
# ============================================================================
class Player:
    def __init__(self, x, y, size=55, localization=None):
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
        
        # Локализация
        self.localization = localization or Localization()
        
        # Атрибуты для прокачки скинов
        self.skin_level = 1
        self.skin_exp = 0
        self.total_exp = 0
        self.completed_levels = 0
        
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
            
            # Визуальный эффект при прыжке
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
    
    def add_exp(self, amount):
        """Добавление опыта скину"""
        self.skin_exp += amount
        self.total_exp += amount
        
        # Проверяем, не пора ли повысить уровень
        while (self.skin_level < MAX_SKIN_LEVEL and 
               self.skin_exp >= EXP_PER_LEVEL[self.skin_level]):
            self.level_up()
            
    def level_up(self):
        """Повышение уровня скина"""
        self.skin_level += 1
        logging.info(f"Skin leveled up to {self.skin_level}!")
        
        # Бонусы при повышении уровня
        if self.skin_level % 5 == 0:
            self.size += 2
            logging.info(f"Player size increased to {self.size}")
            
    def get_exp_percentage(self):
        """Получение процента заполнения текущего уровня"""
        if self.skin_level >= MAX_SKIN_LEVEL:
            return 100
        
        current_level_exp = EXP_PER_LEVEL[self.skin_level - 1]
        next_level_exp = EXP_PER_LEVEL[self.skin_level]
        exp_in_current = self.skin_exp - current_level_exp
        exp_needed = next_level_exp - current_level_exp
        
        if exp_needed == 0:
            return 0
            
        percentage = (exp_in_current / exp_needed) * 100
        return min(100, max(0, percentage))
    
    def add_completed_level(self):
        self.completed_levels += 1

class Obstacle:
    def __init__(self, x, y, obstacle_type, width=60, height=60, color=None):
        self.x = x
        self.y = y
        if isinstance(obstacle_type, ObstacleType):
            self.type = obstacle_type
        else:
            try:
                self.type = ObstacleType(obstacle_type)
            except ValueError:
                self.type = obstacle_type
        self.w = width
        self.h = height
        self.color = color or (255, 0, 0)
        
        # Дополнительные свойства
        self.move_speed = 0
        self.move_direction = 1
        self.original_y = y
        
        # Свойства для улучшенной генерации
        self.bounce_power = 1.0
        self.disappear_timer = 0
        self.visible = True
        self.pulse_phase = random.random() * math.pi * 2
        
    def update(self, game_speed):
        """Обновление позиции препятствия"""
        self.x -= game_speed
        
        # Анимация пульсации
        self.pulse_phase += 0.05
        
        # Движение для движущихся шипов
        obstacle_type_str = self.type.value if isinstance(self.type, ObstacleType) else self.type
        if obstacle_type_str == ObstacleType.MOVING_SPIKE.value:
            self.y += self.move_speed * self.move_direction
            if self.y > self.original_y + 50 or self.y < self.original_y - 50:
                self.move_direction *= -1
        
        # КОНТЕНТ: Вращение для вращающихся шипов
        if obstacle_type_str == ObstacleType.ROTATING_SPIKE.value:
            if not hasattr(self, 'rotation_angle'):
                self.rotation_angle = 0
            if not hasattr(self, 'rotation_speed'):
                self.rotation_speed = 3.0
            self.rotation_angle += self.rotation_speed
        
        # Обновление таймера для исчезающих платформ
        if obstacle_type_str == ObstacleType.DISAPPEARING_PLATFORM.value and self.visible:
            self.disappear_timer -= 1
            if self.disappear_timer <= 0:
                self.visible = False
                
    def get_rect(self):
        """Получение прямоугольника препятствия"""
        return pygame.Rect(self.x, self.y, self.w, self.h)
        
    def is_off_screen(self):
        """Проверка, вышло ли препятствие за экран"""
        return self.x < -100
    
    def get_pulse_offset(self):
        """Возвращает смещение для анимации пульсации"""
        return math.sin(self.pulse_phase) * 2

class Amethyst:
    def __init__(self, x, y, size=30):
        self.x = x
        self.y = y
        self.size = size
        self.collected = False
        self.float_offset = random.random() * math.pi * 2
        self.rotation = 0
        
    def update(self, game_speed):
        """Обновление позиции аметиста с анимацией"""
        self.x -= game_speed
        
        # Анимация плавания
        self.float_offset += 0.05
        self.rotation += 2
        
    def get_rect(self):
        """Получение прямоугольника аметиста"""
        return pygame.Rect(self.x - 2, self.y - 2, self.size + 4, self.size + 4)
        
    def is_off_screen(self):
        """Проверка, вышел ли аметист за экран"""
        return self.x < -50
    
    def get_float_y(self):
        """Возвращает Y позицию с учетом плавающей анимации"""
        return self.y + math.sin(self.float_offset) * 3
    
    def get_current_size(self):
        """Возвращает размер с учетом пульсации"""
        pulse = math.sin(self.float_offset * 2) * 2
        return self.size + pulse

class Bonus:
    """Класс для бонусов (магнит, замедление времени, щит)"""
    def __init__(self, x, y, bonus_type=None):
        self.x = x
        self.y = y
        # Поддержка как Enum, так и строк для обратной совместимости
        if bonus_type is None:
            bonus_type = BonusType.MAGNET
        if isinstance(bonus_type, BonusType):
            self.type = bonus_type
        else:
            try:
                self.type = BonusType(bonus_type)
            except ValueError:
                self.type = bonus_type
        self.size = 25
        self.collected = False
        self.float_offset = random.random() * math.pi * 2
        self.rotation = 0
        self.pulse_phase = 0
        
        # Цвета для разных типов бонусов
        self.colors = {
            BonusType.MAGNET.value: (0, 255, 255),  # Cyan
            BonusType.SLOW_TIME.value: (255, 165, 0),  # Orange
            BonusType.SHIELD.value: (0, 255, 0),  # Green
            BonusType.SPEED_BOOST.value: (255, 0, 255)  # Magenta
        }
        
    def update(self, game_speed):
        """Обновление позиции бонуса"""
        self.x -= game_speed
        self.float_offset += 0.05
        self.rotation += 3
        self.pulse_phase += 0.1
        
    def get_rect(self):
        """Получение прямоугольника бонуса"""
        return pygame.Rect(self.x - 2, self.y - 2, self.size + 4, self.size + 4)
        
    def is_off_screen(self):
        """Проверка, вышел ли бонус за экран"""
        return self.x < -50
    
    def get_float_y(self):
        """Возвращает Y позицию с учетом плавающей анимации"""
        return self.y + math.sin(self.float_offset) * 5
    
    def get_color(self):
        """Возвращает цвет бонуса с пульсацией"""
        bonus_type_str = self.type.value if isinstance(self.type, BonusType) else self.type
        base_color = self.colors.get(bonus_type_str, (255, 255, 255))
        pulse = int(math.sin(self.pulse_phase) * 30)
        return tuple(min(255, max(0, c + pulse)) for c in base_color)

class ShopItem:
    def __init__(self, name_key, description_key, cost, effect_type, localization):
        self.name_key = name_key
        self.description_key = description_key
        self.cost = cost
        self.effect_type = effect_type
        self.localization = localization
    
    def get_name(self):
        """Получение локализованного названия"""
        return self.localization.get(self.name_key)
    
    def get_description(self):
        """Получение локализованного описания"""
        return self.localization.get(self.description_key)

class ParticleSystem:
    """УЛУЧШЕННАЯ система частиц"""
    def __init__(self, max_particles=200):
        self.particles = []
        self.max_particles = max_particles
        
    def add_particles(self, x, y, color, count=5, speed=2, lifetime=30, size_variation=3):
        """Добавление частиц"""
        if len(self.particles) > self.max_particles - count:
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
        """Обновление частиц (оптимизировано)"""
        # Используем list comprehension для более эффективного удаления
        self.particles = [
            particle for particle in self.particles
            if self._update_particle(particle)
        ]
    
    def _update_particle(self, particle):
        """Обновление одной частицы, возвращает True если частица жива"""
        particle['x'] += particle['vx']
        particle['y'] += particle['vy']
        particle['vy'] += particle['gravity']
        particle['lifetime'] -= 1
        return particle['lifetime'] > 0
                
    def draw(self, screen):
        """Отрисовка частиц"""
        for particle in self.particles:
            alpha = int(255 * (particle['lifetime'] / particle['max_lifetime']))
            color = list(particle['color'])
            
            if len(color) == 3:
                color.append(alpha)
            else:
                color[3] = alpha
            
            size = particle['size']
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            
            pygame.draw.circle(surf, color, (size, size), size)
            
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
        # Базовое разрешение для масштабирования
        self.BASE_SCREEN_WIDTH = 800
        self.BASE_SCREEN_HEIGHT = 600
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
        
        # Инициализация локализации
        self.load_language_settings()
        self.localization = Localization(self.language)
        
        # Режим экрана и настройки
        self.fullscreen = False
        self.original_size = (self.SCREEN_WIDTH, self.SCREEN_HEIGHT)
        self.music_volume = 50
        self.sfx_volume = 70
        
        # Инициализация экрана
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption(self.localization.get('game_title'))
        self.clock = pygame.time.Clock()
        
        # Создаем пустого игрока
        self.player = Player(0, 0, localization=self.localization)
        self.player.skin_level = 1
        self.player.skin_exp = 0
        self.player.total_exp = 0
        self.player.completed_levels = 0
        
        # Системы
        self.account_system = AccountSystem()
        self.promo_system = PromoSystem(self.account_system)
        self.max_particles_limit = 300
        self.particle_system = ParticleSystem(self.max_particles_limit)
        
        # Параметры физики
        self.gravity = 0.5
        self.jump_force = -16
        self.max_fall_speed = 15
        self.air_resistance = 0.98
        self.bounce_multiplier = 1.5
        self.acceleration_rate = 0.002
        
        # Состояние игры
        self.state = GameState.MENU
        self.running = True
        self.score = 0
        self.total_amethysts = 0
        self.level_complete = False
        
        # Система заданий
        self.current_quests = []
        self.quest_progress = {}
        self.last_quest_refresh = None
        self.hero_phrase = ""
        self.hero_phrase_timer = 0
        self.hero_phrase_shown_on_entry = False
        self.hero_click_rect = None
        
        # Система статистики
        self.stats = {
            "total_play_time": 0,
            "total_jumps": 0,
            "total_amethysts_collected": 0,
            "total_levels_completed": 0,
            "best_score": 0,
            "best_combo": 0,
            "total_deaths": 0,
            "session_start_time": time.time()
        }
        self.load_stats()
        
        # Система достижений
        self.achievements = {
            "first_jump": False,
            "first_level": False,
            "combo_master": False,
            "speed_demon": False,
            "collector": False,
            "perfectionist": False,
            "veteran": False
        }
        self.load_achievements()
        
        # Система комбо
        self.combo_counter = 0
        self.combo_multiplier = 1.0
        self.combo_timer = 0
        self.max_combo = 0
        self.max_combo_multiplier = 1.0
        self.combo_message = ""
        self.combo_message_timer = 0
        
        # Герой
        self.hero_image = None
        self.load_hero_image()
        
        # Фоновая музыка меню
        self.menu_music = None
        self.music_playing = False
        
        # Звуки и музыка уровней
        self.start_game_sound = None
        self.level_musics = {}  # Словарь для музыки уровней: {level_name: music_path}
        self.title_screen_music = None
        
        # Меню (старая система)
        self.create_menu_options()
        self.selected_option = 0
        
        self.use_pygame_menu = True
        
        # Создаем меню с флагом предотвращения рекурсии
        self._creating_menus = False
        self.create_menus()
        
        # Устанавливаем активное меню при запуске
        if self.use_pygame_menu:
            self.menu = self.main_menu
            self.menu.enable()
        
        # Создаем градиентный фон
        self.menu_bg_surface = self.create_gradient_menu_bg()
        
        # Кэширование для оптимизации производительности
        self.cached_bg_surface = None
        self.cached_bg_camera_x = -1
        self.cached_ground_surface = None
        self.viewport_left = 0
        self.viewport_right = 0
        
        # UI/UX: Эффекты экрана
        self.screen_shake = 0
        self.screen_shake_x = 0
        self.screen_shake_y = 0
        self.flash_alpha = 0
        self.flash_color = (255, 255, 255)
        
        # Меню (pygame-menu)
        self.menu = None
        self.create_menus()
        
        # Устанавливаем активное меню при запуске
        self.state = GameState.MENU
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
        
        # Автозаполнение логина
        last_user = self.account_system.get_last_username()
        if last_user:
            self.login_input = last_user
            self.login_message = f"Последний пользователь: {last_user} - Введите пароль"
        
        # Промокод система
        self.promo_input = ""
        self.promo_message = ""
        
        # Скины
        self.skins = self.load_skins()
        self.current_skin = "cube01"
        self.player_image = None
        
        # Загружаем кастомные скины
        self.load_custom_skins()

        # Сканируем папку на наличие новых скинов (только если нужно)
        # self.scan_for_new_skins()  # Закомментировано для оптимизации загрузки
        
        # Магазин
        self.create_shop_items()
        self.selected_shop_item = 0
        
        # Ежедневный сундук
        self.last_chest_date = None
        self.chest_rewards = []
        self.chest_animation_frame = 0
        
        # Загрузка ресурсов
        self.load_resources()
        
        # Игровые объекты
        self.obstacles = []
        self.amethysts = []
        self.bonuses = []
        self.magnet_active = False
        self.magnet_timer = 0
        self.slow_time_active = False
        self.slow_time_timer = 0
        self.game_speed = 5
        self.base_speed = 5
        
        # Система дэша
        self.dash_speed = 25  # Скорость дэша
        self.dash_duration = 10  # Длительность в кадрах
        self.dash_cooldown = 60  # Кулдаун в кадрах (1 секунда при 60 FPS)
        self.dash_timer = 0
        self.dash_cooldown_timer = 0
        self.is_dashing = False
        self.dash_direction = 1  # 1 - вправо, -1 - влево
        self.camera_x = 0
        self.spawn_timer = 0
        self.percent = 0
        self.distance_traveled = 0
        self.level_end_x = 5000
        
        # Редактор уровней
        self.editor_obstacles = []
        self.editor_amethysts = []
        self.editor_selected_type = ObstacleType.SPIKE
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
        self.editor_panel_height = 80
        self.editor_panel_y = self.SCREEN_HEIGHT - self.editor_panel_height
        
        # Система прокачки и уровней
        self.exp_message = ""
        self.exp_message_timer = 0
        self.exp_boost_active = False
        self.exp_boost_timer = 0
        
        # Загрузка доступных уровней
        self.available_levels = self.load_available_levels()
        self.selected_level_index = 0
        
        # Прогресс по уровням
        self.completed_levels = []
        self.level_progress = {}
        self.load_level_progress()
        
        # Генерация 10 пресет-уровней
        self.preset_levels = self.generate_preset_levels()
        
        # Загрузка заданий
        self.load_quests()
        
        # Пагинация инвентаря
        self.inventory_page = 0
        self.skins_per_page = 15
        
        # Intro screen
        self.intro_timer = 0
        self.intro_text_alpha = 0
        self.intro_subtitle_alpha = 0
        self.intro_bg = None
        
        # Автоматическая загрузка данных
        if self.account_system.current_account:
            self.load_player_data()
            
        # Создаем меню
        self.create_menus()
    
        # Устанавливаем активное меню при запуске
        self.state = GameState.INTRO
        if self.use_pygame_menu:
            self.menu = self.main_menu
            self.menu.enable()
            
        # ВЫБОР УРОВНЕЙ
        self.available_levels = self.load_available_levels()
        self.selected_level_index = 0

    def load_hero_image(self):
        """Загрузка изображения героя"""
        try:
            hero_path = "assets/hero.png"
            if os.path.exists(hero_path):
                self.hero_image = pygame.image.load(hero_path).convert_alpha()
                self.hero_image = pygame.transform.scale(self.hero_image, (150, 200))
            else:
                # Создаем временного героя
                self.hero_image = pygame.Surface((150, 200), pygame.SRCALPHA)
                pygame.draw.rect(self.hero_image, (100, 200, 255), (0, 0, 150, 200))
                pygame.draw.circle(self.hero_image, (255, 200, 150), (75, 60), 40)
                pygame.draw.rect(self.hero_image, (50, 150, 50), (25, 100, 100, 80))
        except Exception as e:
            logging.error(f"Error loading hero image: {e}")
            self.create_default_hero()

    def create_default_hero(self):
        """Создание дефолтного героя"""
        self.hero_image = pygame.Surface((150, 200), pygame.SRCALPHA)
        # Тело - светло-голубой
        pygame.draw.rect(self.hero_image, (173, 216, 230, 200), (0, 0, 150, 200), border_radius=20)
        # Голова - светло-розовый
        pygame.draw.circle(self.hero_image, (255, 218, 185), (75, 60), 40)
        # Глаза - темно-синие
        pygame.draw.circle(self.hero_image, (25, 25, 112), (60, 50), 8)
        pygame.draw.circle(self.hero_image, (25, 25, 112), (90, 50), 8)
        # Улыбка
        pygame.draw.arc(self.hero_image, (0, 0, 0), (55, 65, 40, 30), 0, 3.14, 3)
        # Плащ - светло-фиолетовый
        pygame.draw.polygon(self.hero_image, (221, 160, 221), [(0, 100), (75, 120), (150, 100)])
        # Пояс - золотой
        pygame.draw.rect(self.hero_image, (255, 215, 0), (40, 140, 70, 10))

    def refresh_daily_quests(self):
        """Обновление ежедневных заданий"""
        today = datetime.datetime.now().date().isoformat()
        
        if self.last_quest_refresh != today:
            self.current_quests = random.sample(DAILY_QUESTS, min(3, len(DAILY_QUESTS)))
            self.quest_progress = {quest["id"]: 0 for quest in self.current_quests}
            self.last_quest_refresh = today
            
            # Сохраняем в файл
            self.save_quests()
            
            # Выбираем случайную фразу приветствия
            phrases = HERO_PHRASES['greetings'] if self.language == 'ru' else HERO_PHRASES_EN['greetings']
            self.hero_phrase = random.choice(phrases)
            self.hero_phrase_timer = 180
            
            return True
        return False

    def save_quests(self):
        """Сохранение заданий"""
        try:
            data = {
                "last_refresh": self.last_quest_refresh,
                "quests": self.current_quests,
                "progress": self.quest_progress
            }
            with open("quests.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving quests: {e}")

    def load_quests(self):
        """Загрузка заданий"""
        try:
            if os.path.exists("quests.json"):
                with open("quests.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_quest_refresh = data.get("last_refresh")
                    self.current_quests = data.get("quests", [])
                    self.quest_progress = data.get("progress", {})
                    
                    # Проверяем, не устарели ли задания
                    today = datetime.datetime.now().date().isoformat()
                    if self.last_quest_refresh != today:
                        self.refresh_daily_quests()
        except Exception as e:
            logging.error(f"Error loading quests: {e}")
            self.refresh_daily_quests()

    def update_quest_progress(self, quest_type, amount=1):
        """Обновление прогресса заданий"""
        if not self.current_quests:
            return
        
        # Поддержка как Enum, так и строк
        quest_type_str = quest_type.value if isinstance(quest_type, QuestType) else quest_type
            
        for quest in self.current_quests:
            if quest["id"] == quest_type_str:
                current = self.quest_progress.get(quest["id"], 0)
                self.quest_progress[quest["id"]] = current + amount
                
                # Проверяем выполнение
                if self.quest_progress[quest["id"]] >= quest["target"]:
                    self.complete_quest(quest)
                    
                self.save_quests()
                break

    def complete_quest(self, quest):
        """Завершение задания"""
        # Награда
        reward = quest["reward"]
        self.total_amethysts += reward
        
        # Сообщение
        phrases = HERO_PHRASES['quest_complete'] if self.language == 'ru' else HERO_PHRASES_EN['quest_complete']
        completion_phrase = random.choice(phrases)
        
        # Обновляем баланс в базе данных
        if self.account_system.current_account and self.account_system.conn:
            try:
                cursor = self.account_system.conn.cursor()
                cursor.execute('UPDATE players SET amethysts = amethysts + ? WHERE username = ?',
                             (reward, self.account_system.current_account['username']))
                self.account_system.conn.commit()
            except sqlite3.Error as e:
                logging.error(f"Database error updating quest reward: {e}")
        
        # Удаляем выполненное задание
        self.current_quests = [q for q in self.current_quests if q["id"] != quest["id"]]
        
        # Частицы
        self.particle_system.add_particles(
            self.SCREEN_WIDTH // 2,
            100,
            self.GOLD,
            count=30,
            speed=2,
            size_variation=4
        )
        
        # Сообщение
        quest_name = quest["description_ru"] if self.language == 'ru' else quest["description_en"]
        self.login_message = f"{completion_phrase} +{reward} AM за: {quest_name}"
        
        # Новая фраза героя
        praise_phrases = HERO_PHRASES['praise'] if self.language == 'ru' else HERO_PHRASES_EN['praise']
        self.hero_phrase = random.choice(praise_phrases)
        self.hero_phrase_timer = 180
        
        self.play_sound_safe(self.powerup_sound)

    def update_combo_system(self):
        """Обновление системы комбо"""
        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            if self.combo_counter > 1:  # Минимум 2 аметиста подряд
                self.reset_combo()
            self.combo_counter = 0
            self.combo_multiplier = 1.0

    def activate_bonus(self, bonus_type):
        """Активация бонуса"""
        self.play_sound_safe(self.powerup_sound)
        
        # Поддержка как Enum, так и строк
        if isinstance(bonus_type, BonusType):
            bonus_type_str = bonus_type.value
        else:
            bonus_type_str = bonus_type
        
        if bonus_type_str == BonusType.MAGNET.value:
            self.magnet_active = True
            self.magnet_timer = 600  # 10 секунд при 60 FPS
            self.particle_system.add_particles(
                self.player.x + self.player.size//2,
                self.player.y + self.player.size//2,
                (0, 255, 255),
                count=30,
                speed=3
            )
        elif bonus_type_str == BonusType.SLOW_TIME.value:
            self.slow_time_active = True
            self.slow_time_timer = 300  # 5 секунд
            self.game_speed = max(3, self.game_speed * 0.5)  # Замедляем в 2 раза
            self.particle_system.add_particles(
                self.player.x + self.player.size//2,
                self.player.y + self.player.size//2,
                (255, 165, 0),
                count=30,
                speed=3
            )
        elif bonus_type_str == BonusType.SHIELD.value:
            if self.player:
                self.player.has_shield = True
                self.player.invincible = True
                self.player.invincible_timer = 300  # 5 секунд
                self.particle_system.add_particles(
                    self.player.x + self.player.size//2,
                    self.player.y + self.player.size//2,
                    (0, 255, 0),
                    count=30,
                    speed=3
                )
        elif bonus_type_str == BonusType.SPEED_BOOST.value:
            if self.player:
                self.player.activate_speed_boost()
                self.particle_system.add_particles(
                    self.player.x + self.player.size//2,
                    self.player.y + self.player.size//2,
                    (255, 0, 255),
                    count=30,
                    speed=3
                )
    
    def add_combo(self):
        """Добавление к комбо"""
        self.combo_counter += 1
        self.combo_timer = 90  # 1.5 секунды на комбо (при 60 FPS)
        
        # Рассчитываем множитель
        if self.combo_counter >= 10:
            self.combo_multiplier = 3.0
        elif self.combo_counter >= 5:
            self.combo_multiplier = 2.0
        elif self.combo_counter >= 3:
            self.combo_multiplier = 1.5
        else:
            self.combo_multiplier = 1.0
        
        # Обновляем максимальное комбо
        if self.combo_counter > self.max_combo:
            self.max_combo = self.combo_counter
            self.max_combo_multiplier = self.combo_multiplier
        
        # Показываем сообщение
        if self.combo_counter >= 3:
            self.show_combo_message()

    def reset_combo(self):
        """Сброс комбо"""
        if self.combo_counter >= 3:
            # Сообщение о потере комбо
            if self.language == 'ru':
                self.combo_message = f"Комбо потеряно! Было: x{self.combo_multiplier:.1f}"
            else:
                self.combo_message = f"Combo lost! Was: x{self.combo_multiplier:.1f}"
            self.combo_message_timer = 120
            
            # Частицы
            self.particle_system.add_particles(
                self.SCREEN_WIDTH // 2,
                150,
                self.RED,
                count=20,
                speed=3,
                size_variation=3
            )
        
        self.combo_counter = 0
        self.combo_multiplier = 1.0
        self.combo_timer = 0

    def show_combo_message(self):
        """Показать сообщение о комбо"""
        if self.language == 'ru':
            messages = [
                f"Серия x{self.combo_multiplier:.1f}!",
                f"Горячо! x{self.combo_multiplier:.1f}!",
                f"Неудержимый! x{self.combo_multiplier:.1f}!",
                f"{self.combo_counter} подряд! x{self.combo_multiplier:.1f}!",
            ]
        else:
            messages = [
                f"Combo x{self.combo_multiplier:.1f}!",
                f"Holy shit! x{self.combo_multiplier:.1f}!",
                f"Unstoppable! x{self.combo_multiplier:.1f}!",
                f"{self.combo_counter} in a row! x{self.combo_multiplier:.1f}!",
            ]
        
        self.combo_message = random.choice(messages)
        self.combo_message_timer = 90
        
        # Частицы в зависимости от множителя
        if self.combo_multiplier >= 3.0:
            color = self.GOLD
            count = 25
        elif self.combo_multiplier >= 2.0:
            color = self.PURPLE
            count = 15
        else:
            color = self.CYAN
            count = 10
            
        self.particle_system.add_particles(
            self.SCREEN_WIDTH // 2,
            150,
            color,
            count=count,
            speed=2,
            size_variation=3
        )
        
        self.play_sound_safe(self.powerup_sound)

    def load_language_settings(self):
        """Загрузка настроек из файла"""
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    self.language = settings.get("language", "ru")
                    self.fullscreen = settings.get("fullscreen", False)
                    self.music_volume = settings.get("music_volume", 50)
                    self.sfx_volume = settings.get("sfx_volume", 70)
                    self.max_particles_limit = settings.get("particle_cap", 300)
                    
                    # Применяем настройки звука
                    pygame.mixer.music.set_volume(self.music_volume / 100)
                    if hasattr(self, "particle_system"):
                        self.particle_system.max_particles = self.max_particles_limit
            else:
                self.language = "ru"
                self.fullscreen = False
                self.music_volume = 50
                self.sfx_volume = 70
                self.max_particles_limit = 300
        except Exception as e:
            logging.error(f"Error loading settings: {e}")
            self.language = "ru"
            self.fullscreen = False
            self.music_volume = 50
            self.sfx_volume = 70
            self.max_particles_limit = 300
    
    def save_language_settings(self):
        """Сохранение настроек в файл"""
        try:
            settings = {
                "language": self.language,
                "fullscreen": self.fullscreen,
                "music_volume": self.music_volume,
                "sfx_volume": self.sfx_volume,
                "particle_cap": getattr(self, "max_particles_limit", 300)
            }
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
    
    def set_language(self, language, update_menus=True):
        """Установка языка и обновление интерфейса"""
        if language in ['ru', 'en']:
            self.language = language
            self.localization.set_language(language)
            self.save_language_settings()
            
            # Обновляем заголовок окна
            pygame.display.set_caption(self.localization.get('game_title'))
            
            # Обновляем текст кнопок
            self.create_menu_options()
            self.create_shop_items()
            
            # Пересоздаем меню с новым языком только если нужно
            if update_menus:
                self.create_menus()
                
                # Если мы в меню, обновляем активное меню
                if self.state == GameState.MENU and self.use_pygame_menu:
                    self.menu = self.main_menu
                    if self.menu:
                        self.menu.enable()
    
    def create_menu_options(self):
        """Создание пунктов меню с учетом локализации"""
        self.menu_options = [
            self.localization.get('start_game'),
            self.localization.get('level_select_btn'),
            self.localization.get('level_editor_btn'),
            self.localization.get('shop_btn'),
            self.localization.get('inventory_btn'),
            self.localization.get('daily_chest_btn'),
            self.localization.get('other_menu'),
            self.localization.get('login_logout'),
            self.localization.get('promo_codes_btn'),
            self.localization.get('settings_btn'),
            self.localization.get('skin_progression_btn'),
            self.localization.get('achievements'),
            self.localization.get('switch_menu'),
            self.localization.get('exit')
        ]
    
    def create_shop_items(self):
        """Создание товаров магазина с учетом локализации"""
        self.shop_items = [
            ShopItem('shield', 'shield_desc', 30, EffectType.SHIELD, self.localization),
            ShopItem('speed_boost', 'speed_boost_desc', 25, EffectType.SPEED_BOOST, self.localization),
            ShopItem('extra_life', 'extra_life_desc', 40, EffectType.EXTRA_LIFE, self.localization),
            ShopItem('double_jump', 'double_jump_desc', 50, EffectType.DOUBLE_JUMP, self.localization),
            ShopItem('exp_booster', 'exp_booster_desc', 75, EffectType.EXP_BOOSTER, self.localization)
        ]
    
    def create_gradient_menu_bg(self):
        surf = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
    
        # Цвет градиента зависит от уровня скина
        if self.player and hasattr(self.player, 'skin_level'):
            base_hue = (self.player.skin_level * 24) % 360
        else:
            base_hue = 240
        
        start_color = self.hsv_to_rgb(base_hue, 0.8, 0.2)
        end_color = self.hsv_to_rgb((base_hue + 60) % 360, 0.9, 0.4)
        
        # Создаем вертикальный градиент
        for y in range(self.SCREEN_HEIGHT):
            t = y / self.SCREEN_HEIGHT
            r = self.lerp(start_color[0], end_color[0], t)
            g = self.lerp(start_color[1], end_color[1], t)
            b = self.lerp(start_color[2], end_color[2], t)
            pygame.draw.line(surf, (int(r), int(g), int(b)), (0, y), (self.SCREEN_WIDTH, y))
        
        # Добавляем звезды
        for _ in range(50):
            x = random.randint(0, self.SCREEN_WIDTH)
            y = random.randint(0, self.SCREEN_HEIGHT)
            size = random.randint(1, 3)
            brightness = random.randint(150, 255)
            pygame.draw.circle(surf, (brightness, brightness, brightness), (x, y), size)
        
        return surf

    def create_light_menu_bg(self):
        """Создает светлый фон для меню 'Прочее'"""
        surf = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        
        # Светло-голубой градиент
        start_color = (173, 216, 230)  # Светло-голубой
        end_color = (240, 248, 255)    # Алис блю
        
        # Создаем вертикальный градиент
        for y in range(self.SCREEN_HEIGHT):
            t = y / self.SCREEN_HEIGHT
            r = self.lerp(start_color[0], end_color[0], t)
            g = self.lerp(start_color[1], end_color[1], t)
            b = self.lerp(start_color[2], end_color[2], t)
            pygame.draw.line(surf, (int(r), int(g), int(b)), (0, y), (self.SCREEN_WIDTH, y))
        
        # Добавляем легкие облака или узоры
        for _ in range(20):
            x = random.randint(0, self.SCREEN_WIDTH)
            y = random.randint(0, self.SCREEN_HEIGHT)
            size = random.randint(30, 60)
            alpha = random.randint(20, 50)
            cloud_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(cloud_surf, (255, 255, 255, alpha), (size//2, size//2), size//2)
            surf.blit(cloud_surf, (x, y))
        
        return surf

    def draw_intro(self):
        """Рисует intro экран"""
        # Создаем фон если нужно
        if not self.intro_bg or self.intro_bg.get_size() != (self.SCREEN_WIDTH, self.SCREEN_HEIGHT):
            self.intro_bg = self.create_intro_bg()
        
        self.screen.blit(self.intro_bg, (0, 0))
        
        # Рисуем название
        title_font = pygame.font.Font(None, 72)
        title_text = title_font.render("Millary Hills Digital", True, self.WHITE)
        title_text.set_alpha(self.intro_text_alpha)
        title_rect = title_text.get_rect(center=(self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(title_text, title_rect)
        
        # Рисуем подзаголовок
        subtitle_font = pygame.font.Font(None, 36)
        subtitle_text = subtitle_font.render("приветствуем игрок", True, self.CYAN)
        subtitle_text.set_alpha(self.intro_subtitle_alpha)
        subtitle_rect = subtitle_text.get_rect(center=(self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(subtitle_text, subtitle_rect)

    def create_intro_bg(self):
        """Создает фон для intro с звездами и полярным сиянием"""
        surf = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        surf.fill((0, 0, 0))  # Черный фон
        
        # Добавляем звезды
        for _ in range(100):
            x = random.randint(0, self.SCREEN_WIDTH)
            y = random.randint(0, self.SCREEN_HEIGHT)
            size = random.randint(1, 3)
            brightness = random.randint(150, 255)
            pygame.draw.circle(surf, (brightness, brightness, brightness), (x, y), size)
        
        # Добавляем полярное сияние (зеленовато-голубые полосы)
        for i in range(5):
            y_start = random.randint(0, self.SCREEN_HEIGHT // 2)
            height = random.randint(50, 150)
            alpha = random.randint(30, 80)
            
            aurora_surf = pygame.Surface((self.SCREEN_WIDTH, height), pygame.SRCALPHA)
            for y in range(height):
                # Градиент от зеленого к голубому
                green = 100 + int(155 * (y / height))
                blue = 200 + int(55 * (y / height))
                alpha_val = int(alpha * (1 - abs(y - height//2) / (height//2)))
                pygame.draw.line(aurora_surf, (0, green, blue, alpha_val), (0, y), (self.SCREEN_WIDTH, y))
            
            surf.blit(aurora_surf, (0, y_start))
        
        return surf

    def update_menu_theme(self):
        """Обновление темы меню"""
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
        # Временный флаг для предотвращения рекурсии
        if hasattr(self, '_creating_menus') and self._creating_menus:
            return
        self._creating_menus = True
        
        try:
            theme = self.update_menu_theme()
            
            # Главное меню
            self.main_menu = pygame_menu.Menu(
                self.localization.get('main_menu'),
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=theme,
                onclose=pygame_menu.events.EXIT
            )
            
            # Локализованные кнопки
            self.main_menu.add.button(self.localization.get('start_game'), self.start_game_from_menu)
            self.main_menu.add.button(self.localization.get('level_select_btn'), self.show_level_select_menu)
            self.main_menu.add.button(self.localization.get('level_editor_btn'), self.start_editor_from_menu)
            self.main_menu.add.button(self.localization.get('shop_btn'), self.show_shop_menu)
            self.main_menu.add.button(self.localization.get('inventory_btn'), self.show_inventory_menu)
            self.main_menu.add.button(self.localization.get('daily_chest_btn'), self.open_daily_chest_from_menu)
            self.main_menu.add.button(self.localization.get('other_menu'), self.show_other_menu)
            self.main_menu.add.button(self.localization.get('login_logout'), self.toggle_login_from_menu)
            self.main_menu.add.button(self.localization.get('promo_codes_btn'), self.show_promo_menu)
            self.main_menu.add.button(self.localization.get('settings_btn'), self.show_settings_menu)
            self.main_menu.add.button(self.localization.get('skin_progression_btn'), self.show_skin_progression_menu)
            self.main_menu.add.button(self.localization.get('achievements'), self.show_achievements_menu)
            self.main_menu.add.button(self.localization.get('switch_menu'), self.toggle_menu_system)
            self.main_menu.add.button(self.localization.get('exit'), self.exit_game)
            
            # Меню выбора уровня
            self.level_select_menu = pygame_menu.Menu(
                self.localization.get('level_select'),
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=theme
            )
            
            # Меню магазина
            self.shop_menu = pygame_menu.Menu(
                self.localization.get('shop'),
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=theme
            )
            
            # Меню инвентаря
            self.inventory_menu = pygame_menu.Menu(
                self.localization.get('inventory'),
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=theme
            )
            
            # Меню загрузки скинов
            self.upload_menu = pygame_menu.Menu(
                "Загрузить скин" if self.language == 'ru' else "Upload Skin",
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=theme
            )
            
            # Меню "Прочее"
            light_theme = pygame_menu.themes.THEME_BLUE.copy()
            light_theme.title_background_color = (173, 216, 230, 180)
            light_theme.title_font_color = (25, 25, 112)
            light_theme.widget_font_color = (25, 25, 112)
            light_theme.background_color = (0, 0, 0, 0)
            light_theme.title_font_size = 48
            light_theme.widget_font_size = 32
            light_theme.widget_margin = (0, 15)
            light_theme.widget_padding = 15
            
            self.other_menu = pygame_menu.Menu(
                "Прочее" if self.language == 'ru' else "Other",
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=light_theme,
                center_content=False
            )
            
            # Меню настроек (обновлено с выбором языка)
            self.settings_menu = pygame_menu.Menu(
                self.localization.get('settings'),
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=theme
            )
            
            # Разрешение экрана
            self.settings_menu.add.label(self.localization.get('resolution'), font_color=self.WHITE)
            self.settings_menu.add.selector('', 
                [('800x600', 0), ('1024x768', 1), ('1280x720', 2)], 
                onchange=self.change_resolution)
            
            # Полноэкранный режим
            self.settings_menu.add.label(self.localization.get('fullscreen'), font_color=self.WHITE)
            self.settings_menu.add.selector('', 
                [(self.localization.get('off'), False), (self.localization.get('on'), True)], 
                onchange=self.toggle_fullscreen_setting)
            
            # Громкость музыки
            self.settings_menu.add.label(self.localization.get('music_volume'), font_color=self.WHITE)
            self.settings_menu.add.range_slider('', 50, (0, 100), 1, 
                onchange=self.change_music_volume)
            
            # Громкость эффектов
            self.settings_menu.add.label(self.localization.get('sfx_volume'), font_color=self.WHITE)
            self.settings_menu.add.range_slider('', 70, (0, 100), 1, 
                onchange=self.change_sfx_volume)

            # Лимит частиц
            self.settings_menu.add.label(self.localization.get('particle_cap'), font_color=self.WHITE)
            self.settings_menu.add.range_slider('', self.max_particles_limit, (50, 500), 50,
                onchange=self.change_particle_cap)
            
            # Выбор языка - ОСОБЕННО ВАЖНО: добавляем селектор без вызова обработчика при инициализации
            self.settings_menu.add.label(self.localization.get('language'), font_color=self.WHITE)
            
            # Создаем селектор языка с задержкой вызова обработчика
            language_selector = self.settings_menu.add.selector('', 
                [('Русский', 'ru'), ('English', 'en')], 
                default=0 if self.language == 'ru' else 1)
            
            # Назначаем обработчик ПОСЛЕ создания селектора
            language_selector.set_onchange(self.change_language_setting)
            
            self.settings_menu.add.button(self.localization.get('back'), self.return_to_main_menu)
            
            # Меню промокодов
            self.promo_menu = pygame_menu.Menu(
                self.localization.get('promo_codes'),
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=theme
            )
            
            self.promo_input_widget = self.promo_menu.add.text_input(
                self.localization.get('enter_promo'), 
                default='', maxchar=20)
            self.promo_menu.add.button(self.localization.get('back'), self.return_to_main_menu)
            
            # Меню прокачки скинов
            self.skin_progression_menu = pygame_menu.Menu(
                self.localization.get('skin_progression'),
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=theme
            )
            
            # Добавляем кнопку "Назад"
            self.skin_progression_menu.add.button(self.localization.get('back'), self.return_to_main_menu)

            # Меню достижений
            self.achievements_menu = pygame_menu.Menu(
                self.localization.get('achievements'),
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=theme
            )
            self.update_achievements_menu()
            
        finally:
            self._creating_menus = False
    
    def show_hero_phrase(self):
        """Показать случайную фразу героя"""
        phrases = HERO_PHRASES['greetings'] if self.language == 'ru' else HERO_PHRASES_EN['greetings']
        self.hero_phrase = random.choice(phrases)
        self.hero_phrase_timer = 300  # Показываем фразу дольше (5 секунд при 60 FPS)
        return self.hero_phrase
    
    def on_hero_click(self):
        """Обработчик клика на героя - показывает новую фразу и обновляет меню"""
        self.show_hero_phrase()
        # Пересоздаем меню чтобы обновить фразу
        self.show_other_menu()
    
    def show_other_menu(self):
        """Показать меню 'Прочее' с героем"""
        if self.use_pygame_menu:
            try:
                # Показываем фразу только при заходе в меню, если еще не показывали
                if not self.hero_phrase_shown_on_entry:
                    self.show_hero_phrase()
                    self.hero_phrase_shown_on_entry = True
                
                # Очищаем и обновляем существующее меню
                self.other_menu.clear()
                
                # Добавляем элементы вертикально
                # Изображение героя
                if self.hero_image:
                    self.other_menu.add.image(self.hero_image, scale=(0.7, 0.7))
                    # Добавляем кнопку для взаимодействия с героем
                    click_text = "Нажмите на героя" if self.language == 'ru' else "Click on hero"
                    self.other_menu.add.button(click_text, self.on_hero_click, font_size=14)
                    self.other_menu.add.vertical_margin(10)
                
                # Фраза героя (показываем только если есть активная фраза)
                if self.hero_phrase and self.hero_phrase_timer > 0:
                    current_phrase = self.hero_phrase
                else:
                    current_phrase = ""  # Не показываем фразу, если таймер истек
                
                if current_phrase:
                    self.other_menu.add.label(current_phrase, font_color=self.CYAN, font_size=20)
                    self.other_menu.add.vertical_margin(20)
                
                # Разделитель
                self.other_menu.add.label("─" * 30, font_color=self.WHITE)
                self.other_menu.add.label("ЕЖЕДНЕВНЫЕ ЗАДАНИЯ" if self.language == 'ru' else "DAILY QUESTS", 
                                        font_color=self.GOLD)
                
                # Показываем задания
                if not self.current_quests:
                    self.refresh_daily_quests()
                
                for quest in self.current_quests:
                    progress = self.quest_progress.get(quest["id"], 0)
                    target = quest["target"]
                    
                    # Локализация описания
                    if self.language == 'ru':
                        description = quest.get("description_ru", quest.get("description_en", ""))
                    else:
                        description = quest.get("description_en", "")
                    
                    progress_text = f"{description}: {progress}/{target}"
                    reward_text = f"Награда: {quest['reward']} AM" if self.language == 'ru' else f"Reward: {quest['reward']} AM"
                    
                    self.other_menu.add.label(progress_text, font_color=self.WHITE, font_size=16)
                    self.other_menu.add.label(reward_text, font_color=self.PURPLE, font_size=14)
                    self.other_menu.add.vertical_margin(10)
                
                # Разделитель
                self.other_menu.add.label("─" * 30, font_color=self.WHITE)
                
                # Статистика комбо
                self.other_menu.add.label("СТАТИСТИКА КОМБО" if self.language == 'ru' else "COMBO STATS", 
                                        font_color=self.GOLD)
                self.other_menu.add.label(f"Максимальное комбо: {self.max_combo}" if self.language == 'ru' 
                                        else f"Max combo: {self.max_combo}", 
                                        font_color=self.GREEN, font_size=16)
                self.other_menu.add.label(f"Лучший множитель: x{self.max_combo_multiplier:.1f}" if self.language == 'ru' 
                                        else f"Best multiplier: x{self.max_combo_multiplier:.1f}", 
                                        font_color=self.PURPLE, font_size=16)
                
                self.other_menu.add.vertical_margin(30)
                self.other_menu.add.button(self.localization.get('back'), self.return_to_main_menu)
                
                # Переключаемся на это меню
                self.state = GameState.MENU
                self.menu = self.other_menu
                
            except Exception as e:
                logging.error(f"Error creating other menu: {e}")
                # В случае ошибки переключаемся на старую систему
                self.use_pygame_menu = False
                self.state = GameState.OTHER
        else:
            # Для старой системы меню
            # Показываем фразу только при заходе в меню, если еще не показывали
            if not self.hero_phrase_shown_on_entry:
                self.show_hero_phrase()
                self.hero_phrase_shown_on_entry = True
            self.state = GameState.OTHER
            
    def draw_other(self):
        """Отрисовка меню 'Прочее' для старой системы"""
        self.screen.fill(self.BLACK)
        title = self.title_font.render("Прочее" if self.language == 'ru' else "Other", True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        # Отображение героя (кликабельная область)
        hero_rect = None
        if self.hero_image:
            hero_x = self.SCREEN_WIDTH//2 - self.hero_image.get_width()//2
            hero_y = 100
            self.screen.blit(self.hero_image, (hero_x, hero_y))
            hero_rect = pygame.Rect(hero_x, hero_y, self.hero_image.get_width(), self.hero_image.get_height())
        
        # Фраза героя (показываем только если есть активная фраза)
        y_pos = 320
        if self.hero_phrase and self.hero_phrase_timer > 0:
            phrase_text = self.small_font.render(self.hero_phrase, True, self.CYAN)
            self.screen.blit(phrase_text, (self.SCREEN_WIDTH//2 - phrase_text.get_width()//2, y_pos))
            y_pos += 40
        
        # Сохраняем hero_rect для обработки кликов
        self.hero_click_rect = hero_rect
        
        # Ежедневные задания
        y_pos += 20
        quests_title = self.font.render("ЕЖЕДНЕВНЫЕ ЗАДАНИЯ" if self.language == 'ru' else "DAILY QUESTS", True, self.GOLD)
        self.screen.blit(quests_title, (self.SCREEN_WIDTH//2 - quests_title.get_width()//2, y_pos))
        y_pos += 40
        
        if not self.current_quests:
            self.refresh_daily_quests()
        
        for quest in self.current_quests:
            progress = self.quest_progress.get(quest["id"], 0)
            target = quest["target"]
            
            if self.language == 'ru':
                description = quest.get("description_ru", quest.get("description_en", ""))
            else:
                description = quest.get("description_en", "")
            
            progress_text = f"{description}: {progress}/{target}"
            reward_text = f"Награда: {quest['reward']} AM" if self.language == 'ru' else f"Reward: {quest['reward']} AM"
            
            progress_surf = self.small_font.render(progress_text, True, self.WHITE)
            reward_surf = self.small_font.render(reward_text, True, self.PURPLE)
            
            self.screen.blit(progress_surf, (self.SCREEN_WIDTH//2 - progress_surf.get_width()//2, y_pos))
            y_pos += 30
            self.screen.blit(reward_surf, (self.SCREEN_WIDTH//2 - reward_surf.get_width()//2, y_pos))
            y_pos += 40
        
        # Статистика комбо
        y_pos += 20
        combo_title = self.font.render("СТАТИСТИКА КОМБО" if self.language == 'ru' else "COMBO STATS", True, self.GOLD)
        self.screen.blit(combo_title, (self.SCREEN_WIDTH//2 - combo_title.get_width()//2, y_pos))
        y_pos += 40
        
        max_combo_text = f"Максимальное комбо: {self.max_combo}" if self.language == 'ru' else f"Max combo: {self.max_combo}"
        multiplier_text = f"Лучший множитель: x{self.max_combo_multiplier:.1f}" if self.language == 'ru' else f"Best multiplier: x{self.max_combo_multiplier:.1f}"
        
        max_combo_surf = self.font.render(max_combo_text, True, self.GREEN)
        multiplier_surf = self.font.render(multiplier_text, True, self.PURPLE)
        
        self.screen.blit(max_combo_surf, (self.SCREEN_WIDTH//2 - max_combo_surf.get_width()//2, y_pos))
        y_pos += 40
        self.screen.blit(multiplier_surf, (self.SCREEN_WIDTH//2 - multiplier_surf.get_width()//2, y_pos))
        
        # Кнопка Назад
        back_rect = pygame.Rect(self.SCREEN_WIDTH//2 - 100, self.SCREEN_HEIGHT - 80, 200, 50)
        mouse_pos = pygame.mouse.get_pos()
        
        # Эффект наведения
        if back_rect.collidepoint(mouse_pos):
            pygame.draw.rect(self.screen, (70, 70, 100), back_rect, border_radius=10)
        else:
            pygame.draw.rect(self.screen, (50, 50, 80), back_rect, border_radius=10)
        
        pygame.draw.rect(self.screen, self.GOLD, back_rect, 3, border_radius=10)
        back_text = self.font.render("Назад" if self.language == 'ru' else "Back", True, self.WHITE)
        self.screen.blit(back_text, (back_rect.centerx - back_text.get_width()//2, back_rect.centery - back_text.get_height()//2))
        
        # Подсказка
        hint_text = self.small_font.render("Нажмите на кнопку 'Назад' или ESC" if self.language == 'ru' else "Click 'Back' or press ESC", True, self.WHITE)
        self.screen.blit(hint_text, (self.SCREEN_WIDTH//2 - hint_text.get_width()//2, self.SCREEN_HEIGHT - 30))

    def draw_achievements(self):
        """Отрисовка достижений для старой системы меню"""
        self.screen.fill(self.BLACK)

        title = self.title_font.render(self.localization.get('achievements'), True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 40))

        unlocked = [k for k, v in self.achievements.items() if v]
        summary_text = self.font.render(f"{len(unlocked)}/{len(self.achievements)}", True, self.GREEN)
        self.screen.blit(summary_text, (self.SCREEN_WIDTH//2 - summary_text.get_width()//2, 100))

        y = 160
        for key, done in self.achievements.items():
            status = "✓" if done else "…"
            color = self.GREEN if done else self.WHITE
            text = self.small_font.render(f"{status} {key}", True, color)
            self.screen.blit(text, (100, y))
            y += 30
            if y > self.SCREEN_HEIGHT - 100:
                break

        back_rect = pygame.Rect(self.SCREEN_WIDTH//2 - 100, self.SCREEN_HEIGHT - 80, 200, 50)
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.rect(self.screen, (70, 70, 100) if back_rect.collidepoint(mouse_pos) else (50, 50, 80), back_rect, border_radius=10)
        pygame.draw.rect(self.screen, self.GOLD, back_rect, 3, border_radius=10)
        back_text = self.font.render("Назад" if self.language == 'ru' else "Back", True, self.WHITE)
        self.screen.blit(back_text, (back_rect.centerx - back_text.get_width()//2, back_rect.centery - back_text.get_height()//2))
    
    def change_language_setting(self, value, language):
        """Изменение языка из настроек"""
        # Обновляем язык без немедленного пересоздания меню
        old_language = self.language
        self.language = language
        self.localization.set_language(language)
        self.save_language_settings()
        
        # Обновляем заголовок окна
        pygame.display.set_caption(self.localization.get('game_title'))
        
        # Только если язык действительно изменился, обновляем меню
        if old_language != language:
            # Отложенное обновление меню
            pygame.time.set_timer(pygame.USEREVENT, 100)
            
            # Обновляем текст кнопок
            self.create_menu_options()
            self.create_shop_items()
            
            # Показываем сообщение
            if hasattr(self, 'settings_menu'):
                # Здесь можно добавить временное сообщение о смене языка
                pass
    
    def start_game_from_menu(self):
        """Запуск игры из меню"""
        if self.menu and self.menu.is_enabled():
            self.menu.disable()
        self.start_game()
    
    def start_editor_from_menu(self):
        """Запуск редактора из меню"""
        if self.menu and self.menu.is_enabled():
            self.menu.disable()
        self.start_editor()
    
    def open_daily_chest_from_menu(self):
        """Открытие сундука из меню"""
        self.open_daily_chest()
    
    def toggle_login_from_menu(self):
        """Переключение логина из меню"""
        self.toggle_login()
    
    def show_skin_progression_menu(self):
        """Показать меню прокачки скинов"""
        self.update_skin_progression_menu()
        self.state = GameState.MENU
        self.menu = self.skin_progression_menu

    def show_achievements_menu(self):
        """Показать меню достижений"""
        self.update_achievements_menu()
        self.state = GameState.MENU
        self.menu = self.achievements_menu

    def update_achievements_menu(self):
        """Обновление меню достижений"""
        if not hasattr(self, 'achievements_menu'):
            return

        self.achievements_menu.clear()
        self.achievements_menu.add.label(self.localization.get('achievements').upper(), font_color=self.GOLD)

        unlocked = [name for name, done in self.achievements.items() if done]
        total = len(self.achievements)
        unlocked_count = len(unlocked)

        summary = f"{unlocked_count}/{total}"
        self.achievements_menu.add.label(
            f"{self.localization.get('achievements')}: {summary}",
            font_color=self.GREEN
        )

        if unlocked:
            self.achievements_menu.add.label("✓ " + ", ".join(unlocked), font_color=self.CYAN, font_size=18)

        # Список доступных достижений
        self.achievements_menu.add.label("─" * 30, font_color=self.WHITE)
        for key in self.achievements:
            status = "✓" if self.achievements[key] else "…"
            text = f"{status} {key}"
            color = self.GREEN if self.achievements[key] else self.WHITE
            self.achievements_menu.add.label(text, font_color=color, font_size=20)

        self.achievements_menu.add.button(self.localization.get('back'), self.return_to_main_menu)
        
    def update_skin_progression_menu(self):
        """Обновление меню прокачки скинов с локализацией"""
        self.skin_progression_menu.clear()
        
        self.skin_progression_menu.add.label(
            self.localization.get('skin_progression').upper(), 
            font_color=self.GOLD
        )
        
        if self.account_system.current_account:
            self.skin_progression_menu.add.label(
                f'{self.localization.get("login")}: {self.account_system.current_account["username"]}',
                font_color=self.WHITE
            )
        
        # Информация о текущем скине
        skin = self.skins.get(self.current_skin, {})
        skin_name = skin.get("name", "Unknown")
        if isinstance(skin_name, dict):
            skin_name = skin_name.get(self.language, "Unknown")
        self.skin_progression_menu.add.label(
            f'{self.localization.get("skin_progress")}: {skin_name}',
            font_color=self.CYAN
        )
        
        if self.player and hasattr(self.player, 'skin_level'):
            # Уровень скина
            level_text = f'{self.localization.get("level")}: {self.player.skin_level}/{MAX_SKIN_LEVEL}'
            self.skin_progression_menu.add.label(level_text, font_color=self.GREEN)
            
            # Опыт текущего уровня
            if self.player.skin_level < len(EXP_PER_LEVEL):
                next_level_exp = EXP_PER_LEVEL[self.player.skin_level]
                current_level_exp = EXP_PER_LEVEL[self.player.skin_level - 1]
                exp_in_current = self.player.skin_exp - current_level_exp
                exp_needed = next_level_exp - current_level_exp
                exp_text = f'{self.localization.get("exp")}: {exp_in_current}/{exp_needed}'
            else:
                exp_text = f'{self.localization.get("exp")}: {self.player.skin_exp} (МАКС. УРОВЕНЬ)'
            self.skin_progression_menu.add.label(exp_text, font_color=self.PURPLE)
            
            # Общий опыт
            total_exp_text = f'{self.localization.get("total_exp")}: {self.player.total_exp}'
            self.skin_progression_menu.add.label(total_exp_text, font_color=self.GOLD)
            
            # Прогресс
            progress = self.player.get_exp_percentage()
            progress_text = f'{self.localization.get("progress")}: {progress:.1f}%'
            self.skin_progression_menu.add.label(progress_text, font_color=self.WHITE)
            
            # Пройденные уровни
            completed_text = f'{self.localization.get("completed_levels")}: {self.get_completed_custom_levels()}'
            self.skin_progression_menu.add.label(completed_text, font_color=self.LIME)
        else:
            self.skin_progression_menu.add.label('Данные игрока не загружены', font_color=self.RED)
        
        # Разделитель
        self.skin_progression_menu.add.label("─" * 30, font_color=self.WHITE)
        self.skin_progression_menu.add.label("НАГРАДЫ ЗА УРОВНИ", font_color=self.GOLD)
        
        # Показываем информацию о первых 5 уровнях
        for level in range(1, min(6, MAX_SKIN_LEVEL + 1)):
            if self.player and hasattr(self.player, 'skin_level') and self.player.skin_level >= level:
                status = "✓ ОТКРЫТО"
                color = self.GREEN
            else:
                if level < len(EXP_PER_LEVEL):
                    status = f"Требуется {EXP_PER_LEVEL[level]} опыта"
                else:
                    status = "МАКС. УРОВЕНЬ"
                color = self.WHITE
            
            self.skin_progression_menu.add.label(
                f'Уровень {level}: {status}',
                font_color=color,
                font_size=20
            )
        
        self.skin_progression_menu.add.button(self.localization.get('back'), self.return_to_main_menu)

    def exit_game(self):
        """Выход из игры"""
        self.running = False

    def toggle_menu_system(self):
        """Переключение между старой и новой системой меню"""
        self.use_pygame_menu = not self.use_pygame_menu
        
        self.state = GameState.MENU
        
        if self.use_pygame_menu:
            self.menu = self.main_menu
            if self.menu:
                self.menu.enable()
        else:
            if self.menu:
                self.menu.disable()
            self.menu = None
            self.selected_option = 0

    def show_level_select_menu(self):
        """Показать меню выбора уровня с локализацией"""
        self.level_select_menu.clear()
        self.level_select_menu.add.label(
            self.localization.get('level_select').upper(), 
            font_color=self.GOLD
        )
        
        for i, level in enumerate(self.available_levels):
            # Локализуем описание уровня
            level_name = level['name']
            level_desc = level['description']
            
            # Если описание нуждается в локализации
            if level_desc in self.localization.texts:
                level_desc = self.localization.get(level_desc)
            
            self.level_select_menu.add.button(
                f"{level_name} - {level_desc}", 
                lambda idx=i: self.start_selected_level(idx)
            )
        
        self.level_select_menu.add.button(self.localization.get('back'), self.return_to_main_menu)
        self.state = GameState.MENU
        self.menu = self.level_select_menu

    def show_shop_menu(self):
        """Показать меню магазина с локализацией"""
        self.shop_menu.clear()
        self.shop_menu.add.label(self.localization.get('shop').upper(), font_color=self.GOLD)
        
        # Баланс
        balance_text = f'{self.localization.get("amethysts")}: {self.total_amethysts}'
        self.shop_menu.add.label(balance_text, font_color=self.PURPLE, font_size=24)
        
        # Добавляем разделитель
        self.shop_menu.add.label("─" * 40, font_color=self.WHITE)
        
        # Отображаем товары
        for i, item in enumerate(self.shop_items):
            can_afford = self.total_amethysts >= item.cost
            color = self.GREEN if can_afford else self.RED
            
            # Информация о товаре
            item_info = f"{item.get_name()} - {item.cost} AM"
            self.shop_menu.add.label(item_info, font_color=color, font_size=22)
            
            # Описание товара
            self.shop_menu.add.label(item.get_description(), font_color=self.WHITE, font_size=18)
            
            # Кнопка покупки
            btn_text = 'Купить' if can_afford and self.language == 'ru' else 'Buy' if can_afford else self.localization.get('purchase_failed')
            self.shop_menu.add.button(
                btn_text,
                lambda i=item: self.buy_shop_item_from_menu(i),
                background_color=color if can_afford else (100, 100, 100),
                font_color=self.BLACK if can_afford else self.WHITE,
                font_size=20
            )
            
            # Отступ между товарами
            if i < len(self.shop_items) - 1:
                self.shop_menu.add.label("", font_color=self.WHITE)
        
        self.shop_menu.add.button(self.localization.get('back'), self.return_to_main_menu)
        self.state = GameState.MENU
        self.menu = self.shop_menu

    def show_inventory_menu(self):
        """Показать меню инвентаря с локализацией"""
        self.inventory_menu.clear()
        
        self.inventory_menu.add.label(
            self.localization.get('inventory').upper(), 
            font_color=self.GOLD
        )
        
        if self.account_system.current_account:
            self.inventory_menu.add.label(
                f'{self.localization.get("login")}: {self.account_system.current_account["username"]}',
                font_color=self.WHITE
            )
        
        # Создаем сетку для скинов с пагинацией
        skin_items = list(self.skins.items())
        total_skins = len(skin_items)
        start_index = self.inventory_page * self.skins_per_page
        end_index = min(start_index + self.skins_per_page, total_skins)
        
        for i in range(start_index, end_index):
            skin_id, skin = skin_items[i]
            skin_color = self.GREEN if skin["owned"] else (100, 100, 100)
            border_color = self.GOLD if skin_id == self.current_skin else skin_color
            
            # Получаем локализованное название скина
            skin_name = skin["name"]
            if isinstance(skin_name, dict):
                skin_name = skin_name.get(self.language, skin_name.get('ru', 'Unknown'))
            
            # Создаем кнопку для скина
            self.inventory_menu.add.button(
                skin_name,
                lambda sid=skin_id: self.select_skin_from_menu(sid),
                background_color=border_color,
                font_color=self.BLACK if skin["owned"] else self.WHITE,
                font_size=20
            )
        
        # Кнопки навигации
        if total_skins > self.skins_per_page:
            nav_text = f"{self.inventory_page + 1}/{(total_skins + self.skins_per_page - 1) // self.skins_per_page}"
            self.inventory_menu.add.label(nav_text, font_color=self.CYAN)
            
            if self.inventory_page > 0:
                self.inventory_menu.add.button("◀ Предыдущая" if self.language == 'ru' else "◀ Previous", 
                                             self.prev_inventory_page)
            if end_index < total_skins:
                self.inventory_menu.add.button("Следующая ▶" if self.language == 'ru' else "Next ▶", 
                                             self.next_inventory_page)
        
        # Добавляем разделитель
        self.inventory_menu.add.label("─" * 40, font_color=self.WHITE)
        
        # Информация о текущем скине
        skin = self.skins.get(self.current_skin, {})
        skin_name = skin.get("name", "Unknown")
        if isinstance(skin_name, dict):
            skin_name = skin_name.get(self.language, skin_name.get('ru', 'Unknown'))
        self.inventory_menu.add.label(
            f'{self.localization.get("skin_progress")}: {skin_name}',
            font_color=self.CYAN
        )
        
        # Баланс
        self.inventory_menu.add.label(
            f'{self.localization.get("amethysts")}: {self.total_amethysts}',
            font_color=self.PURPLE
        )
        
        # Кнопка для загрузки новых скинов
        self.inventory_menu.add.button(
            "Загрузить новый скин" if self.language == 'ru' else "Upload New Skin",
            self.show_skin_upload_menu,
            background_color=(100, 100, 200),
            font_color=self.WHITE
        )
        
        self.inventory_menu.add.button(self.localization.get('back'), self.return_to_main_menu)
        
        self.state = GameState.MENU
        self.menu = self.inventory_menu
    
    def prev_inventory_page(self):
        """Предыдущая страница инвентаря"""
        if self.inventory_page > 0:
            self.inventory_page -= 1
        self.show_inventory_menu()
    
    def next_inventory_page(self):
        """Следующая страница инвентаря"""
        total_pages = (len(self.skins) + self.skins_per_page - 1) // self.skins_per_page
        if self.inventory_page < total_pages - 1:
            self.inventory_page += 1
        self.show_inventory_menu()
    
    def show_settings_menu(self):
        """Показать меню настроек"""
        self.state = GameState.MENU
        self.menu = self.settings_menu

    def show_promo_menu(self):
        """Показать меню промокодов"""
        self.state = GameState.MENU
        self.menu = self.promo_menu

    def toggle_login(self):
        """Переключение логина/логаута"""
        if self.account_system.current_account:
            self.account_system.current_account = None
            self.total_amethysts = 0
            self.login_message = self.localization.get('logout_success')
            self.state = GameState.MENU
            if self.use_pygame_menu:
                self.menu = self.main_menu
        else:
            self.state = GameState.LOGIN
            self.menu = None

    def change_resolution(self, value, index):
        """Изменение разрешения экрана"""
        resolutions = [(800, 600), (1024, 768), (1280, 720)]
        new_size = resolutions[index]
        
        if not self.fullscreen:
            # ИСПРАВЛЕНИЕ: Масштабируем позиции игрока и объектов при изменении разрешения
            scale_x = new_size[0] / self.SCREEN_WIDTH if self.SCREEN_WIDTH > 0 else 1.0
            scale_y = new_size[1] / self.SCREEN_HEIGHT if self.SCREEN_HEIGHT > 0 else 1.0
            
            # Масштабируем позицию игрока, если игра активна
            if self.state == GameState.PLAYING and self.player:
                self.player.x = int(self.player.x * scale_x)
                self.player.y = int(self.player.y * scale_y)
                self.camera_x = int(self.camera_x * scale_x)
            
            # Масштабируем препятствия
            if hasattr(self, 'obstacles'):
                for obj in self.obstacles:
                    obj.x = int(obj.x * scale_x)
                    obj.y = int(obj.y * scale_y)
            
            # Масштабируем аметисты
            if hasattr(self, 'amethysts'):
                for amethyst in self.amethysts:
                    amethyst.x = int(amethyst.x * scale_x)
                    amethyst.y = int(amethyst.y * scale_y)
            
            # Масштабируем бонусы
            if hasattr(self, 'bonuses'):
                for bonus in self.bonuses:
                    bonus.x = int(bonus.x * scale_x)
                    bonus.y = int(bonus.y * scale_y)
            
            # Масштабируем level_end_x
            if hasattr(self, 'level_end_x'):
                self.level_end_x = int(self.level_end_x * scale_x)
            
            self.SCREEN_WIDTH, self.SCREEN_HEIGHT = new_size
            self.original_size = new_size
            self.screen = pygame.display.set_mode(new_size)
            
            # Сбрасываем кэш фона для пересоздания
            self.cached_bg_surface = None
            self.cached_ground_surface = None
            
            # Обновляем фон и меню под новое разрешение
            self.menu_bg_surface = self.create_gradient_menu_bg()
            if self.menu_bg:
                self.menu_bg = pygame.transform.scale(self.menu_bg, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
            if self.game_bg:
                self.game_bg = pygame.transform.scale(self.game_bg, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
            self.create_menus()

    def toggle_fullscreen_setting(self, value, fullscreen):
        """Переключение полноэкранного режима из настроек"""
        self.toggle_fullscreen()
        self.save_language_settings()

    def change_music_volume(self, value):
        """Изменение громкости музыки"""
        self.music_volume = value
        pygame.mixer.music.set_volume(value / 100)
        self.save_language_settings()

    def change_sfx_volume(self, value):
        """Изменение громкости звуковых эффектов"""
        self.sfx_volume = value
        # Сохраняем настройки
        self.save_language_settings()

    def change_particle_cap(self, value):
        """Изменение лимита частиц"""
        self.max_particles_limit = int(value)
        if hasattr(self, 'particle_system'):
            self.particle_system.max_particles = self.max_particles_limit
        self.save_language_settings()

    def buy_shop_item_from_menu(self, item):
        """Покупка товара из меню магазина"""
        success = self.buy_shop_item(item)
        if success:
            # Обновляем данные игрока после покупки
            account_data = self.account_system.get_current_account_data()
            self.total_amethysts = account_data.get("amethysts", 0)
            # Показываем сообщение об успешной покупке
            success_menu = pygame_menu.Menu(
                self.localization.get('purchase_success'),
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=self.update_menu_theme()
            )
            success_menu.add.label(f'{item.get_name()} {self.localization.get("purchase_success").lower()}', font_color=self.GREEN)
            success_menu.add.button(self.localization.get('back'), self.show_shop_menu)
            self.menu = success_menu
        else:
            # Показываем сообщение об ошибке
            error_menu = pygame_menu.Menu(
                self.localization.get('purchase_failed'),
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=self.update_menu_theme()
            )
            if self.login_message:
                error_menu.add.label(self.login_message, font_color=self.RED)
            else:
                error_menu.add.label(self.localization.get('purchase_failed'), font_color=self.RED)
            error_menu.add.button(self.localization.get('back'), self.show_shop_menu)
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
                    self.localization.get('purchase_failed'),
                    self.SCREEN_WIDTH,
                    self.SCREEN_HEIGHT,
                    theme=self.update_menu_theme()
                )
                error_menu.add.label(self.localization.get('purchase_failed'), font_color=self.RED)
                error_menu.add.button(self.localization.get('back'), self.show_inventory_menu)
                self.menu = error_menu
        else:
            # Нельзя купить
            error_menu = pygame_menu.Menu(
                self.localization.get('purchase_failed'),
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT,
                theme=self.update_menu_theme()
            )
            error_menu.add.label(f"Нужно {skin['cost']} аметистов!", font_color=self.RED)
            error_menu.add.button(self.localization.get('back'), self.show_inventory_menu)
            self.menu = error_menu

    def redeem_promo_from_menu(self):
        """Активация промокода из меню"""
        code = self.promo_input_widget.get_value()
        if code:
            result = self.promo_system.redeem_promo(code)
            # Локализуем сообщение результата
            if "received" in result.lower():
                localized_result = self.localization.get('promo_success')
            elif "invalid" in result.lower():
                localized_result = self.localization.get('promo_invalid')
            elif "already used" in result.lower():
                localized_result = self.localization.get('promo_used')
            else:
                localized_result = result
            
            self.promo_menu.add.label(localized_result, 
                font_color=self.GREEN if "received" in result.lower() else self.RED, 
                label_id="promo_result")
            
            if "received" in result.lower():
                account_data = self.account_system.get_current_account_data()
                self.total_amethysts = account_data.get("amethysts", 0)

    # ОСНОВНЫЕ МЕТОДЫ ИГРЫ
    def load_available_levels(self):
        """Загрузка списка доступных уровней с локализацией"""
        levels = [
            {
                "name": "Случайная генерация" if self.language == 'ru' else "Random Generation",
                "file": "random", 
                "description": "Бесконечная случайная генерация" if self.language == 'ru' else "Infinite random generation"
            },
            {
                "name": "Обучение" if self.language == 'ru' else "Tutorial",
                "file": "levels/tutorial.json", 
                "description": "Обучение для новичков" if self.language == 'ru' else "Beginner tutorial"
            },
            {
                "name": "Лёгкий забег" if self.language == 'ru' else "Easy Run",
                "file": "levels/easy.json", 
                "description": "Простой уровень с платформами" if self.language == 'ru' else "Simple level with platforms"
            },
            {
                "name": "Платформенный рай" if self.language == 'ru' else "Platform Paradise",
                "file": "levels/platforms.json", 
                "description": "Много платформ и прыжков" if self.language == 'ru' else "Many platforms and jumps"
            },
            {
                "name": "Шиповая арена" if self.language == 'ru' else "Spike Challenge",
                "file": "levels/spikes.json", 
                "description": "Сложный уровень с шипами" if self.language == 'ru' else "Difficult level with spikes"
            },
            {
                "name": "Ледяной лабиринт" if self.language == 'ru' else "Ice Maze",
                "file": "levels/ice.json", 
                "description": "Скользкий ледяной уровень" if self.language == 'ru' else "Slippery ice level"
            },
            {
                "name": "Огненная бездна" if self.language == 'ru' else "Fire Abyss",
                "file": "levels/fire.json", 
                "description": "Горячий уровень с лавой" if self.language == 'ru' else "Hot level with lava"
            },
            {
                "name": "Космический прыжок" if self.language == 'ru' else "Space Jump",
                "file": "levels/space.json", 
                "description": "Нулевая гравитация в космосе" if self.language == 'ru' else "Zero gravity in space"
            },
            {
                "name": "Босс: Дракон" if self.language == 'ru' else "Boss: Dragon",
                "file": "levels/boss_dragon.json", 
                "description": "Сразитесь с огнедышащим драконом" if self.language == 'ru' else "Fight the fire-breathing dragon"
            },
        ]
        
        # Добавляем пользовательские уровни
        custom_levels_folder = "levels"
        if os.path.exists(custom_levels_folder):
            for filename in os.listdir(custom_levels_folder):
                if filename.endswith(".json") and filename not in ["tutorial.json", "easy.json", "platforms.json", "spikes.json"]:
                    level_name = filename.replace(".json", "").replace("_", " ").title()
                    if self.language == 'ru':
                        levels.append({
                            "name": f"Пользовательский: {level_name}",
                            "file": f"{custom_levels_folder}/{filename}",
                            "description": "Пользовательский уровень"
                        })
                    else:
                        levels.append({
                            "name": f"Custom: {level_name}",
                            "file": f"{custom_levels_folder}/{filename}",
                            "description": "Custom level"
                        })
        
        return levels
    
    def show_level_select_menu(self):
        """Показать меню выбора уровня с пресет-уровнями"""
        self.level_select_menu.clear()
        self.level_select_menu.add.label(
            self.localization.get('level_select').upper(), 
            font_color=self.GOLD
        )
        
        # Добавляем стандартные уровни
        for i, level in enumerate(self.available_levels):
            self.level_select_menu.add.button(
                f"{level['name']} - {level['description']}", 
                lambda idx=i: self.start_selected_level(idx)
            )
        
        # Добавляем разделитель
        self.level_select_menu.add.label("─" * 30, font_color=self.WHITE)
        preset_title = "ПРЕСЕТ-УРОВНИ (1-10)" if self.language == 'ru' else "PRESET LEVELS (1-10)"
        self.level_select_menu.add.label(preset_title, font_color=self.CYAN)
        
        # Добавляем пресет-уровни
        for i, level in enumerate(self.preset_levels):
            # Проверяем, пройден ли уровень
            is_completed = level["name"] in self.completed_levels
            status = "✓ " if is_completed else ""
            
            # Локализуем имя уровня
            level_name = level['name']
            if ':' in level_name:
                parts = level_name.split(': ')
                if self.language == 'ru':
                    level_name = f"{parts[0]}: {parts[1]}"
            
            self.level_select_menu.add.button(
                f"{status}{level_name}", 
                lambda idx=i: self.start_preset_level(idx)
            )
        
        self.level_select_menu.add.button(self.localization.get('back'), self.return_to_main_menu)
        self.state = GameState.MENU
        self.menu = self.level_select_menu
    
    def start_preset_level(self, index):
        """Запуск пресет-уровня"""
        if 0 <= index < len(self.preset_levels):
            level_data = self.preset_levels[index]
            self.start_game_with_level(level_data)
            self.state = GameState.PLAYING
            
            # Запоминаем имя уровня для награды опытом
            self.current_level_name = level_data["name"]
    
    def hsv_to_rgb(self, h, s, v):
        """Конвертация HSV в RGB цвет"""
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
        """Линейная интерполяция"""
        return start + (end - start) * t
    
    def ease_out_quad(self, x):
        """Функция easing для плавных анимаций"""
        return 1 - (1 - x) * (1 - x)
    
    def create_gradient_surface(self, width, height, start_color, end_color):
        """Создание градиентной поверхности"""
        surf = pygame.Surface((width, height))
        
        for y in range(height):
            t = y / height
            r = self.lerp(start_color[0], end_color[0], t)
            g = self.lerp(start_color[1], end_color[1], t)
            b = self.lerp(start_color[2], end_color[2], t)
            
            pygame.draw.line(surf, (int(r), int(g), int(b)), (0, y), (width, y))
        
        return surf
    
 # ========================================================================
    # СИСТЕМА ПРОКАЧКИ СКИНОВ
    # ========================================================================
    def calculate_level_exp(self, amethysts_collected, score, custom_levels_completed):
        base_exp = (amethysts_collected * 15) + (score // 2) + 50
        bonus_exp = custom_levels_completed * 25
        total_exp = int(base_exp + bonus_exp)
        
        if self.exp_boost_active:
            total_exp = int(total_exp * 1.2)
            self.exp_boost_timer -= 1
            if self.exp_boost_timer <= 0:
                self.exp_boost_active = False
        
        return max(10, total_exp)
    
    def calculate_level_progress(self):
        # Используем пройденную дистанцию для оценки прогресса
        if self.level_end_x and self.level_end_x > 0:
            return min(100, int((self.distance_traveled / self.level_end_x) * 100))
        return min(100, int(self.distance_traveled / 15))

    def compute_level_end_x(self, level_data):
        """Расчет длины уровня по данным"""
        base = level_data.get("level_end_x", 3000)
        obstacles = level_data.get("obstacles", [])
        amethysts = level_data.get("amethysts", [])

        max_obj = 0
        if obstacles:
            max_obj = max(o.get("x", 0) + o.get("w", 60) for o in obstacles)

        max_ame = 0
        if amethysts:
            max_ame = max(a.get("x", 0) + 50 for a in amethysts)

        return max(base, max_obj + 200, max_ame + 200)
    
    def award_exp_on_level_complete(self, level_name):
        if not self.player or not hasattr(self.player, 'skin_level'):
            logging.error("Cannot award EXP: player not initialized")
            return
            
        if level_name not in self.completed_levels:
            self.completed_levels.append(level_name)
            self.player.add_completed_level()
            
            collected_amethysts = len([a for a in self.amethysts if a.collected])
            self.level_progress[level_name] = {
                "score": self.score,
                "amethysts": collected_amethysts,
                "date": datetime.datetime.now().isoformat()
            }
            
            self.save_level_progress()
        
        collected_amethysts = len([a for a in self.amethysts if a.collected])
        custom_levels_completed = self.get_completed_custom_levels()
        
        exp_earned = self.calculate_level_exp(
            collected_amethysts,
            self.score,
            custom_levels_completed
        )
        
        logging.info(f"Awarding {exp_earned} EXP for level {level_name}")
        
        old_level = self.player.skin_level
        self.player.add_exp(exp_earned)
        
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
        
        level_up_msg = ""
        if old_level < self.player.skin_level:
            level_up_msg = f" {self.localization.get('level_up')} {old_level}→{self.player.skin_level}"
        
        self.exp_message = f"+{exp_earned} Square-EXP!{level_up_msg}"
        self.exp_message_timer = 180
        
        self.particle_system.add_particles(
            self.SCREEN_WIDTH // 2,
            self.SCREEN_HEIGHT // 2,
            self.GOLD,
            count=20,
            speed=2,
            size_variation=5
        )
        
        self.play_sound_safe(self.powerup_sound)
        
    def debug_skin_progression(self):
        print("\n=== SKIN PROGRESSION DEBUG ===")
        print(f"Player exists: {self.player is not None}")
        if self.player:
            print(f"Player skin level: {self.player.skin_level}")
            print(f"Player skin EXP: {self.player.skin_exp}")
            print(f"Player total EXP: {self.player.total_exp}")
            print(f"Completed levels: {self.player.completed_levels}")
            
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
        
        if not self.player:
            self.current_skin = new_skin_id
            self.safe_load_skin()
            return True
        
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
                self.player.skin_level = 1
                self.player.skin_exp = 0
                logging.info(f"New skin {new_skin_id}, starting at level 1")
        
        self.safe_load_skin()
        logging.info(f"Switched skin from {old_skin} to {new_skin_id}")
        return True
        
    def get_completed_custom_levels(self):
        if not self.player:
            return 0
        return self.player.completed_levels
    
    def load_level_progress(self):
        try:
            if os.path.exists("level_progress.json"):
                with open("level_progress.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.completed_levels = data.get("completed_levels", [])
                    self.level_progress = data.get("level_progress", {})
                    
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
        try:
            data = {
                "completed_levels": self.completed_levels,
                "level_progress": self.level_progress
            }
            
            with open("level_progress.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving level progress: {e}")
            
    # СИСТЕМА 10 ПРЕСЕТ-УРОВНЕЙ
    def generate_preset_levels(self):
        preset_levels = []
        
        # Уровень 1: Обучение
        level1 = {
            "name": "Preset 1: Tutorial" if self.language == 'en' else "Пресет 1: Обучение",
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
            "name": "Preset 2: Platform Paradise" if self.language == 'en' else "Пресет 2: Платформенный рай",
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
        
        # Добавляем первые 5 уровней
        preset_levels.extend([level1, level2])
        
        # Генерация остальных уровней
        for i in range(3, 11):
            level = self.generate_random_preset_level(i)
            preset_levels.append(level)
        
        return preset_levels
    
    def generate_random_preset_level(self, level_num):
        difficulty = min(1.0, (level_num - 1) / 10)
        level_length = int(2000 + difficulty * 3000)
        
        level_name_en = f"Preset {level_num}: Challenge"
        level_name_ru = f"Пресет {level_num}: Испытание"
        
        level_data = {
            "name": level_name_en if self.language == 'en' else level_name_ru,
            "player_start_x": 150,
            "player_start_y": 400,
            "speed": int(5 + difficulty * 5),
            "level_end_x": level_length,
            "obstacles": [],
            "amethysts": [],
            "random_generation": False
        }
        
        num_obstacles = int(8 + difficulty * 12)
        
        for i in range(num_obstacles):
            x = 300 + (i * level_length) // num_obstacles + random.randint(-100, 100)
            rand_type = random.random()
            
            if rand_type < 0.4:  # Шипы
                height = random.randint(80, 120)
                level_data["obstacles"].append({
                    "x": x,
                    "y": 500 - height,
                    "w": 60,
                    "h": height,
                    "type": "spike",
                    "color": [220, 20, 60]
                })
            elif rand_type < 0.65:  # Платформы
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
                
                if random.random() < 0.5:
                    level_data["amethysts"].append({
                        "x": x + width // 2 - 15,
                        "y": y - 50,
                        "size": random.randint(25, 35)
                    })
            elif rand_type < 0.85:  # Прыгучие платформы
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
            else:  # Исчезающие платформы
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
        
        num_amethysts = int(5 + difficulty * 15)
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
    
     # УЛУЧШЕННАЯ ГЕНЕРАЦИЯ ПРЕПЯТСТВИЙ
    def spawn_random_obstacle(self):
        obstacle_types = [
            (ObstacleType.SPIKE, 0.30),
            (ObstacleType.PLATFORM, 0.22),
            (ObstacleType.MOVING_SPIKE, 0.13),
            (ObstacleType.SPIKE_CLUSTER, 0.08),
            (ObstacleType.BOUNCING_PLATFORM, 0.07),
            (ObstacleType.DISAPPEARING_PLATFORM, 0.06),
            (ObstacleType.ROTATING_SPIKE, 0.08),  # КОНТЕНТ: Новое препятствие
            (ObstacleType.ICE_PLATFORM, 0.06)  # КОНТЕНТ: Новое препятствие
        ]
        
        types, weights = zip(*obstacle_types)
        obstacle_type = random.choices(types, weights=weights)[0]
        
        if obstacle_type == ObstacleType.SPIKE:
            self.spawn_spike()
        elif obstacle_type == ObstacleType.PLATFORM:
            self.spawn_platform()
        elif obstacle_type == ObstacleType.MOVING_SPIKE:
            self.spawn_moving_spike()
        elif obstacle_type == ObstacleType.SPIKE_CLUSTER:
            self.spawn_spike_cluster()
        elif obstacle_type == ObstacleType.BOUNCING_PLATFORM:
            self.spawn_bouncing_platform()
        elif obstacle_type == ObstacleType.DISAPPEARING_PLATFORM:
            self.spawn_disappearing_platform()
        elif obstacle_type == ObstacleType.ROTATING_SPIKE:
            self.spawn_rotating_spike()
        elif obstacle_type == ObstacleType.ICE_PLATFORM:
            self.spawn_ice_platform()
    
    def spawn_spike(self):
        height = random.choice([80, 100, 120, 150])
        spike_color = random.choice([
            (220, 20, 60),
            (255, 69, 0),
            (199, 21, 133),
            (178, 34, 34)
        ])
        
        self.obstacles.append(Obstacle(
            self.SCREEN_WIDTH + 50,
            self.SCREEN_HEIGHT - height,
            ObstacleType.SPIKE,
            60, height,
            spike_color
        ))
    
    def spawn_platform(self):
        width = random.randint(120, 250)
        height = 25
        y_pos = random.randint(300, 450)
        
        platform_color = random.choice([
            (70, 130, 180),
            (100, 149, 237),
            (30, 144, 255),
            (0, 191, 255)
        ])
        
        platform = Obstacle(
            self.SCREEN_WIDTH + 50,
            y_pos,
            ObstacleType.PLATFORM,
            width, height,
            platform_color
        )
        self.obstacles.append(platform)
        
        if random.random() < 0.4:
            self.amethysts.append(Amethyst(
                platform.x + width // 2 - 15,
                y_pos - 40,
                size=random.randint(25, 35)
            ))
    
    def spawn_moving_spike(self):
        height = random.choice([60, 80, 100])
        spike_color = (255, 69, 0)
        
        spike = Obstacle(
            self.SCREEN_WIDTH + 50,
            self.SCREEN_HEIGHT - height,
            ObstacleType.MOVING_SPIKE,
            50, height,
            spike_color
        )
        spike.move_speed = random.uniform(1.0, 3.0)
        spike.original_y = spike.y
        self.obstacles.append(spike)
    
    def spawn_spike_cluster(self):
        cluster_width = random.randint(200, 350)
        spike_count = random.randint(3, 6)
        spike_width = cluster_width // spike_count
        
        for i in range(spike_count):
            spike_height = random.choice([70, 90, 110, 130])
            self.obstacles.append(Obstacle(
                self.SCREEN_WIDTH + 50 + i * spike_width,
                self.SCREEN_HEIGHT - spike_height,
                ObstacleType.SPIKE,
                spike_width - 10, spike_height,
                (178, 34, 34)
            ))
    
    def spawn_bouncing_platform(self):
        width = random.randint(120, 200)
        height = 25
        y_pos = random.randint(300, 450)
        
        platform = Obstacle(
            self.SCREEN_WIDTH + 50,
            y_pos,
            ObstacleType.BOUNCING_PLATFORM,
            width, height,
            (0, 200, 100)
        )
        platform.bounce_power = random.uniform(1.3, 1.8)
        self.obstacles.append(platform)
        
        if random.random() < 0.5:
            self.amethysts.append(Amethyst(
                platform.x + width // 2 - 15,
                y_pos - 40,
                size=random.randint(25, 35)
            ))
    
    def spawn_disappearing_platform(self):
        width = random.randint(100, 180)
        height = 25
        y_pos = random.randint(300, 450)
        
        platform = Obstacle(
            self.SCREEN_WIDTH + 50,
            y_pos,
            ObstacleType.DISAPPEARING_PLATFORM,
            width, height,
            (255, 165, 0)
        )
        platform.disappear_timer = random.randint(45, 90)
        platform.visible = True
        self.obstacles.append(platform)
        
        if random.random() < 0.6:
            self.amethysts.append(Amethyst(
                platform.x + width // 2 - 15,
                y_pos - 40,
                size=random.randint(30, 40)
            ))
    
    # КОНТЕНТ: Новые типы препятствий
    def spawn_rotating_spike(self):
        """Вращающийся шип"""
        height = random.choice([70, 90, 110])
        spike = Obstacle(
            self.SCREEN_WIDTH + 50,
            self.SCREEN_HEIGHT - height,
            ObstacleType.ROTATING_SPIKE,
            50, height,
            (255, 100, 100)
        )
        spike.rotation_speed = random.uniform(2.0, 4.0)
        spike.rotation_angle = 0
        self.obstacles.append(spike)
    
    def spawn_ice_platform(self):
        """Ледяная платформа (скользкая)"""
        width = random.randint(120, 200)
        height = 25
        y_pos = random.randint(300, 450)
        
        platform = Obstacle(
            self.SCREEN_WIDTH + 50,
            y_pos,
            ObstacleType.ICE_PLATFORM,
            width, height,
            (173, 216, 230)  # Светло-голубой цвет льда
        )
        platform.slippery = True
        self.obstacles.append(platform)
        
        if random.random() < 0.4:
            self.amethysts.append(Amethyst(
                platform.x + width // 2 - 15,
                y_pos - 40,
                size=random.randint(25, 35)
            ))
    
    def handle_collisions(self):
        if not self.player:
            return
            
        player_rect = self.player.get_rect()
        
        # Оптимизация: проверяем только объекты на экране или рядом
        screen_left = self.camera_x - 100
        screen_right = self.camera_x + self.SCREEN_WIDTH + 100
        
        for obj in self.obstacles:
            # Пропускаем объекты далеко за экраном
            if obj.x + obj.w < screen_left or obj.x > screen_right:
                continue
                
            # Получаем строковое значение типа для сравнения
            obj_type_str = obj.type.value if isinstance(obj.type, ObstacleType) else obj.type
            
            if not obj.visible and obj_type_str == ObstacleType.DISAPPEARING_PLATFORM.value:
                continue
                
            obj_rect = obj.get_rect()
            
            if player_rect.colliderect(obj_rect):
                if obj_type_str in [ObstacleType.SPIKE.value, ObstacleType.MOVING_SPIKE.value]:
                    self.handle_spike_collision(obj)
                elif obj_type_str == ObstacleType.PLATFORM.value:
                    self.handle_platform_collision(obj)
                elif obj_type_str == ObstacleType.BOUNCING_PLATFORM.value:
                    self.handle_bouncing_platform_collision(obj)
                elif obj_type_str == ObstacleType.DISAPPEARING_PLATFORM.value:
                    self.handle_disappearing_platform_collision(obj)
                elif obj_type_str == ObstacleType.SPIKE_CLUSTER.value:
                    self.handle_spike_collision(obj)
                elif obj_type_str == ObstacleType.ROTATING_SPIKE.value:
                    self.handle_spike_collision(obj)
                elif obj_type_str == ObstacleType.ICE_PLATFORM.value:
                    self.handle_ice_platform_collision(obj)
                elif obj_type_str == ObstacleType.ROTATING_SPIKE.value:
                    self.handle_spike_collision(obj)
                elif obj_type_str == ObstacleType.ICE_PLATFORM.value:
                    self.handle_ice_platform_collision(obj)
    
    def handle_spike_collision(self, spike):
        if self.player.invincible:
            return
            
        self.state = GameState.GAME_OVER
        self.play_sound_safe(self.crash_sound)
        
        # UI/UX: Эффект тряски экрана при смерти
        self.screen_shake = 30
        self.flash_alpha = 200
        self.flash_color = (255, 0, 0)
        
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
        if self.player.vy > 0 and self.player.y < platform.y:
            self.player.y = platform.y - self.player.size
            self.player.vy = 0
            self.player.on_ground = True
            self.player.jumps_left = 2 + (1 if self.player.has_double_jump else 0)
            
            self.particle_system.add_particles(
                self.player.x + self.player.size//2,
                self.player.y + self.player.size,
                (150, 150, 255, 180),
                count=5,
                speed=1,
                size_variation=2
            )
    
    def handle_bouncing_platform_collision(self, platform):
        if self.player.vy > 0:
            self.player.y = platform.y - self.player.size
            bounce_strength = self.jump_force * platform.bounce_power
            self.player.vy = bounce_strength
            self.player.on_ground = False
            self.player.jumps_left = 1 + (1 if self.player.has_double_jump else 0)
            
            self.particle_system.add_particles(
                self.player.x + self.player.size//2,
                self.player.y + self.player.size,
                (0, 255, 100, 200),
                count=10,
                speed=2,
                size_variation=3
            )
            
            self.play_sound_safe(self.powerup_sound)
    
    def handle_disappearing_platform_collision(self, platform):
        if self.player.vy > 0 and self.player.y < platform.y:
            self.player.y = platform.y - self.player.size
            self.player.vy = 0
            self.player.on_ground = True
            self.player.jumps_left = 2 + (1 if self.player.has_double_jump else 0)
            platform.disappear_timer = 20
            
            self.particle_system.add_particles(
                platform.x + platform.w//2,
                platform.y,
                (255, 165, 0, 150),
                count=8,
                speed=1,
                size_variation=2
            )
    
    def handle_ice_platform_collision(self, platform):
        """КОНТЕНТ: Обработка коллизии с ледяной платформой"""
        if self.player.vy > 0 and self.player.y < platform.y:
            self.player.y = platform.y - self.player.size
            self.player.vy = 0
            self.player.on_ground = True
            self.player.jumps_left = 2 + (1 if self.player.has_double_jump else 0)
            
            # Ледяная платформа делает игрока скользким
            if not hasattr(self.player, 'ice_slide'):
                self.player.ice_slide = True
                self.player.ice_slide_timer = 180  # 3 секунды при 60 FPS
            
            self.particle_system.add_particles(
                self.player.x + self.player.size//2,
                self.player.y + self.player.size,
                (173, 216, 230, 200),
                count=10,
                speed=1.5,
                size_variation=2
            )
    
    def safe_load_skin(self):
        try:
            if self.current_skin not in self.skins:
                self.current_skin = "cube01"

            skin_info = self.skins[self.current_skin]
            filename = skin_info["image"]
            
            # Пробуем разные пути
            paths_to_try = [
                f"game project/skins/{filename}",
                f"skins/processed/{filename}",
                f"skins/{filename}",
                f"assets/skins/{filename}",
                f"{filename}"  # Прямой путь
            ]
            
            skin_image = None
            actual_path = None
            
            # Ищем файл
            for path in paths_to_try:
                if os.path.exists(path):
                    actual_path = path
                    break
            
            if actual_path:
                # Если это уже обработанный файл из processed/, загружаем напрямую
                if "processed" in actual_path:
                    skin_image = pygame.image.load(actual_path).convert_alpha()
                else:
                    # Используем новую функцию обработки
                    skin_image = self.process_and_load_skin(actual_path)
            
            if skin_image:
                self.player_image = skin_image
                logging.info(f"Skin loaded and processed successfully: {self.current_skin}")
            else:
                # Создаем дефолтный скин
                logging.warning(f"Skin file not found or processing failed: {filename}")
                self.create_default_skin(skin_info)
                
        except Exception as e:
            logging.warning(f"Скин не загрузился: {e}")
            self.create_default_skin()
            
    def process_and_load_skin(self, filename, target_size=None):
        """
        Загружает и обрабатывает изображение скина:
        1. Обрезает прозрачные края
        2. Масштабирует до нужного размера
        3. Сохраняет пропорции
        4. Добавляет контур для куба
        """
        try:
            # Загружаем изображение
            img = pygame.image.load(filename).convert_alpha()
            
            # Если не указан размер, используем базовый
            if target_size is None:
                if self.player and hasattr(self.player, 'skin_level'):
                    base_size = 60
                    size_increase = min(20, (self.player.skin_level - 1) * 2)
                    target_size = base_size + size_increase
                else:
                    target_size = 60
            
            # 1. Находим границы непрозрачных пикселей
            rect = img.get_rect()
            alpha_surface = pygame.surfarray.pixels_alpha(img)
            
            # Находим ненулевые строки и столбцы
            rows = pygame.surfarray.array2d(img)[:, :] > 0
            cols = pygame.surfarray.array2d(img)[:, :].T > 0
            
            try:
                # Получаем границы
                top = rows.any(axis=1).argmax()
                bottom = rows.shape[0] - rows[::-1].any(axis=1).argmax()
                left = cols.any(axis=1).argmax()
                right = cols.shape[0] - cols[::-1].any(axis=1).argmax()
                
                # Проверяем, что границы валидны
                if bottom > top and right > left:
                    # Обрезаем изображение
                    cropped_img = img.subsurface(pygame.Rect(left, top, right-left, bottom-top))
                else:
                    cropped_img = img
            except:
                # Если произошла ошибка при обрезке, используем оригинал
                cropped_img = img
            
            # 2. Масштабируем с сохранением пропорций
            original_width, original_height = cropped_img.get_size()
            aspect_ratio = original_width / original_height
            
            if original_width > original_height:
                # Шире, чем высота
                new_width = target_size
                new_height = int(target_size / aspect_ratio)
            else:
                # Выше, чем ширина или квадрат
                new_height = target_size
                new_width = int(target_size * aspect_ratio)
            
            # Масштабируем
            scaled_img = pygame.transform.smoothscale(cropped_img, (new_width, new_height))
            
            # 3. Создаем квадратное изображение нужного размера
            final_surface = pygame.Surface((target_size, target_size), pygame.SRCALPHA)
            
            # Центрируем отмасштабированное изображение
            x_offset = (target_size - new_width) // 2
            y_offset = (target_size - new_height) // 2
            final_surface.blit(scaled_img, (x_offset, y_offset))
            
            # 4. Автоматически определяем, нужен ли контур (для кубов)
            # Проверяем форму изображения
            is_square_like = abs(original_width - original_height) / max(original_width, original_height) < 0.2
            has_alpha = img.get_at((0, 0))[3] < 255  # Проверяем прозрачность в углу
            
            # Если изображение похоже на квадрат и не полностью прозрачное - добавляем контур
            if is_square_like and not has_alpha:
                # Определяем цвет контура (немного темнее среднего цвета изображения)
                # Берем несколько точек для анализа цвета
                color_samples = [
                    img.get_at((original_width//4, original_height//4)),
                    img.get_at((original_width//2, original_height//2)),
                    img.get_at((3*original_width//4, 3*original_height//4))
                ]
                
                # Вычисляем средний цвет
                avg_r = sum(c[0] for c in color_samples) // len(color_samples)
                avg_g = sum(c[1] for c in color_samples) // len(color_samples)
                avg_b = sum(c[2] for c in color_samples) // len(color_samples)
                avg_a = sum(c[3] for c in color_samples) // len(color_samples)
                
                # Создаем более темный цвет для контура
                border_color = (
                    max(0, avg_r - 30),
                    max(0, avg_g - 30),
                    max(0, avg_b - 30),
                    avg_a
                )
                
                # Рисуем контур
                border_width = max(2, target_size // 30)
                pygame.draw.rect(final_surface, border_color, 
                            (0, 0, target_size, target_size), border_width)
            
            # 5. Добавляем эффект при высоком уровне скина
            if self.player and hasattr(self.player, 'skin_level') and self.player.skin_level >= 10:
                # Создаем свечение
                glow_size = target_size + 10
                glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                glow_color = self.hsv_to_rgb((self.player.skin_level * 30) % 360, 0.7, 1.0)
                pygame.draw.circle(glow_surf, (*glow_color, 100), 
                                (glow_size//2, glow_size//2), glow_size//2)
                
                # Создаем финальную поверхность со свечением
                final_with_glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                final_with_glow.blit(glow_surf, (0, 0))
                final_with_glow.blit(final_surface, 
                                ((glow_size - target_size)//2, 
                                    (glow_size - target_size)//2))
                return final_with_glow
            
            return final_surface
            
        except Exception as e:
            logging.error(f"Error processing skin image {filename}: {e}")
            return None
    def add_custom_skin(self, skin_id, image_path, name_ru=None, name_en=None, cost=0, 
                    auto_process=True, custom_size=None):
        """
        Динамически добавляет новый скин в игру
        
        Args:
            skin_id: Уникальный идентификатор скина
            image_path: Путь к файлу изображения
            name_ru: Русское название (опционально)
            name_en: Английское название (опционально)
            cost: Стоимость в аметистах
            auto_process: Автоматически обрабатывать изображение
            custom_size: Кастомный размер (если None - автоопределение)
        """
        try:
            # Проверяем, существует ли файл
            if not os.path.exists(image_path):
                logging.error(f"Image file not found: {image_path}")
                return False
            
            # Обрабатываем изображение если нужно
            if auto_process:
                output_dir = "skins/processed"
                os.makedirs(output_dir, exist_ok=True)
                output_path = f"{output_dir}/{skin_id}.png"
                if os.path.exists(output_path):
                    # Уже обработано, используем существующее
                    image_filename = f"{skin_id}.png"
                else:
                    processed_image = self.process_and_load_skin(image_path, custom_size)
                    if processed_image:
                        # Сохраняем обработанное изображение
                        pygame.image.save(processed_image, output_path)
                        image_filename = f"{skin_id}.png"
                        
                        # Перемещаем оригинал в backup
                        backup_dir = "skins/original"
                        os.makedirs(backup_dir, exist_ok=True)
                        import shutil
                        shutil.copy2(image_path, f"{backup_dir}/{skin_id}_original.png")
                    else:
                        # Используем оригинальный файл
                        image_filename = os.path.basename(image_path)
            else:
                image_filename = os.path.basename(image_path)
                # Копируем файл в папку скинов если его там нет
                target_path = f"skins/{image_filename}"
                if not os.path.exists(target_path):
                    import shutil
                    shutil.copy2(image_path, target_path)
            
            # Создаем запись о скине
            skin_data = {
                "name": {
                    "ru": name_ru or f"Пользовательский {skin_id}",
                    "en": name_en or f"Custom {skin_id}"
                },
                "cost": cost,
                "owned": False,
                "locked": cost > 0,  # Блокируем если стоимость > 0
                "image": image_filename,
                "custom": True  # Флаг кастомного скина
            }
            
            # Добавляем в список скинов
            self.skins[skin_id] = skin_data
            
            # Сохраняем в JSON файл
            self.save_custom_skins()
            
            logging.info(f"Custom skin added: {skin_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error adding custom skin: {e}")
            return False

    def save_custom_skins(self):
        """Сохраняет кастомные скины в файл"""
        try:
            # Фильтруем только кастомные скины
            custom_skins = {k: v for k, v in self.skins.items() if v.get("custom", False)}
            
            if custom_skins:
                with open("custom_skins.json", "w", encoding="utf-8") as f:
                    json.dump(custom_skins, f, indent=4, ensure_ascii=False)
                logging.info(f"Saved {len(custom_skins)} custom skins")
        except Exception as e:
            logging.error(f"Error saving custom skins: {e}")

    def load_custom_skins(self):
        """Загружает кастомные скины из файла"""
        try:
            if os.path.exists("custom_skins.json"):
                with open("custom_skins.json", "r", encoding="utf-8") as f:
                    custom_skins = json.load(f)
                
                # Добавляем в основной словарь скинов
                self.skins.update(custom_skins)
                logging.info(f"Loaded {len(custom_skins)} custom skins")
        except Exception as e:
            logging.error(f"Error loading custom skins: {e}")
            
    def scan_for_new_skins(self):
        """Автоматически сканирует папку skins и добавляет новые скины"""
        try:
            skins_dir = "skins"
            if not os.path.exists(skins_dir):
                os.makedirs(skins_dir)
                return
            
            # Список поддерживаемых форматов
            valid_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
            
            for filename in os.listdir(skins_dir):
                # Проверяем расширение
                if any(filename.lower().endswith(ext) for ext in valid_extensions):
                    skin_id = os.path.splitext(filename)[0]
                    
                    # Проверяем, не добавлен ли уже этот скин
                    if skin_id not in self.skins:
                        # Генерируем уникальный ID
                        base_id = skin_id
                        counter = 1
                        while skin_id in self.skins:
                            skin_id = f"{base_id}_{counter}"
                            counter += 1
                        
                        # Добавляем скин
                        success = self.add_custom_skin(
                            skin_id=skin_id,
                            image_path=f"{skins_dir}/{filename}",
                            name_ru=f"Авто: {skin_id}",
                            name_en=f"Auto: {skin_id}",
                            cost=100,  # Базовая стоимость
                            auto_process=True
                        )
                        
                        if success:
                            logging.info(f"Auto-added skin: {skin_id}")
            
            # Также сканируем подпапки
            for root, dirs, files in os.walk(skins_dir):
                for filename in files:
                    if any(filename.lower().endswith(ext) for ext in valid_extensions):
                        full_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(full_path, skins_dir)
                        skin_id = os.path.splitext(relative_path)[0].replace('/', '_').replace('\\', '_')
                        
                        if skin_id not in self.skins:
                            self.add_custom_skin(
                                skin_id=skin_id,
                                image_path=full_path,
                                name_ru=f"Авто: {skin_id}",
                                name_en=f"Auto: {skin_id}",
                                cost=150,
                                auto_process=True
                            )
                            
        except Exception as e:
            logging.error(f"Error scanning for new skins: {e}")
            
    def show_skin_upload_menu(self):
        """Показывает меню загрузки кастомных скинов"""
        self.upload_menu.clear()
        
        self.upload_menu.add.label("Загрузите изображение в папку 'skins'", 
                            font_color=self.WHITE)
        
        self.upload_menu.add.label("Поддерживаемые форматы: PNG, JPG, BMP", 
                            font_color=self.CYAN)
        
        # Кнопка для сканирования новых скинов
        self.upload_menu.add.button("Сканировать папку 'skins'" if self.language == 'ru' else "Scan 'skins' folder",
                            self.scan_and_update_skins)
        
        self.upload_menu.add.button(self.localization.get('back'), self.show_inventory_menu)
        
        self.state = GameState.MENU
        self.menu = self.upload_menu

    def scan_and_update_skins(self):
        """Сканирует папку и обновляет список скинов"""
        self.scan_for_new_skins()
        self.show_inventory_menu()
        
    def create_default_skin(self, skin_info=None):
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
        try:
            account_data = self.account_system.get_current_account_data()
            if account_data:
                self.total_amethysts = account_data.get("amethysts", 0)
                self.load_player_skins()
                self.load_player_upgrades()
                
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
                        self.player.skin_level = 1
                        self.player.skin_exp = 0
                        self.player.total_exp = 0
                        self.player.completed_levels = 0
                        logging.info(f"No progression found for skin {self.current_skin}, starting fresh")
                
                logging.info(f"Player data loaded for: {account_data['username']}")
        except Exception as e:
            logging.error(f"Error loading player data: {e}")
        
    def load_skins(self):
        """Загрузка информации о скинах с локализацией"""
        return {
            "cube01": {
                "name": {"ru": "Базовый куб", "en": "Basic Cube"},
                "cost": 0, 
                "owned": True, 
                "locked": False, 
                "image": "cube01.png"
            },
            "cube02": {
                "name": {"ru": "Золотой куб", "en": "Gold Cube"},
                "cost": 50, 
                "owned": False, 
                "locked": False, 
                "image": "cube02.png"
            },
            "cube03": {
                "name": {"ru": "Алмазный куб", "en": "Diamond Cube"},
                "cost": 100, 
                "owned": False, 
                "locked": False, 
                "image": "cube03.png"
            },
            "cube04": {
                "name": {"ru": "Огненный куб", "en": "Fire Cube"},
                "cost": 150, 
                "owned": False, 
                "locked": True, 
                "image": "cube04.png"
            },
            "cube05": {
                "name": {"ru": "Ледяной куб", "en": "Ice Cube"},
                "cost": 200, 
                "owned": False, 
                "locked": True, 
                "image": "cube05.png"
            },
            "cube06": {
                "name": {"ru": "Радужный куб", "en": "Rainbow Cube"},
                "cost": 300, 
                "owned": False, 
                "locked": True, 
                "image": "cube06.png"
            }
        }
    
    def load_player_skins(self):
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
        if not self.account_system.current_account:
            return
            
        try:
            cursor = self.account_system.conn.cursor()
            cursor.execute('SELECT upgrade_type FROM player_upgrades WHERE player_id = ?', 
                         (self.account_system.current_account["id"],))
            
            owned_upgrades = [row[0] for row in cursor.fetchall()]
            
            self.player_upgrades = owned_upgrades
            
            if self.player:
                if 'shield' in owned_upgrades:
                    self.player.has_shield = True
                if 'double_jump' in owned_upgrades:
                    self.player.has_double_jump = True
                    self.player.jumps_left = 3
                if 'exp_booster' in owned_upgrades:
                    self.exp_boost_active = True
                    self.exp_boost_timer = 3
                
        except sqlite3.Error as e:
            logging.error(f"Error loading player upgrades: {e}")

    def initialize_new_player_skins(self):
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
        """ИСПРАВЛЕНИЕ: Безопасное переключение полноэкранного режима"""
        try:
            # Сохраняем текущее состояние
            was_fullscreen = self.fullscreen
            self.fullscreen = not self.fullscreen
            
            # ИСПРАВЛЕНИЕ: Правильное переключение без зависаний
            if self.fullscreen:
                # Переключаемся в полноэкранный режим
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                # Возвращаемся в оконный режим
                self.screen = pygame.display.set_mode(self.original_size)
            
            # Обновляем размеры экрана
            new_width, new_height = self.screen.get_size()
            
            # ИСПРАВЛЕНИЕ: Масштабируем позиции при переключении режима
            if self.state == GameState.PLAYING:
                scale_x = new_width / self.SCREEN_WIDTH if self.SCREEN_WIDTH > 0 else 1.0
                scale_y = new_height / self.SCREEN_HEIGHT if self.SCREEN_HEIGHT > 0 else 1.0
                
                if self.player:
                    self.player.x = int(self.player.x * scale_x)
                    self.player.y = int(self.player.y * scale_y)
                    self.camera_x = int(self.camera_x * scale_x)
                
                if hasattr(self, 'obstacles'):
                    for obj in self.obstacles:
                        obj.x = int(obj.x * scale_x)
                        obj.y = int(obj.y * scale_y)
                
                if hasattr(self, 'amethysts'):
                    for amethyst in self.amethysts:
                        amethyst.x = int(amethyst.x * scale_x)
                        amethyst.y = int(amethyst.y * scale_y)
                
                if hasattr(self, 'level_end_x'):
                    self.level_end_x = int(self.level_end_x * scale_x)
            
            self.SCREEN_WIDTH, self.SCREEN_HEIGHT = new_width, new_height
            
            # Сбрасываем кэш фона
            self.cached_bg_surface = None
            self.cached_ground_surface = None
            
            # Обновляем ресурсы
            self.menu_bg_surface = self.create_gradient_menu_bg()
            self.create_menus()
            self.safe_load_skin()
            
            # Принудительное обновление экрана для предотвращения зависаний
            pygame.display.flip()
            
        except pygame.error as e:
            logging.error(f"Error switching fullscreen: {e}")
            # Откатываем изменения при ошибке
            self.fullscreen = was_fullscreen
            try:
                if not self.fullscreen:
                    self.screen = pygame.display.set_mode(self.original_size)
                else:
                    self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except:
                pass
        
    def load_resources(self):
        try:
            folders = ["sounds", "skins", "backgrounds", "menu", "levels", "chests", "assets"]
            for folder in folders:
                if not os.path.exists(folder):
                    os.makedirs(folder)
                    logging.info(f"Created folder: {folder}")

            self.menu_bg_surface = self.create_gradient_menu_bg()

            sound_paths = [
                "sounds/crash.wav", "game project/sounds/crash.wav",
                "sounds/collect.wav", "game project/sounds/collect.wav",
                "sounds/chest_open.wav", "sounds/open chest.wav", "game project/sounds/open chest.wav",
                "sounds/level_complete.wav",
                "sounds/powerup.wav", "sounds/SFX_Powerup_01.wav", "sounds/SFX_Powerup_02.wav", "game project/sounds/powerup.wav",
                "sounds/jump.wav", "sounds/bonus.wav",
                "sounds/ThisGameIsOver.wav", "game project/sounds/ThisGameIsOver.wav"
            ]
            
            self.crash_sound = None
            self.collect_sound = None
            self.chest_sound = None
            self.level_complete_sound = None
            self.powerup_sound = None
            self.jump_sound = None
            self.bonus_sound = None
            self.game_over_sound = None
            
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
                    elif "jump" in path and not self.jump_sound and os.path.exists(path):
                        self.jump_sound = pygame.mixer.Sound(path)
                    elif "bonus" in path and not self.bonus_sound and os.path.exists(path):
                        self.bonus_sound = pygame.mixer.Sound(path)
                    elif "ThisGameIsOver" in path and not self.game_over_sound and os.path.exists(path):
                        self.game_over_sound = pygame.mixer.Sound(path)
                except Exception as e:
                    continue

            # Загрузка фоновой музыки меню
            music_paths = [
                "sounds/polygons_n_light.mp3",
                "sounds/polygons_n_light.ogg", 
                "sounds/polygons_n_light.wav",
                "game project/sounds/polygons_n_light.mp3",
                "game project/sounds/polygons_n_light.ogg",
                "game project/sounds/polygons_n_light.wav"
            ]
            
            for path in music_paths:
                try:
                    if os.path.exists(path):
                        pygame.mixer.music.load(path)
                        self.menu_music = path
                        logging.info(f"Loaded menu music: {path}")
                        break
                except Exception as e:
                    continue

            # Загрузка звука начала игры
            start_game_paths = [
                "sounds/start game.wav",
                "game project/sounds/start game.wav"
            ]
            
            for path in start_game_paths:
                try:
                    if os.path.exists(path):
                        self.start_game_sound = pygame.mixer.Sound(path)
                        logging.info(f"Loaded start game sound: {path}")
                        break
                except Exception as e:
                    continue
            
            # Загрузка музыки уровней
            level_music_files = {
                "Level 1": ["sounds/Level 1.wav", "game project/sounds/Level 1.wav"],
                "Level 2": ["sounds/Level 2.wav", "game project/sounds/Level 2.wav"], 
                "Level 3": ["sounds/Level 3.wav", "game project/sounds/Level 3.wav"]
            }
            
            for level_name, paths in level_music_files.items():
                for path in paths:
                    try:
                        if os.path.exists(path):
                            self.level_musics[level_name] = path
                            logging.info(f"Loaded {level_name} music: {path}")
                            break
                    except Exception as e:
                        continue
            
            # Загрузка музыки экрана окончания
            title_screen_paths = [
                "sounds/Title Screen.wav",
                "game project/sounds/Title Screen.wav"
            ]
            
            for path in title_screen_paths:
                try:
                    if os.path.exists(path):
                        self.title_screen_music = path
                        logging.info(f"Loaded title screen music: {path}")
                        break
                except Exception as e:
                    continue

            self.safe_load_skin()
            self.load_hero_image()
            
            # Создаем фоны для меню
            self.menu_bg_surface = self.create_gradient_menu_bg()
            self.light_menu_bg = self.create_light_menu_bg()
        
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
            self.menu_bg_surface = self.create_gradient_menu_bg()

    def create_default_chest(self):
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        pygame.draw.rect(surf, (139, 69, 19), (50, 100, 100, 60))
        pygame.draw.rect(surf, (160, 82, 45), (50, 80, 100, 30))
        pygame.draw.rect(surf, (255, 215, 0), (70, 85, 60, 20))
        pygame.draw.circle(surf, (255, 215, 0), (100, 95), 8)
        return surf

    def create_gradient_bg(self):
        surf = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        for y in range(self.SCREEN_HEIGHT):
            color_value = 20 + int(30 * (y / self.SCREEN_HEIGHT))
            pygame.draw.line(surf, (color_value, color_value, 80), (0, y), (self.SCREEN_WIDTH, y))
        return surf

    def play_sound_safe(self, sound):
        if sound and pygame.mixer.get_init():
            try:
                # Применяем настройку громкости звуковых эффектов
                sound.set_volume(self.sfx_volume / 100 * 0.3)  # 0.3 - базовый уровень
                sound.play()
            except pygame.error as e:
                logging.warning(f"Could not play sound: {e}")

    # ОСНОВНЫЕ МЕТОДЫ
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            # блок для обработки отложенного обновления меню
            if event.type == pygame.USEREVENT:
                self.create_menus()
                pygame.time.set_timer(pygame.USEREVENT, 0)
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_ESCAPE:
                    if self.state == GameState.INTRO:
                        self.state = GameState.MENU
                        if self.use_pygame_menu:
                            self.menu = self.main_menu
                            self.menu.enable()
                    else:
                        self.handle_escape_key()
                elif event.key == pygame.K_TAB and self.state == GameState.MENU:
                    self.toggle_menu_system()
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN) and self.state == GameState.INTRO:
                    # Пропустить intro
                    self.state = GameState.MENU
                    if self.use_pygame_menu:
                        self.menu = self.main_menu
                        self.menu.enable()
            
            if (self.state == GameState.MENU and self.use_pygame_menu and 
                self.menu and self.menu.is_enabled()):
                self.menu.update([event])
                
            elif self.state == GameState.MENU and not self.use_pygame_menu:
                self.handle_menu_events(event)
            elif self.state == GameState.PLAYING:
                self.handle_game_events(event)
            elif self.state == GameState.SHOP:
                self.handle_shop_events(event)
            elif self.state == GameState.GAME_OVER:
                self.handle_game_over_events(event)
            elif self.state == GameState.LOGIN:
                self.handle_login_events(event)
            elif self.state == GameState.PROMO:
                self.handle_promo_events(event)
            elif self.state == GameState.EDITOR:
                self.handle_editor_events(event)
            elif self.state == GameState.PAUSED:
                self.handle_pause_events(event)
            elif self.state == GameState.INVENTORY:
                self.handle_inventory_events(event)
            elif self.state == GameState.CHEST:
                self.handle_chest_events(event)
            elif self.state == GameState.LEVEL_SELECT:
                self.handle_level_select_events(event)
            elif self.state == GameState.LEVEL_COMPLETE:
                self.handle_level_complete_events(event)
            elif self.state == GameState.SKIN_PROGRESSION:
                self.handle_skin_progression_events(event)
            elif self.state == GameState.OTHER:
                self.handle_other_events(event)
            elif self.state == GameState.ACHIEVEMENTS:
                self.handle_achievements_events(event)
                
    def handle_other_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_to_main_menu()
    
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Проверка клика на героя
            if hasattr(self, 'hero_click_rect') and self.hero_click_rect and self.hero_click_rect.collidepoint(mouse_pos):
                self.show_hero_phrase()
            
            # Проверка клика на кнопку "Назад"
            back_rect = pygame.Rect(self.SCREEN_WIDTH//2 - 100, self.SCREEN_HEIGHT - 80, 200, 50)
            if back_rect.collidepoint(mouse_pos):
                self.return_to_main_menu()

    def handle_skin_progression_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_to_main_menu()

    def handle_achievements_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_to_main_menu()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            back_rect = pygame.Rect(self.SCREEN_WIDTH//2 - 100, self.SCREEN_HEIGHT - 80, 200, 50)
            if back_rect.collidepoint(pygame.mouse.get_pos()):
                self.return_to_main_menu()

    def handle_escape_key(self):
        if self.state == GameState.PLAYING:
            self.state = GameState.PAUSED
        elif self.state == GameState.PAUSED:
            self.state = GameState.PLAYING
        elif self.state in [GameState.SHOP, GameState.INVENTORY, GameState.LEVEL_SELECT, 
                           GameState.LOGIN, GameState.PROMO, GameState.CHEST, GameState.LEVEL_COMPLETE,
                           GameState.OTHER, GameState.SKIN_PROGRESSION, GameState.ACHIEVEMENTS]:
            self.return_to_main_menu()
        elif self.state == GameState.GAME_OVER:
            self.return_to_main_menu()
        elif self.state == GameState.EDITOR:
            self.return_to_main_menu()

    def return_to_main_menu(self):
        self.state = GameState.MENU
        # Сбрасываем флаг показа фразы при выходе из меню "Прочее"
        self.hero_phrase_shown_on_entry = False
        if self.use_pygame_menu:
            self.menu = self.main_menu
            if self.menu:
                self.menu.enable()
        else:
            self.menu = None

    def handle_menu_events(self, event):
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
                self.state = GameState.PROMO
                self.promo_input = ""
                self.promo_message = ""
                
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            for i, option in enumerate(self.menu_options):
                text_rect = pygame.Rect(self.SCREEN_WIDTH//2 - 150, 180 + i*50, 300, 40)
                if text_rect.collidepoint(mouse_pos):
                    self.selected_option = i
                    self.execute_menu_action()
                    break
                    
        elif event.type == pygame.MOUSEMOTION:
            # Подсветка пунктов меню при наведении
            mouse_pos = pygame.mouse.get_pos()
            for i, option in enumerate(self.menu_options):
                text_rect = pygame.Rect(self.SCREEN_WIDTH//2 - 150, 180 + i*50, 300, 40)
                if text_rect.collidepoint(mouse_pos):
                    self.selected_option = i
                    break
                    
    def execute_menu_action(self):
        option = self.menu_options[self.selected_option]
        
        if option == self.localization.get('start_game'):
            self.start_game()
        elif option == self.localization.get('level_select_btn'):
            self.state = GameState.LEVEL_SELECT
            self.selected_level_index = 0
        elif option == self.localization.get('level_editor_btn'):
            self.start_editor()
        elif option == self.localization.get('shop_btn'):
            self.state = GameState.SHOP
            self.selected_shop_item = 0
        elif option == self.localization.get('inventory_btn'):
            self.state = GameState.INVENTORY
        elif option == self.localization.get('daily_chest_btn'):
            self.open_daily_chest()
        elif option == self.localization.get('other_menu'):
            self.show_other_menu()
        elif option == self.localization.get('login_logout'):
            self.toggle_login()
        elif option == self.localization.get('promo_codes_btn'):
            self.state = GameState.PROMO
            self.promo_input = ""
            self.promo_message = ""
        elif option == self.localization.get('settings_btn'):
            self.show_settings_menu()
        elif option == self.localization.get('skin_progression_btn'):
            self.show_skin_progression_menu()
        elif option == self.localization.get('achievements'):
            if self.use_pygame_menu:
                self.show_achievements_menu()
            else:
                self.state = GameState.ACHIEVEMENTS
                self.menu = None
        elif option == self.localization.get('exit'):
            self.running = False

    def handle_level_select_events(self, event):
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
        if index is None:
            index = self.selected_level_index
            
        selected_level = self.available_levels[index]
        
        if selected_level["file"] == "random":
            self.start_game()
        else:
            self.load_custom_level(selected_level["file"])
        self.state = GameState.PLAYING

    def load_custom_level(self, filename):
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
        level_data = {
            "name": "Default Level" if self.language == 'en' else "Стандартный уровень",
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
        if not self.account_system.current_account:
            self.state = GameState.LOGIN
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
                    self.chest_rewards = [{"type": "message", "text": self.localization.get('chest_already_opened')}]
                    self.state = GameState.CHEST
                    return
        except sqlite3.Error as e:
            self.chest_rewards = [{"type": "message", "text": self.localization.get('purchase_failed')}]
            self.state = GameState.CHEST
            return
        
        self.generate_chest_rewards()
        self.state = GameState.CHEST
        self.chest_animation_frame = 0
        
        try:
            cursor.execute('UPDATE players SET last_chest_date = ? WHERE username = ?',
                         (today.strftime('%Y-%m-%d'), self.account_system.current_account['username']))
            self.account_system.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error updating chest date: {e}")
        
        self.play_sound_safe(self.chest_sound)

    def generate_chest_rewards(self):
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
                    skin_name = self.skins[skin_id]["name"]
                    if isinstance(skin_name, dict):
                        skin_name = skin_name.get(self.language, skin_name.get('ru', 'Unknown'))
                    rewards.append({"type": "skin", "skin_id": skin_id, "name": skin_name})
                    
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
        self.state = GameState.PLAYING
        
        # Воспроизводим звук начала игры
        if self.start_game_sound:
            self.play_sound_safe(self.start_game_sound)
        
        self.score = 0
        self.base_speed = level_data.get("speed", 8)
        self.game_speed = self.base_speed
        self.camera_x = 0
        self.spawn_timer = 0
        self.percent = 0
        self.distance_traveled = 0
        self.level_complete = False
        
        # ИСПРАВЛЕНИЕ: Вычисляем масштаб ДО использования
        scale_x = self.SCREEN_WIDTH / self.BASE_SCREEN_WIDTH if self.BASE_SCREEN_WIDTH > 0 else 1.0
        scale_y = self.SCREEN_HEIGHT / self.BASE_SCREEN_HEIGHT if self.BASE_SCREEN_HEIGHT > 0 else 1.0
        
        # ИСПРАВЛЕНИЕ: Масштабируем конец уровня
        base_level_end_x = self.compute_level_end_x(level_data)
        self.level_end_x = int(base_level_end_x * scale_x)
        
        # Устанавливаем имя уровня для награды опытом
        self.current_level_name = level_data.get("name", "Custom Level")

        # ИСПРАВЛЕНИЕ: Создаем игрока с масштабированной позицией
        base_start_x = level_data.get("player_start_x", 150)
        base_start_y = level_data.get("player_start_y", 400)
        self.player = Player(
            int(base_start_x * scale_x),
            int(base_start_y * scale_y)
        )
        
        # Применяем улучшения
        if hasattr(self, 'account_system') and self.account_system.current_account:
            self.load_player_upgrades()

        # ИСПРАВЛЕНИЕ: Создаем препятствия с масштабированием позиций
        self.obstacles = []
        for obs_data in level_data.get("obstacles", []):
            # Масштабируем позиции и размеры препятствий
            scaled_x = int(obs_data["x"] * scale_x)
            scaled_y = int(obs_data["y"] * scale_y)
            scaled_w = int(obs_data.get("w", 60) * scale_x)
            scaled_h = int(obs_data.get("h", 60) * scale_y)
            
            obstacle = Obstacle(
                scaled_x, 
                scaled_y, 
                obs_data["type"],
                scaled_w,
                scaled_h,
                obs_data.get("color", (255, 0, 0))
            )
            obstacle_type_str = obstacle.type.value if isinstance(obstacle.type, ObstacleType) else obstacle.type
            if obstacle_type_str == ObstacleType.MOVING_SPIKE.value:
                obstacle.move_speed = obs_data.get("move_speed", 2.0)
                obstacle.move_direction = obs_data.get("move_direction", 1)
                obstacle.original_y = int(obs_data.get("original_y", obstacle.y) * scale_y)
            self.obstacles.append(obstacle)

        # ИСПРАВЛЕНИЕ: Создаем аметисты с масштабированием
        self.amethysts = []
        for amethyst_data in level_data.get("amethysts", []):
            scaled_x = int(amethyst_data["x"] * scale_x)
            scaled_y = int(amethyst_data["y"] * scale_y)
            scaled_size = int(amethyst_data.get("size", 30) * min(scale_x, scale_y))
            self.amethysts.append(Amethyst(
                scaled_x,
                scaled_y,
                scaled_size
            ))
        
        # Создаем бонусы
        self.bonuses = []
        self.magnet_active = False
        self.magnet_timer = 0
        self.slow_time_active = False
        self.slow_time_timer = 0

        self.enable_random_generation = level_data.get("random_generation", False)

    def handle_game_events(self, event):
        if event.type == pygame.KEYDOWN and self.player:
            if event.key == pygame.K_SPACE or event.key == pygame.K_UP:
                success, effect_size = self.player.jump(self.jump_force)
                if success:
                    self.play_sound_safe(self.jump_sound)
                    self.particle_system.add_particles(
                        self.player.x + self.player.size//2,
                        self.player.y + self.player.size,
                        (200, 200, 255),
                        count=effect_size,
                        speed=2
                    )
                    self.update_quest_progress(QuestType.JUMP_COUNT)
                    self.stats["total_jumps"] = self.stats.get("total_jumps", 0) + 1
            elif event.key == pygame.K_p:
                self.state = GameState.PAUSED
            elif event.key == pygame.K_h and self.player.has_shield:
                self.player.activate_shield()
            elif event.key == pygame.K_b:
                self.player.activate_speed_boost()
            elif event.key == pygame.K_F10:
                self.force_complete_level()
            elif event.key == pygame.K_F9:
                self.debug_skin_progression()
            elif event.key == pygame.K_q and self.dash_cooldown_timer == 0:
                self.activate_dash()
        
        # Обработка клика мыши для прыжка
        elif event.type == pygame.MOUSEBUTTONDOWN and self.player:
            if event.button == 1:
                success, effect_size = self.player.jump(self.jump_force)
                if success:
                    self.play_sound_safe(self.jump_sound)
                    self.particle_system.add_particles(
                        self.player.x + self.player.size//2,
                        self.player.y + self.player.size,
                        (200, 200, 255),
                        count=effect_size,
                        speed=2
                    )
                    self.update_quest_progress(QuestType.JUMP_COUNT)
                    self.stats["total_jumps"] = self.stats.get("total_jumps", 0) + 1
    
    def activate_dash(self):
        """Активация дэша"""
        if self.dash_cooldown_timer == 0 and not self.is_dashing:
            self.is_dashing = True
            self.dash_timer = self.dash_duration
            self.dash_cooldown_timer = self.dash_cooldown
            
            # Определяем направление дэша (вправо если игрок движется вправо, иначе влево)
            self.dash_direction = 1 if self.player.x < self.SCREEN_WIDTH // 2 else -1
            
            # Эффекты дэша
            self.play_sound_safe(self.powerup_sound)  # Или добавить отдельный звук дэша
            self.particle_system.add_particles(
                self.player.x + self.player.size//2,
                self.player.y + self.player.size//2,
                (255, 255, 0),  # Желтые частицы
                count=15,
                speed=5
            )

    def handle_pause_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                self.state = GameState.PLAYING
            elif event.key == pygame.K_m:
                self.return_to_main_menu()

    def handle_shop_events(self, event):
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
        if not self.account_system.current_account:
            self.login_message = "Пожалуйста, войдите в систему!" if self.language == 'ru' else "Please login first!"
            self.state = GameState.LOGIN
            return False
            
        item = self.shop_items[self.selected_shop_item]
        
        if self.total_amethysts < item.cost:
            self.login_message = f"Недостаточно аметистов! Нужно {item.cost}" if self.language == 'ru' else f"Not enough amethysts! Need {item.cost}"
            return False
            
        try:
            cursor = self.account_system.conn.cursor()
            
            cursor.execute('SELECT 1 FROM player_upgrades WHERE player_id = ? AND upgrade_type = ?',
                        (self.account_system.current_account["id"], item.effect_type))
            
            if cursor.fetchone():
                self.login_message = "У вас уже есть это улучшение!" if self.language == 'ru' else "You already have this upgrade!"
                return False
            
            self.total_amethysts -= item.cost
            cursor.execute('UPDATE players SET amethysts = ? WHERE username = ?',
                        (self.total_amethysts, self.account_system.current_account['username']))
            
            effect_type_str = item.effect_type.value if isinstance(item.effect_type, EffectType) else item.effect_type
            cursor.execute('INSERT INTO player_upgrades (player_id, upgrade_type) VALUES (?, ?)',
                        (self.account_system.current_account["id"], effect_type_str))
            
            self.account_system.conn.commit()
            
            if effect_type_str == EffectType.SHIELD.value:
                if self.player:
                    self.player.has_shield = True
            elif effect_type_str == EffectType.SPEED_BOOST.value:
                pass
            elif effect_type_str == EffectType.DOUBLE_JUMP.value:
                if self.player:
                    self.player.has_double_jump = True
                    self.player.jumps_left = 3
            elif effect_type_str == EffectType.EXP_BOOSTER.value:
                if self.player:
                    self.exp_boost_active = True
                    self.exp_boost_timer = 3
                
            self.login_message = f"{item.get_name()} {self.localization.get('purchase_success').lower()}"
            self.play_sound_safe(self.powerup_sound)
            return True
            
        except sqlite3.Error as e:
            self.login_message = self.localization.get('purchase_failed')
            logging.error(f"Error buying shop item: {e}")
            return False
        
    def handle_inventory_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_to_main_menu()
                
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            skin_keys = list(self.skins.keys())
            skins_per_row = 3
            skin_size = 140
            skin_margin = 15
            center_x = self.SCREEN_WIDTH // 2
            start_x = center_x - ((skins_per_row * (skin_size + skin_margin)) - skin_margin) // 2
            start_y = 150
            
            for i, skin_id in enumerate(skin_keys):
                row = i // skins_per_row
                col = i % skins_per_row
                x = start_x + col * (skin_size + skin_margin)
                y = start_y + row * (skin_size + skin_margin)
                
                if y + skin_size > self.SCREEN_HEIGHT - 100:
                    continue
                    
                skin_rect = pygame.Rect(x, y, skin_size, skin_size)
                if skin_rect.collidepoint(mouse_pos):
                    skin = self.skins[skin_id]
                    if skin["owned"]:
                        # Переключаем скин
                        self.current_skin = skin_id
                        self.safe_load_skin()
                        # Воспроизводим звук
                        self.play_sound_safe(self.powerup_sound)
                        
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
                            self.current_skin = skin_id
                            self.safe_load_skin()
                            self.play_sound_safe(self.powerup_sound)
                            
                            # Эффекты покупки
                            self.particle_system.add_particles(
                                x + skin_size//2,
                                y + skin_size//2,
                                self.GOLD,
                                count=30,
                                speed=3,
                                size_variation=4
                            )
                            
                        except sqlite3.Error as e:
                            logging.error(f"Database error buying skin: {e}")
                            # Откатываем покупку в случае ошибки
                            self.total_amethysts += skin["cost"]
                            skin["owned"] = False
                    break

    def handle_chest_events(self, event):
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            self.return_to_main_menu()

    def handle_level_complete_events(self, event):
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            self.return_to_main_menu()

    def update_game(self):
        if not self.player or not self.player.alive:
            return

        if self.level_complete:
            # Если уровень завершен, сразу показываем экран завершения
            # (не ждем падения игрока)
            if self.state != GameState.LEVEL_COMPLETE:
                self.show_level_complete_screen()
            return

        # Обновление игрока
        self.player.update(self.gravity, self.max_fall_speed, self.air_resistance)
        
        # Обновление дэша
        if self.is_dashing:
            self.dash_timer -= 1
            if self.dash_timer <= 0:
                self.is_dashing = False
        else:
            if self.dash_cooldown_timer > 0:
                self.dash_cooldown_timer -= 1
        
        # Применение дэша к игроку
        if self.is_dashing:
            self.player.x += self.dash_speed * self.dash_direction
            # Эффекты частиц во время даша
            if random.random() < 0.3:  # 30% шанс создания частицы
                particle_x = self.player.x + random.randint(-10, 10)
                particle_y = self.player.y + random.randint(-10, 10)
                self.particle_system.add_particles(particle_x, particle_y, 
                                                random.choice([self.CYAN, self.PURPLE, self.GOLD]),
                                                count=1, speed=2, lifetime=15, size_variation=2)
        
        # КОНТЕНТ: Обработка эффекта скольжения на льду
        if hasattr(self.player, 'ice_slide') and self.player.ice_slide:
            if hasattr(self.player, 'ice_slide_timer'):
                self.player.ice_slide_timer -= 1
                if self.player.ice_slide_timer <= 0:
                    self.player.ice_slide = False

        # ИСПРАВЛЕНИЕ: Проверка земли с масштабированием
        GROUND_Y = int(self.SCREEN_HEIGHT * 0.833)  # 500 для 600px, масштабируется
        GROUND_BUFFER = 8
        
        if self.player.y >= GROUND_Y - GROUND_BUFFER:
            self.player.y = GROUND_Y
            self.player.vy = 0
            
            if not self.player.on_ground:
                self.player.on_ground = True
                self.player.jumps_left = 2 + (1 if self.player.has_double_jump else 0)
                
                # Эффекты частиц при приземлении
                self.particle_system.add_particles(
                    self.player.x + self.player.size//2,
                    self.player.y + self.player.size,
                    (150, 150, 255),
                    count=8,
                    speed=1.5
                )

        # ИСПРАВЛЕНИЕ: Смерть от падения с учетом текущего разрешения
        death_y = int(self.SCREEN_HEIGHT * 1.17)  # Примерно 700 для 600px, масштабируется
        if self.player.y > death_y:
            self.state = GameState.GAME_OVER
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
            # Двигаем прогресс по дистанции даже на фиксированных уровнях
            self.distance_traveled += self.game_speed * 0.1
            self.percent = self.calculate_level_progress()
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
                
                # Дополнительные эффекты завершения уровня
                for _ in range(20):
                    angle = random.uniform(0, 2 * math.pi)
                    distance = random.uniform(20, 60)
                    x = self.player.x + self.player.size//2 + math.cos(angle) * distance
                    y = self.player.y + self.player.size//2 + math.sin(angle) * distance
                    self.particle_system.add_particles(x, y, self.CYAN, count=3, speed=2, lifetime=30)
            
                # Награда за завершение уровня
                completion_bonus = 20
                self.total_amethysts += completion_bonus
                
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
                        
                # Обновление задания "complete_level"
                self.update_quest_progress(QuestType.COMPLETE_LEVEL)
                
                # Обновление статистики
                self.stats["total_levels_completed"] = self.stats.get("total_levels_completed", 0) + 1
                if self.score > self.stats.get("best_score", 0):
                    self.stats["best_score"] = self.score
                if self.max_combo > self.stats.get("best_combo", 0):
                    self.stats["best_combo"] = self.max_combo
                self.check_achievements()
                self.save_stats()
                
                # Немедленно показываем экран завершения уровня
                self.show_level_complete_screen()
                return

        # Случайная генерация
        if self.enable_random_generation:
            self.distance_traveled += self.game_speed * 0.1
            if self.player.speed_boost_timer == 0 and self.game_speed > self.base_speed:
                self.game_speed = self.base_speed
                
            self.game_speed += self.acceleration_rate
            
            if self.enable_random_generation:
                self.percent = min(100, int(self.distance_traveled / 15))
        
            self.spawn_timer += 1
            spawn_interval = max(20, 60 - int(self.game_speed * 2))
            
            if self.spawn_timer > spawn_interval:
                self.spawn_timer = 0
                self.spawn_random_obstacle()
                
                # Случайный спавн бонусов (5% шанс)
                if random.random() < 0.05 and hasattr(self, 'bonuses'):
                    bonus_type = random.choice(["magnet", "slow_time", "shield", "speed_boost"])
                    y_pos = random.randint(200, 450)
                    self.bonuses.append(Bonus(
                        self.SCREEN_WIDTH + 50,
                        y_pos,
                        bonus_type
                    ))

        # ОПТИМИЗАЦИЯ: Обновление области видимости (viewport culling)
        self.viewport_left = self.camera_x - 100
        self.viewport_right = self.camera_x + self.SCREEN_WIDTH + 100
        
        # Обновление объектов (оптимизировано с culling)
        obstacles_to_remove = []
        for i, obj in enumerate(self.obstacles):
            # Обновляем только объекты в области видимости или рядом
            if obj.x + obj.w >= self.viewport_left - 200 and obj.x <= self.viewport_right + 200:
                obj.update(self.game_speed)
            
            if obj.is_off_screen():
                obstacles_to_remove.append(i)
                self.score += 1
                self.update_quest_progress(QuestType.SCORE_POINTS, amount=1)
        
        # Удаляем препятствия в обратном порядке, чтобы индексы не сдвигались
        for i in reversed(obstacles_to_remove):
            self.obstacles.pop(i)
        if len(self.obstacles) > 120:
            self.obstacles = self.obstacles[-120:]

        # ОПТИМИЗАЦИЯ: Обновление аметистов с culling
        for amethyst in self.amethysts:
            # Обновляем только аметисты в области видимости
            if amethyst.x + amethyst.size >= self.viewport_left - 200 and amethyst.x <= self.viewport_right + 200:
                amethyst.update(self.game_speed)
        self.amethysts = [amethyst for amethyst in self.amethysts if not amethyst.is_off_screen()]
        if len(self.amethysts) > 60:
            self.amethysts = self.amethysts[-60:]
        
        # ОПТИМИЗАЦИЯ: Обновление бонусов с culling
        if hasattr(self, 'bonuses'):
            for bonus in self.bonuses:
                # Обновляем только бонусы в области видимости
                if bonus.x + bonus.size >= self.viewport_left - 200 and bonus.x <= self.viewport_right + 200:
                    bonus.update(self.game_speed)
            self.bonuses = [bonus for bonus in self.bonuses if not bonus.is_off_screen() and not bonus.collected]
            if len(self.bonuses) > 30:
                self.bonuses = self.bonuses[-30:]
        
        # Обновление эффектов бонусов
        if hasattr(self, 'magnet_timer') and self.magnet_timer > 0:
            self.magnet_timer -= 1
            if self.magnet_timer <= 0:
                self.magnet_active = False
        
        if hasattr(self, 'slow_time_timer') and self.slow_time_timer > 0:
            self.slow_time_timer -= 1
            if self.slow_time_timer <= 0:
                self.slow_time_active = False
                if hasattr(self, 'base_speed'):
                    self.game_speed = self.base_speed

        # Обновление системы комбо
        self.update_combo_system()

        # Обновление частиц
        self.particle_system.update()

        # Проверка коллизий
        self.handle_collisions()

        # Сбор аметистов (с эффектом магнита)
        player_rect = self.player.get_rect()
        magnet_range = 150 if self.magnet_active else 0
        
        for amethyst in self.amethysts[:]:
            if not amethyst.collected:
                amethyst_rect = amethyst.get_rect()
                
                # Эффект магнита - притягиваем аметисты
                if self.magnet_active:
                    dx = player_rect.centerx - amethyst_rect.centerx
                    dy = player_rect.centery - amethyst_rect.centery
                    distance = math.sqrt(dx*dx + dy*dy)
                    if distance < magnet_range and distance > 0:
                        pull_strength = (magnet_range - distance) / magnet_range * 3
                        amethyst.x += dx / distance * pull_strength
                        amethyst.y += dy / distance * pull_strength
                
                if player_rect.colliderect(amethyst_rect):
                    amethyst.collected = True
                    amethysts_gained = int(self.combo_multiplier)
                    self.total_amethysts += amethysts_gained
                    self.stats["total_amethysts_collected"] = self.stats.get("total_amethysts_collected", 0) + amethysts_gained
                    self.add_combo()  # Добавляем к комбо
                    self.update_quest_progress(QuestType.COLLECT_AMETHYSTS)  # Обновляем задание
                    
                    # UI/UX: Легкий эффект вспышки при сборе аметиста
                    self.flash_alpha = min(100, self.flash_alpha + 30)
                    self.flash_color = (148, 0, 211)  # Фиолетовый цвет аметиста
                    
                    # UI/UX: Легкий эффект вспышки при сборе аметиста
                    self.flash_alpha = min(100, self.flash_alpha + 30)
                    self.flash_color = (148, 0, 211)  # Фиолетовый цвет аметиста
                    
                    # UI/UX: Легкий эффект вспышки при сборе аметиста
                    self.flash_alpha = min(100, self.flash_alpha + 30)
                    self.flash_color = (148, 0, 211)  # Фиолетовый цвет аметиста
        
        # Сбор бонусов
        if hasattr(self, 'bonuses'):
            for bonus in self.bonuses[:]:
                if not bonus.collected and player_rect.colliderect(bonus.get_rect()):
                    bonus.collected = True
                    self.activate_bonus(bonus.type)
                    
                    # Звук бонуса
                    self.play_sound_safe(self.bonus_sound)
                    
                    # Бонусные очки за комбо
                    bonus_score = int(10 * (self.combo_multiplier - 1))
                    if bonus_score > 0:
                        self.score += bonus_score
                        self.update_quest_progress(QuestType.SCORE_POINTS, amount=bonus_score)
                    
                    self.play_sound_safe(self.collect_sound)
                    
                    particle_count = min(20, 10 + self.player.skin_level)
                    self.particle_system.add_particles(
                        bonus.x + bonus.size//2,
                        bonus.y + bonus.size//2,
                        self.PURPLE,
                        count=particle_count,
                        speed=3
                    )
                    
                    if self.account_system.current_account and self.account_system.conn:
                        try:
                            cursor = self.account_system.conn.cursor()
                            cursor.execute('UPDATE players SET amethysts = ? WHERE username = ?',
                                         (self.total_amethysts, self.account_system.current_account['username']))
                            self.account_system.conn.commit()
                        except sqlite3.Error as e:
                            logging.error(f"Database error updating amethysts: {e}")

        # Камера
        target_camera_x = self.player.x - 250
        self.camera_x += (target_camera_x - self.camera_x) * 0.1

        # Прогресс для кастомных уровней уже рассчитан в начале update_game()
        # Дублирующий расчет удален для оптимизации

    def handle_level_complete(self):
        if self.player:
            self.player.y += 5
            self.player.x += 3
            
            if self.player.y > self.SCREEN_HEIGHT + 100:
                self.show_level_complete_screen()

    def show_level_complete_screen(self):
        self.state = GameState.LEVEL_COMPLETE

    def spawn_random_obstacle(self):
        obstacle_type = random.choices(
            [ObstacleType.SPIKE, ObstacleType.PLATFORM, ObstacleType.MOVING_SPIKE, ObstacleType.SPIKE_CLUSTER],
            weights=[0.4, 0.3, 0.2, 0.1]
        )[0]
        
        if obstacle_type == ObstacleType.SPIKE:
            height = random.choice([80, 100, 120, 150])
            self.obstacles.append(Obstacle(
                self.SCREEN_WIDTH + 50,
                self.SCREEN_HEIGHT - height,
                ObstacleType.SPIKE,
                60, height,
                (220, 20, 60)
            ))
            
        elif obstacle_type == ObstacleType.PLATFORM:
            width = random.randint(120, 250)
            height = 25
            y_pos = random.randint(300, 450)
            platform = Obstacle(
                self.SCREEN_WIDTH + 50,
                y_pos,
                ObstacleType.PLATFORM,
                width, height,
                (70, 130, 180)
            )
            self.obstacles.append(platform)
            
            if random.random() < 0.3:
                self.amethysts.append(Amethyst(
                    platform.x + width // 2 - 15,
                    y_pos - 40
                ))
                
        elif obstacle_type == ObstacleType.MOVING_SPIKE:
            height = random.choice([60, 80, 100])
            spike = Obstacle(
                self.SCREEN_WIDTH + 50,
                self.SCREEN_HEIGHT - height,
                ObstacleType.MOVING_SPIKE,
                50, height,
                (255, 69, 0)
            )
            spike.move_speed = random.uniform(1.0, 3.0)
            spike.original_y = spike.y
            self.obstacles.append(spike)
            
        elif obstacle_type == ObstacleType.SPIKE_CLUSTER:
            cluster_width = random.randint(200, 350)
            spike_count = random.randint(3, 6)
            spike_width = cluster_width // spike_count
            
            for i in range(spike_count):
                spike_height = random.choice([70, 90, 110, 130])
                self.obstacles.append(Obstacle(
                    self.SCREEN_WIDTH + 50 + i * spike_width,
                    self.SCREEN_HEIGHT - spike_height,
                    ObstacleType.SPIKE,
                    spike_width - 10, spike_height,
                    (178, 34, 34)
                ))
                
    # РЕДАКТОР УРОВНЕЙ
    def start_editor(self):
        self.editor_obstacles = []
        self.editor_amethysts = []
        self.editor_selected_type = ObstacleType.SPIKE
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
        self.editor_panel_height = 80
        self.editor_panel_y = self.SCREEN_HEIGHT - self.editor_panel_height
        self.state = GameState.EDITOR

    def handle_editor_events(self, event):
        if not hasattr(self, "editor_panel_y"):
            self.editor_panel_y = self.SCREEN_HEIGHT - 80
            self.editor_panel_height = 80
    
        mx, my = pygame.mouse.get_pos()
        wx = mx + self.editor_camera_x
        wy = my + self.editor_camera_y

        # УЛУЧШЕНИЕ РЕДАКТОРА: Проверка клика по панели инструментов
        if my > self.editor_panel_y:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Определяем, какой инструмент выбран
                panel_item_width = self.SCREEN_WIDTH // 8
                item_index = mx // panel_item_width
                
                obstacle_types = [
                    ObstacleType.SPIKE,
                    ObstacleType.PLATFORM,
                    ObstacleType.MOVING_SPIKE,
                    ObstacleType.ROTATING_SPIKE,
                    ObstacleType.ICE_PLATFORM,
                    ObstacleType.BOUNCING_PLATFORM,
                    ObstacleType.DISAPPEARING_PLATFORM,
                    None  # Аметист
                ]
                
                if item_index < len(obstacle_types):
                    if obstacle_types[item_index] is None:
                        # Добавляем аметист
                        if self.editor_grid_snap:
                            wx = round(wx / 40) * 40
                            wy = round(wy / 40) * 40
                        self.editor_amethysts.append(Amethyst(wx, wy))
                    else:
                        self.editor_selected_type = obstacle_types[item_index]
            return  # Не обрабатываем дальше, если клик по панели

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                clicked = None
                for obj in self.editor_obstacles:
                    obj_rect = self.get_editor_object_rect(obj)
                    if obj_rect.collidepoint(mx, my):
                        clicked = obj
                        break
                
                # УЛУЧШЕНИЕ: Также проверяем аметисты
                if not clicked:
                    for i, amethyst in enumerate(self.editor_amethysts):
                        amethyst_rect = pygame.Rect(
                            amethyst.x - self.editor_camera_x,
                            amethyst.y - self.editor_camera_y,
                            amethyst.size * 2,
                            amethyst.size * 2
                        )
                        if amethyst_rect.collidepoint(mx, my):
                            self.editor_selected_object = amethyst
                            self.editor_dragging = True
                            self.editor_drag_start = (mx, my)
                            return

                if clicked:
                    self.editor_selected_object = clicked
                    self.editor_dragging = True
                    self.editor_drag_start = (mx, my)
                else:
                    # УЛУЧШЕНИЕ: Не создаем объект, если клик по панели
                    if my < self.editor_panel_y:
                        if self.editor_grid_snap:
                            wx = round(wx / 40) * 40
                            wy = round(wy / 40) * 40

                        obj = Obstacle(wx, wy, self.editor_selected_type)
                        editor_type_str = self.editor_selected_type.value if isinstance(self.editor_selected_type, ObstacleType) else self.editor_selected_type
                        if editor_type_str == ObstacleType.SPIKE.value:
                            obj.w = 60
                            obj.h = 80
                            obj.color = (220, 20, 60)
                        elif editor_type_str == ObstacleType.PLATFORM.value:
                            obj.w = 120
                            obj.h = 25
                            obj.color = (70, 130, 180)
                        elif editor_type_str == ObstacleType.MOVING_SPIKE.value:
                            obj.w = 50
                            obj.h = 80
                            obj.color = (255, 69, 0)
                            obj.move_speed = 2.0
                        elif editor_type_str == ObstacleType.ROTATING_SPIKE.value:
                            obj.w = 50
                            obj.h = 80
                            obj.color = (255, 100, 100)
                            obj.rotation_speed = 3.0
                            obj.rotation_angle = 0
                        elif editor_type_str == ObstacleType.ICE_PLATFORM.value:
                            obj.w = 120
                            obj.h = 25
                            obj.color = (173, 216, 230)
                        elif editor_type_str == ObstacleType.BOUNCING_PLATFORM.value:
                            obj.w = 120
                            obj.h = 25
                            obj.color = (0, 200, 100)
                            obj.bounce_power = 1.5
                        elif editor_type_str == ObstacleType.DISAPPEARING_PLATFORM.value:
                            obj.w = 120
                            obj.h = 25
                            obj.color = (255, 165, 0)
                            obj.disappear_timer = 60
                            obj.visible = True
                        
                        if editor_type_str == ObstacleType.MOVING_SPIKE.value:
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
            # УЛУЧШЕНИЕ: Движение объектов мышкой (препятствия и аметисты)
            if self.editor_dragging and self.editor_selected_object:
                dx = mx - self.editor_drag_start[0]
                dy = my - self.editor_drag_start[1]
                if self.editor_grid_snap:
                    dx = round(dx / 40) * 40
                    dy = round(dy / 40) * 40
                
                # УЛУЧШЕНИЕ: Поддержка движения аметистов
                if isinstance(self.editor_selected_object, Amethyst):
                    self.editor_selected_object.x += dx
                    self.editor_selected_object.y += dy
                else:
                    # Препятствие
                    self.editor_selected_object.x += dx
                    self.editor_selected_object.y += dy
                    obj_type_str = self.editor_selected_object.type.value if isinstance(self.editor_selected_object.type, ObstacleType) else self.editor_selected_object.type
                    if obj_type_str == ObstacleType.MOVING_SPIKE.value:
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
                self.editor_selected_type = ObstacleType.SPIKE
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.editor_selected_type = ObstacleType.PLATFORM
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self.editor_selected_type = ObstacleType.MOVING_SPIKE
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
        if not hasattr(self, 'editor_panel_y'):
            self.editor_panel_y = self.SCREEN_HEIGHT - 80
            self.editor_panel_height = 80
            
            self.screen.fill((15, 15, 35))

        # УЛУЧШЕНИЕ РЕДАКТОРА: Рисуем сетку только до панели
        if self.editor_show_grid:
            grid = 40
            offset_x = self.editor_camera_x % grid
            offset_y = self.editor_camera_y % grid
            for x in range(offset_x, self.SCREEN_WIDTH, grid):
                pygame.draw.line(self.screen, (60, 60, 80), (x, 0), (x, self.editor_panel_y))
            for y in range(offset_y, self.editor_panel_y, grid):
                pygame.draw.line(self.screen, (60, 60, 80), (0, y), (self.SCREEN_WIDTH, y))

        for obj in self.editor_obstacles:
            x = obj.x - self.editor_camera_x
            y = obj.y - self.editor_camera_y

            if -100 < x < self.SCREEN_WIDTH + 100 and -100 < y < self.SCREEN_HEIGHT + 100:
                obj_type_str = obj.type.value if isinstance(obj.type, ObstacleType) else obj.type
                if obj_type_str == ObstacleType.SPIKE.value:
                    points = [(x+20, y+60), (x+40, y), (x+60, y+60)]
                    color = (255, 80, 80) if obj == self.editor_selected_object else self.RED
                    pygame.draw.polygon(self.screen, color, points)
                    pygame.draw.polygon(self.screen, self.WHITE, points, 2)

                elif obj_type_str == ObstacleType.PLATFORM.value:
                    rect = (x, y, obj.w, obj.h)
                    color = self.GOLD if obj == self.editor_selected_object else (200, 160, 40)
                    pygame.draw.rect(self.screen, color, rect)
                    pygame.draw.rect(self.screen, self.WHITE, rect, 3)

                elif obj_type_str == ObstacleType.MOVING_SPIKE.value:
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

        # УЛУЧШЕНИЕ: Выделение выбранного объекта (препятствие или аметист)
        if self.editor_selected_object:
            sx = self.editor_selected_object.x - self.editor_camera_x
            sy = self.editor_selected_object.y - self.editor_camera_y
            
            if isinstance(self.editor_selected_object, Amethyst):
                # Выделение аметиста
                sx += self.editor_selected_object.size // 2
                sy += self.editor_selected_object.size // 2
                pygame.draw.circle(self.screen, self.CYAN, (int(sx), int(sy)), 25, 3)
            else:
                # Выделение препятствия
                sel_obj_type_str = self.editor_selected_object.type.value if isinstance(self.editor_selected_object.type, ObstacleType) else self.editor_selected_object.type
                if sel_obj_type_str == ObstacleType.PLATFORM.value:
                    sx += self.editor_selected_object.w // 2
                    sy += self.editor_selected_object.h // 2
                else:
                    sx += 40
                    sy += 30
                pygame.draw.circle(self.screen, self.CYAN, (int(sx), int(sy)), 50, 3)

        # Локализованные подсказки редактора
        # Локализованные подсказки редактора
    # ИСПРАВЛЕНИЕ: Получаем строковое значение типа препятствия
        editor_selected_type_str = ""
        if isinstance(self.editor_selected_type, ObstacleType):
            editor_selected_type_str = self.editor_selected_type.value.upper()
        elif isinstance(self.editor_selected_type, str):
            editor_selected_type_str = self.editor_selected_type.upper()
        else:
            editor_selected_type_str = str(self.editor_selected_type)
        
        lines = [
            self.localization.get('editor_title'),
            f"{self.localization.get('objects_count')}: {len(self.editor_obstacles)} | {self.localization.get('amethysts_count')}: {len(self.editor_amethysts)} | {self.localization.get('object_type')}: {editor_selected_type_str}",
            f"{self.localization.get('grid')}: {self.localization.get('on') if self.editor_grid_snap else self.localization.get('off')} (G) | {self.localization.get('show_grid')}: {self.localization.get('on') if self.editor_show_grid else self.localization.get('off')} (H)",
            "1/2/3 — смена типа | A — добавить аметист | ЛКМ — поставить/выбрать | ПКМ — удалить",
            "DEL — удалить выбранный | C — очистить | Ctrl+S — сохранить | Ctrl+L — загрузить",
            "Shift+Колёсико — прокрутка | ESC — выход"
        ]
        
        for i, text in enumerate(lines):
            color = self.CYAN if i == 0 else self.WHITE
            surf = self.small_font.render(text, True, color)
            self.screen.blit(surf, (10, 10 + i*25))

        # УЛУЧШЕНИЕ РЕДАКТОРА: Панель инструментов снизу
        panel_y = self.editor_panel_y
        pygame.draw.rect(self.screen, (30, 30, 50), (0, panel_y, self.SCREEN_WIDTH, self.editor_panel_height))
        pygame.draw.line(self.screen, (100, 100, 120), (0, panel_y), (self.SCREEN_WIDTH, panel_y), 2)
        
        # Иконки инструментов
        obstacle_types = [
            (ObstacleType.SPIKE, "Шип", (220, 20, 60)),
            (ObstacleType.PLATFORM, "Платформа", (70, 130, 180)),
            (ObstacleType.MOVING_SPIKE, "Движ. шип", (255, 69, 0)),
            (ObstacleType.ROTATING_SPIKE, "Вращ. шип", (150, 0, 150)),
            (ObstacleType.ICE_PLATFORM, "Лёд", (173, 216, 230)),
            (ObstacleType.BOUNCING_PLATFORM, "Прыжок", (0, 200, 100)),
            (ObstacleType.DISAPPEARING_PLATFORM, "Исчез.", (255, 165, 0)),
            (None, "Аметист", self.PURPLE)  # Аметист
        ]
        
        panel_item_width = self.SCREEN_WIDTH // len(obstacle_types)
        for i, (obs_type, name, color) in enumerate(obstacle_types):
            x_pos = i * panel_item_width
            item_rect = pygame.Rect(x_pos, panel_y, panel_item_width, self.editor_panel_height)
            
            # Подсветка выбранного инструмента
            is_selected = (obs_type == self.editor_selected_type) or (obs_type is None and isinstance(self.editor_selected_object, Amethyst))
            bg_color = (60, 60, 80) if is_selected else (40, 40, 60)
            pygame.draw.rect(self.screen, bg_color, item_rect)
            pygame.draw.rect(self.screen, color if is_selected else (80, 80, 100), item_rect, 2)
            
            # Рисуем иконку
            icon_y = panel_y + 10
            if obs_type is None:
                # Аметист
                pygame.draw.circle(self.screen, color, (x_pos + panel_item_width // 2, icon_y + 15), 12)
                pygame.draw.circle(self.screen, self.WHITE, (x_pos + panel_item_width // 2, icon_y + 15), 12, 2)
            elif obs_type == ObstacleType.SPIKE:
                # Шип
                points = [(x_pos + panel_item_width // 2 - 10, icon_y + 20), 
                         (x_pos + panel_item_width // 2, icon_y), 
                         (x_pos + panel_item_width // 2 + 10, icon_y + 20)]
                pygame.draw.polygon(self.screen, color, points)
            elif obs_type == ObstacleType.PLATFORM:
                # Платформа
                pygame.draw.rect(self.screen, color, (x_pos + 5, icon_y + 10, panel_item_width - 10, 8))
            else:
                # Другие типы - упрощенная иконка
                pygame.draw.rect(self.screen, color, (x_pos + 5, icon_y + 5, panel_item_width - 10, 20))
            
            # Название инструмента
            name_surf = self.small_font.render(name, True, self.WHITE)
            name_x = x_pos + (panel_item_width - name_surf.get_width()) // 2
            self.screen.blit(name_surf, (name_x, panel_y + 35))
        
        if self.editor_message and self.editor_message_timer > 0:
            msg_surf = self.font.render(self.editor_message, True, self.GREEN)
            self.screen.blit(msg_surf, (self.SCREEN_WIDTH//2 - msg_surf.get_width()//2, panel_y - 30))

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
            
            obstacles_data = []
            for obj in self.editor_obstacles:
                obj_type_str = obj.type.value if isinstance(obj.type, ObstacleType) else obj.type
                obj_data = {
                    "x": obj.x, "y": obj.y, "type": obj_type_str,
                    "w": obj.w, "h": obj.h, "color": obj.color
                }
                if obj_type_str == ObstacleType.MOVING_SPIKE.value:
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
            self.editor_message = f"Уровень сохранен: {os.path.basename(filename)}" if self.language == 'ru' else f"Level saved: {os.path.basename(filename)}"
            self.editor_message_timer = 180
            
        except Exception as e:
            self.editor_message = f"Ошибка сохранения: {e}" if self.language == 'ru' else f"Save error: {e}"
            self.editor_message_timer = 180

    def load_level(self):
        try:
            filename = f"levels/{self.editor_level_name}.json"
            if not os.path.exists(filename):
                files = [f for f in os.listdir("levels") if f.endswith(".json")]
                if files:
                    filename = f"levels/{files[0]}"
                else:
                    self.editor_message = "Нет сохраненных уровней" if self.language == 'ru' else "No saved levels"
                    self.editor_message_timer = 180
                    return
            
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                
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
            self.editor_message = f"Уровень загружен: {os.path.basename(filename)}" if self.language == 'ru' else f"Level loaded: {os.path.basename(filename)}"
            self.editor_message_timer = 180
            
        except Exception as e:
            self.editor_message = f"Ошибка загрузки: {e}" if self.language == 'ru' else f"Load error: {e}"
            self.editor_message_timer = 180

    # УЛУЧШЕННАЯ ОТРИСОВКА С ОПТИМИЗАЦИЕЙ
    def draw_game(self):
        # ОПТИМИЗАЦИЯ: Кэширование фона
        parallax_offset = int(self.camera_x * 0.3) % self.SCREEN_WIDTH
        
        # Создаем кэшированный фон только если камера значительно сдвинулась
        if (self.cached_bg_surface is None or 
            abs(self.cached_bg_camera_x - parallax_offset) > 50):
            self.cached_bg_surface = pygame.Surface((self.SCREEN_WIDTH * 2, self.SCREEN_HEIGHT))
            for i in range(self.SCREEN_HEIGHT):
                color_value = 10 + int(40 * (i / self.SCREEN_HEIGHT))
                base_color = (color_value, color_value, 60 + color_value)
                
                if int(i / 20) % 2 == 0:
                    stripe_color = (color_value + 10, color_value + 10, 70 + color_value)
                else:
                    stripe_color = base_color
                
                pygame.draw.line(self.cached_bg_surface, stripe_color, 
                               (0, i), (self.SCREEN_WIDTH * 2, i))
            self.cached_bg_camera_x = parallax_offset
        
        # Отрисовка кэшированного фона
        self.screen.blit(self.cached_bg_surface, (-parallax_offset, 0))
        
        # ОПТИМИЗАЦИЯ: Кэширование земли
        if self.cached_ground_surface is None:
            self.cached_ground_surface = pygame.Surface((self.SCREEN_WIDTH, 50))
            for i in range(0, self.SCREEN_WIDTH, 40):
                color_variation = random.randint(-10, 10)
                ground_color = (50 + color_variation, 50 + color_variation, 90 + color_variation)
                pygame.draw.rect(self.cached_ground_surface, ground_color, (i, 0, 40, 50))
                pygame.draw.line(self.cached_ground_surface, (70, 70, 110), (i, 0), (i, 50), 2)
        
        self.screen.blit(self.cached_ground_surface, (0, 550))

        # ФИНИШНЫЙ ПОРТАЛ
        if not self.enable_random_generation:
            portal_x = self.level_end_x - self.camera_x
            if -100 < portal_x < self.SCREEN_WIDTH + 100:
                time_ms = pygame.time.get_ticks()
                pulse = math.sin(time_ms * 0.01) * 15 + math.sin(time_ms * 0.005) * 8
                portal_width = 100 + pulse
                portal_rect = pygame.Rect(portal_x, 300, portal_width, 200)
                
                for layer in range(3):
                    layer_offset = layer * 20
                    for i in range(200):
                        color_value = int(128 + 127 * math.sin(i * 0.1 + time_ms * 0.005 + layer * 0.5))
                        alpha = 255 - layer * 80
                        color = (color_value, 0, color_value, alpha)
                        
                        line_surf = pygame.Surface((portal_width, 1), pygame.SRCALPHA)
                        line_surf.fill(color)
                        self.screen.blit(line_surf, (portal_x, 300 + i + layer_offset))
                
                pygame.draw.rect(self.screen, self.GOLD, portal_rect, 6)
                
                if portal_x < self.SCREEN_WIDTH - 100:
                    finish_text = self.font.render("FINISH", True, self.GOLD)
                    text_shadow = self.font.render("FINISH", True, (0, 0, 0, 128))
                    
                    self.screen.blit(text_shadow, (portal_x + 12, 272))
                    self.screen.blit(finish_text, (portal_x + 10, 270))
                    
        # ФИНИШНАЯ ЛИНИЯ
        if not self.enable_random_generation and self.level_end_x > 0:
            finish_x = self.level_end_x - self.camera_x
            if -100 < finish_x < self.SCREEN_WIDTH + 100:
                pulse = math.sin(pygame.time.get_ticks() * 0.01) * 10
                pygame.draw.line(self.screen, self.GOLD,
                            (finish_x, 100),
                            (finish_x, 500), 6 + int(pulse))
                
                if finish_x < self.SCREEN_WIDTH - 50:
                    finish_text = self.font.render("SQUARE COMPLETE", True, self.GOLD)
                    text_rect = finish_text.get_rect(center=(finish_x + 50, 80))
                    self.screen.blit(finish_text, text_rect)

        # ПРЕПЯТСТВИЯ (с оптимизацией culling)
        for obj in self.obstacles:
            x = obj.x - self.camera_x
            # ОПТИМИЗАЦИЯ: Ранний выход для объектов вне экрана
            if x < -150 or x > self.SCREEN_WIDTH + 150:
                continue
            if -100 < x < self.SCREEN_WIDTH + 100:
                obj_type_str = obj.type.value if isinstance(obj.type, ObstacleType) else obj.type
                if obj_type_str == ObstacleType.SPIKE.value:
                    points = [(x + obj.w//2, obj.y), (x, obj.y + obj.h), (x + obj.w, obj.y + obj.h)]
                    pygame.draw.polygon(self.screen, obj.color, points)
                    
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
                    
                elif obj_type_str == ObstacleType.MOVING_SPIKE.value:
                    points = [(x + obj.w//2, obj.y), (x, obj.y + obj.h), (x + obj.w, obj.y + obj.h)]
                    pygame.draw.polygon(self.screen, obj.color, points)
                    pygame.draw.polygon(self.screen, (200, 50, 0), points, 3)
                    
                elif obj_type_str == ObstacleType.PLATFORM.value:
                    pygame.draw.rect(self.screen, obj.color, (x, obj.y, obj.w, obj.h))
                    
                    for i in range(0, obj.w, 10):
                        line_color = (40, 80, 120) if i % 20 == 0 else (60, 100, 140)
                        pygame.draw.line(self.screen, line_color, 
                                       (x + i, obj.y), 
                                       (x + i, obj.y + obj.h), 2)
                    
                    pygame.draw.rect(self.screen, (40, 80, 120), (x, obj.y, obj.w, obj.h), 3)
                    
                elif obj_type_str == ObstacleType.BOUNCING_PLATFORM.value:
                    pulse = math.sin(pygame.time.get_ticks() * 0.02) * 3
                    pygame.draw.rect(self.screen, obj.color, 
                                   (x, obj.y + pulse, obj.w, obj.h))
                    
                    bounce_lines = int(obj.bounce_power * 5)
                    for i in range(bounce_lines):
                        line_y = obj.y + obj.h + i * 3
                        alpha = 255 - i * 40
                        line_surf = pygame.Surface((obj.w, 1), pygame.SRCALPHA)
                        line_surf.fill((0, 255, 100, alpha))
                        self.screen.blit(line_surf, (x, line_y))
                    
                    pygame.draw.rect(self.screen, (0, 150, 50), 
                                   (x, obj.y + pulse, obj.w, obj.h), 3)
                    
                elif obj_type_str == ObstacleType.DISAPPEARING_PLATFORM.value:
                    if obj.visible:
                        alpha = max(100, min(255, obj.disappear_timer * 4))
                        platform_surf = pygame.Surface((obj.w, obj.h), pygame.SRCALPHA)
                        pygame.draw.rect(platform_surf, (*obj.color, alpha), (0, 0, obj.w, obj.h))
                        self.screen.blit(platform_surf, (x, obj.y))
                        
                        if obj.disappear_timer < 30:
                            blink = math.sin(pygame.time.get_ticks() * 0.1) > 0
                            if blink:
                                pygame.draw.rect(self.screen, (255, 255, 255, 100), 
                                               (x, obj.y, obj.w, obj.h), 2)
                        
                        pygame.draw.rect(self.screen, (200, 100, 0), 
                                       (x, obj.y, obj.w, obj.h), 3)
                
                # КОНТЕНТ: Отрисовка вращающегося шипа
                elif obj_type_str == ObstacleType.ROTATING_SPIKE.value:
                    if hasattr(obj, 'rotation_angle'):
                        # Вращаем шип вокруг центра
                        center_x = x + obj.w // 2
                        center_y = obj.y + obj.h // 2
                        angle = obj.rotation_angle * math.pi / 180
                        
                        # Создаем точки треугольника с учетом вращения
                        size = min(obj.w, obj.h) // 2
                        points = []
                        for i in range(3):
                            point_angle = angle + (i * 2 * math.pi / 3)
                            px = center_x + size * math.cos(point_angle)
                            py = center_y + size * math.sin(point_angle)
                            points.append((px, py))
                        
                        pygame.draw.polygon(self.screen, obj.color, points)
                        pygame.draw.polygon(self.screen, (200, 50, 50), points, 3)
                    else:
                        # Fallback если нет угла вращения
                        points = [(x + obj.w//2, obj.y), (x, obj.y + obj.h), (x + obj.w, obj.y + obj.h)]
                        pygame.draw.polygon(self.screen, obj.color, points)
                        pygame.draw.polygon(self.screen, (200, 50, 50), points, 3)
                
                # КОНТЕНТ: Отрисовка ледяной платформы
                elif obj_type_str == ObstacleType.ICE_PLATFORM.value:
                    # Ледяной эффект с бликами
                    pygame.draw.rect(self.screen, obj.color, (x, obj.y, obj.w, obj.h))
                    
                    # Блики на льду
                    time_ms = pygame.time.get_ticks()
                    for i in range(0, obj.w, 30):
                        if (i + time_ms // 50) % 60 < 20:
                            highlight = pygame.Surface((20, obj.h), pygame.SRCALPHA)
                            highlight.fill((255, 255, 255, 100))
                            self.screen.blit(highlight, (x + i, obj.y))
                    
                    pygame.draw.rect(self.screen, (135, 206, 250), (x, obj.y, obj.w, obj.h), 3)

        # БОНУСЫ (с оптимизацией culling)
        if hasattr(self, 'bonuses'):
            for bonus in self.bonuses:
                if not bonus.collected:
                    x = bonus.x - self.camera_x
                    # ОПТИМИЗАЦИЯ: Ранний выход для бонусов вне экрана
                    if x < -100 or x > self.SCREEN_WIDTH + 100:
                        continue
                    y = bonus.get_float_y()
                    if -50 < x < self.SCREEN_WIDTH + 50:
                        color = bonus.get_color()
                        size = bonus.size + int(math.sin(bonus.pulse_phase) * 3)
                        
                        # Рисуем бонус как звезду
                        points = []
                        for i in range(5):
                            angle = (i * 2 * math.pi / 5) - math.pi / 2 + bonus.rotation * math.pi / 180
                            outer_x = x + size * math.cos(angle)
                            outer_y = y + size * math.sin(angle)
                            points.append((outer_x, outer_y))
                            
                            angle += math.pi / 5
                            inner_x = x + size * 0.4 * math.cos(angle)
                            inner_y = y + size * 0.4 * math.sin(angle)
                            points.append((inner_x, inner_y))
                        
                        pygame.draw.polygon(self.screen, color, points)
                        pygame.draw.polygon(self.screen, (255, 255, 255), points, 2)
        
        # АМЕТИСТЫ (с оптимизацией culling)
        for amethyst in self.amethysts:
            if not amethyst.collected:
                x = amethyst.x - self.camera_x
                # ОПТИМИЗАЦИЯ: Ранний выход для аметистов вне экрана
                if x < -100 or x > self.SCREEN_WIDTH + 100:
                    continue
                if -50 < x < self.SCREEN_WIDTH + 50:
                    float_y = amethyst.get_float_y()
                    current_size = amethyst.get_current_size()
                    
                    if self.amethyst_image:
                        rotated_image = pygame.transform.rotate(self.amethyst_image, amethyst.rotation)
                        scaled_size = int(current_size * 1.5)
                        scaled_image = pygame.transform.scale(rotated_image, (scaled_size, scaled_size))
                        
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
                        pygame.draw.circle(self.screen, (148, 0, 211), 
                                         (int(x + 15), int(float_y + 15)), int(current_size//2))
                        pygame.draw.circle(self.screen, (255, 255, 255), 
                                         (int(x + 15), int(float_y + 15)), int(current_size//2), 2)

        # ИГРОК
        if self.player:
            px = self.player.x - self.camera_x
            py = self.player.y
            
            # Эффект щита
            if self.player.invincible:
                shield_radius = self.player.size + 5 + math.sin(pygame.time.get_ticks() * 0.05) * 3
                shield_surf = pygame.Surface((shield_radius*2, shield_radius*2), pygame.SRCALPHA)
                
                for i in range(3):
                    radius = shield_radius - i * 3
                    alpha = 100 - i * 30
                    pygame.draw.circle(shield_surf, (0, 255, 255, alpha), 
                                     (shield_radius, shield_radius), radius, 2)
                
                self.screen.blit(shield_surf, (px - shield_radius + self.player.size//2, 
                                             py - shield_radius + self.player.size//2))
            
            # Эффекты даша
            if self.is_dashing:
                # След даша
                trail_length = 8
                for i in range(trail_length):
                    trail_alpha = int(255 * (1 - i / trail_length))
                    trail_size = self.player.size * (1 - i * 0.1)
                    trail_x = px - (i + 1) * self.dash_speed * self.dash_direction * 0.5
                    trail_surf = pygame.Surface((int(trail_size), int(trail_size)), pygame.SRCALPHA)
                    
                    if self.player_image:
                        trail_image = pygame.transform.scale(self.player_image, (int(trail_size), int(trail_size)))
                        trail_image.set_alpha(trail_alpha)
                        trail_surf.blit(trail_image, (0, 0))
                    else:
                        pygame.draw.rect(trail_surf, (*self.CYAN, trail_alpha), (0, 0, int(trail_size), int(trail_size)))
                    
                    self.screen.blit(trail_surf, (trail_x, py))
                
                # Энергетические волны вокруг игрока
                wave_radius = self.player.size + 10 + math.sin(pygame.time.get_ticks() * 0.1) * 5
                wave_surf = pygame.Surface((wave_radius*2, wave_radius*2), pygame.SRCALPHA)
                pygame.draw.circle(wave_surf, (0, 255, 255, 150), (wave_radius, wave_radius), wave_radius, 3)
                self.screen.blit(wave_surf, (px - wave_radius + self.player.size//2, 
                                           py - wave_radius + self.player.size//2))
            
            # Тень
            if not self.player.on_ground:
                shadow_size = max(20, 40 - abs(self.player.vy) * 2)
                shadow_alpha = max(50, 150 - abs(self.player.vy) * 10)
                shadow_surf = pygame.Surface((shadow_size, 10), pygame.SRCALPHA)
                shadow_surf.fill((0, 0, 0, shadow_alpha))
                self.screen.blit(shadow_surf, 
                               (px + (self.player.size - shadow_size)//2, 560))
            
            # Отображение игрока
            if self.player_image:
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

        # Отображение комбо
        if self.combo_counter >= 2:
            # Фон для комбо
            combo_bg = pygame.Surface((200, 60), pygame.SRCALPHA)
            combo_bg.fill((0, 0, 0, 150))
            combo_bg_rect = combo_bg.get_rect(center=(self.SCREEN_WIDTH//2, 120))
            self.screen.blit(combo_bg, combo_bg_rect)
            
            # Текст комбо
            if self.language == 'ru':
                combo_text = f"КОМБО: {self.combo_counter} (x{self.combo_multiplier:.1f})"
            else:
                combo_text = f"COMBO: {self.combo_counter} (x{self.combo_multiplier:.1f})"
            
            combo_surf = self.font.render(combo_text, True, self.GOLD)
            combo_rect = combo_surf.get_rect(center=(self.SCREEN_WIDTH//2, 120))
            self.screen.blit(combo_surf, combo_rect)
            
            # Таймер комбо (полоска)
            timer_width = 180 * (self.combo_timer / 90)
            timer_rect = pygame.Rect(self.SCREEN_WIDTH//2 - 90, 145, timer_width, 5)
            timer_color = self.GREEN if self.combo_timer > 60 else self.ORANGE if self.combo_timer > 30 else self.RED
            pygame.draw.rect(self.screen, timer_color, timer_rect)
            pygame.draw.rect(self.screen, self.WHITE, (self.SCREEN_WIDTH//2 - 90, 145, 180, 5), 1)

        # ИНТЕРФЕЙС с локализацией
        percent_text = self.title_font.render(f"{self.percent}%", True, self.GOLD)
        percent_rect = percent_text.get_rect(center=(self.SCREEN_WIDTH//2, 30))
        
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
        score_text = self.small_font.render(f"{self.localization.get('score')}: {self.score}", True, self.WHITE)
        speed_text = self.small_font.render(f"{self.localization.get('speed')}: {int(self.game_speed)}", True, self.WHITE)
        amethyst_text = self.small_font.render(f"{self.localization.get('amethysts')}: {self.total_amethysts}", True, self.PURPLE)
        
        self.screen.blit(score_text, (20, 20))
        self.screen.blit(speed_text, (20, 50))
        self.screen.blit(amethyst_text, (20, 80))
        
        # Информация о прокачке скина справа
        if self.player:
            level_text = self.small_font.render(f"{self.localization.get('level')} {self.player.skin_level}", True, self.GOLD)
            exp_text = self.small_font.render(f"{self.localization.get('exp')}: {self.player.skin_exp}", True, self.PURPLE)
            
            self.screen.blit(level_text, (self.SCREEN_WIDTH - 120, 20))
            self.screen.blit(exp_text, (self.SCREEN_WIDTH - 120, 50))
            
            # Прогресс бар опыта
            progress = self.player.get_exp_percentage()
            bar_width = 100
            bar_height = 8
            bar_x = self.SCREEN_WIDTH - bar_width - 30
            bar_y = 80
            
            pygame.draw.rect(self.screen, (50, 50, 50), 
                            (bar_x, bar_y, bar_width, bar_height),
                            border_radius=4)
            
            filled_width = int(bar_width * progress / 100)
            pygame.draw.rect(self.screen, self.GREEN, 
                            (bar_x, bar_y, filled_width, bar_height),
                            border_radius=4)
            
            pygame.draw.rect(self.screen, self.WHITE, 
                            (bar_x, bar_y, bar_width, bar_height), 1,
                            border_radius=4)
            
            percent_text = f"{progress:.0f}%"
            percent_surf = self.tiny_font.render(percent_text, True, self.WHITE)
            self.screen.blit(percent_surf, (bar_x + bar_width + 5, bar_y - 3))
            
            # Индикатор буста опыта
            if self.exp_boost_active:
                boost_text = self.tiny_font.render("EXP+20%", True, self.LIME)
                self.screen.blit(boost_text, (self.SCREEN_WIDTH - 80, 95))

        # УЛУЧШЕННЫЙ HUD: Улучшения игрока и таймеры бонусов
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
                if self.language == 'ru':
                    upgrades_display = "Улучшения: " + ", ".join(upgrades_text)
                else:
                    upgrades_display = "Upgrades: " + ", ".join(upgrades_text)
                upgrades_surf = self.small_font.render(upgrades_display, True, self.CYAN)
                self.screen.blit(upgrades_surf, (20, 110))
            
            # UI/UX: Таймеры активных бонусов
            bonus_y = 140
            if hasattr(self, 'magnet_active') and self.magnet_active and self.magnet_timer > 0:
                magnet_time = self.magnet_timer / 60.0
                bonus_text = f"MAGNET: {magnet_time:.1f}s" if self.language == 'en' else f"МАГНИТ: {magnet_time:.1f}с"
                bonus_surf = self.tiny_font.render(bonus_text, True, self.CYAN)
                self.screen.blit(bonus_surf, (20, bonus_y))
                # Прогресс-бар таймера
                bar_width = 150
                bar_height = 4
                timer_progress = self.magnet_timer / 600.0  # 600 = 10 секунд при 60 FPS
                pygame.draw.rect(self.screen, (50, 50, 50), (20, bonus_y + 18, bar_width, bar_height))
                pygame.draw.rect(self.screen, self.CYAN, (20, bonus_y + 18, int(bar_width * timer_progress), bar_height))
                bonus_y += 30
            
            if hasattr(self, 'slow_time_active') and self.slow_time_active and self.slow_time_timer > 0:
                slow_time = self.slow_time_timer / 60.0
                bonus_text = f"SLOW TIME: {slow_time:.1f}s" if self.language == 'en' else f"ЗАМЕДЛЕНИЕ: {slow_time:.1f}с"
                bonus_surf = self.tiny_font.render(bonus_text, True, self.ORANGE)
                self.screen.blit(bonus_surf, (20, bonus_y))
                # Прогресс-бар таймера
                bar_width = 150
                bar_height = 4
                timer_progress = self.slow_time_timer / 300.0  # 300 = 5 секунд при 60 FPS
                pygame.draw.rect(self.screen, (50, 50, 50), (20, bonus_y + 18, bar_width, bar_height))
                pygame.draw.rect(self.screen, self.ORANGE, (20, bonus_y + 18, int(bar_width * timer_progress), bar_height))
                bonus_y += 30
            
            if self.player.invincible and self.player.invincible_timer > 0:
                inv_time = self.player.invincible_timer / 60.0
                bonus_text = f"SHIELD: {inv_time:.1f}s" if self.language == 'en' else f"ЩИТ: {inv_time:.1f}с"
                bonus_surf = self.tiny_font.render(bonus_text, True, self.GREEN)
                self.screen.blit(bonus_surf, (20, bonus_y))
                # Прогресс-бар таймера
                bar_width = 150
                bar_height = 4
                timer_progress = self.player.invincible_timer / 300.0  # 300 = 5 секунд при 60 FPS
                pygame.draw.rect(self.screen, (50, 50, 50), (20, bonus_y + 18, bar_width, bar_height))
                pygame.draw.rect(self.screen, self.GREEN, (20, bonus_y + 18, int(bar_width * timer_progress), bar_height))
        
        # Индикатор прогресса заданий (справа внизу)
        if self.current_quests and self.state == GameState.PLAYING:
            quest_y = self.SCREEN_HEIGHT - 120
            quest_count = 0
            for quest in self.current_quests[:3]:  # Показываем максимум 3 задания
                progress = self.quest_progress.get(quest["id"], 0)
                target = quest["target"]
                percentage = min(100, (progress / target * 100)) if target > 0 else 0
                
                # Фон для задания
                quest_bg = pygame.Surface((200, 30), pygame.SRCALPHA)
                quest_bg.fill((0, 0, 0, 150))
                self.screen.blit(quest_bg, (self.SCREEN_WIDTH - 210, quest_y))
                
                # Текст прогресса
                quest_text = f"{progress}/{target}"
                quest_surf = self.tiny_font.render(quest_text, True, self.WHITE)
                self.screen.blit(quest_surf, (self.SCREEN_WIDTH - 200, quest_y + 2))
                
                # Прогресс-бар
                bar_width = 180
                bar_height = 4
                bar_x = self.SCREEN_WIDTH - 200
                bar_y = quest_y + 18
                
                pygame.draw.rect(self.screen, (50, 50, 50), 
                                (bar_x, bar_y, bar_width, bar_height))
                pygame.draw.rect(self.screen, self.GREEN if percentage >= 100 else self.CYAN, 
                                (bar_x, bar_y, int(bar_width * percentage / 100), bar_height))
                
                quest_y += 35
                quest_count += 1
                if quest_count >= 3:
                    break

        # Сообщение о полученном опыте
        if self.exp_message and self.exp_message_timer > 0:
            alpha = min(255, self.exp_message_timer * 2)
            exp_surf = self.font.render(self.exp_message, True, self.GOLD)
            exp_surf.set_alpha(alpha)
            
            shadow_surf = self.font.render(self.exp_message, True, (0, 0, 0, alpha//2))
            shadow_rect = shadow_surf.get_rect(center=(self.SCREEN_WIDTH//2 + 2, 102))
            self.screen.blit(shadow_surf, shadow_rect)
            
            exp_rect = exp_surf.get_rect(center=(self.SCREEN_WIDTH//2, 100))
            self.screen.blit(exp_surf, exp_rect)
        
        # Сообщение о комбо
        if self.combo_message and self.combo_message_timer > 0:
            alpha = min(255, self.combo_message_timer * 2)
            msg_surf = self.font.render(self.combo_message, True, self.GOLD)
            msg_surf.set_alpha(alpha)
            msg_rect = msg_surf.get_rect(center=(self.SCREEN_WIDTH//2, 180))
            self.screen.blit(msg_surf, msg_rect)
        
        # Управление с локализацией
        controls_text = self.small_font.render(
            f"{self.localization.get('controls_jump')} | {self.localization.get('controls_shield')} | {self.localization.get('controls_boost')} | {self.localization.get('controls_pause')}", 
            True, self.WHITE
        )
        controls_shadow = self.small_font.render(
            f"{self.localization.get('controls_jump')} | {self.localization.get('controls_shield')} | {self.localization.get('controls_boost')} | {self.localization.get('controls_pause')}", 
            True, (0, 0, 0, 128)
        )
        
        self.screen.blit(controls_shadow, 
                        (self.SCREEN_WIDTH//2 - controls_text.get_width()//2 + 1, 
                         self.SCREEN_HEIGHT - 29))
        
        self.screen.blit(controls_text, 
                        (self.SCREEN_WIDTH//2 - controls_text.get_width()//2, 
                         self.SCREEN_HEIGHT - 30))
        
        # Отрисовка частиц поверх всего
        self.particle_system.draw(self.screen)
        
        # Экран завершения уровня
        if self.level_complete:
            overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
            
            complete_text = self.title_font.render(self.localization.get('level_complete'), True, self.GOLD)
            text_shadow = self.title_font.render(self.localization.get('level_complete'), True, (0, 0, 0, 128))
            
            self.screen.blit(text_shadow, 
                           (self.SCREEN_WIDTH//2 - complete_text.get_width()//2 + 3, 
                            self.SCREEN_HEIGHT//2 - complete_text.get_height()//2 + 3))
            
            self.screen.blit(complete_text, 
                           (self.SCREEN_WIDTH//2 - complete_text.get_width()//2, 
                            self.SCREEN_HEIGHT//2 - complete_text.get_height()//2))
            
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
        """Отрисовка магазина с локализацией"""
        self.screen.fill(self.BLACK)
        title = self.title_font.render(self.localization.get('shop').upper(), True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        if self.player:
            exp_info = self.small_font.render(
                f"{self.localization.get('skin_progress')}: {self.localization.get('level')} {self.player.skin_level} | {self.localization.get('exp')}: {self.player.skin_exp}", 
                True, self.PURPLE
            )
            self.screen.blit(exp_info, (self.SCREEN_WIDTH//2 - exp_info.get_width()//2, 100))
        
        for i, item in enumerate(self.shop_items):
            y_pos = 150 + i * 100
            is_selected = i == self.selected_shop_item
            
            bg_color = (50, 50, 80) if is_selected else (30, 30, 50)
            pygame.draw.rect(self.screen, bg_color, (200, y_pos, 400, 80))
            pygame.draw.rect(self.screen, self.GOLD if is_selected else self.WHITE, (200, y_pos, 400, 80), 3)
            
            can_afford = self.total_amethysts >= item.cost
            color = self.GOLD if can_afford else (100, 100, 100)
            
            # Локализованные названия
            name_text = self.font.render(item.get_name(), True, color)
            cost_text = self.font.render(f"{item.cost} AM", True, self.PURPLE)
            desc_text = self.small_font.render(item.get_description(), True, self.WHITE)
            
            self.screen.blit(name_text, (220, y_pos + 10))
            self.screen.blit(cost_text, (500, y_pos + 10))
            self.screen.blit(desc_text, (220, y_pos + 45))
            
        # Баланс
        balance_text = self.font.render(f"{self.localization.get('amethysts')}: {self.total_amethysts}", True, self.PURPLE)
        self.screen.blit(balance_text, (self.SCREEN_WIDTH//2 - balance_text.get_width()//2, 500))
            
        # Подсказки
        back_text = self.font.render("ВВЕРХ/ВНИЗ: Выбор | ENTER: Купить | ESC: Назад" if self.language == 'ru' else "UP/DOWN: Select | ENTER: Buy | ESC: Back", True, self.WHITE)
        self.screen.blit(back_text, (self.SCREEN_WIDTH//2 - back_text.get_width()//2, 550))
        
    def draw_level_complete(self):
        """Отрисовка завершения уровня с улучшенными эффектами"""
        # Анимированный фон
        time = pygame.time.get_ticks() * 0.001
        for i in range(50):
            x = (i * 50 + time * 20) % (self.SCREEN_WIDTH + 100) - 50
            y = self.SCREEN_HEIGHT - 100 + math.sin(time + i) * 20
            size = 3 + math.sin(time * 2 + i) * 2
            pygame.draw.circle(self.screen, (100, 200, 255, 100), (int(x), int(y)), int(size))
        
        # Пульсирующий текст "УРОВЕНЬ ПРОЙДЕН"
        scale = 1.0 + 0.2 * math.sin(time * 3)
        complete_text = self.title_font.render(self.localization.get('level_complete'), True, self.GOLD)
        complete_text = pygame.transform.scale(complete_text, 
                                             (int(complete_text.get_width() * scale),
                                              int(complete_text.get_height() * scale)))
        
        self.screen.blit(complete_text, 
                        (self.SCREEN_WIDTH//2 - complete_text.get_width()//2, 
                         self.SCREEN_HEIGHT//2 - 120))
        
        # Статистика с анимацией
        collected_amethysts = len([a for a in self.amethysts if a.collected])
        total_amethysts = len(self.amethysts)
        
        stats = [
            f"{self.localization.get('score')}: {self.score}",
            f"{self.localization.get('amethysts')}: {collected_amethysts}/{total_amethysts}",
            f"{self.localization.get('percentage')}: {self.percent}%",
            f"Бонус за завершение: +20 {self.localization.get('amethysts').lower()}!" if self.language == 'ru' else f"Completion Bonus: +20 Amethysts!",
        ]
        
        for i, stat in enumerate(stats):
            # Анимация появления строк
            alpha = min(255, int((time - 2 - i * 0.3) * 255))
            if alpha > 0:
                stat_text = self.font.render(stat, True, (*self.WHITE, alpha))
                self.screen.blit(stat_text, (self.SCREEN_WIDTH//2 - stat_text.get_width()//2, 
                                           self.SCREEN_HEIGHT//2 + i*45 - 20))
        
        # Подсказка с миганием
        if int(time * 2) % 2:
            hint_text = self.small_font.render("Нажмите любую клавишу для продолжения" if self.language == 'ru' else "Press any key to continue", True, self.CYAN)
            self.screen.blit(hint_text, (self.SCREEN_WIDTH//2 - hint_text.get_width()//2, 
                                       self.SCREEN_HEIGHT - 80))
        
        # Конфетти эффект
        for _ in range(3):
            x = random.randint(0, self.SCREEN_WIDTH)
            y = random.randint(0, self.SCREEN_HEIGHT)
            color = random.choice([self.GOLD, self.CYAN, self.PURPLE, (255, 100, 100)])
            pygame.draw.circle(self.screen, color, (x, y), 2)

    def draw_menu(self):
        """Отрисовка старого меню с локализацией"""
        if self.menu_bg:
            self.screen.blit(self.menu_bg, (0, 0))
        else:
            self.screen.fill(self.BLACK)
        
        title = self.title_font.render(self.localization.get('game_title'), True, self.GOLD)
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
            "F11: Полный экран | L: Вход/Выход | P: Промокод | TAB: Смена меню",
            "НОВОЕ: Прогресс скинов, 10 пресет-уровней, улучшенная физика!",
            "Проходите уровни, чтобы зарабатывать Square-EXP и повышать уровень скина!"
        ] if self.language == 'ru' else [
            "F11: Fullscreen | L: Login/Logout | P: Promo Code | TAB: Switch Menu",
            "NEW: Skin Progression, 10 Preset Levels, Improved Physics!",
            "Complete levels to earn Square-EXP and level up your skin!"
        ]
        
        for i, hint in enumerate(hints):
            hint_text = self.small_font.render(hint, True, self.WHITE)
            self.screen.blit(hint_text, (20, 20 + i*30))
            
        if self.account_system.current_account:
            username = self.account_system.current_account['username']
            
            if self.player:
                skin_info = f" | {self.localization.get('skin_progress')}: {self.localization.get('level')} {self.player.skin_level}"
            else:
                skin_info = ""
                
            account_text = self.small_font.render(
                f"{self.localization.get('login')}: {username}{skin_info} | {self.localization.get('amethysts')}: {self.total_amethysts}", 
                True, self.GREEN
            )
            self.screen.blit(account_text, (20, self.SCREEN_HEIGHT - 40))
        else:
            login_text = self.small_font.render("Нажмите L для входа" if self.language == 'ru' else "Press L to login", True, self.WHITE)
            self.screen.blit(login_text, (20, self.SCREEN_HEIGHT - 40))
            
    def draw_button(self, text, rect, color, hover_color=None, mouse_pos=None):
        """Отрисовка кнопки с эффектом наведения"""
        if hover_color and rect.collidepoint(mouse_pos):
            current_color = hover_color
        else:
            current_color = color
        
        pygame.draw.rect(self.screen, current_color, rect, border_radius=8)
        pygame.draw.rect(self.screen, self.WHITE, rect, 2, border_radius=8)
        
        text_surf = self.font.render(text, True, self.WHITE)
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)

    def draw_inventory(self):
        self.screen.fill(self.BLACK)
        
        # Градиентный фон
        gradient_surf = self.create_gradient_menu_bg()
        self.screen.blit(gradient_surf, (0, 0))
        
        title = self.title_font.render(self.localization.get('inventory').upper(), True, self.GOLD)
        title_rect = title.get_rect(center=(self.SCREEN_WIDTH//2, 50))
        self.screen.blit(title, title_rect)
        
        center_x = self.SCREEN_WIDTH // 2
        
        # Информация об аккаунте
        if self.account_system.current_account:
            player_text = self.font.render(f"{self.localization.get('login')}: {self.account_system.current_account['username']}", 
                                        True, self.WHITE)
            player_rect = player_text.get_rect(center=(center_x, 100))
            self.screen.blit(player_text, player_rect)
        
        # Отображение скинов в сетке
        skin_keys = list(self.skins.keys())
        skins_per_row = 3
        skin_size = 140  # Увеличиваем размер для лучшего отображения
        skin_margin = 15
        start_x = center_x - ((skins_per_row * (skin_size + skin_margin)) - skin_margin) // 2
        start_y = 150
        
        # Создаем временную поверхность для предпросмотра скинов
        temp_surface = pygame.Surface((100, 100), pygame.SRCALPHA)
        
        for i, skin_id in enumerate(skin_keys):
            row = i // skins_per_row
            col = i % skins_per_row
            x = start_x + col * (skin_size + skin_margin)
            y = start_y + row * (skin_size + skin_margin)
            
            # Пропускаем если выходит за пределы экрана
            if y + skin_size > self.SCREEN_HEIGHT - 100:
                continue
            
            skin = self.skins[skin_id]
            
            # Фон для скина
            bg_color = (40, 40, 60) if skin_id != self.current_skin else (60, 60, 90)
            border_color = self.GREEN if skin_id == self.current_skin else (100, 100, 150)
            
            # Рамка скина
            pygame.draw.rect(self.screen, bg_color, (x, y, skin_size, skin_size), border_radius=12)
            pygame.draw.rect(self.screen, border_color, (x, y, skin_size, skin_size), 4, border_radius=12)
            
            # Предпросмотр скина - создаем изображение на основе названия
            preview_size = 80
            preview_x = x + (skin_size - preview_size) // 2
            preview_y = y + 20
            
            # Определяем цвет скина по его названию
            skin_name = skin["name"].lower() if isinstance(skin["name"], str) else skin["name"].get(self.language, "").lower()
            
            if "gold" in skin_name:
                # Золотой куб
                pygame.draw.rect(self.screen, self.GOLD, (preview_x, preview_y, preview_size, preview_size), border_radius=8)
                pygame.draw.rect(self.screen, (255, 215, 0), (preview_x + 5, preview_y + 5, preview_size - 10, preview_size - 10), border_radius=6)
                # Эффект блеска
                for dx in range(0, preview_size, 10):
                    pygame.draw.line(self.screen, (255, 255, 200, 100), 
                                (preview_x + dx, preview_y), 
                                (preview_x + dx, preview_y + preview_size), 2)
            
            elif "diamond" in skin_name:
                # Алмазный куб
                diamond_color = (185, 242, 255)
                pygame.draw.rect(self.screen, diamond_color, (preview_x, preview_y, preview_size, preview_size), border_radius=10)
                pygame.draw.rect(self.screen, (220, 255, 255), (preview_x + 10, preview_y + 10, preview_size - 20, preview_size - 20), border_radius=6)
                # Эффект отражения
                pygame.draw.polygon(self.screen, (255, 255, 255, 150), [
                    (preview_x + 20, preview_y + 20),
                    (preview_x + 40, preview_y + 10),
                    (preview_x + 60, preview_y + 20),
                    (preview_x + 40, preview_y + 30)
                ])
            
            elif "fire" in skin_name:
                # Огненный куб
                fire_colors = [(255, 100, 0), (255, 69, 0), (255, 140, 0)]
                for j, color in enumerate(fire_colors):
                    offset = j * 3
                    pygame.draw.rect(self.screen, color, 
                                (preview_x + offset, preview_y + offset, 
                                    preview_size - offset*2, preview_size - offset*2), 
                                border_radius=8 - j)
                # Эффект пламени
                for fx in range(preview_x + 10, preview_x + preview_size - 10, 15):
                    flame_height = random.randint(5, 15)
                    pygame.draw.polygon(self.screen, (255, 200, 0), [
                        (fx, preview_y + preview_size),
                        (fx + 5, preview_y + preview_size - flame_height),
                        (fx + 10, preview_y + preview_size)
                    ])
            
            elif "ice" in skin_name:
                # Ледяной куб
                ice_colors = [(173, 216, 230), (135, 206, 235), (176, 224, 230)]
                pygame.draw.rect(self.screen, ice_colors[0], (preview_x, preview_y, preview_size, preview_size), border_radius=10)
                pygame.draw.rect(self.screen, ice_colors[1], (preview_x + 5, preview_y + 5, preview_size - 10, preview_size - 10), border_radius=8)
                # Эффект кристаллов
                for ix in range(0, preview_size, 20):
                    for iy in range(0, preview_size, 20):
                        if (ix + iy) % 40 == 0:
                            pygame.draw.circle(self.screen, (255, 255, 255, 150), 
                                            (preview_x + ix + 10, preview_y + iy + 10), 3)
            
            elif "rainbow" in skin_name:
                # Радужный куб
                rainbow_surf = pygame.Surface((preview_size, preview_size), pygame.SRCALPHA)
                for px in range(preview_size):
                    hue = (px * 4) % 360
                    color_rgb = self.hsv_to_rgb(hue, 1.0, 1.0)
                    pygame.draw.line(rainbow_surf, color_rgb, (px, 0), (px, preview_size))
                self.screen.blit(rainbow_surf, (preview_x, preview_y))
                # Анимация
                time_ms = pygame.time.get_ticks()
                pulse = math.sin(time_ms * 0.005) * 3
                pygame.draw.rect(self.screen, (255, 255, 255, 100), 
                            (preview_x - pulse, preview_y - pulse, 
                                preview_size + pulse*2, preview_size + pulse*2), 
                            3, border_radius=10)
            
            else:
                # Базовый куб (белый)
                pygame.draw.rect(self.screen, self.WHITE, (preview_x, preview_y, preview_size, preview_size), border_radius=8)
                pygame.draw.rect(self.screen, (200, 200, 200), (preview_x + 5, preview_y + 5, preview_size - 10, preview_size - 10), border_radius=6)
                # Текстура
                for tx in range(0, preview_size, 15):
                    pygame.draw.line(self.screen, (150, 150, 150), 
                                (preview_x + tx, preview_y), 
                                (preview_x + tx, preview_y + preview_size), 1)
                for ty in range(0, preview_size, 15):
                    pygame.draw.line(self.screen, (150, 150, 150), 
                                (preview_x, preview_y + ty), 
                                (preview_x + preview_size, preview_y + ty), 1)
            
            # Название скина
            skin_name_display = skin["name"]
            if isinstance(skin_name_display, dict):
                skin_name_display = skin_name_display.get(self.language, skin_name_display.get('ru', 'Unknown'))
            
            name_text = self.small_font.render(skin_name_display, True, self.WHITE)
            name_rect = name_text.get_rect(center=(x + skin_size//2, y + skin_size - 35))
            self.screen.blit(name_text, name_rect)
            
            # Статус скина
            if skin["owned"]:
                status_text = self.small_font.render(self.localization.get('owned'), True, self.GREEN)
                status_color = self.GREEN
            elif skin["locked"]:
                status_text = self.small_font.render(self.localization.get('locked'), True, self.RED)
                status_color = self.RED
            else:
                status_text = self.small_font.render(f"{skin['cost']} AM", True, self.GOLD)
                status_color = self.GOLD
            
            status_rect = status_text.get_rect(center=(x + skin_size//2, y + skin_size - 15))
            
            # Подложка для статуса
            status_bg = pygame.Rect(status_rect.x - 5, status_rect.y - 2, 
                                status_rect.width + 10, status_rect.height + 4)
            pygame.draw.rect(self.screen, (30, 30, 50), status_bg, border_radius=4)
            self.screen.blit(status_text, status_rect)
            
            # Подсветка при наведении мыши
            mouse_pos = pygame.mouse.get_pos()
            skin_rect = pygame.Rect(x, y, skin_size, skin_size)
            if skin_rect.collidepoint(mouse_pos):
                # Полупрозрачный слой при наведении
                hover_surf = pygame.Surface((skin_size, skin_size), pygame.SRCALPHA)
                hover_surf.fill((255, 255, 255, 50))
                self.screen.blit(hover_surf, (x, y))
                
                # Усиленная рамка
                pygame.draw.rect(self.screen, status_color, (x, y, skin_size, skin_size), 4, border_radius=12)
                
                # Информация о скине при наведении
                info_y = y - 25
                if not skin["owned"] and not skin["locked"]:
                    info_text = self.small_font.render("Кликните для покупки" if self.language == 'ru' 
                                                    else "Click to purchase", True, self.CYAN)
                    info_rect = info_text.get_rect(center=(x + skin_size//2, info_y))
                    
                    # Подложка для информации
                    info_bg = pygame.Rect(info_rect.x - 8, info_rect.y - 4, 
                                        info_rect.width + 16, info_rect.height + 8)
                    pygame.draw.rect(self.screen, (20, 20, 40), info_bg, border_radius=6)
                    self.screen.blit(info_text, info_rect)
        
        # Баланс внизу
        balance_text = self.font.render(f"{self.localization.get('amethysts')}: {self.total_amethysts}", 
                                    True, self.PURPLE)
        balance_rect = balance_text.get_rect(center=(center_x, self.SCREEN_HEIGHT - 70))
        
        # Подложка для баланса
        balance_bg = pygame.Rect(balance_rect.x - 15, balance_rect.y - 8, 
                            balance_rect.width + 30, balance_rect.height + 16)
        pygame.draw.rect(self.screen, (40, 40, 60), balance_bg, border_radius=10)
        pygame.draw.rect(self.screen, self.PURPLE, balance_bg, 2, border_radius=10)
        self.screen.blit(balance_text, balance_rect)
        
        # Подсказки внизу
        hint_text = self.small_font.render("Нажмите на скин для выбора/покупки | ESC: Назад" if self.language == 'ru' 
                                        else "Click on skin to select/buy | ESC: Back", True, self.WHITE)
        hint_rect = hint_text.get_rect(center=(center_x, self.SCREEN_HEIGHT - 30))
        self.screen.blit(hint_text, hint_rect)
    
    def draw_chest(self):
        self.screen.fill(self.BLACK)
        scale = 1.0 + 0.1 * math.sin(self.chest_animation_frame * 0.1)
        self.chest_animation_frame += 1
        
        if self.chest_image:
            scaled_chest = pygame.transform.scale(self.chest_image, (int(200 * scale), int(200 * scale)))
            self.screen.blit(scaled_chest, (self.SCREEN_WIDTH//2 - 100, 150))
        else:
            pygame.draw.rect(self.screen, (139, 69, 19), (self.SCREEN_WIDTH//2 - 100, 150, 200, 200))
        
        title = self.title_font.render(self.localization.get('daily_chest'), True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        y_offset = 370
        for reward in self.chest_rewards:
            if reward["type"] == "amethyst":
                reward_text = self.font.render(f"+{reward['amount']} {self.localization.get('amethysts')}!", True, self.PURPLE)
                self.screen.blit(reward_text, (self.SCREEN_WIDTH//2 - reward_text.get_width()//2, y_offset))
                y_offset += 40
            elif reward["type"] == "skin":
                reward_text = self.font.render(f"Новый скин: {reward['name']}!" if self.language == 'ru' else f"New Skin: {reward['name']}!", True, self.GOLD)
                self.screen.blit(reward_text, (self.SCREEN_WIDTH//2 - reward_text.get_width()//2, y_offset))
                y_offset += 40
            elif reward["type"] == "message":
                reward_text = self.font.render(reward["text"], True, self.RED)
                self.screen.blit(reward_text, (self.SCREEN_WIDTH//2 - reward_text.get_width()//2, y_offset))
                y_offset += 40
        
        hint_text = self.small_font.render("Нажмите в любом месте для продолжения" if self.language == 'ru' else "Click anywhere to continue", True, self.WHITE)
        self.screen.blit(hint_text, (self.SCREEN_WIDTH//2 - hint_text.get_width()//2, self.SCREEN_HEIGHT - 50))

    def draw_pause(self):
        overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        pause_text = self.title_font.render(self.localization.get('paused'), True, self.GOLD)
        continue_text = self.font.render("Нажмите P или ESC для продолжения" if self.language == 'ru' else "Press P or ESC to continue", True, self.WHITE)
        menu_text = self.font.render("Нажмите M для главного меню" if self.language == 'ru' else "Press M for main menu", True, self.WHITE)
        
        self.screen.blit(pause_text, (self.SCREEN_WIDTH//2 - pause_text.get_width()//2, 200))
        self.screen.blit(continue_text, (self.SCREEN_WIDTH//2 - continue_text.get_width()//2, 280))
        self.screen.blit(menu_text, (self.SCREEN_WIDTH//2 - menu_text.get_width()//2, 320))

    def draw_game_over(self):
        self.screen.fill(self.BLACK)
        
        # Обновляем статистику при смерти
        self.stats["total_deaths"] = self.stats.get("total_deaths", 0) + 1
        if self.score > self.stats.get("best_score", 0):
            self.stats["best_score"] = self.score
        if self.max_combo > self.stats.get("best_combo", 0):
            self.stats["best_combo"] = self.max_combo
        self.check_achievements()
        self.save_stats()
        
        game_over = self.title_font.render(self.localization.get('game_over'), True, self.RED)
        self.screen.blit(game_over, (self.SCREEN_WIDTH//2 - game_over.get_width()//2, 80))
        
        # Статистика сессии
        y_pos = 150
        session_title = self.font.render("СТАТИСТИКА СЕССИИ" if self.language == 'ru' else "SESSION STATS", True, self.GOLD)
        self.screen.blit(session_title, (self.SCREEN_WIDTH//2 - session_title.get_width()//2, y_pos))
        y_pos += 40
        
        score_text = self.small_font.render(f"{self.localization.get('score')}: {self.score}", True, self.WHITE)
        self.screen.blit(score_text, (self.SCREEN_WIDTH//2 - score_text.get_width()//2, y_pos))
        y_pos += 30
        
        percent_text = self.small_font.render(f"{self.localization.get('percentage')}: {self.percent}%", True, self.GOLD)
        self.screen.blit(percent_text, (self.SCREEN_WIDTH//2 - percent_text.get_width()//2, y_pos))
        y_pos += 30
        
        combo_text = self.small_font.render(f"Комбо: {self.max_combo}" if self.language == 'ru' else f"Combo: {self.max_combo}", True, self.CYAN)
        self.screen.blit(combo_text, (self.SCREEN_WIDTH//2 - combo_text.get_width()//2, y_pos))
        y_pos += 30
        
        # Общая статистика
        y_pos += 20
        total_title = self.font.render("ОБЩАЯ СТАТИСТИКА" if self.language == 'ru' else "TOTAL STATS", True, self.GOLD)
        self.screen.blit(total_title, (self.SCREEN_WIDTH//2 - total_title.get_width()//2, y_pos))
        y_pos += 40
        
        best_score_text = self.small_font.render(
            f"Лучший счёт: {self.stats.get('best_score', 0)}" if self.language == 'ru' 
            else f"Best Score: {self.stats.get('best_score', 0)}", True, self.WHITE)
        self.screen.blit(best_score_text, (self.SCREEN_WIDTH//2 - best_score_text.get_width()//2, y_pos))
        y_pos += 25
        
        levels_text = self.small_font.render(
            f"Пройдено уровней: {self.stats.get('total_levels_completed', 0)}" if self.language == 'ru'
            else f"Levels Completed: {self.stats.get('total_levels_completed', 0)}", True, self.WHITE)
        self.screen.blit(levels_text, (self.SCREEN_WIDTH//2 - levels_text.get_width()//2, y_pos))
        y_pos += 25
        
        amethysts_text = self.small_font.render(
            f"Собрано аметистов: {self.stats.get('total_amethysts_collected', 0)}" if self.language == 'ru'
            else f"Amethysts Collected: {self.stats.get('total_amethysts_collected', 0)}", True, self.PURPLE)
        self.screen.blit(amethysts_text, (self.SCREEN_WIDTH//2 - amethysts_text.get_width()//2, y_pos))
        
        restart_text = self.font.render("Нажмите ENTER для рестарта или ESC для меню" if self.language == 'ru' else "Press ENTER to restart or ESC for menu", True, self.WHITE)
        self.screen.blit(restart_text, (self.SCREEN_WIDTH//2 - restart_text.get_width()//2, self.SCREEN_HEIGHT - 50))

    def draw_login(self):
        self.screen.fill(self.BLACK)
        
        # Градиентный фон
        gradient_surf = self.create_gradient_menu_bg()
        self.screen.blit(gradient_surf, (0, 0))
        
        title = self.title_font.render(self.localization.get('login'), True, self.GOLD)
        self.screen.blit(title, (self.SCREEN_WIDTH//2 - title.get_width()//2, 80))
        
        # Центрируем все элементы
        center_x = self.SCREEN_WIDTH // 2
        
        login_text = self.font.render("Имя пользователя:" if self.language == 'ru' else "Username:", True, self.WHITE)
        login_text_rect = login_text.get_rect(center=(center_x, 200))
        self.screen.blit(login_text, login_text_rect)
        
        login_rect = pygame.Rect(center_x - 125, 220, 250, 35)
        pygame.draw.rect(self.screen, self.WHITE if self.active_input == "login" else (100, 100, 100), login_rect, 2)
        login_input_text = self.font.render(self.login_input, True, self.WHITE)
        login_input_rect = login_input_text.get_rect(center=login_rect.center)
        self.screen.blit(login_input_text, login_input_rect)
        
        password_text = self.font.render("Пароль:" if self.language == 'ru' else "Password:", True, self.WHITE)
        password_text_rect = password_text.get_rect(center=(center_x, 280))
        self.screen.blit(password_text, password_text_rect)
        
        password_rect = pygame.Rect(center_x - 125, 300, 250, 35)
        pygame.draw.rect(self.screen, self.WHITE if self.active_input == "password" else (100, 100, 100), password_rect, 2)
        hidden_password = "*" * len(self.password_input)
        password_input_text = self.font.render(hidden_password, True, self.WHITE)
        password_input_rect = password_input_text.get_rect(center=password_rect.center)
        self.screen.blit(password_input_text, password_input_rect)
        
        if self.login_message:
            message_color = self.GREEN if "success" in self.login_message.lower() else self.RED
            message_text = self.font.render(self.login_message, True, message_color)
            message_rect = message_text.get_rect(center=(center_x, 360))
            self.screen.blit(message_text, message_rect)
        
        hint1 = self.small_font.render("TAB: Смена поля, ENTER: Войти, ESC: Назад" if self.language == 'ru' 
                                    else "TAB: Switch field, ENTER: Login, ESC: Back", True, self.WHITE)
        hint2 = self.small_font.render("Новый аккаунт будет создан автоматически" if self.language == 'ru' 
                                    else "New account will be created automatically", True, self.WHITE)
        
        hint1_rect = hint1.get_rect(center=(center_x, 420))
        hint2_rect = hint2.get_rect(center=(center_x, 450))
        self.screen.blit(hint1, hint1_rect)
        self.screen.blit(hint2, hint2_rect)
    
        # Кнопка "Назад" внизу
        back_text = self.font.render("ESC: Назад" if self.language == 'ru' else "ESC: Back", True, self.WHITE)
        back_rect = back_text.get_rect(center=(center_x, self.SCREEN_HEIGHT - 50))
        pygame.draw.rect(self.screen, (50, 50, 80), (back_rect.x - 10, back_rect.y - 5, back_rect.width + 20, back_rect.height + 10))
        self.screen.blit(back_text, back_rect)

    def draw_promo(self):
        self.screen.fill(self.BLACK)
        
        # Градиентный фон
        gradient_surf = self.create_gradient_menu_bg()
        self.screen.blit(gradient_surf, (0, 0))
        
        title = self.title_font.render(self.localization.get('promo_codes'), True, self.GOLD)
        title_rect = title.get_rect(center=(self.SCREEN_WIDTH//2, 100))
        self.screen.blit(title, title_rect)
        
        center_x = self.SCREEN_WIDTH // 2
        
        # Поле ввода промокода
        promo_label = self.font.render("Введите промокод:" if self.language == 'ru' else "Enter promo code:", 
                                    True, self.WHITE)
        promo_label_rect = promo_label.get_rect(center=(center_x, 180))
        self.screen.blit(promo_label, promo_label_rect)
        
        promo_rect = pygame.Rect(center_x - 150, 210, 300, 40)
        pygame.draw.rect(self.screen, self.WHITE, promo_rect, 2)
        promo_text = self.font.render(self.promo_input, True, self.WHITE)
        promo_text_rect = promo_text.get_rect(center=promo_rect.center)
        self.screen.blit(promo_text, promo_text_rect)
        
        # Сообщение о результате
        if self.promo_message:
            message_color = self.GREEN if "received" in self.promo_message.lower() else self.RED
            message_text = self.font.render(self.promo_message, True, message_color)
            message_rect = message_text.get_rect(center=(center_x, 280))
            self.screen.blit(message_text, message_rect)
        
        # Доступные коды
        available_codes = self.small_font.render(self.localization.get('available_codes'), 
                                            True, (100, 100, 255))
        available_codes_rect = available_codes.get_rect(center=(center_x, 330))
        self.screen.blit(available_codes, available_codes_rect)
        
        # Подсказки
        hint1 = self.small_font.render("ENTER: Активировать, ESC: Назад" if self.language == 'ru' 
                                    else "ENTER: Activate, ESC: Back", True, self.WHITE)
        hint1_rect = hint1.get_rect(center=(center_x, 380))
        self.screen.blit(hint1, hint1_rect)
        
        # Кнопка "Назад"
        back_text = self.font.render("ESC: Назад" if self.language == 'ru' else "ESC: Back", True, self.WHITE)
        back_rect = back_text.get_rect(center=(center_x, self.SCREEN_HEIGHT - 50))
        pygame.draw.rect(self.screen, (50, 50, 80), (back_rect.x - 10, back_rect.y - 5, back_rect.width + 20, back_rect.height + 10))
        self.screen.blit(back_text, back_rect)
    
    def draw_level_select(self):
        self.screen.fill(self.BLACK)
        title = self.title_font.render(self.localization.get('level_select'), True, self.GOLD)
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
        
        hint_text = self.small_font.render("ВВЕРХ/ВНИЗ: Выбор | ENTER: Играть | ESC: Назад" if self.language == 'ru' else "UP/DOWN: Select | ENTER: Play | ESC: Back", True, self.WHITE)
        self.screen.blit(hint_text, (self.SCREEN_WIDTH//2 - hint_text.get_width()//2, self.SCREEN_HEIGHT - 50))

    def draw(self):
        self.screen.fill(self.BLACK)
        
        if self.state == GameState.INTRO:
            self.draw_intro()
        elif self.state == GameState.MENU and self.use_pygame_menu and self.menu:
            # Выбираем фон в зависимости от меню
            if self.menu == self.other_menu and hasattr(self, 'light_menu_bg'):
                self.screen.blit(self.light_menu_bg, (0, 0))
            else:
                self.screen.blit(self.menu_bg_surface, (0, 0))
            if self.menu.is_enabled():
                self.menu.draw(self.screen)
        elif self.state == GameState.MENU and not self.use_pygame_menu:
            self.draw_menu()
        elif self.state == GameState.PLAYING:
            self.draw_game()
        elif self.state == GameState.SHOP:
            self.draw_shop()
        elif self.state == GameState.GAME_OVER:
            self.draw_game_over()
        elif self.state == GameState.LOGIN:
            self.draw_login()
        elif self.state == GameState.PROMO:
            self.draw_promo()
        elif self.state == GameState.EDITOR:
            self.draw_editor()
        elif self.state == GameState.PAUSED:
            self.draw_pause()
        elif self.state == GameState.INVENTORY:
            self.draw_inventory()
        elif self.state == GameState.CHEST:
            self.draw_chest()
        elif self.state == GameState.LEVEL_SELECT:
            self.draw_level_select()
        elif self.state == GameState.LEVEL_COMPLETE:
            self.draw_level_complete()
        elif self.state == GameState.OTHER:
            if self.use_pygame_menu and self.menu:
                self.screen.blit(self.menu_bg_surface, (0, 0))
                self.menu.draw(self.screen)
            else:
                # Для старой системы меню
                self.draw_other()
        elif self.state == GameState.ACHIEVEMENTS:
            if self.use_pygame_menu and self.menu:
                self.screen.blit(self.menu_bg_surface, (0, 0))
                self.menu.draw(self.screen)
            else:
                self.draw_achievements()
        
        # Отрисовка частиц
        if self.state in [GameState.PLAYING, GameState.LEVEL_COMPLETE, GameState.GAME_OVER]:
            self.particle_system.draw(self.screen)
        
        # UI/UX: Эффект вспышки экрана
        if self.flash_alpha > 0:
            flash_surf = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((*self.flash_color, min(255, self.flash_alpha)))
            self.screen.blit(flash_surf, (0, 0))
        
        # UI/UX: Применение тряски экрана
        if self.screen_shake_x != 0 or self.screen_shake_y != 0:
            # Создаем временную поверхность для тряски
            temp_screen = self.screen.copy()
            self.screen.fill(self.BLACK)
            self.screen.blit(temp_screen, (self.screen_shake_x, self.screen_shake_y))
        
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
            self.login_message = "Пожалуйста, заполните все поля" if self.language == 'ru' else "Please fill all fields"
            return
            
        if not self.account_system.conn:
            self.login_message = "Ошибка подключения к базе данных - перезапустите игру" if self.language == 'ru' else "Database connection failed - please restart game"
            return
        
        login_success = self.account_system.login(self.login_input, self.password_input)
        
        if login_success:
            self.login_message = self.localization.get('login_success')
            self.load_player_data()
            self.return_to_main_menu()
            return
            
        create_success = self.account_system.create_account(self.login_input, self.password_input)
        
        if create_success:
            login_after_create = self.account_system.login(self.login_input, self.password_input)
            
            if login_after_create:
                self.login_message = "Новый аккаунт создан и выполнен вход!" if self.language == 'ru' else "New account created and logged in!"
                self.load_player_data()
                self.initialize_new_player_skins()
                self.return_to_main_menu()
            else:
                self.login_message = "Аккаунт создан, но вход не выполнен. Попробуйте войти снова." if self.language == 'ru' else "Account created but login failed. Please try logging in again."
        else:
            self.login_message = "Ошибка входа! Имя пользователя может быть занято." if self.language == 'ru' else "Login failed! Username may be taken."

    def process_promo(self):
        if not self.account_system.current_account:
            self.promo_message = "Пожалуйста, войдите в систему!" if self.language == 'ru' else "Please login first!"
            return
            
        result = self.promo_system.redeem_promo(self.promo_input)
        
        # Локализуем сообщение
        if "received" in result.lower():
            self.promo_message = self.localization.get('promo_success')
        elif "invalid" in result.lower():
            self.promo_message = self.localization.get('promo_invalid')
        elif "already used" in result.lower():
            self.promo_message = self.localization.get('promo_used')
        else:
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
        
        autosave_timer = 0
        
        while self.running:
            self.handle_events()
            
            if self.state == GameState.INTRO:
                self.intro_timer += 1
                # Анимация появления текста
                if self.intro_timer > 60:  # Через 1 секунду
                    self.intro_text_alpha = min(255, self.intro_text_alpha + 5)
                if self.intro_timer > 120:  # Через 2 секунды
                    self.intro_subtitle_alpha = min(255, self.intro_subtitle_alpha + 5)
                if self.intro_timer > 300:  # Через 5 секунд
                    self.state = GameState.MENU
                    if self.use_pygame_menu:
                        self.menu = self.main_menu
                        self.menu.enable()
            
            if self.state == GameState.PLAYING and self.player:
                self.update_game()
                
                autosave_timer += 1
                if autosave_timer >= 1800:
                    self.auto_save_progress()
                    autosave_timer = 0
            
            if self.state == GameState.EDITOR and self.editor_message_timer > 0:
                self.editor_message_timer -= 1
                if self.editor_message_timer == 0:
                    self.editor_message = ""
            
            if self.exp_message_timer > 0:
                self.exp_message_timer -= 1
            
            if self.combo_message_timer > 0:
                self.combo_message_timer -= 1
                
            if self.hero_phrase_timer > 0:
                self.hero_phrase_timer -= 1
            
            # UI/UX: Обновление эффектов экрана
            if self.screen_shake > 0:
                self.screen_shake -= 1
                self.screen_shake_x = random.randint(-5, 5) if self.screen_shake > 0 else 0
                self.screen_shake_y = random.randint(-5, 5) if self.screen_shake > 0 else 0
            else:
                self.screen_shake_x = 0
                self.screen_shake_y = 0
            
            if self.flash_alpha > 0:
                self.flash_alpha = max(0, self.flash_alpha - 10)
            
            # Управление фоновой музыкой
            if self.state in [GameState.MENU, GameState.OTHER, GameState.SHOP, GameState.INVENTORY, 
                             GameState.LOGIN, GameState.PROMO, GameState.SKIN_PROGRESSION, 
                             GameState.ACHIEVEMENTS, GameState.LEVEL_SELECT, GameState.CHEST]:
                if self.menu_music and not self.music_playing:
                    try:
                        pygame.mixer.music.load(self.menu_music)
                        pygame.mixer.music.play(-1)  # -1 означает бесконечное воспроизведение
                        self.music_playing = True
                        logging.info("Started menu music")
                    except Exception as e:
                        logging.error(f"Could not play menu music: {e}")
            elif self.state == GameState.PLAYING:
                # Воспроизводим музыку уровня, если доступна
                current_level_music = None
                if hasattr(self, 'current_level_name') and self.current_level_name:
                    # Проверяем, есть ли музыка для этого уровня
                    for level_key, music_path in self.level_musics.items():
                        if level_key.lower() in self.current_level_name.lower():
                            current_level_music = music_path
                            break
                
                if current_level_music and not self.music_playing:
                    try:
                        pygame.mixer.music.load(current_level_music)
                        pygame.mixer.music.play(-1)
                        self.music_playing = True
                        logging.info(f"Started level music: {current_level_music}")
                    except Exception as e:
                        logging.error(f"Could not play level music: {e}")
                elif not current_level_music and self.music_playing:
                    # Если нет музыки уровня, останавливаем музыку
                    try:
                        pygame.mixer.music.stop()
                        self.music_playing = False
                        logging.info("Stopped music - no level music available")
                    except Exception as e:
                        logging.error(f"Could not stop music: {e}")
            elif self.state == GameState.LEVEL_COMPLETE:
                # Воспроизводим музыку экрана окончания
                if self.title_screen_music and not self.music_playing:
                    try:
                        pygame.mixer.music.load(self.title_screen_music)
                        pygame.mixer.music.play(-1)
                        self.music_playing = True
                        logging.info("Started title screen music")
                    except Exception as e:
                        logging.error(f"Could not play title screen music: {e}")
            elif self.state in [GameState.EDITOR, GameState.GAME_OVER]:
                if self.music_playing:
                    try:
                        pygame.mixer.music.stop()
                        self.music_playing = False
                        logging.info("Stopped music for editor/game over")
                    except Exception as e:
                        logging.error(f"Could not stop music: {e}")
            
            self.draw()
            
            fps_counter += 1
            if time.time() - fps_time >= 1.0:
                fps_display = f"FPS: {fps_counter}"
                fps_counter = 0
                fps_time = time.time()
                
                if len(self.obstacles) > 50:
                    self.obstacles = self.obstacles[-30:]
                if len(self.amethysts) > 30:
                    self.amethysts = self.amethysts[-20:]
            
            if self.state == GameState.PLAYING and fps_display:
                fps_text = self.small_font.render(fps_display, True, (100, 255, 100, 180))
                self.screen.blit(fps_text, (10, self.SCREEN_HEIGHT - 30))
            
            self.clock.tick(60)
        
        self.save_on_exit()
        pygame.quit()
        sys.exit()
    
    def load_stats(self):
        """Загрузка статистики игрока"""
        try:
            if os.path.exists("stats.json"):
                with open("stats.json", "r", encoding="utf-8") as f:
                    loaded_stats = json.load(f)
                    self.stats.update(loaded_stats)
        except Exception as e:
            logging.error(f"Error loading stats: {e}")
    
    def save_stats(self):
        """Сохранение статистики игрока"""
        try:
            # Обновляем время игры
            if self.state == GameState.PLAYING:
                self.stats["total_play_time"] += time.time() - self.stats.get("session_start_time", time.time())
                self.stats["session_start_time"] = time.time()
            
            with open("stats.json", "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving stats: {e}")
    
    def load_achievements(self):
        """Загрузка достижений"""
        try:
            if os.path.exists("achievements.json"):
                with open("achievements.json", "r", encoding="utf-8") as f:
                    self.achievements.update(json.load(f))
        except Exception as e:
            logging.error(f"Error loading achievements: {e}")
    
    def save_achievements(self):
        """Сохранение достижений"""
        try:
            with open("achievements.json", "w", encoding="utf-8") as f:
                json.dump(self.achievements, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving achievements: {e}")
    
    def check_achievements(self):
        """Проверка и разблокировка достижений"""
        achievements_unlocked = []
        
        # Первый прыжок
        if not self.achievements.get("first_jump") and self.stats.get("total_jumps", 0) > 0:
            self.achievements["first_jump"] = True
            achievements_unlocked.append("Первый прыжок!" if self.language == 'ru' else "First Jump!")
        
        # Первый уровень
        if not self.achievements.get("first_level") and self.stats.get("total_levels_completed", 0) > 0:
            self.achievements["first_level"] = True
            achievements_unlocked.append("Первый уровень!" if self.language == 'ru' else "First Level!")
        
        # Мастер комбо
        if not self.achievements.get("combo_master") and self.max_combo >= 10:
            self.achievements["combo_master"] = True
            achievements_unlocked.append("Мастер комбо!" if self.language == 'ru' else "Combo Master!")
        
        # Скоростной демон
        if not self.achievements.get("speed_demon") and self.game_speed >= 15:
            self.achievements["speed_demon"] = True
            achievements_unlocked.append("Скоростной демон!" if self.language == 'ru' else "Speed Demon!")
        
        # Коллекционер
        if not self.achievements.get("collector") and self.stats.get("total_amethysts_collected", 0) >= 100:
            self.achievements["collector"] = True
            achievements_unlocked.append("Коллекционер!" if self.language == 'ru' else "Collector!")
        
        # Перфекционист
        if not self.achievements.get("perfectionist") and self.percent >= 100:
            self.achievements["perfectionist"] = True
            achievements_unlocked.append("Перфекционист!" if self.language == 'ru' else "Perfectionist!")
        
        # Ветеран
        if not self.achievements.get("veteran") and self.stats.get("total_play_time", 0) >= 3600:  # 1 час
            self.achievements["veteran"] = True
            achievements_unlocked.append("Ветеран!" if self.language == 'ru' else "Veteran!")
        
        if achievements_unlocked:
            self.save_achievements()
            # Можно добавить визуальное уведомление о достижении
            logging.info(f"Achievements unlocked: {achievements_unlocked}")
    
    def auto_save_progress(self):
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
        self.auto_save_progress()
        self.save_level_progress()
        self.save_quests()

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
        """Безопасное обновление схемы базы данных"""
        if not self.conn:
            logging.warning("Database connection not available for schema update")
            return
            
        try:
            cursor = self.conn.cursor()
            
            # 1. Проверяем и обновляем таблицу players
            cursor.execute("PRAGMA table_info(players)")
            player_columns = {col[1] for col in cursor.fetchall()}
            
            required_player_columns = {'id', 'username', 'password', 'amethysts', 'last_chest_date'}
            for column in required_player_columns:
                if column not in player_columns:
                    try:
                        if column == 'last_chest_date':
                            cursor.execute(f"ALTER TABLE players ADD COLUMN {column} TEXT")
                        elif column == 'amethysts':
                            cursor.execute(f"ALTER TABLE players ADD COLUMN {column} INTEGER DEFAULT 0")
                    except sqlite3.OperationalError as e:
                        # Колонка уже существует
                        logging.debug(f"Column {column} might already exist: {e}")
            
            # 2. Создаём таблицу skin_progression, если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS skin_progression (
                    player_id INTEGER,
                    skin_id TEXT,
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    total_exp INTEGER DEFAULT 0,
                    completed_levels INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(player_id) REFERENCES players(id),
                    PRIMARY KEY (player_id, skin_id)
                )
            ''')
            
            # 3. Проверяем существование всех таблиц
            required_tables = ['players', 'promo_used', 'player_skins', 
                             'player_upgrades', 'game_sessions', 'skin_progression']
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            for table in required_tables:
                if table not in existing_tables:
                    logging.warning(f"Table {table} is missing, game may need reinstall")
            
            # 4. Добавляем индекс для производительности
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_skin_progression 
                ON skin_progression(player_id, skin_id)
            ''')
            
            self.conn.commit()
            logging.info("Database schema updated successfully")
            
        except sqlite3.Error as e:
            logging.error(f"Failed to update database schema: {e}")
            # Пытаемся восстановить соединение
            try:
                self.conn.rollback()
            except:
                pass
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

    def save_skin_progression(self, player_id, skin_id, level, exp, total_exp, completed_levels):
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

