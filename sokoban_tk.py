"""A simple implementation of Sokoban.

The purpose of this module is to provide a sufficiently large
code-base to learn the art of unit testing.
"""

from __future__ import print_function
from collections import namedtuple
from enum import Enum

import threading
import time
import json
import sys
import tkinter as tk
from types import SimpleNamespace

import solver_astar

Tile = namedtuple("Tile", "wall worker dock box")
Dir = Enum('Dir', 'UP DN LT RT')
Key = Enum('Key', 'UP DOWN LEFT RIGHT QUIT SKIP SOLVE PREV RESET INFO EXPORT SPEED1 SPEED2 SPEED3')


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
        self._window = tk.Tk()
        self._window.title("Sokoban!")
        self._canvas = tk.Canvas(self._window)
        self._canvas.pack()
        self._images = {}
        self._event_handler = None

    def load_images(self):
        tile_names = (
            ("wall", Tile(wall=True, worker=False, dock=False, box=False)),
            ("floor", Tile(wall=False, worker=False, dock=False, box=False)),
            ("dock", Tile(dock=True, wall=False, worker=False, box=False)),
            ("box", Tile(box=True, wall=False, worker=False, dock=False)),
            ("worker", Tile(worker=True, wall=False, dock=False, box=False)),
            ("box-docked", Tile(box=True, dock=True, wall=False, worker=False)),
            ("worker-docked", Tile(worker=True, dock=True, wall=False, box=False))
        )

        for name, tile in tile_names:
            self._images[tile] = tk.PhotoImage(file="tiles/{}.ppm".format(name))

    def setup_world(self, world):
        """Sets the size of the game window."""
        width = world.ncols * GameView.TILE_SIZE
        height = world.nrows * GameView.TILE_SIZE
        self._canvas.config(width=width, height=height)

    def show_world(self, world):
        """Updates the tiles on the game window."""
        self._canvas.delete("all")
        for y in range(world.nrows):
            for x in range(world.ncols):
                tile = world.get((x, y))
                sx = x * GameView.TILE_SIZE
                sy = y * GameView.TILE_SIZE
                img = self._images[tile]
                self._canvas.create_image(sx, sy, image=img, tag="all", anchor=tk.NW)

    def quit(self):
        self._window.quit()

    def run(self, event_handler):
        self._event_handler = event_handler
        self._window.bind("<KeyPress>", self._on_key_press)
        self._window.mainloop()

    def schedule(self, delay_ms, callback):
        self._window.after(delay_ms, callback)

    def show_text_dialog(self, title, text):
        dialog = tk.Toplevel(self._window)
        dialog.title(title)
        frame = tk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True)
        text_widget = tk.Text(frame, width=80, height=30)
        text_widget.insert("1.0", text)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(frame, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)

    def show_tree_dialog(self, title, detail_text, tree_data):
        pass

    def _on_key_press(self, event):
        """Maps the key pressed, and invokes key handler callback."""
        key_map = {
            "Up": Key.UP,
            "Left": Key.LEFT,
            "Right": Key.RIGHT,
            "Down": Key.DOWN,
            "q": Key.QUIT,
            "n": Key.SKIP,
            "N": Key.SKIP,
            "s": Key.SOLVE,
            "S": Key.SOLVE,
            "p": Key.PREV,
            "P": Key.PREV,
            "r": Key.RESET,
            "R": Key.RESET,
            "i": Key.INFO,
            "I": Key.INFO,
            "e": Key.EXPORT,
            "E": Key.EXPORT,
            "1": Key.SPEED1,
            "2": Key.SPEED2,
            "3": Key.SPEED3,
        }
        try:
            self._event_handler.handle_key(key_map[event.keysym])
        except KeyError:
            pass


class Sokoban:
    """Game director, ties up engine, world and view."""

    def __init__(self, levels):
        self._levels = levels
        self._current = 0
        self._engine = GameEngine()
        self._view = GameView()
        self._solving = False
        self._solution_moves = []
        self._last_solve = None
        self._last_solve_world = None
        self._speed_level = 2
        self._move_delay_ms = 80
        self._tree_topk = 5
        self._trace_limit_display = 40
        self._trace_limit_export = 200
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

        def run_solver():
            snapshot = self._snapshot_world(self._world)
            result = solver_astar.solve_astar(
                self._world, trace_limit=self._trace_limit_display
            )
            self._view.schedule(0, lambda: self._start_solution(result))
            self._last_solve_world = snapshot

        thread = threading.Thread(target=run_solver)
        thread.daemon = True
        thread.start()

    def _start_solution(self, result):
        self._last_solve = result
        if result["cost"] < 0:
            print("Aucune solution")
            self._solving = False
            return

        print(solver_astar.format_summary(result))
        self._solution_moves = list(result["moves"])
        self._animate_solution_step(0)

    def _animate_solution_step(self, index):
        if index >= len(self._solution_moves):
            self._solving = False
            if self._engine.is_game_over(self._world):
                self._goto_next()
            return

        move = self._solution_moves[index]
        if move == "U":
            self._move(Dir.UP)
        elif move == "D":
            self._move(Dir.DN)
        elif move == "L":
            self._move(Dir.LT)
        elif move == "R":
            self._move(Dir.RT)
        self._view.schedule(
            self._move_delay_ms, lambda: self._animate_solution_step(index + 1)
        )

    def _show_info(self):
        if not self._last_solve:
            print("Aucune donnee de solveur")
            return
        detail = solver_astar.format_details(self._last_solve)
        self._view.show_text_dialog("Details A*", detail)

    def _export_tree(self):
        if not self._last_solve:
            print("Aucune donnee de solveur")
            return
        stamp = time.strftime("%Y%m%d_%H%M%S")
        base = "astar_tree_{0}".format(stamp)
        dot_path = base + ".dot"

        def run_export():
            snapshot = self._last_solve_world or self._snapshot_world(self._world)
            result = solver_astar.solve_astar(
                snapshot, tree_limits=None, trace_limit=self._trace_limit_export
            )
            tree_data = result.get("tree")
            if not tree_data or not tree_data.get("nodes"):
                msg = "Aucun arbre a exporter"
            else:
                solver_astar.export_tree_dot(tree_data, dot_path)
                msg = "Arbre exporte: {0}".format(dot_path)
            self._view.schedule(0, lambda: self._finish_export(msg))

        thread = threading.Thread(target=run_export)
        thread.daemon = True
        thread.start()

    def _finish_export(self, msg):
        print(msg)
        self._view.show_text_dialog("Export", msg)

    @staticmethod
    def _snapshot_world(world):
        return SimpleNamespace(
            worker_pos=[world.worker_pos[0]],
            box_pos=list(world.box_pos),
            dock_pos=list(world.dock_pos),
            wall_pos=list(world.wall_pos),
        )

    def _set_speed(self, level):
        speeds = {1: 150, 2: 80, 3: 30}
        self._speed_level = level
        self._move_delay_ms = speeds[level]
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
        elif key == Key.EXPORT:
            self._export_tree()
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
        return json.load(open("levels.json"))
    except (OSError, IOError, ValueError):
        print("sokoban: loading levels failed!", file=sys.stderr)
        exit(1)

if __name__ == "__main__":
    Sokoban(load_levels())
