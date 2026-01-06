import os, json, redis
from dotenv import load_dotenv
load_dotenv()

_redis = redis.from_url(os.getenv("REDIS_URL","redis://localhost:6379/0"), decode_responses=True)

def cache_get(k: str):
    return _redis.get(k)

def cache_set(k: str, v, ttl=60):
    _redis.setex(k, ttl, json.dumps(v))
