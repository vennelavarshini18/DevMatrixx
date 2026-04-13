

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import random
from typing import Optional, Dict, Any, List, Tuple

from .core_classes import (
    Agent, Goal,
    StaticObstacle, PatrolObstacle, RandomWalkObstacle,
    CompetingRobot, CurriculumTracker,
)


class WarehouseEnv(gym.Env):
    

    metadata = {"render_modes": ["human", "ansi"], "render_fps": 10}

    
    REWARD_STEP_PENALTY = -0.01
    REWARD_CLOSER_SCALE = 0.1       
    REWARD_WALL_HIT = -1.0
    REWARD_COLLISION = -10.0
    REWARD_GOAL = 100.0
    REWARD_COMPETITOR_STEALS = -15.0   

    
    MAX_STEPS_PER_EPISODE = 200

    
    STAGE2_STATIC = 5
    STAGE2_PATROL = 3
    STAGE2_RANDOM = 2

    
    STAGE3_COMPETITORS = 2

    def __init__(self, grid_size: int = 15, render_mode: Optional[str] = None):
        super().__init__()

        self.grid_size = grid_size
        self.render_mode = render_mode

        
        self.action_space = spaces.Discrete(4)
        self.observation_space = spaces.Box(
            low=0, high=255,
            shape=(3, self.grid_size, self.grid_size),
            dtype=np.uint8,
        )

        
        self.agent = Agent()
        self.goal = Goal()
        self.obstacles: List = []

        
        self.curriculum = CurriculumTracker(window_size=100, advance_threshold=0.90)

        
        self.current_step = 0
        self.episode_reward = 0.0
        self.prev_distance = 0

    

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None):
        """Reset the environment for a new episode."""
        super().reset(seed=seed)

        self.current_step = 0
        self.episode_reward = 0.0
        self.agent.status = "moving"

        positions = self._sample_unique_positions(2)
        self.agent.set_position(*positions[0])
        self.goal.x, self.goal.y = positions[1]

        self._spawn_obstacles()

        self.prev_distance = self._manhattan_distance()

        obs = self._build_observation()
        info = self._build_info()

        return obs, info

    

    def step(self, action: int):
        
        self.current_step += 1
        reward = 0.0
        terminated = False
        truncated = False

        
        new_x, new_y = self.agent.move(action, self.grid_size)

        
        if new_x < 0 or new_x >= self.grid_size or new_y < 0 or new_y >= self.grid_size:
            reward += self.REWARD_WALL_HIT
            self.agent.status = "blocked"
            
        else:
            
            obstacle_positions = {(obs.x, obs.y) for obs in self.obstacles}
            if (new_x, new_y) in obstacle_positions:
                reward += self.REWARD_COLLISION
                self.agent.status = "collided"
                terminated = True
            else:
                
                self.agent.set_position(new_x, new_y)
                self.agent.status = "moving"

                
                if self.agent.x == self.goal.x and self.agent.y == self.goal.y:
                    reward += self.REWARD_GOAL
                    self.agent.status = "reached_goal"
                    terminated = True

        
        if not terminated:
            current_distance = self._manhattan_distance()
            delta = self.prev_distance - current_distance  
            reward += delta * self.REWARD_CLOSER_SCALE
            self.prev_distance = current_distance

        
        reward += self.REWARD_STEP_PENALTY

        
        self._update_obstacles()

        
        if not terminated:
            obstacle_positions_after = {(obs.x, obs.y) for obs in self.obstacles}
            if (self.agent.x, self.agent.y) in obstacle_positions_after:
                reward += self.REWARD_COLLISION
                self.agent.status = "collided"
                terminated = True

        
        if not terminated:
            for obs in self.obstacles:
                if isinstance(obs, CompetingRobot) and obs.reached_goal:
                    reward += self.REWARD_COMPETITOR_STEALS
                    self.agent.status = "goal_stolen"
                    terminated = True
                    break

        
        if self.current_step >= self.MAX_STEPS_PER_EPISODE and not terminated:
            truncated = True

        
        if terminated or truncated:
            success = (self.agent.status == "reached_goal")
            self.curriculum.record(success)
            self.curriculum.try_advance()

       
        self.episode_reward += reward

        obs = self._build_observation()
        info = self._build_info()

        if self.render_mode == "human":
            self.render()

        return obs, reward, terminated, truncated, info

    

    def _build_observation(self) -> np.ndarray:
        
        obs = np.zeros((3, self.grid_size, self.grid_size), dtype=np.uint8)

        # Channel 0: Obstacles
        for obstacle in self.obstacles:
            if 0 <= obstacle.x < self.grid_size and 0 <= obstacle.y < self.grid_size:
                obs[0, obstacle.y, obstacle.x] = 255

        # Channel 1: Agent
        obs[1, self.agent.y, self.agent.x] = 255

        # Channel 2: Goal
        obs[2, self.goal.y, self.goal.x] = 255

        return obs

    

    def _manhattan_distance(self) -> int:
        return abs(self.agent.x - self.goal.x) + abs(self.agent.y - self.goal.y)

    def _build_info(self) -> Dict[str, Any]:
        
        return {
            "stage": self.curriculum.current_stage,
            "success_rate": round(self.curriculum.success_rate, 4),
            "agent_pos": [self.agent.x, self.agent.y],
            "goal_pos": [self.goal.x, self.goal.y],
            "distance_to_goal": self._manhattan_distance(),
            "obstacles": [obs.to_dict() for obs in self.obstacles],
            "episode_step": self.current_step,
            "total_episodes": self.curriculum.total_episodes,
        }

    

    def _spawn_obstacles(self):
        self.obstacles = []

        if self.curriculum.current_stage == 1:
            return

        if self.curriculum.current_stage >= 2:
            occupied = {(self.agent.x, self.agent.y), (self.goal.x, self.goal.y)}

            for i in range(self.STAGE2_STATIC):
                pos = self._sample_free_position(occupied)
                self.obstacles.append(StaticObstacle(f"s_{i}", pos[0], pos[1]))
                occupied.add(pos)

            for i in range(self.STAGE2_PATROL):
                start = self._sample_free_position(occupied)
                occupied.add(start)
                waypoints = self._generate_patrol_path(start, occupied)
                self.obstacles.append(PatrolObstacle(f"p_{i}", waypoints, speed=2))

            
            for i in range(self.STAGE2_RANDOM):
                pos = self._sample_free_position(occupied)
                self.obstacles.append(RandomWalkObstacle(f"r_{i}", pos[0], pos[1]))
                occupied.add(pos)

        if self.curriculum.current_stage >= 3:
            
            for i in range(self.STAGE3_COMPETITORS):
                pos = self._sample_free_position(occupied)
                self.obstacles.append(
                    CompetingRobot(
                        f"c_{i}", pos[0], pos[1],
                        self.goal.x, self.goal.y,
                        speed=3  
                    )
                )
                occupied.add(pos)

    def _update_obstacles(self):
        
        for obstacle in self.obstacles:
            occupied = set()
            occupied.add((self.agent.x, self.agent.y))
            occupied.add((self.goal.x, self.goal.y))
            for other in self.obstacles:
                if other.id != obstacle.id:
                    occupied.add((other.x, other.y))
            obstacle.update(self.current_step, self.grid_size, occupied)

    def _generate_patrol_path(
        self, start: Tuple[int, int], occupied: set
    ) -> List[Tuple[int, int]]:
        
        path = [start]
        current = start
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        for _ in range(random.randint(1, 3)):  
            random.shuffle(directions)
            moved = False
            for dx, dy in directions:
                nx, ny = current[0] + dx, current[1] + dy
                if (
                    0 <= nx < self.grid_size
                    and 0 <= ny < self.grid_size
                    and (nx, ny) not in occupied
                    and (nx, ny) not in path
                ):
                    path.append((nx, ny))
                    occupied.add((nx, ny))
                    current = (nx, ny)
                    moved = True
                    break
            if not moved:
                break

        
        if len(path) < 2:
            
            nx, ny = start[0], start[1]
            for dx, dy in directions:
                nx2, ny2 = start[0] + dx, start[1] + dy
                if (
                    0 <= nx2 < self.grid_size
                    and 0 <= ny2 < self.grid_size
                    and (nx2, ny2) not in occupied
                ):
                    path.append((nx2, ny2))
                    break
            if len(path) < 2:
                path.append(start)  # Fallback: just stay

        return path

    

    def _sample_unique_positions(self, n: int) -> List[Tuple[int, int]]:
        
        all_positions = [
            (x, y) for x in range(self.grid_size) for y in range(self.grid_size)
        ]
        return random.sample(all_positions, n)

    def _sample_free_position(self, occupied: set) -> Tuple[int, int]:
        
        while True:
            x = random.randint(0, self.grid_size - 1)
            y = random.randint(0, self.grid_size - 1)
            if (x, y) not in occupied:
                return (x, y)

    

    def get_state(self) -> Dict[str, Any]:
        
        return {
            "episode": self.curriculum.total_episodes,
            "step": self.current_step,
            "agent": self.agent.to_dict(),
            "goal": self.goal.to_dict(),
            "obstacles": [obs.to_dict() for obs in self.obstacles],
            "metrics": {
                "reward_this_step": round(self.episode_reward, 4),
                "total_reward": round(self.episode_reward, 4),
                "distance_to_goal": self._manhattan_distance(),
            },
            "stage": self.curriculum.current_stage,
            "done": self.agent.status in ("collided", "reached_goal", "goal_stolen"),
        }

    

    def render(self):
        symbols = {
            "empty": "· ",
            "agent": "A ",
            "goal": "G ",
            "static": "# ",
            "patrol": "P ",
            "random_walk": "R ",
            "competing_robot": "C ",
        }

        grid = [["· "] * self.grid_size for _ in range(self.grid_size)]

        
        for obs in self.obstacles:
            if 0 <= obs.x < self.grid_size and 0 <= obs.y < self.grid_size:
                grid[obs.y][obs.x] = symbols.get(obs.type, "? ")

        grid[self.goal.y][self.goal.x] = symbols["goal"]

        
        grid[self.agent.y][self.agent.x] = symbols["agent"]

        
        header = f"Stage {self.curriculum.current_stage} | Step {self.current_step} | Reward {self.episode_reward:.2f} | Dist {self._manhattan_distance()}"
        print(f"\n{'─' * (self.grid_size * 2 + 2)}")
        print(f" {header}")
        print(f"{'─' * (self.grid_size * 2 + 2)}")
        for row in grid:
            print("|" + "".join(row) + "|")
        print(f"{'─' * (self.grid_size * 2 + 2)}")

    

    def __repr__(self):
        return (
            f"WarehouseEnv(grid={self.grid_size}x{self.grid_size}, "
            f"stage={self.curriculum.current_stage}, "
            f"obstacles={len(self.obstacles)})"
        )
