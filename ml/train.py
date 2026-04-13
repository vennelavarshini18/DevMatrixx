

import os
import sys
import argparse
import time
from datetime import datetime

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

from agent_model import POLICY_KWARGS

# ──────────────────────────────────────────────
# Custom Callbacks
# ──────────────────────────────────────────────


class CurriculumMonitorCallback(BaseCallback):
    

    def __init__(self, verbose: int = 1):
        super().__init__(verbose)
        self.episode_results = []
        self.last_logged_stage = 1

    def _on_step(self) -> bool:
        infos = self.locals.get("infos", [])
        for info in infos:
            if "episode" in info:
                # Episode finished
                ep_reward = info["episode"]["r"]
                self.episode_results.append(ep_reward > 50.0)

            # Read ML1's curriculum state directly from info
            stage = info.get("stage", 1)
            success_rate = info.get("success_rate", 0.0)

            # Log to TensorBoard
            self.logger.record("curriculum/stage", stage)
            self.logger.record("curriculum/ml1_success_rate", success_rate)

            if stage != self.last_logged_stage:
                self.last_logged_stage = stage
                if self.verbose:
                    print(f"\n{'='*60}")
                    print(f"🎓 ML1 CURRICULUM ADVANCED → Stage {stage}")
                    print(f"{'='*60}\n")

        # Also log our own success tracking
        if self.episode_results:
            recent = self.episode_results[-100:]
            self.logger.record("curriculum/ml2_success_rate", np.mean(recent))

        return True


class RewardLoggerCallback(BaseCallback):
    

    def __init__(self, log_freq: int = 1000, verbose: int = 0):
        super().__init__(verbose)
        self.log_freq = log_freq
        self.episode_rewards = []
        self.episode_lengths = []
        self.collisions = 0
        self.goals_reached = 0
        self.wall_hits = 0

    def _on_step(self) -> bool:
        infos = self.locals.get("infos", [])
        for info in infos:
            if "episode" in info:
                self.episode_rewards.append(info["episode"]["r"])
                self.episode_lengths.append(info["episode"]["l"])

                # Track success/failure types from info
                ep_reward = info["episode"]["r"]
                if ep_reward > 50:
                    self.goals_reached += 1
                elif ep_reward < -5:
                    self.collisions += 1

        if self.num_timesteps % self.log_freq == 0 and self.episode_rewards:
            recent = self.episode_rewards[-100:]
            self.logger.record("reward/mean_100ep", np.mean(recent))
            self.logger.record("reward/max_100ep", np.max(recent))
            self.logger.record("reward/min_100ep", np.min(recent))
            self.logger.record("reward/std_100ep", np.std(recent))

            recent_len = self.episode_lengths[-100:]
            self.logger.record("episode/mean_length", np.mean(recent_len))
            self.logger.record("episode/total_episodes", len(self.episode_rewards))
            self.logger.record("episode/total_goals", self.goals_reached)
            self.logger.record("episode/total_collisions", self.collisions)

            total_eps = len(self.episode_rewards)
            if total_eps > 0:
                self.logger.record("episode/goal_rate", self.goals_reached / total_eps)
                self.logger.record("episode/collision_rate", self.collisions / total_eps)

        return True


# ──────────────────────────────────────────────
# Environment Factory
# ──────────────────────────────────────────────


def make_env(grid_size: int, max_steps: int, use_real_env: bool = False):
    
    def _init():
        if use_real_env:
            try:
                # ML1 lives at DevMatrixx/ml1/ — add DevMatrixx root to path
                devmatrixx_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                if devmatrixx_root not in sys.path:
                    sys.path.insert(0, devmatrixx_root)
                from ml1.env import WarehouseEnv
                env = WarehouseEnv(grid_size=grid_size)
                print(f"🌍 Using ML1's WarehouseEnv ({grid_size}×{grid_size})")
            except ImportError as e:
                print(f"⚠️  ML1's env not found ({e}), falling back to dummy env")
                from dummy_env import DummyWarehouseEnv
                env = DummyWarehouseEnv(grid_size=grid_size, max_steps=max_steps)
        else:
            from dummy_env import DummyWarehouseEnv
            env = DummyWarehouseEnv(grid_size=grid_size, max_steps=max_steps)

        return Monitor(env)

    return _init


# ──────────────────────────────────────────────
# Training
# ──────────────────────────────────────────────


def train(args):
    print(f"""
╔══════════════════════════════════════════════════════╗
║       🤖 WAREHOUSE RL — TRAINING LAUNCH 🤖          ║
╠══════════════════════════════════════════════════════╣
║  Grid Size:     {args.grid_size}×{args.grid_size:<34}║
║  Timesteps:     {args.timesteps:<37,}║
║  Learning Rate: {args.lr:<37}║
║  Entropy Coef:  {args.ent_coef:<37}║
║  Gamma:         {args.gamma:<37}║
║  Batch Size:    {args.batch_size:<37}║
║  N Steps:       {args.n_steps:<37}║
║  N Envs:        {args.n_envs:<37}║
║  Run Name:      {args.run_name:<37}║
║  Real Env:      {str(args.real_env):<37}║
║  Device:        {args.device:<37}║
╚══════════════════════════════════════════════════════╝
    """)

    # ── Create vectorized environments ──
    env_fns = [make_env(args.grid_size, args.max_steps, args.real_env) for _ in range(args.n_envs)]

    if args.n_envs > 1:
        try:
            vec_env = SubprocVecEnv(env_fns)
            print(f"✅ Using SubprocVecEnv with {args.n_envs} parallel envs")
        except Exception as e:
            print(f"⚠️  SubprocVecEnv failed ({e}), using DummyVecEnv")
            vec_env = DummyVecEnv(env_fns)
    else:
        vec_env = DummyVecEnv(env_fns)

    # ── Create eval environment ──
    eval_env = DummyVecEnv([make_env(args.grid_size, args.max_steps, args.real_env)])

    # ── Paths ──
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = f"{args.run_name}_{timestamp}"
    checkpoint_dir = os.path.join(args.checkpoint_dir, run_dir)
    best_model_dir = os.path.join(args.checkpoint_dir, f"{run_dir}_best")

    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(best_model_dir, exist_ok=True)

    # ── Build PPO model ──
    model = PPO(
        policy="CnnPolicy",
        env=vec_env,
        learning_rate=args.lr,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        n_epochs=args.n_epochs,
        gamma=args.gamma,
        gae_lambda=args.gae_lambda,
        clip_range=args.clip_range,
        ent_coef=args.ent_coef,
        vf_coef=0.5,
        max_grad_norm=0.5,
        policy_kwargs=POLICY_KWARGS,
        tensorboard_log=args.tb_dir,
        verbose=1,
        seed=args.seed,
        device=args.device,
    )

    total_params = sum(p.numel() for p in model.policy.parameters())
    print(f"📊 Total model parameters: {total_params:,}")
    print(f"📐 Observation space: {vec_env.observation_space}")
    print(f"🎮 Action space: {vec_env.action_space}")

    # ── Callbacks ──
    checkpoint_callback = CheckpointCallback(
        save_freq=max(args.save_freq // args.n_envs, 1),
        save_path=checkpoint_dir,
        name_prefix="warehouse_agent",
        save_replay_buffer=False,
        save_vecnormalize=False,
    )

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=best_model_dir,
        log_path=best_model_dir,
        eval_freq=max(args.eval_freq // args.n_envs, 1),
        n_eval_episodes=10,
        deterministic=True,
        render=False,
    )

    curriculum_monitor = CurriculumMonitorCallback()
    reward_logger = RewardLoggerCallback(log_freq=1000)

    callbacks = CallbackList([
        checkpoint_callback,
        eval_callback,
        curriculum_monitor,
        reward_logger,
    ])

    # ── TRAIN! ──
    print(f"\n🚀 Training started at {datetime.now().strftime('%H:%M:%S')}")
    print(f"📈 TensorBoard: tensorboard --logdir={os.path.abspath(args.tb_dir)}")
    print(f"💾 Checkpoints: {checkpoint_dir}")
    print(f"🏆 Best model: {best_model_dir}\n")

    start_time = time.time()

    try:
        model.learn(
            total_timesteps=args.timesteps,
            callback=callbacks,
            tb_log_name=run_dir,
            progress_bar=True,
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted! Saving emergency checkpoint...")
        emergency_path = os.path.join(checkpoint_dir, "emergency_model")
        model.save(emergency_path)
        print(f"💾 Emergency checkpoint saved: {emergency_path}")

    # ── Save final model ──
    final_path = os.path.join(checkpoint_dir, "final_model")
    model.save(final_path)

    elapsed = time.time() - start_time
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)

    print(f"""
╔══════════════════════════════════════════════════════╗
║          ✅ TRAINING COMPLETE ✅                     ║
╠══════════════════════════════════════════════════════╣
║  Duration:    {int(hours)}h {int(minutes)}m {int(seconds)}s                              ║
║  Final model: {final_path:<38}║
║  Best model:  {best_model_dir:<38}║
╚══════════════════════════════════════════════════════╝
    """)

    vec_env.close()
    eval_env.close()

    return final_path


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="🤖 Warehouse RL Training Pipeline (ML2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick smoke test (dummy env)
  python train.py --timesteps 10000

  # Hyperparameter sweep run
  python train.py --timesteps 50000 --lr 3e-4 --ent_coef 0.01 --run_name sweep_lr3e4

  # With ML1's real env  
  python train.py --timesteps 100000 --real_env --run_name test_real

  # OVERNIGHT BAKE 🔥
  python train.py --timesteps 2000000 --run_name overnight_bake --real_env
        """,
    )

    # Core
    parser.add_argument("--grid_size", type=int, default=15, help="Grid size (default: 15)")
    parser.add_argument("--timesteps", type=int, default=100_000, help="Total training timesteps")
    parser.add_argument("--max_steps", type=int, default=200, help="Max steps per episode")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--device", type=str, default="auto", help="Device: auto, cpu, cuda, mps")

    # Hyperparameters — THE KNOBS YOU TUNE
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    parser.add_argument("--ent_coef", type=float, default=0.01, help="Entropy coefficient (exploration)")
    parser.add_argument("--gamma", type=float, default=0.99, help="Discount factor")
    parser.add_argument("--gae_lambda", type=float, default=0.95, help="GAE lambda")
    parser.add_argument("--clip_range", type=float, default=0.2, help="PPO clip range")
    parser.add_argument("--batch_size", type=int, default=64, help="Minibatch size")
    parser.add_argument("--n_steps", type=int, default=2048, help="Steps per rollout")
    parser.add_argument("--n_epochs", type=int, default=10, help="PPO epochs per update")

    # Parallelism
    parser.add_argument("--n_envs", type=int, default=4, help="Number of parallel environments")

    # Environment
    parser.add_argument("--real_env", action="store_true", help="Use ML1's real env instead of dummy")

    # Logging & Checkpoints
    parser.add_argument("--run_name", type=str, default="train", help="Name for this training run")
    parser.add_argument("--tb_dir", type=str, default="./tb_logs", help="TensorBoard log directory")
    parser.add_argument("--checkpoint_dir", type=str, default="./checkpoints", help="Checkpoint directory")
    parser.add_argument("--save_freq", type=int, default=50_000, help="Save checkpoint every N steps")
    parser.add_argument("--eval_freq", type=int, default=10_000, help="Evaluate every N steps")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(args)
