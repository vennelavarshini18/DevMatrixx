

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import numpy as np
from env import WarehouseEnv
from env.core_classes import (
    Agent, Goal, StaticObstacle, PatrolObstacle, RandomWalkObstacle, CurriculumTracker
)


def test_reward_closer():
    """Moving closer to goal should yield positive distance reward."""
    env = WarehouseEnv(grid_size=15)
    env.reset(seed=100)

    # Force agent at (0,0), goal at (14,14) — so any right/down move is good
    env.agent.set_position(0, 0)
    env.goal.x, env.goal.y = 14, 14
    env.prev_distance = env._manhattan_distance()  # 28

    # Move Right (action=3): x goes 0->1, distance 28->27, delta=+1
    _, reward, terminated, _, _ = env.step(3)
    # Expected: +1 * 0.1 (closer) + -0.01 (step penalty) = +0.09
    assert not terminated, "Should not terminate on empty room move"
    assert reward > 0, f"Moving closer should give positive reward, got {reward}"
    print(f"✅ test_reward_closer PASSED — reward: {reward:.4f} (expected ~+0.09)")


def test_reward_away():
    """Moving away from goal should yield negative distance reward."""
    env = WarehouseEnv(grid_size=15)
    env.reset(seed=100)

    # Force agent at (5,5), goal at (14,14)
    env.agent.set_position(5, 5)
    env.goal.x, env.goal.y = 14, 14
    env.prev_distance = env._manhattan_distance()  # 18

    # Move Left (action=2): x goes 5->4, distance 18->19, delta=-1
    _, reward, _, _, _ = env.step(2)
    # Expected: -1 * 0.1 (farther) + -0.01 (step penalty) = -0.11
    assert reward < 0, f"Moving away should give negative reward, got {reward}"
    print(f"✅ test_reward_away PASSED — reward: {reward:.4f} (expected ~-0.11)")


def test_collision_penalty():
    """Hitting an obstacle should give -10 and end the episode."""
    env = WarehouseEnv(grid_size=15)
    env.reset(seed=42)

    # Force Stage 2 and manually place an obstacle
    env.curriculum.current_stage = 2
    env.obstacles = [StaticObstacle("test_obs", 5, 5)]

    # Place agent right next to obstacle
    env.agent.set_position(4, 5)
    env.goal.x, env.goal.y = 14, 14
    env.prev_distance = env._manhattan_distance()

    # Move Right (action=3) — should hit obstacle at (5,5)
    _, reward, terminated, _, _ = env.step(3)
    assert terminated, "Should terminate on collision"
    assert reward <= -10, f"Collision should give -10 penalty, got {reward}"
    assert env.agent.status == "collided", f"Status should be 'collided', got '{env.agent.status}'"
    print(f"✅ test_collision_penalty PASSED — reward: {reward:.2f}, status: {env.agent.status}")


def test_goal_reward():
    """Reaching the goal should give +100 and end the episode."""
    env = WarehouseEnv(grid_size=15)
    env.reset(seed=42)

    # Place agent one step away from goal
    env.agent.set_position(13, 14)
    env.goal.x, env.goal.y = 14, 14
    env.prev_distance = env._manhattan_distance()  # 1

    # Move Right (action=3) — should reach goal
    _, reward, terminated, _, _ = env.step(3)
    assert terminated, "Should terminate on reaching goal"
    assert reward >= 99, f"Goal reward should be ~100, got {reward}"
    assert env.agent.status == "reached_goal", f"Status should be 'reached_goal', got '{env.agent.status}'"
    print(f"✅ test_goal_reward PASSED — reward: {reward:.2f}, status: {env.agent.status}")


def test_wall_bounce():
    """Hitting a wall should give -1 and keep agent in place."""
    env = WarehouseEnv(grid_size=15)
    env.reset(seed=42)

    # Place agent at edge
    env.agent.set_position(0, 0)
    env.goal.x, env.goal.y = 14, 14
    env.prev_distance = env._manhattan_distance()

    # Move Up (action=0) while at y=0 — should bounce
    _, reward, terminated, _, _ = env.step(0)
    assert not terminated, "Wall bounce should not terminate"
    assert env.agent.x == 0 and env.agent.y == 0, "Agent should stay at (0,0)"
    assert env.agent.status == "blocked", f"Status should be 'blocked', got '{env.agent.status}'"
    # Wall penalty is -1.0 + step penalty -0.01 = -1.01
    assert reward < -0.5, f"Wall hit should be punished, got {reward}"
    print(f"✅ test_wall_bounce PASSED — reward: {reward:.2f}, agent stayed at (0,0)")


def test_curriculum_auto_advance():
    """CurriculumTracker should advance from Stage 1 to Stage 2 at 90% success."""
    tracker = CurriculumTracker(window_size=10, advance_threshold=0.90)
    assert tracker.current_stage == 1

    # Record 9 successes out of 10
    for _ in range(9):
        tracker.record(True)
    tracker.record(False)  # 10th is failure -> 90% exactly
    assert tracker.success_rate == 0.9
    advanced = tracker.try_advance()
    assert advanced, "Should advance at exactly 90%"
    assert tracker.current_stage == 2
    assert len(tracker.history) == 0, "History should reset after advancing"

    print(f"✅ test_curriculum_auto_advance PASSED — Stage 1 -> Stage 2 at 90%")


def test_curriculum_no_premature_advance():
    """Should NOT advance before window is full."""
    tracker = CurriculumTracker(window_size=100, advance_threshold=0.90)

    # Record 50 successes (only 50% of window filled)
    for _ in range(50):
        tracker.record(True)
    assert tracker.success_rate == 1.0  # All successes so far
    assert not tracker.should_advance(), "Should not advance with incomplete window"

    print(f" test_curriculum_no_premature_advance PASSED — Blocked until window full")


def test_stage2_spawns_obstacles():
    """Stage 2 should spawn all 3 types of obstacles."""
    env = WarehouseEnv(grid_size=15)
    env.reset(seed=42)

    # Force Stage 2
    env.curriculum.current_stage = 2
    env.reset(seed=42)

    assert len(env.obstacles) > 0, "Stage 2 should spawn obstacles"
    types_present = {obs.type for obs in env.obstacles}
    assert "static" in types_present, "Stage 2 should have static obstacles"
    assert "patrol" in types_present, "Stage 2 should have patrol obstacles"
    assert "random_walk" in types_present, "Stage 2 should have random_walk obstacles"

    # Verify correct counts
    static_count = sum(1 for o in env.obstacles if o.type == "static")
    patrol_count = sum(1 for o in env.obstacles if o.type == "patrol")
    random_count = sum(1 for o in env.obstacles if o.type == "random_walk")
    assert static_count == 5, f"Expected 5 static, got {static_count}"
    assert patrol_count == 3, f"Expected 3 patrol, got {patrol_count}"
    assert random_count == 2, f"Expected 2 random, got {random_count}"

    print(f"✅ test_stage2_spawns_obstacles PASSED — {len(env.obstacles)} obstacles "
          f"(static={static_count}, patrol={patrol_count}, random={random_count})")


def test_patrol_obstacle_moves():
    """Patrol obstacle should bounce along its waypoints."""
    waypoints = [(3, 3), (4, 3), (5, 3)]
    patrol = PatrolObstacle("p_test", waypoints, speed=1)
    assert patrol.x == 3 and patrol.y == 3, "Should start at first waypoint"

    positions = [(patrol.x, patrol.y)]
    for step in range(1, 10):
        patrol.update(step, 15, set())
        positions.append((patrol.x, patrol.y))

    # Should have moved from (3,3) through the waypoints
    unique_positions = set(positions)
    assert len(unique_positions) >= 2, f"Patrol should move, visited: {unique_positions}"
    # All positions should be on the waypoint path
    for pos in unique_positions:
        assert pos in waypoints, f"Patrol went off-path: {pos} not in {waypoints}"

    print(f"✅ test_patrol_obstacle_moves PASSED — visited {len(unique_positions)} unique positions: {unique_positions}")


def test_random_walk_moves():
    """RandomWalk obstacle should change position over time."""
    rw = RandomWalkObstacle("r_test", 7, 7)
    initial_pos = (rw.x, rw.y)

    positions = set()
    positions.add(initial_pos)
    for step in range(50):
        rw.update(step, 15, set())
        positions.add((rw.x, rw.y))

    assert len(positions) > 1, "RandomWalk should move at least once in 50 steps"
    print(f"✅ test_random_walk_moves PASSED — visited {len(positions)} unique positions")


def test_get_state_stage2():
    """get_state() should return full obstacle info in Stage 2."""
    env = WarehouseEnv(grid_size=15)
    env.curriculum.current_stage = 2
    env.reset(seed=42)
    env.step(1)

    state = env.get_state()

    # Validate JSON
    json_str = json.dumps(state)
    assert len(json_str) > 100, "Stage 2 state should be richer than empty room"

    # Obstacles should be present
    assert len(state["obstacles"]) == 10, f"Expected 10 obstacles, got {len(state['obstacles'])}"

    # Each obstacle should have id, x, y, type
    for obs in state["obstacles"]:
        assert "id" in obs, "Obstacle missing 'id'"
        assert "x" in obs, "Obstacle missing 'x'"
        assert "y" in obs, "Obstacle missing 'y'"
        assert "type" in obs, "Obstacle missing 'type'"
        assert obs["type"] in ("static", "patrol", "random_walk"), f"Bad type: {obs['type']}"

    # Patrol obstacles should have dx, dy
    patrols = [o for o in state["obstacles"] if o["type"] == "patrol"]
    for p in patrols:
        assert "dx" in p and "dy" in p, f"Patrol {p['id']} missing dx/dy"

    print(f"✅ test_get_state_stage2 PASSED — {len(state['obstacles'])} obstacles in JSON ({len(json_str)} chars)")


def test_full_stress_run():
    """Run 5000 steps with curriculum advancement — nothing should crash."""
    env = WarehouseEnv(grid_size=15)
    # Use smaller window so we can actually see stage advancement
    env.curriculum = CurriculumTracker(window_size=20, advance_threshold=0.90)
    obs, info = env.reset(seed=42)

    total_steps = 0
    total_episodes = 0
    total_goals = 0
    total_collisions = 0
    max_stage_reached = 1
    stage_transitions = []

    for _ in range(5000):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_steps += 1

        assert obs.shape == (3, 15, 15)
        assert not np.isnan(reward), f"NaN reward at step {total_steps}!"
        assert not np.isinf(reward), f"Inf reward at step {total_steps}!"

        if env.curriculum.current_stage > max_stage_reached:
            max_stage_reached = env.curriculum.current_stage
            stage_transitions.append((total_steps, max_stage_reached))

        if terminated or truncated:
            total_episodes += 1
            if env.agent.status == "reached_goal":
                total_goals += 1
            elif env.agent.status == "collided":
                total_collisions += 1
            obs, info = env.reset()

    print(f"✅ test_full_stress_run PASSED")
    print(f"   Steps: {total_steps}, Episodes: {total_episodes}")
    print(f"   Goals: {total_goals}, Collisions: {total_collisions}")
    print(f"   Max Stage: {max_stage_reached}")
    if stage_transitions:
        for step, stage in stage_transitions:
            print(f"   → Stage {stage} unlocked at step {step}")
    else:
        print(f"   (No stage transitions — random agent not good enough, expected)")


def test_observation_consistency():
    """Observation channels should match actual entity positions."""
    env = WarehouseEnv(grid_size=15)
    env.curriculum.current_stage = 2
    env.reset(seed=99)

    for _ in range(50):
        obs, _, terminated, truncated, _ = env.step(env.action_space.sample())
        if terminated or truncated:
            obs, _ = env.reset()
            continue

        # Channel 1 (agent) — exactly one cell lit at agent's actual position
        agent_cells = np.argwhere(obs[1] == 255)
        assert len(agent_cells) == 1, f"Agent channel has {len(agent_cells)} cells lit"
        assert agent_cells[0][0] == env.agent.y and agent_cells[0][1] == env.agent.x, \
            f"Agent channel ({agent_cells[0]}) != actual pos ({env.agent.y}, {env.agent.x})"

        # Channel 2 (goal) — exactly one cell lit at goal's actual position
        goal_cells = np.argwhere(obs[2] == 255)
        assert len(goal_cells) == 1
        assert goal_cells[0][0] == env.goal.y and goal_cells[0][1] == env.goal.x

        # Channel 0 (obstacles) — count should match actual obstacle count
        obs_cells = np.sum(obs[0] == 255)
        # Could be slightly off if two obstacles share a cell momentarily
        assert obs_cells <= len(env.obstacles), f"More obstacle cells ({obs_cells}) than obstacles ({len(env.obstacles)})"

    print("✅ test_observation_consistency PASSED — obs channels match entity positions")


if __name__ == "__main__":
    print("=" * 60)
    print("ML1 PHASE 2+3 — CURRICULUM, REWARDS & OBSTACLES")
    print("=" * 60)

    tests = [
        test_reward_closer,
        test_reward_away,
        test_collision_penalty,
        test_goal_reward,
        test_wall_bounce,
        test_curriculum_auto_advance,
        test_curriculum_no_premature_advance,
        test_stage2_spawns_obstacles,
        test_patrol_obstacle_moves,
        test_random_walk_moves,
        test_get_state_stage2,
        test_observation_consistency,
        test_full_stress_run,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED — {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    if failed == 0:
        print(f"🎉 ALL {passed}/{passed} TESTS PASSED — Phase 2+3 VALIDATED")
    else:
        print(f"⚠️  {passed}/{passed + failed} passed, {failed} FAILED")
    print("=" * 60)
