import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
import json

from app.core.config import settings

router = APIRouter(prefix="/ws", tags=["websockets"])

@router.websocket("/meetings/{meeting_id}")
async def websocket_endpoint(websocket: WebSocket, meeting_id: int):
    await websocket.accept()
    print(f"Client connected to WebSocket for meeting {meeting_id}")

    # Async connection to Redis Pub/Sub
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    channel_name = f"meeting_progress_{meeting_id}"
    
    await pubsub.subscribe(channel_name)

    try:
        while True:
            # Yield loop control and poll for Redis Pub/Sub messages
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                data = json.loads(message["data"])
                await websocket.send_json(data)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print(f"Client disconnected from WebSocket for meeting {meeting_id}")
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()
        await r.close()
