import asyncio
import websockets

async def test():
    try:
        async with websockets.connect("ws://localhost:8000/ws") as ws:
            print("Connected!")
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print("Received:", msg[:100], "...")
    except Exception as e:
        print("Error:", e)

asyncio.run(test())
