import os
import sys
import argparse
import time
from datetime import datetime
from collections import deque

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.callbacks import (
    CheckpointCallback,
    EvalCallback,
    CallbackList,
    BaseCallback,
)
from stable_baselines3.common.monitor import Monitor

# Add root folder to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml1.env import WarehouseEnv
from ml.agent_model import POLICY_KWARGS
from ml.train import RewardLoggerCallback


# ──────────────────────────────────────────────
# Advanced Synchronized Environment
# ──────────────────────────────────────────────

class AdvancedWarehouseEnv(WarehouseEnv):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._locked_stage = 2  # Start directly at Stage 2 !

    def force_stage(self, stage: int):
        
        self._locked_stage = stage
        self.curriculum.current_stage = stage

    def reset(self, seed=None, options=None):
        
        self.curriculum.current_stage = self._locked_stage
        obs, info = super().reset(seed=seed, options=options)
        self.curriculum.current_stage = self._locked_stage
        return obs, info


def make_env(grid_size: int, max_steps: int):
    def _init():
        env = AdvancedWarehouseEnv(grid_size=grid_size)
        
        return Monitor(env)
    return _init



class GlobalCurriculumCallback(BaseCallback):
    def __init__(self, window_size=100, advance_threshold=0.50, verbose=1):
        super().__init__(verbose)
        self.history = deque(maxlen=window_size)
        self.advance_threshold = advance_threshold
        self.current_stage = 2  # We assume we loaded Stage 1's best model!

    def _on_training_start(self):
        # Broadcast immediately to sync them all up
        self.training_env.env_method("force_stage", self.current_stage)
        if self.verbose:
            print(f"\n🌍 Global Hub: Broadcasted initial Stage {self.current_stage} to all CPUs!\n")

    def _on_step(self) -> bool:
        infos = self.locals.get("infos", [])
        for info in infos:
            if "episode" in info:
                # Goal reached = reward > 50
                success = info["episode"]["r"] > 50.0
                self.history.append(1 if success else 0)

        # Log it
        if len(self.history) > 0:
            rate = sum(self.history) / len(self.history)
            self.logger.record("curriculum/global_success_rate", rate)
            self.logger.record("curriculum/global_stage", self.current_stage)

            # Check for graduation to Stage 3
            if len(self.history) >= self.history.maxlen and rate >= self.advance_threshold:
                if self.current_stage == 2:
                    self.current_stage = 3
                    self.history.clear()

                    if self.verbose:
                        print(f"\n{'='*60}")
                        print(f"🎓 GLOBAL HUB ADVANCED TRULY → Stage {self.current_stage}! COMPETING ROBOTS SPAWNED!")
                        print(f"{'='*60}\n")
                        
                    # Broadcaast the rank up command to all worker CPUs simultaneously!
                    self.training_env.env_method("force_stage", self.current_stage)

        return True




def train_advanced(args):

    # 1. Spin up the advanced environments
    env_fns = [make_env(args.grid_size, args.max_steps) for _ in range(args.n_envs)]
    if args.n_envs > 1:
        vec_env = SubprocVecEnv(env_fns)
    else:
        vec_env = DummyVecEnv(env_fns)

    # 2. Paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = f"{args.run_name}_{timestamp}"
    checkpoint_dir = os.path.join(args.checkpoint_dir, run_dir)
    best_model_dir = os.path.join(args.checkpoint_dir, f"{run_dir}_best")
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(best_model_dir, exist_ok=True)

    # 3. Load the pre-baked model
    print(f"🧠 Loading pre-baked master model from: {args.pretrained}")
    if not os.path.exists(args.pretrained):
        print(f"❌ ERROR: File not found: {args.pretrained}")
        sys.exit(1)

    model = PPO.load(
        args.pretrained,
        env=vec_env,
        device="auto",
        custom_objects={
            "learning_rate": args.lr,
            "ent_coef": args.ent_coef,
        }
    )

    # 4. Global Synced Callbacks
    eval_env = DummyVecEnv([make_env(args.grid_size, args.max_steps)])
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=best_model_dir,
        log_path=best_model_dir,
        eval_freq=max(args.eval_freq // args.n_envs, 1),
        deterministic=True,
    )
    
    global_hub = GlobalCurriculumCallback()
    reward_logger = RewardLoggerCallback(log_freq=1000)
    
    callbacks = CallbackList([
        CheckpointCallback(save_freq=max(args.save_freq // args.n_envs, 1), save_path=checkpoint_dir, name_prefix="adv_agent"),
        eval_callback,
        global_hub,
        reward_logger,
    ])

    print(f"\n🚀 Training Stage 2 started at {datetime.now().strftime('%H:%M:%S')}")
    model.learn(total_timesteps=args.timesteps, callback=callbacks, tb_log_name=run_dir, reset_num_timesteps=False)
    
    final_path = os.path.join(checkpoint_dir, "final_model_advanced")
    model.save(final_path)
    print(f"✅ ADVANCED TRAINING COMPLETE. Model saved to {final_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrained", type=str, required=True, help="Path to best_model.zip")
    parser.add_argument("--grid_size", type=int, default=15)
    parser.add_argument("--timesteps", type=int, default=1_000_000)
    parser.add_argument("--max_steps", type=int, default=200)
    parser.add_argument("--lr", type=float, default=1e-4) # Smaller learning rate for fine-tuning
    parser.add_argument("--ent_coef", type=float, default=0.01)
    parser.add_argument("--n_envs", type=int, default=4)
    parser.add_argument("--run_name", type=str, default="stage2_resume")
    parser.add_argument("--checkpoint_dir", type=str, default="./checkpoints")
    parser.add_argument("--save_freq", type=int, default=100_000)
    parser.add_argument("--eval_freq", type=int, default=10_000)
    args = parser.parse_args()
    train_advanced(args)
