# config.py
import pygame
import os
import logging

# Инициализация pygame
pygame.init()
pygame.mixer.init()

# Настройки экрана
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FULLSCREEN = True

# Цвета
COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255),
    (255, 255, 0), (255, 0, 255)
]
PURPLE = (128, 0, 128)
GOLD = (255, 215, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Состояния игры
MENU = 0
PLAYING = 1
GAME_OVER = 2
SHOP = 3

# Пути
ASSETS_DIR = os.path.join("assets")
SKINS_DIR = os.path.join("skins")
SOUNDS_DIR = os.path.join("sounds")
MENU_DIR = os.path.join("menu")
LEVELS_DIR = os.path.join("levels")

# Настройки игрока
PLAYER_SIZE = 60
PLAYER_SPEED = 8
JUMP_FORCE = -18
GRAVITY = 0.8
MAX_JUMPS = 1

# Другие настройки
OBSTACLE_FREQUENCY = 1000
TIME_SLOW_DURATION = 3000