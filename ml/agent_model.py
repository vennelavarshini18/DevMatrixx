
import torch
import torch.nn as nn
import gymnasium as gym
import numpy as np
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor


class WarehouseCNN(BaseFeaturesExtractor):
 

    def __init__(self, observation_space: gym.spaces.Box, features_dim: int = 256):
        super().__init__(observation_space, features_dim)

        n_channels = observation_space.shape[0]  

        self.cnn = nn.Sequential(
            
            nn.Conv2d(n_channels, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),

            
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),

            
            nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),

            
            nn.AdaptiveAvgPool2d((4, 4)),

            nn.Flatten(),
        )

        
        self.linear = nn.Sequential(
            nn.Linear(64 * 4 * 4, features_dim),
            nn.ReLU(),
        )

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        
        return self.linear(self.cnn(observations))




POLICY_KWARGS = {
    "features_extractor_class": WarehouseCNN,
    "features_extractor_kwargs": {"features_dim": 256},
    "net_arch": {
        "pi": [128, 64],   
        "vf": [128, 64],   
    },
}




if __name__ == "__main__":
    print(" Testing WarehouseCNN Feature Extractor\n")

    test_cases = [
        (5, "5×5 (live pitch demo)"),
        (15, "15×15 (training grid)"),
        (100, "100×100 (jaw-dropper demo)"),
    ]

    for grid_size, label in test_cases:
        
        obs_space = gym.spaces.Box(
            low=0, high=255,
            shape=(3, grid_size, grid_size),
            dtype=np.uint8,
        )
        model = WarehouseCNN(obs_space, features_dim=256)

        
        dummy_obs_uint8 = np.zeros((1, 3, grid_size, grid_size), dtype=np.uint8)
        dummy_obs_uint8[0, 0, 0, 0] = 255   
        dummy_obs_uint8[0, 1, 3, 4] = 255   
        dummy_obs_uint8[0, 2, grid_size-1, grid_size-1] = 255  

        
        dummy_obs_float = torch.tensor(dummy_obs_uint8, dtype=torch.float32) / 255.0

        features = model(dummy_obs_float)
        assert features.shape == (1, 256), f"Expected (1, 256), got {features.shape}"
        print(f"   {label}: output shape {features.shape}")

    # Count params
    obs_space_15 = gym.spaces.Box(low=0, high=255, shape=(3, 15, 15), dtype=np.uint8)
    model_15 = WarehouseCNN(obs_space_15, features_dim=256)
    total_params = sum(p.numel() for p in model_15.parameters())
    print(f"\n Total parameters: {total_params:,}")
    print(" All sanity checks passed! CNN is grid-size agnostic.")
