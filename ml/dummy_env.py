

import numpy as np
import gymnasium as gym
from gymnasium import spaces
from collections import deque
import random


class DummyWarehouseEnv(gym.Env):
    

    metadata = {"render_modes": ["human", "ansi"], "render_fps": 10}

    
    REWARD_STEP_PENALTY = -0.01
    REWARD_CLOSER_SCALE = 0.1
    REWARD_WALL_HIT = -1.0
    REWARD_COLLISION = -10.0
    REWARD_GOAL = 100.0
    MAX_STEPS_PER_EPISODE = 200

    def __init__(self, grid_size: int = 15, max_steps: int = 200, render_mode=None):
        super().__init__()
        self.grid_size = grid_size
        self.max_steps = max_steps or self.MAX_STEPS_PER_EPISODE
        self.render_mode = render_mode

        
        self.action_space = spaces.Discrete(4)
        self.observation_space = spaces.Box(
            low=0, high=255,
            shape=(3, grid_size, grid_size),
            dtype=np.uint8,
        )

        
        self._action_to_delta = {
            0: (0, -1),   
            1: (0, 1),    
            2: (-1, 0),   
            3: (1, 0),    
        }

        
        self.agent_x = 0
        self.agent_y = 0
        self.agent_status = "moving"
        self.goal_x = 0
        self.goal_y = 0
        self.obstacles = []
        self.current_step = 0
        self.episode_reward = 0.0
        self.prev_distance = 0
        self.episode_count = 0

        
        self.current_stage = 1
        self._success_history = deque(maxlen=100)
        self._total_episodes = 0

    @property
    def success_rate(self):
        if not self._success_history:
            return 0.0
        return sum(self._success_history) / len(self._success_history)

    def _manhattan_distance(self) -> int:
        return abs(self.agent_x - self.goal_x) + abs(self.agent_y - self.goal_y)

    def _spawn_obstacles(self):
        
        self.obstacles = []

        # Static Warehouse Environment layout
        # 1 in every 3 columns has shelves, leaving 2 rows of gaps front/back
        shelf_id = 0
        for x in range(2, self.grid_size - 1, 3):
            for y in range(2, self.grid_size - 2):
                self.obstacles.append({
                    "id": f"s_{shelf_id}", "x": x, "y": y, "type": "static"
                })
                shelf_id += 1

    def _sample_free_position(self, occupied):
        while True:
            x = random.randint(0, self.grid_size - 1)
            y = random.randint(0, self.grid_size - 1)
            if (x, y) not in occupied:
                return (x, y)

    def _update_obstacles(self):
        """Move patrol and random_walk obstacles each step."""
        for obs in self.obstacles:
            if obs["type"] == "patrol":
                new_x = obs["x"] + obs.get("dx", 0)
                new_y = obs["y"] + obs.get("dy", 0)
                # Reverse at edges
                if new_x < 0 or new_x >= self.grid_size:
                    obs["dx"] = -obs.get("dx", 0)
                    new_x = obs["x"]
                if new_y < 0 or new_y >= self.grid_size:
                    obs["dy"] = -obs.get("dy", 0)
                    new_y = obs["y"]
                obs["x"] = new_x
                obs["y"] = new_y

            elif obs["type"] == "random_walk":
                dx = random.choice([-1, 0, 1])
                dy = random.choice([-1, 0, 1])
                obs["x"] = max(0, min(self.grid_size - 1, obs["x"] + dx))
                obs["y"] = max(0, min(self.grid_size - 1, obs["y"] + dy))

    def _build_observation(self) -> np.ndarray:
        
        obs = np.zeros((3, self.grid_size, self.grid_size), dtype=np.uint8)

        # Channel 0: OBSTACLES (255 where obstacles are)
        for o in self.obstacles:
            oy, ox = o["y"], o["x"]
            if 0 <= oy < self.grid_size and 0 <= ox < self.grid_size:
                obs[0, oy, ox] = 255

        # Channel 1: AGENT (255 where agent is)
        obs[1, self.agent_y, self.agent_x] = 255

        # Channel 2: GOAL (255 where goal is)
        obs[2, self.goal_y, self.goal_x] = 255

        return obs

    def _check_collision(self, x: int, y: int) -> bool:
        
        for o in self.obstacles:
            if o["x"] == x and o["y"] == y:
                return True
        return False

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._total_episodes += 1
        self.episode_count = self._total_episodes

        self._spawn_obstacles()

        
        occupied = {(obs["x"], obs["y"]) for obs in self.obstacles}
        agent_pos = self._sample_free_position(occupied)
        occupied.add(agent_pos)
        self.agent_x, self.agent_y = agent_pos
        
        goal_pos = self._sample_free_position(occupied)
        self.goal_x, self.goal_y = goal_pos
        self.current_step = 0
        self.episode_reward = 0.0
        self.agent_status = "moving"
        self.prev_distance = self._manhattan_distance()

        obs = self._build_observation()
        info = self._build_info()
        return obs, info

    def step(self, action: int):
        self.current_step += 1
        reward = 0.0
        terminated = False

        dx, dy = self._action_to_delta[action]
        new_x = self.agent_x + dx
        new_y = self.agent_y + dy

        # ── Wall hit ──
        if new_x < 0 or new_x >= self.grid_size or new_y < 0 or new_y >= self.grid_size:
            reward += self.REWARD_WALL_HIT
            self.agent_status = "blocked"
            # Agent stays in place

        # ── Collision with obstacle ──
        elif self._check_collision(new_x, new_y):
            reward += self.REWARD_COLLISION
            self.agent_status = "collided"
            terminated = True

        # ── Successful move ──
        else:
            self.agent_x = new_x
            self.agent_y = new_y
            self.agent_status = "moving"

            # Check goal
            if self.agent_x == self.goal_x and self.agent_y == self.goal_y:
                reward += self.REWARD_GOAL
                self.agent_status = "reached_goal"
                terminated = True

        # ── Dense reward: distance shaping ──
        if not terminated:
            curr_distance = self._manhattan_distance()
            delta = self.prev_distance - curr_distance
            reward += delta * self.REWARD_CLOSER_SCALE
            self.prev_distance = curr_distance

        # ── Step penalty ──
        reward += self.REWARD_STEP_PENALTY

        # ── Update moving obstacles ──
        self._update_obstacles()

        # ── Post-move collision (obstacle walked into agent) ──
        if not terminated and self._check_collision(self.agent_x, self.agent_y):
            reward += self.REWARD_COLLISION
            self.agent_status = "collided"
            terminated = True

        self.episode_reward += reward

        # ── Truncation ──
        truncated = (self.current_step >= self.max_steps) and not terminated

        # ── Track curriculum ──
        if terminated or truncated:
            self._success_history.append(self.agent_status == "reached_goal")
            if len(self._success_history) >= 100 and self.success_rate >= 0.90:
                if self.current_stage < 3:
                    self.current_stage += 1
                    self._success_history.clear()
                    print(f"🎓 CURRICULUM → Stage {self.current_stage}")

        obs = self._build_observation()
        info = self._build_info()

        return obs, reward, terminated, truncated, info

    def _build_info(self) -> dict:
        """Build info dict matching ML1's exact schema."""
        return {
            "stage": self.current_stage,
            "success_rate": round(self.success_rate, 4),
            "agent_pos": [self.agent_x, self.agent_y],
            "goal_pos": [self.goal_x, self.goal_y],
            "distance_to_goal": self._manhattan_distance(),
            "obstacles": [dict(o) for o in self.obstacles],
            "episode_step": self.current_step,
            "total_episodes": self._total_episodes,
        }

    def get_state(self) -> dict:
        """JSON-serializable snapshot matching ML1's get_state() output."""
        return {
            "episode": self._total_episodes,
            "step": self.current_step,
            "agent": {
                "x": self.agent_x,
                "y": self.agent_y,
                "status": self.agent_status,
            },
            "goal": {
                "x": self.goal_x,
                "y": self.goal_y,
            },
            "obstacles": [dict(o) for o in self.obstacles],
            "metrics": {
                "reward_this_step": round(self.episode_reward, 4),
                "total_reward": round(self.episode_reward, 4),
                "distance_to_goal": self._manhattan_distance(),
            },
            "stage": self.current_stage,
            "done": self.agent_status in ("collided", "reached_goal"),
        }

    def set_stage(self, stage: int):
        """Allow external curriculum control."""
        self.current_stage = min(stage, 3)

    def render(self):
        if self.render_mode == "ansi":
            symbols = {"static": "#", "patrol": "P", "random_walk": "R"}
            grid = [["." for _ in range(self.grid_size)] for _ in range(self.grid_size)]
            for o in self.obstacles:
                if 0 <= o["y"] < self.grid_size and 0 <= o["x"] < self.grid_size:
                    grid[o["y"]][o["x"]] = symbols.get(o["type"], "?")
            grid[self.goal_y][self.goal_x] = "G"
            grid[self.agent_y][self.agent_x] = "A"
            return "\n".join(" ".join(row) for row in grid)
        return None


# ──────────────────────────────────────────────
# Quick test
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import json

    env = DummyWarehouseEnv(grid_size=15, render_mode="ansi")
    obs, info = env.reset(seed=42)

    print(f"Observation shape: {obs.shape}, dtype: {obs.dtype}")
    print(f"Obs value range: [{obs.min()}, {obs.max()}]")
    print(f"Action space: {env.action_space}")

    # Verify channel order: Ch0=obstacles, Ch1=agent, Ch2=goal
    agent_channel = obs[1]  # Channel 1 should have agent
    goal_channel = obs[2]   # Channel 2 should have goal
    assert agent_channel.sum() == 255, f"Channel 1 (agent) wrong: sum={agent_channel.sum()}"
    assert goal_channel.sum() == 255, f"Channel 2 (goal) wrong: sum={goal_channel.sum()}"
    print(f" Channel order verified: Ch0=obstacles, Ch1=agent, Ch2=goal")

    print(f"\nInfo dict keys: {list(info.keys())}")
    print(f"\nInitial grid:\n{env.render()}\n")

    # Run 10 random steps
    for i in range(10):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        action_names = {0: "Up", 1: "Down", 2: "Left", 3: "Right"}
        print(f"Step {i+1}: {action_names[action]} → status={env.agent_status}, reward={reward:.2f}, dist={info['distance_to_goal']}")
        if terminated or truncated:
            print(f"  Episode ended! Status: {env.agent_status}")
            break

    print(f"\nget_state() sample:")
    print(json.dumps(env.get_state(), indent=2))

    # Final contract assertions
    assert obs.dtype == np.uint8
    assert obs.shape == (3, 15, 15)
    assert obs.max() <= 255
    print("\n Dummy env matches ML1's actual code I/O contract!")