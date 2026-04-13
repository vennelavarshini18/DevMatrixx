

import random
from collections import deque
from typing import List, Tuple, Optional, Dict, Any


class Agent:
    

    def __init__(self, x: int = 0, y: int = 0):
        self.x = x
        self.y = y
        self.status = "moving"  # "moving", "blocked", "collided", "reached_goal"

    def move(self, action: int, grid_size: int) -> Tuple[int, int]:
        
        dx, dy = {0: (0, -1), 1: (0, 1), 2: (-1, 0), 3: (1, 0)}[action]
        new_x = self.x + dx
        new_y = self.y + dy
        return new_x, new_y

    def set_position(self, x: int, y: int):
        self.x = x
        self.y = y

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y, "status": self.status}


class Goal:
    

    def __init__(self, x: int = 0, y: int = 0):
        self.x = x
        self.y = y

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y}


# ---------------------------------------------------------------------------
# Obstacle Types
# ---------------------------------------------------------------------------

class StaticObstacle:
    

    def __init__(self, obs_id: str, x: int, y: int):
        self.id = obs_id
        self.x = x
        self.y = y
        self.type = "static"

    def update(self, step_count: int, grid_size: int, occupied: set):
        """Static obstacles don't move — no-op."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "x": self.x, "y": self.y, "type": self.type}


class PatrolObstacle:
    

    def __init__(self, obs_id: str, waypoints: List[Tuple[int, int]], speed: int = 1):
        """
        Args:
            obs_id: Unique identifier
            waypoints: List of (x, y) coords defining the patrol path
            speed: How many steps between each move (1 = every step)
        """
        self.id = obs_id
        self.waypoints = waypoints
        self.speed = max(1, speed)
        self.current_wp_index = 0
        self.direction = 1  # 1 = forward through waypoints, -1 = reverse
        self.x = waypoints[0][0]
        self.y = waypoints[0][1]
        self.type = "patrol"

    def update(self, step_count: int, grid_size: int, occupied: set):
        """Move to the next waypoint in the patrol path."""
        if step_count % self.speed != 0:
            return

        # Advance waypoint index (bounce back and forth)
        self.current_wp_index += self.direction
        if self.current_wp_index >= len(self.waypoints):
            self.direction = -1
            self.current_wp_index = len(self.waypoints) - 2
        elif self.current_wp_index < 0:
            self.direction = 1
            self.current_wp_index = 1

        # Clamp in case of single-waypoint edge case
        self.current_wp_index = max(0, min(self.current_wp_index, len(self.waypoints) - 1))

        new_x, new_y = self.waypoints[self.current_wp_index]
        # Only move if the target cell isn't occupied by another obstacle
        if (new_x, new_y) not in occupied:
            self.x = new_x
            self.y = new_y

    def to_dict(self) -> Dict[str, Any]:
        # dx/dy hints for FE animation direction
        if len(self.waypoints) >= 2:
            next_idx = min(self.current_wp_index + self.direction, len(self.waypoints) - 1)
            next_idx = max(0, next_idx)
            dx = self.waypoints[next_idx][0] - self.x
            dy = self.waypoints[next_idx][1] - self.y
        else:
            dx, dy = 0, 0
        return {"id": self.id, "x": self.x, "y": self.y, "type": self.type, "dx": dx, "dy": dy}


class RandomWalkObstacle:
    

    def __init__(self, obs_id: str, x: int, y: int):
        self.id = obs_id
        self.x = x
        self.y = y
        self.type = "random_walk"

    def update(self, step_count: int, grid_size: int, occupied: set):
        """Move to a random neighboring cell (or stay in place)."""
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0), (0, 0)]  # includes staying
        random.shuffle(directions)

        for dx, dy in directions:
            new_x = self.x + dx
            new_y = self.y + dy
            if 0 <= new_x < grid_size and 0 <= new_y < grid_size and (new_x, new_y) not in occupied:
                self.x = new_x
                self.y = new_y
                return
        # If all neighbors occupied, stay in place (no-op)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "x": self.x, "y": self.y, "type": self.type}


class CompetingRobot:
    

    def __init__(self, obs_id: str, x: int, y: int, goal_x: int, goal_y: int, speed: int = 2):
        """
        Args:
            obs_id: Unique identifier
            x, y: Starting position
            goal_x, goal_y: The goal this robot moves toward
            speed: Steps between each move (higher = slower robot)
        """
        self.id = obs_id
        self.x = x
        self.y = y
        self.goal_x = goal_x
        self.goal_y = goal_y
        self.speed = max(1, speed)
        self.type = "competing_robot"
        self.reached_goal = False

    def update(self, step_count: int, grid_size: int, occupied: set):
        """Move one step closer to the goal using greedy Manhattan reduction."""
        if step_count % self.speed != 0:
            return
        if self.reached_goal:
            return

        # Try to reduce distance to goal greedily
        best_move = None
        best_dist = abs(self.x - self.goal_x) + abs(self.y - self.goal_y)

        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        random.shuffle(directions)  # Shuffle to break ties randomly

        for dx, dy in directions:
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < grid_size and 0 <= ny < grid_size and (nx, ny) not in occupied:
                dist = abs(nx - self.goal_x) + abs(ny - self.goal_y)
                if dist < best_dist:
                    best_dist = dist
                    best_move = (nx, ny)

        if best_move:
            self.x, self.y = best_move

        # Check if we reached the goal
        if self.x == self.goal_x and self.y == self.goal_y:
            self.reached_goal = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "x": self.x, "y": self.y,
            "type": self.type, "reached_goal": self.reached_goal
        }


# ---------------------------------------------------------------------------
# Curriculum Tracker
# ---------------------------------------------------------------------------

class CurriculumTracker:
    

    def __init__(self, window_size: int = 100, advance_threshold: float = 0.90):
        self.window_size = window_size
        self.advance_threshold = advance_threshold
        self.current_stage = 1
        self.max_stage = 3
        self.history: deque = deque(maxlen=window_size)
        self.total_episodes = 0

    def record(self, success: bool):
        
        self.history.append(1 if success else 0)
        self.total_episodes += 1

    @property
    def success_rate(self) -> float:
        
        if len(self.history) == 0:
            return 0.0
        return sum(self.history) / len(self.history)

    def should_advance(self) -> bool:
        
        if self.current_stage >= self.max_stage:
            return False
        if len(self.history) < self.window_size:
            return False
        return self.success_rate >= self.advance_threshold

    def try_advance(self) -> bool:
        
        if self.should_advance():
            self.current_stage += 1
            self.history.clear()  # Reset history for the new stage
            print(f"[CURRICULUM] Advanced to Stage {self.current_stage}!")
            return True
        return False
