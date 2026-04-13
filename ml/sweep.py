"""
ML2 — Hyperparameter Sweep Script
===================================
Runs 5 quick mini-bakes to find the best lr + entropy combo.
Each run does 50k steps (~5 min). Check TensorBoard after all 5 finish.

Usage:
  python sweep.py              # Run all 5 sweeps sequentially
  python sweep.py --quick      # Run shorter 10k step sweeps (~1 min each)
"""

import subprocess
import sys
import argparse


SWEEP_CONFIGS = [
    {"lr": 3e-4, "ent_coef": 0.01,  "name": "sweep_baseline"},
    {"lr": 1e-4, "ent_coef": 0.05,  "name": "sweep_explore_more"},
    {"lr": 5e-4, "ent_coef": 0.005, "name": "sweep_exploit_more"},
    {"lr": 3e-4, "ent_coef": 0.02,  "name": "sweep_balanced"},
    {"lr": 1e-3, "ent_coef": 0.01,  "name": "sweep_aggressive_lr"},
]


def run_sweep(quick: bool = False):
    timesteps = 10_000 if quick else 50_000
    mode = "QUICK" if quick else "FULL"

    print(f"""
╔══════════════════════════════════════════════════════╗
║     🔬 HYPERPARAMETER SWEEP ({mode})                ║
╠══════════════════════════════════════════════════════╣
║  {len(SWEEP_CONFIGS)} configs × {timesteps:,} steps each                       ║
║  Monitor: tensorboard --logdir=./tb_logs             ║
╚══════════════════════════════════════════════════════╝
    """)

    for i, config in enumerate(SWEEP_CONFIGS, 1):
        print(f"\n{'='*50}")
        print(f"🔬 Sweep {i}/{len(SWEEP_CONFIGS)}: {config['name']}")
        print(f"   lr={config['lr']}, ent_coef={config['ent_coef']}")
        print(f"{'='*50}\n")

        cmd = [
            sys.executable, "train.py",
            "--timesteps", str(timesteps),
            "--lr", str(config["lr"]),
            "--ent_coef", str(config["ent_coef"]),
            "--run_name", config["name"],
            "--grid_size", "15",
            "--n_envs", "4",
            "--save_freq", str(timesteps),  # Only save at end
            "--eval_freq", str(timesteps // 5),
            "--real_env", # Use the actual ML1 codebase now!
        ]

        result = subprocess.run(cmd)

        if result.returncode != 0:
            print(f"❌ Sweep {config['name']} failed!")
        else:
            print(f"✅ Sweep {config['name']} done!")

    print(f"""
╔══════════════════════════════════════════════════════╗
║     ✅ ALL SWEEPS COMPLETE                           ║
║                                                      ║
║  Now open TensorBoard and compare:                   ║
║  tensorboard --logdir=./tb_logs                      ║
║                                                      ║
║  Pick the config with the highest reward curve       ║
║  and use those params for the overnight bake! 🔥     ║
╚══════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Run shorter 10k step sweeps")
    args = parser.parse_args()
    run_sweep(quick=args.quick)
