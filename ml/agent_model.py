"""
ML2 — Custom CNN Feature Extractor for Warehouse RL Agent
==========================================================
The robot's "visual cortex". Takes a 3-channel grid observation
and outputs feature vectors for the policy & value heads.

ML1's Observation Contract (from ML1's actual _build_observation code):
  - dtype: np.uint8, values 0 or 255
  - shape: (3, grid_size, grid_size)
  - Channel 0: OBSTACLES (255 where obstacles exist)
  - Channel 1: AGENT position (255 at agent's cell)
  - Channel 2: GOAL position (255 at goal's cell)

⚠️  NOTE: The original spec doc listed a different channel order.
     ML1's actual code is the ground truth. CNN doesn't care about
     the semantic meaning of channels — it learns the mapping.

SB3 automatically normalizes uint8 observations to [0, 1] float32
via CnnPolicy's built-in preprocessing. No manual normalization needed.

Architecture:
  Conv2d(3→32, 3×3) → ReLU → Conv2d(32→64, 3×3) → ReLU →
  Conv2d(64→64, 3×3) → ReLU → AdaptiveAvgPool(4×4) → 
  Flatten → Linear(→256) → ReLU

Key design: AdaptiveAvgPool2d makes this grid-size AGNOSTIC.
  Train on 15×15, infer on 5×5 or 100×100 — same model.
"""

import torch
import torch.nn as nn
import gymnasium as gym
import numpy as np
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor


class WarehouseCNN(BaseFeaturesExtractor):
    """
    Custom CNN that processes the 3-channel grid observation.
    Designed for 15×15 training grids but works on any square grid
    thanks to AdaptiveAvgPool2d.
    """

    def __init__(self, observation_space: gym.spaces.Box, features_dim: int = 256):
        super().__init__(observation_space, features_dim)

        n_channels = observation_space.shape[0]  # Should be 3

        self.cnn = nn.Sequential(
            # Layer 1: Capture local patterns (agent near wall, near obstacle)
            nn.Conv2d(n_channels, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),

            # Layer 2: Capture medium-range spatial relationships
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),

            # Layer 3: Capture global spatial understanding
            nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),

            # Adaptive pooling — THIS is what makes it grid-size agnostic
            # Whether input is 15×15 or 100×100, output is always 4×4×64
            nn.AdaptiveAvgPool2d((4, 4)),

            nn.Flatten(),
        )

        # Linear projection to feature vector
        self.linear = nn.Sequential(
            nn.Linear(64 * 4 * 4, features_dim),
            nn.ReLU(),
        )

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        # SB3 CnnPolicy auto-normalizes uint8 → float32 [0,1] before calling this
        return self.linear(self.cnn(observations))


# ──────────────────────────────────────────────
# Policy kwargs to plug into SB3's PPO
# ──────────────────────────────────────────────

POLICY_KWARGS = {
    "features_extractor_class": WarehouseCNN,
    "features_extractor_kwargs": {"features_dim": 256},
    "net_arch": {
        "pi": [128, 64],   # Policy head: 256 → 128 → 64 → 4 actions
        "vf": [128, 64],   # Value head:  256 → 128 → 64 → 1 scalar
    },
}


# ──────────────────────────────────────────────
# Sanity checks — test all 3 demo grid sizes
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("🧠 Testing WarehouseCNN Feature Extractor\n")

    test_cases = [
        (5, "5×5 (live pitch demo)"),
        (15, "15×15 (training grid)"),
        (100, "100×100 (jaw-dropper demo)"),
    ]

    for grid_size, label in test_cases:
        # Create obs space matching ML1's spec: uint8
        obs_space = gym.spaces.Box(
            low=0, high=255,
            shape=(3, grid_size, grid_size),
            dtype=np.uint8,
        )
        model = WarehouseCNN(obs_space, features_dim=256)

        # Simulate SB3's preprocessing: uint8 → float32 [0,1]
        dummy_obs_uint8 = np.zeros((1, 3, grid_size, grid_size), dtype=np.uint8)
        dummy_obs_uint8[0, 0, 0, 0] = 255   # Agent at (0,0)
        dummy_obs_uint8[0, 1, 3, 4] = 255   # Obstacle at (4,3)
        dummy_obs_uint8[0, 2, grid_size-1, grid_size-1] = 255  # Goal at corner

        # SB3 normalizes: obs / 255.0
        dummy_obs_float = torch.tensor(dummy_obs_uint8, dtype=torch.float32) / 255.0

        features = model(dummy_obs_float)
        assert features.shape == (1, 256), f"Expected (1, 256), got {features.shape}"
        print(f"  ✅ {label}: output shape {features.shape}")

    # Count params
    obs_space_15 = gym.spaces.Box(low=0, high=255, shape=(3, 15, 15), dtype=np.uint8)
    model_15 = WarehouseCNN(obs_space_15, features_dim=256)
    total_params = sum(p.numel() for p in model_15.parameters())
    print(f"\n📊 Total parameters: {total_params:,}")
    print("🎉 All sanity checks passed! CNN is grid-size agnostic.")
