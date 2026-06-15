from __future__ import annotations

import json
from uuid import UUID

from redis.asyncio import Redis


class RedisSessionMemoryStore:
    def __init__(self, redis: Redis, *, key_prefix: str = "session") -> None:
        self._redis = redis
        self._key_prefix = key_prefix

    async def get_session(self, user_id: UUID, session_id: str) -> dict[str, object] | None:
        raw_value = await self._redis.get(self._key(user_id, session_id))
        if raw_value is None:
            return None

        if isinstance(raw_value, bytes):
            raw_value = raw_value.decode("utf-8")

        decoded = json.loads(raw_value)
        if not isinstance(decoded, dict):
            raise ValueError("stored session payload must be a JSON object")
        return decoded

    async def set_session(
        self,
        user_id: UUID,
        session_id: str,
        value: dict[str, object],
        ttl_seconds: int,
    ) -> None:
        if not session_id.strip():
            raise ValueError("session_id is required")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        await self._redis.set(
            self._key(user_id, session_id),
            json.dumps(value),
            ex=ttl_seconds,
        )

    async def clear_session(self, user_id: UUID, session_id: str) -> None:
        await self._redis.delete(self._key(user_id, session_id))

    def _key(self, user_id: UUID, session_id: str) -> str:
        return f"{self._key_prefix}:{user_id}:{session_id}"
