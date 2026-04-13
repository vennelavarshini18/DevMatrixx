import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from mock_data import get_mock_frames

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    frames = get_mock_frames()
    try:
        while True:
            for frame in frames:
                await websocket.send_text(json.dumps(frame))
                await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
