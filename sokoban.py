"""A simple implementation of Sokoban.

The purpose of this module is to provide a sufficiently large
code-base to learn the art of unit testing.
"""

from __future__ import print_function
from collections import namedtuple
from builtins import open as xopen
from enum import Enum

import argparse
import json
import sys
import time
import pygame

import solver_astar

Tile = namedtuple("Tile", "wall worker dock box")
Dir = Enum('Dir', 'UP DN LT RT')
Key = Enum('Key', 'UP DOWN LEFT RIGHT QUIT SKIP SOLVE PREV RESET INFO SPEED1 SPEED2 SPEED3')


class World:
    """Represents the positions of worker, walls, boxes and docks.

    Walls and docks are fixed for a level. Methods are provided to
    move worker and boxes, around.
    """

    def __init__(self, level_info):
        self.worker_pos = []
        self.box_pos = []
        self.dock_pos = []
        self.wall_pos = []
        self.nrows = 0
        self.ncols = 0
        self._parse(level_info)

    def _parse(self, level_info):
        """Parses the level and initialize initial level state.

        Raises ValueError if parsing level fails.
        """
        for i, line in enumerate(level_info):
            for j, tile in enumerate(line):
                pos = (j, i)
                #
                # Tile   |   | Dock
                # -------+---+-----
                # Worker | @ | +
                # Floor  |   | .
                # Box    | $ | *
                # Wall   | # | x
                #
                if tile in ('@', '+'):
                    self.worker_pos.append(pos)
                if tile in ('$', '*'):
                    self.box_pos.append(pos)
                if tile in ('.', '*', '+'):
                    self.dock_pos.append(pos)
                if tile == '#':
                    self.wall_pos.append(pos)
                if tile not in ('@', '+', '$', '*', '.', '#', ' ', '\n'):
                    msg = "character not recognized {0}".format(tile)
                    raise ValueError(msg)

        if len(self.worker_pos) != 1:
            raise ValueError("worker not found")

        if len(self.dock_pos) != len(self.box_pos):
            raise ValueError("boxes and docks count mismatch")

        if len(self.box_pos) == 0:
            raise ValueError("boxes not found")

        self.nrows = len(level_info)
        self.ncols = max(len(l) for l in level_info)

    def get(self, pos):
        """Returns the tile information at specified position."""
        return Tile(wall = (pos in self.wall_pos),
                    worker = (pos in self.worker_pos),
                    dock = (pos in self.dock_pos),
                    box = (pos in self.box_pos))

    def push_box(self, from_pos, to_pos):
        """Moves box from 'from_pos' to 'to_pos'."""
        self.box_pos.remove(from_pos)
        self.box_pos.append(to_pos)

    def move_worker(self, to_pos):
        """Moves worker to specified position."""
        self.worker_pos = [to_pos]


class GameEngine:
    """Rules engine, decides what is possible within the world.

    Rules:
      * Worker cannot move into a wall
      * Worker can only push 1 box at a time

    Also provides method to check if player has won.
    """

    @staticmethod
    def move(direction, world):
        """Move player in a specified direction."""
        x, y = world.worker_pos[0]

        if direction == Dir.UP:
            next_pos = (x, y - 1)
            push_pos = (x, y - 2)
        elif direction == Dir.DN:
            next_pos = (x, y + 1)
            push_pos = (x, y + 2)
        elif direction == Dir.RT:
            next_pos = (x + 1, y)
            push_pos = (x + 2, y)
        else:  # if direction == Dir.LT:
            next_pos = (x - 1, y)
            push_pos = (x - 2, y)

        next_tile = world.get(next_pos)
        push_tile = world.get(push_pos)

        if next_tile.wall:
            return

        if next_tile.box:
            if not push_tile.wall and not push_tile.box:
                world.push_box(next_pos, push_pos)
                world.move_worker(next_pos)
            return

        world.move_worker(next_pos)

    @staticmethod
    def is_game_over(world):
        """Returns True if all boxes are in docks, False otherwise."""
        for box in world.box_pos:
            if box not in world.dock_pos:
                return False
        return True


class GameView:
    """Interacts with user getting inputs and displaying the world."""
    TILE_SIZE = 32

    def __init__(self):
        self._screen = None
        self._images = {}
        self._done = False
        pygame.init()
        pygame.display.set_caption("Sokoban!")

    def load_images(self):
        """Loads tile images from file."""
        tile_names = (
            ("wall", Tile(wall=True, worker=False, dock=False, box=False)),
            ("floor", Tile(wall=False, worker=False, dock=False, box=False)),
            ("dock", Tile(dock=True, wall=False, worker=False, box=False)),
            ("box", Tile(box=True, wall=False, worker=False, dock=False)),
            ("worker", Tile(worker=True, wall=False, dock=False, box=False)),
            ("box-docked", Tile(box=True, dock=True, wall=False, worker=False)),
            ("worker-docked", Tile(worker=True, dock=True, wall=False, box=False))
        )

        self._images = {}
        for name, tile in tile_names:
            self._images[tile] = pygame.image.load("tiles/{0}.ppm".format(name))

    def setup_world(self, world):
        """Sets the size of the game window."""
        width = world.ncols * GameView.TILE_SIZE
        height = world.nrows * GameView.TILE_SIZE
        self._screen = pygame.display.set_mode((width, height))

    def show_world(self, world):
        """Updates the tiles on the game window."""
        self._screen.fill((0, 0, 0))
        for y in range(world.nrows):
            for x in range(world.ncols):
                tile = world.get((x, y))
                sx = x * GameView.TILE_SIZE
                sy = y * GameView.TILE_SIZE
                img = self._images[tile]
                self._screen.blit(img, (sx, sy))
        pygame.display.flip()

    def quit(self):
        """Exits from main loop."""
        pygame.quit()
        self._done = True

    def run_once(self, event_handler):
        key_map = {
            pygame.K_UP: Key.UP,
            pygame.K_LEFT: Key.LEFT,
            pygame.K_RIGHT: Key.RIGHT,
            pygame.K_DOWN: Key.DOWN,
            pygame.K_q: Key.QUIT,
            pygame.K_n: Key.SKIP,
            pygame.K_s: Key.SOLVE,
            pygame.K_p: Key.PREV,
            pygame.K_r: Key.RESET,
            pygame.K_i: Key.INFO,
            pygame.K_1: Key.SPEED1,
            pygame.K_2: Key.SPEED2,
            pygame.K_3: Key.SPEED3,
        }
        event = pygame.event.wait()
        if event.type == pygame.QUIT:
            event_handler.handle_key(Key.QUIT)
        elif event.type == pygame.KEYDOWN:
            try:
                event_handler.handle_key(key_map[event.key])
            except KeyError:
                pass

    def run(self, event_handler):
        """Runs the main event loop."""
        while not self._done:
            self.run_once(event_handler)


class Sokoban:
    """Game director, ties up engine, world and view."""

    def __init__(self, levels):
        self._levels = levels
        self._current = 0
        self._engine = GameEngine()
        self._view = GameView()
        self._solving = False
        self._last_solve = None
        self._speed_level = 2
        self._move_delay = 0.08
        self._view.load_images()

        self._world = World(self._levels[self._current])
        self._view.setup_world(self._world)
        self._view.show_world(self._world)
        self._view.run(self)

    def _goto_next(self):
        """Increments level and update world."""
        self._current = (self._current + 1) % len(self._levels)
        self._world = World(self._levels[self._current])
        self._view.setup_world(self._world)
        self._view.show_world(self._world)

    def _goto_prev(self):
        """Decrements level and update world."""
        self._current = (self._current - 1) % len(self._levels)
        self._world = World(self._levels[self._current])
        self._view.setup_world(self._world)
        self._view.show_world(self._world)

    def _reset_level(self):
        """Reloads current level."""
        self._world = World(self._levels[self._current])
        self._view.setup_world(self._world)
        self._view.show_world(self._world)

    def _move(self, direction):
        """Make move and update in view."""
        self._engine.move(direction, self._world)
        self._view.show_world(self._world)

    def _solve_and_play(self):
        if self._solving:
            return
        self._solving = True

        result = solver_astar.solve_astar(self._world)
        self._last_solve = result
        if result["cost"] < 0:
            print("Aucune solution")
            self._solving = False
            return

        print(solver_astar.format_summary(result))

        for move in result["moves"]:
            if move == "U":
                self._move(Dir.UP)
            elif move == "D":
                self._move(Dir.DN)
            elif move == "L":
                self._move(Dir.LT)
            elif move == "R":
                self._move(Dir.RT)
            pygame.event.pump()
            time.sleep(self._move_delay)

        self._solving = False
        if self._engine.is_game_over(self._world):
            self._goto_next()

    def _show_info(self):
        if not self._last_solve:
            print("Aucune donnee de solveur")
            return
        print(solver_astar.format_search_report(self._last_solve))
        print("Arbre graphique disponible dans sokoban_tk.py")

    def _set_speed(self, level):
        speeds = {1: 0.15, 2: 0.08, 3: 0.03}
        self._speed_level = level
        self._move_delay = speeds[level]
        print("Vitesse reglee a {0}".format(level))

    def handle_key(self, key):
        """Processes a key event.

          * Invoke engine to update the world
          * Invoke view to display the world
          * Check game over and move to next level
        """
        if key == Key.QUIT:
            self._view.quit()
        elif key == Key.INFO:
            self._show_info()
        elif key == Key.SPEED1:
            self._set_speed(1)
        elif key == Key.SPEED2:
            self._set_speed(2)
        elif key == Key.SPEED3:
            self._set_speed(3)
        elif self._solving:
            return
        elif key == Key.UP:
            self._move(Dir.UP)
        elif key == Key.RIGHT:
            self._move(Dir.RT)
        elif key == Key.LEFT:
            self._move(Dir.LT)
        elif key == Key.DOWN:
            self._move(Dir.DN)
        elif key == Key.SKIP:
            self._goto_next()
        elif key == Key.SOLVE:
            self._solve_and_play()
        elif key == Key.PREV:
            self._goto_prev()
        elif key == Key.RESET:
            self._reset_level()

        if self._engine.is_game_over(self._world):
            self._goto_next()

def load_levels():
    """Returns levels loaded from a JSON file."""
    try:
        return json.load(xopen("levels.json"))
    except (OSError, IOError, ValueError):
        print("sokoban: loading levels failed!", file=sys.stderr)
        exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sokoban")
    parser.add_argument(
        "--solve-level",
        type=int,
        default=None,
        help="Solve level index (0-based) and exit",
    )
    args = parser.parse_args()

    levels = load_levels()
    if args.solve_level is not None:
        if args.solve_level < 0 or args.solve_level >= len(levels):
            print("Index de niveau invalide", file=sys.stderr)
            sys.exit(1)
        result = solver_astar.solve_astar(levels[args.solve_level])
        if result["cost"] < 0:
            print("Aucune solution")
        else:
            print("Mouvements: {0}".format(result["moves_str"]))
            print(solver_astar.format_summary(result))
        sys.exit(0)

    Sokoban(levels)
