def get_mock_frames():
    return [
        {
            "episode": 1,
            "step": 0,
            "agent": {"x": 0, "y": 0, "status": "moving"},
            "goal": {"x": 14, "y": 14},
            "obstacles": [
                {"id": "s_0", "x": 3, "y": 4, "type": "static"},
                {"id": "p_0", "x": 8, "y": 2, "type": "patrol", "dx": 1, "dy": 0},
                {"id": "r_0", "x": 11, "y": 6, "type": "random_walk"},
            ],
            "metrics": {
                "reward_this_step": 0,
                "total_reward": 0,
                "distance_to_goal": 28,
            },
            "stage": 2,
            "done": False,
        },
        {
            "episode": 1,
            "step": 1,
            "agent": {"x": 1, "y": 0, "status": "moving"},
            "goal": {"x": 14, "y": 14},
            "obstacles": [
                {"id": "s_0", "x": 3, "y": 4, "type": "static"},
                {"id": "p_0", "x": 9, "y": 2, "type": "patrol", "dx": 1, "dy": 0},
                {"id": "r_0", "x": 11, "y": 7, "type": "random_walk"},
            ],
            "metrics": {
                "reward_this_step": 0.09,
                "total_reward": 0.09,
                "distance_to_goal": 27,
            },
            "stage": 2,
            "done": False,
        },
        {
            "episode": 1,
            "step": 2,
            "agent": {"x": 1, "y": 1, "status": "moving"},
            "goal": {"x": 14, "y": 14},
            "obstacles": [
                {"id": "s_0", "x": 3, "y": 4, "type": "static"},
                {"id": "p_0", "x": 10, "y": 2, "type": "patrol", "dx": 1, "dy": 0},
                {"id": "r_0", "x": 10, "y": 7, "type": "random_walk"},
            ],
            "metrics": {
                "reward_this_step": 0.09,
                "total_reward": 0.18,
                "distance_to_goal": 26,
            },
            "stage": 2,
            "done": False,
        },
        {
            "episode": 1,
            "step": 3,
            "agent": {"x": 1, "y": 1, "status": "collided"},
            "goal": {"x": 14, "y": 14},
            "obstacles": [
                {"id": "s_0", "x": 3, "y": 4, "type": "static"},
                {"id": "p_0", "x": 11, "y": 2, "type": "patrol", "dx": 1, "dy": 0},
                {"id": "r_0", "x": 1, "y": 1, "type": "random_walk"},
            ],
            "metrics": {
                "reward_this_step": -10,
                "total_reward": -9.82,
                "distance_to_goal": 26,
            },
            "stage": 2,
            "done": True,
        },
    ]
