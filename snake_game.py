import json
import math
import os
import random
import sys

import pygame

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
GRID_SIZE = 20
GRID_WIDTH = WINDOW_WIDTH // GRID_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // GRID_SIZE

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 200, 0)
DARK_GREEN = (0, 140, 0)
RED = (220, 40, 40)

SCORE_PER_FOOD = 10
START_FPS = 10
MAX_FPS = 20
FOODS_PER_SPEEDUP = 5

HIGHSCORE_FILE = "highscore.json"


def load_high_score():
    if not os.path.exists(HIGHSCORE_FILE):
        return 0
    try:
        with open(HIGHSCORE_FILE, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
            return int(data.get("high_score", 0))
    except (json.JSONDecodeError, OSError, ValueError):
        return 0


def save_high_score(score):
    try:
        with open(HIGHSCORE_FILE, "w", encoding="utf-8") as file_handle:
            json.dump({"high_score": score}, file_handle)
    except OSError:
        pass


def grid_to_pixel(position):
    return position[0] * GRID_SIZE, position[1] * GRID_SIZE


def random_food_position(occupied):
    available = [(x, y) for x in range(GRID_WIDTH) for y in range(GRID_HEIGHT) if (x, y) not in occupied]
    return random.choice(available) if available else None


def clamp_fps(foods_eaten):
    return min(MAX_FPS, START_FPS + (foods_eaten // FOODS_PER_SPEEDUP))


class Snake:
    def __init__(self):
        self.segments = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
        self.segments.append((self.segments[0][0] - 1, self.segments[0][1]))
        self.segments.append((self.segments[1][0] - 1, self.segments[1][1]))
        self.direction = (1, 0)
        self.pending_direction = self.direction
        self.grow_pending = 0

    def set_direction(self, new_direction):
        if (new_direction[0] == -self.direction[0] and new_direction[1] == -self.direction[1]):
            return
        self.pending_direction = new_direction

    def move(self):
        self.direction = self.pending_direction
        head_x, head_y = self.segments[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)
        self.segments.insert(0, new_head)
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.segments.pop()

    def grow(self):
        self.grow_pending += 1

    def hits_wall(self):
        head_x, head_y = self.segments[0]
        return head_x < 0 or head_x >= GRID_WIDTH or head_y < 0 or head_y >= GRID_HEIGHT

    def hits_self(self):
        return self.segments[0] in self.segments[1:]


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 32)
        self.large_font = pygame.font.Font(None, 48)
        self.high_score = load_high_score()
        self.reset()
        self.eat_sound = self.build_beep_sound(440, 0.08)
        self.game_over_sound = self.build_beep_sound(180, 0.3)

    def reset(self):
        self.snake = Snake()
        self.food_position = random_food_position(set(self.snake.segments))
        self.score = 0
        self.foods_eaten = 0
        self.game_over = False
        self.show_instructions = True

    def build_beep_sound(self, frequency, duration):
        if not pygame.mixer.get_init():
            return None
        sample_rate = 44100
        samples = int(sample_rate * duration)
        buffer = bytearray()
        volume = 0.4
        for i in range(samples):
            value = int(32767 * volume * math.sin(2 * math.pi * frequency * (i / sample_rate)))
            buffer += value.to_bytes(2, byteorder="little", signed=True)
        return pygame.mixer.Sound(buffer=bytes(buffer))

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_r) and self.game_over:
                    self.reset()
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.snake.set_direction((0, -1))
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    self.snake.set_direction((0, 1))
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.snake.set_direction((-1, 0))
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.snake.set_direction((1, 0))

    def update(self):
        if self.game_over:
            return
        self.snake.move()
        if self.snake.hits_wall() or self.snake.hits_self():
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
                save_high_score(self.high_score)
            if self.game_over_sound:
                self.game_over_sound.play()
            return
        if self.food_position and self.snake.segments[0] == self.food_position:
            self.snake.grow()
            self.score += SCORE_PER_FOOD
            self.foods_eaten += 1
            if self.eat_sound:
                self.eat_sound.play()
            self.food_position = random_food_position(set(self.snake.segments))

    def draw_grid(self):
        for x in range(0, WINDOW_WIDTH, GRID_SIZE):
            pygame.draw.line(self.screen, WHITE, (x, 0), (x, WINDOW_HEIGHT), 1)
        for y in range(0, WINDOW_HEIGHT, GRID_SIZE):
            pygame.draw.line(self.screen, WHITE, (0, y), (WINDOW_WIDTH, y), 1)

    def draw_snake(self):
        for index, segment in enumerate(self.snake.segments):
            color = DARK_GREEN if index == 0 else GREEN
            x, y = grid_to_pixel(segment)
            rect = pygame.Rect(x, y, GRID_SIZE, GRID_SIZE)
            pygame.draw.rect(self.screen, color, rect, border_radius=6)

    def draw_food(self):
        if not self.food_position:
            return
        x, y = grid_to_pixel(self.food_position)
        rect = pygame.Rect(x, y, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(self.screen, RED, rect, border_radius=6)

    def draw_score(self):
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))

    def draw_instructions(self):
        if not self.show_instructions:
            return
        instruction = "Arrow keys/WASD to move, eat red food, don't crash! SPACE to restart."
        text_surface = self.font.render(instruction, True, WHITE)
        rect = text_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 30))
        self.screen.blit(text_surface, rect)

    def draw_game_over(self):
        if not self.game_over:
            return
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        title = self.large_font.render("Game Over", True, WHITE)
        score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
        high_text = self.font.render(f"High Score: {self.high_score}", True, WHITE)
        restart_text = self.font.render("Press SPACE or R to restart", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 60)))
        self.screen.blit(score_text, score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 10)))
        self.screen.blit(high_text, high_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 25)))
        self.screen.blit(restart_text, restart_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 70)))

    def run_frame(self):
        self.handle_input()
        self.update()
        self.screen.fill(BLACK)
        self.draw_grid()
        self.draw_food()
        self.draw_snake()
        self.draw_score()
        self.draw_instructions()
        self.draw_game_over()
        pygame.display.flip()
        self.clock.tick(clamp_fps(self.foods_eaten))
        if self.show_instructions and self.foods_eaten > 0:
            self.show_instructions = False


def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Snake")
    game = Game(screen)
    while True:
        game.run_frame()


if __name__ == "__main__":
    main()
