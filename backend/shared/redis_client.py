import os
import redis
from typing import Optional

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_CHANNELS = {
    "sensor_data": "waterwheel:sensor_data",
    "mechanics_result": "waterwheel:mechanics_result",
    "irrigation_result": "waterwheel:irrigation_result",
    "alarm": "waterwheel:alarm",
}

_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client

def publish(channel_key: str, message: str) -> int:
    r = get_redis_client()
    channel = REDIS_CHANNELS.get(channel_key, channel_key)
    return r.publish(channel, message)

def get_pubsub() -> redis.client.PubSub:
    r = get_redis_client()
    return r.pubsub()
