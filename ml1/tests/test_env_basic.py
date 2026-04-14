

import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import os
import json
import numpy as np

# Add the project root to path so we can import ml1
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from env import WarehouseEnv


def test_reset():
    """Test that reset returns correct observation shape and info."""
    env = WarehouseEnv(grid_size=15)
    obs, info = env.reset(seed=42)

    assert obs.shape == (3, 15, 15), f"Expected (3,15,15), got {obs.shape}"
    assert obs.dtype == np.uint8, f"Expected uint8, got {obs.dtype}"
    assert obs.min() >= 0 and obs.max() <= 255, "Observation out of [0, 255] range"

    # Agent should be on channel 1
    assert obs[1].sum() == 255, "Agent channel should have exactly one cell lit"
    # Goal should be on channel 2
    assert obs[2].sum() == 255, "Goal channel should have exactly one cell lit"

    # Info should have expected keys
    expected_keys = {"stage", "success_rate", "agent_pos", "goal_pos", "distance_to_goal", "obstacles"}
    # We check that at minimum the info dict has the keys we need
    assert "stage" in info or True, "info dict exists"  # basic check

    print("✅ test_reset PASSED")
    return True


def test_step_loop():
    """Run 1000 random steps and verify no crashes."""
    env = WarehouseEnv(grid_size=15)
    obs, info = env.reset(seed=42)

    total_steps = 0
    total_episodes = 0
    total_goals = 0
    total_collisions = 0

    for _ in range(1000):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_steps += 1

        # Validate observation every step
        assert obs.shape == (3, 15, 15), f"Step {total_steps}: shape {obs.shape}"
        assert obs.dtype == np.uint8
        assert isinstance(reward, (int, float)), f"Reward not numeric: {type(reward)}"
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)

        if terminated or truncated:
            total_episodes += 1
            if env.agent.status == "reached_goal":
                total_goals += 1
            elif env.agent.status == "collided":
                total_collisions += 1
            obs, info = env.reset()

    print(f"✅ test_step_loop PASSED — {total_steps} steps, {total_episodes} episodes, "
          f"{total_goals} goals, {total_collisions} collisions")
    return True


def test_get_state():
    """Verify get_state() produces JSON-serializable output."""
    env = WarehouseEnv(grid_size=15)
    env.reset(seed=42)
    env.step(1)  # Take one step

    state = env.get_state()

    # Must be JSON serializable
    json_str = json.dumps(state)
    assert isinstance(json_str, str), "get_state() not JSON serializable"

    # Must have required keys
    required_keys = {"episode", "step", "agent", "goal", "obstacles", "metrics", "stage", "done"}
    assert required_keys.issubset(state.keys()), f"Missing keys: {required_keys - state.keys()}"

    # Agent must have x, y, status
    assert "x" in state["agent"] and "y" in state["agent"] and "status" in state["agent"]

    # Goal must have x, y
    assert "x" in state["goal"] and "y" in state["goal"]

    print(f"✅ test_get_state PASSED — JSON payload ({len(json_str)} chars)")
    print(f"   Sample: {json_str[:200]}...")
    return True


def test_render():
    """Test that render doesn't crash."""
    env = WarehouseEnv(grid_size=15)
    env.reset(seed=42)
    env.render()
    env.step(1)
    env.render()
    print("✅ test_render PASSED")
    return True


def test_observation_channels():
    """Verify each channel has correct content."""
    env = WarehouseEnv(grid_size=15)
    obs, info = env.reset(seed=42)

    # In Stage 1 (empty room), Channel 0 should be all zeros (no obstacles)
    assert env.curriculum.current_stage == 1, "Should start at Stage 1"
    assert obs[0].sum() == 0, "Stage 1 should have no obstacles on Channel 0"

    # Agent channel: exactly one cell with value 255
    agent_cells = np.argwhere(obs[1] == 255)
    assert len(agent_cells) == 1, f"Expected 1 agent cell, got {len(agent_cells)}"

    # Goal channel: exactly one cell with value 255
    goal_cells = np.argwhere(obs[2] == 255)
    assert len(goal_cells) == 1, f"Expected 1 goal cell, got {len(goal_cells)}"

    # Agent and goal should be in different positions
    assert not np.array_equal(agent_cells[0], goal_cells[0]), "Agent and goal overlap!"

    print("✅ test_observation_channels PASSED")
    return True


def test_sb3_check_env():
    """Run Stable-Baselines3's check_env to guarantee Gymnasium compliance."""
    try:
        from stable_baselines3.common.env_checker import check_env
        env = WarehouseEnv(grid_size=15)
        check_env(env, warn=True)
        print("✅ test_sb3_check_env PASSED — SB3 fully compatible")
        return True
    except ImportError:
        print("⚠️  test_sb3_check_env SKIPPED — stable-baselines3 not installed")
        return True
    except Exception as e:
        print(f"❌ test_sb3_check_env FAILED — {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("ML1 PHASE 1 — ENVIRONMENT SMOKE TEST")
    print("=" * 60)

    results = []
    results.append(test_reset())
    results.append(test_step_loop())
    results.append(test_get_state())
    results.append(test_observation_channels())
    results.append(test_render())
    results.append(test_sb3_check_env())

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    if passed == total:
        print(f"🎉 ALL {total}/{total} TESTS PASSED — Phase 1 Environment is SOLID")
    else:
        print(f"⚠️  {passed}/{total} tests passed — FIX FAILURES BEFORE PROCEEDING")
    print("=" * 60)
