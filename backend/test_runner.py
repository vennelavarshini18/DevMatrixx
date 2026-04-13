import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ml.inference import InferenceRunner

CHECKPOINT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "ml",
        "checkpoints",
        "OVERNIGHT_BAKE_20260413_004249_best",
        "best_model.zip"
    )
)

async def test_runner():
    try:
        runner = InferenceRunner(
            checkpoint_path=CHECKPOINT_PATH,
            grid_size=15,
            max_steps=200,
            use_real_env=True,
            step_delay=0.1
        )
        print("Runner initialized!")
        
        async for state in runner.run_episode():
            print("Got state!")
            break
            
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test_runner())
