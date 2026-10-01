from fastapi import HTTPException

from .config import settings


class BodyLimitMiddleware:
    """Enforce limits while receiving chunked bodies, not just Content-Length."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        received = 0
        maximum = settings().max_upload_mb * 3 * 1024 * 1024 + 16384

        async def bounded_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > maximum:
                    raise HTTPException(413, "Upload exceeds the total request size limit")
            return message

        await self.app(scope, bounded_receive, send)
