
import os
import sys
import argparse
import json
import asyncio
import numpy as np
from typing import Optional, Dict, Any, AsyncGenerator

from stable_baselines3 import PPO

# CRITICAL FIX: Add the 'ml' folder directly to sys.path so SB3 can find 'agent_model' during unpickling
ml_dir = os.path.dirname(os.path.abspath(__file__))
if ml_dir not in sys.path:
    sys.path.insert(0, ml_dir)

import agent_model


class InferenceRunner:
    """
    Runs a trained PPO model in ML1's WarehouseEnv and yields
    get_state() JSON for each step. Designed for the WebSocket pipeline.
    """

    def __init__(
        self,
        checkpoint_path: str,
        grid_size: int = 100,
        max_steps: int = 800,
        device: str = "cpu",
        use_real_env: bool = True,
        step_delay: float = 0.05,
    ):
        
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        self.model = PPO.load(checkpoint_path, device=device)
        self.grid_size = grid_size
        self.max_steps = max_steps
        self.step_delay = step_delay
        self.device = device

        # Create environment
        if use_real_env:
            try:
                import sys
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                from ml1.env.warehouse_env import WarehouseEnv
                self.env = WarehouseEnv(grid_size=grid_size)
                print(f"Inference env: ML1's WarehouseEnv ({grid_size}x{grid_size})")
            except ImportError as e:
                print(f"Failed to import real env: {e}")
                from dummy_env import DummyWarehouseEnv
                self.env = DummyWarehouseEnv(grid_size=grid_size, max_steps=max_steps)
                print(f"Inference env: DummyWarehouseEnv ({grid_size}x{grid_size})")
        else:
            from dummy_env import DummyWarehouseEnv
            self.env = DummyWarehouseEnv(grid_size=grid_size, max_steps=max_steps)
            print(f"Inference env: DummyWarehouseEnv ({grid_size}x{grid_size})")

        # Phase 2 model with Stage 3 (competing robots) unlocked for demo!
        # The Phase 2 model learned Stage 2 obstacles. Stage 3 adds competing robots.
        if hasattr(self.env, "curriculum"):
            self.env.curriculum.current_stage = 3

        print(f"Agent loaded from {checkpoint_path}")
        print(f"   Grid: {grid_size}×{grid_size} | Device: {device} | Delay: {step_delay}s")

    def predict(self, observation: np.ndarray, deterministic: bool = False) -> int:
        """Given observation, return the best action."""
        action, _ = self.model.predict(observation, deterministic=deterministic)
        return int(action)

    def run_episode_sync(self) -> list:
        
        obs, info = self.env.reset()
        states = []

        # Send initial state
        state = self.env.get_state()
        state["done"] = False
        states.append(state)

        done = False
        while not done:
            action = self.predict(obs)
            obs, reward, terminated, truncated, info = self.env.step(action)
            done = terminated or truncated

            state = self.env.get_state()
            state["done"] = done
            state["metrics"]["reward_this_step"] = float(reward)
            states.append(state)

        return states

    async def run_episode(self) -> AsyncGenerator[Dict[str, Any], None]:
        
        obs, info = self.env.reset()

        # Yield initial state
        state = self.env.get_state()
        state["done"] = False
        yield state

        done = False
        while not done:
            action = self.predict(obs)
            obs, reward, terminated, truncated, info = self.env.step(action)
            done = terminated or truncated

            state = self.env.get_state()
            state["done"] = done
            state["metrics"]["reward_this_step"] = float(reward)
            yield state

            if self.step_delay > 0:
                await asyncio.sleep(self.step_delay)

    def get_model_info(self) -> Dict[str, Any]:
        
        return {
            "grid_size": self.grid_size,
            "max_steps": self.max_steps,
            "device": self.device,
            "total_params": sum(p.numel() for p in self.model.policy.parameters()),
        }


# ──────────────────────────────────────────────
# Standalone test
# ──────────────────────────────────────────────


def run_demo(checkpoint_path: str, grid_size: int, episodes: int, use_real_env: bool = False):
    """Run a quick inference demo to verify the model works."""

    runner = InferenceRunner(
        checkpoint_path,
        grid_size=grid_size,
        max_steps=grid_size * 4,
        use_real_env=use_real_env,
        step_delay=0,
    )

    print(f"\n📊 Model info: {json.dumps(runner.get_model_info(), indent=2)}\n")

    successes = 0
    total_steps = 0

    for ep in range(episodes):
        states = runner.run_episode_sync()
        final_state = states[-1]

        ep_steps = final_state["step"]
        agent_status = final_state["agent"]["status"]
        total_reward = final_state["metrics"]["total_reward"]

        success = agent_status == "reached_goal"
        successes += int(success)
        total_steps += ep_steps

        status_icon = "✅" if success else "💥" if agent_status == "collided" else "⏰"
        print(f"  {status_icon} Episode {ep+1}/{episodes}: {agent_status} | Steps: {ep_steps} | Reward: {total_reward:.1f}")

    print(f"\n Results: {successes}/{episodes} successes ({successes/episodes:.0%})")
    print(f"   Avg steps: {total_steps / episodes:.0f}")

    # Print sample get_state() JSON for BE reference
    print(f"\n Sample get_state() JSON (for BE):")
    sample = states[min(5, len(states)-1)]
    print(json.dumps(sample, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="🤖 Run trained agent inference")
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to model .zip")
    parser.add_argument("--grid_size", type=int, default=15, help="Grid size for inference")
    parser.add_argument("--episodes", type=int, default=5, help="Number of episodes to run")
    parser.add_argument("--real_env", action="store_true", help="Use the ML1 real env")
    args = parser.parse_args()

    run_demo(args.checkpoint, args.grid_size, args.episodes, args.real_env)