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

#Игрок
class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 40
        self.speed = 5
        self.velocity_y = 0
        self.jump_force = -15
        self.gravity = 0.8
        self.is_jumping = False
        self.shape = 'cube'
    
    def jump(self):
        if not self.is_jumping:
            self.velocity_y = self.jump_force
            self.is_jumping = True

    def update(self):
        #Автоматическое движение
        self.x += self.speed

        #Гравитация и прыжок
        self.velocity_y += self.gravity
        self.y += self.velocity_y

        #Проверка земли
        if self.y >= SCREEN_HEIGHT - self.size:
            self.y = SCREEN_HEIGHT - self.size
            self.velocity_y = 0
            self.is_jumping = False

    def draw(self, screen):
        if self.shape == 'cube':
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
                crash_sound()
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
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Square Jump v1.0")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = MENU
        self.player = Player(100, SCREEN_HEIGHT - 100)
        self.obstacles = []
        self.score = 0
        self.font = pygame.font.SysFont(None, 36)
        self.obstacle_timer = 0
        self.obstacle_frequency = 1000  # Частота появления препятствий
        self.game_speed = 5
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.state == MENU:
                        self.state = PLAYING
                    self.player.jump()
                if event.key == pygame.K_RETURN and self.state == GAME_OVER:
                    self.reset_game()
                    
    def reset_game(self):
        self.player = Player(100, SCREEN_HEIGHT - 100)
        self.obstacles = []
        self.score = 0
        self.game_speed = 5
        self.state = PLAYING
                
                    
                    
    def spawn_obstacles(self):
        # генерации уровня
        if random.random() < 0.02 and self.state == PLAYING and len(self.obstacles) < 5: 
            obstacle_type = random.choice(["spike", "platform"])
            y = SCREEN_HEIGHT - 100 if obstacle_type == 'platform' else SCREEN_HEIGHT - 40
            self.obstacles.append(Obstacle(SCREEN_WIDTH, y, obstacle_type))
             
    def check_collisions(self):
        for obstacle in self.obstacles:
            if obstacle.check_collision(self.player):
                if obstacle.type == "spike":
                    self.state = GAME_OVER


    def update(self):
        if self.state == PLAYING:
            self.player.update()
            
            #проверка выхода за экран
            if self.player.x > SCREEN_WIDTH:
                self.player.x = -self.player.size

            #Препятствия
            self.spawn_obstacles()
            self.game_speed += 0.001
            for obstacle in self.obstacles[:]:
                obstacle.update(self.game_speed)
                if obstacle.is_offscreen():
                    self.obstacles.remove(obstacle)
            self.check_collisions()
            self.score += 1
            

    def draw(self):
        offset_x = self.player.x - 100
        self.screen.fill(BLACK)
        if self.state == MENU:
            #Рисовка меню
            font = pygame.font.SysFont(None, 48)
            title = self.font.render("Press SPACE to Start", True, WHITE)
            self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, SCREEN_HEIGHT // 2))
        else:
            #Отрисовка игрока со смещением
            self.player.draw(self.screen)
            for obstacle in self.obstacles:
                #смещение к препятствиям
                if obstacle.type == "spike":
                    pygame.draw.polygon(self.screen, obstacle.color, [
                    (obstacle.x - offset_x, obstacle.y + obstacle.height),
                    (obstacle.x - offset_x + obstacle.width // 2, obstacle.y),
                    (obstacle.x - offset_x + obstacle.width, obstacle.y + obstacle.height)
                ])
                elif obstacle.type == "platform":
                    pygame.draw.rect(self.screen, obstacle.color, 
                        (obstacle.x - offset_x, obstacle.y, obstacle.width, obstacle.height))
                #Отрисовка счета
            score_text = self.font.render(f"Score: {self.score}", True, WHITE)
            self.screen.blit(score_text, (20, 20))
            if self.state == GAME_OVER:
                game_over_text = self.font.render("Dont give up! Press ENTER to Restart", True, WHITE)
                self.screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 2))
        pygame.display.flip()
        
        
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)

if __name__ == "__main__":
    game = Game()
    game.run()




    

        




