import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings
from app.database import init_supabase
from app.routers import auth, conversations, memory, voice, stripe, embed, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Origins allowed for CORS — kept as a frozenset so the safety-net middleware
# can use it independently of FastAPI's CORSMiddleware.
_CORS_ORIGINS: frozenset[str] = frozenset({
    "https://amy-silverstien-1.onrender.com",
    "https://amy-silverstien.onrender.com",
    "https://amy-silverstien-backend.onrender.com",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
})


class _GuaranteeCORSMiddleware:
    """
    Outermost raw-ASGI safety net.

    Starlette's ServerErrorMiddleware (added automatically by uvicorn/starlette)
    sends a raw 500 using the un-wrapped `send` channel when an exception
    escapes the entire app stack, which means CORSMiddleware never adds its
    headers and the browser sees a CORS-blocked response.

    This middleware sits OUTSIDE CORSMiddleware. If any exception escapes the
    FastAPI stack (including CORSMiddleware itself), we catch it here and
    return a proper JSON 500 WITH CORS headers before ServerErrorMiddleware
    can interfere.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def _tracked_send(message: dict) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, _tracked_send)
        except Exception as exc:
            logger.exception(f"Exception escaped FastAPI stack: {exc}")
            if response_started:
                return  # headers already sent — can't send another response

            req_headers = dict(scope.get("headers", []))
            origin = req_headers.get(b"origin", b"").decode("utf-8", errors="replace")

            raw_headers: list[tuple[bytes, bytes]] = [(b"content-type", b"application/json")]
            if origin in _CORS_ORIGINS or origin.endswith(".onrender.com"):
                raw_headers += [
                    (b"access-control-allow-origin", origin.encode()),
                    (b"access-control-allow-credentials", b"true"),
                    (b"vary", b"origin"),
                ]

            body = b'{"detail":"Internal server error"}'
            raw_headers.append((b"content-length", str(len(body)).encode()))

            await send({"type": "http.response.start", "status": 500, "headers": raw_headers})
            await send({"type": "http.response.body", "body": body, "more_body": False})


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_supabase()
    yield


app = FastAPI(
    title="Amy Chatbot API",
    description="AI dating advice companion with persistent memory",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
# Order matters: add_middleware() is LIFO — the LAST call becomes the outermost.
# We want:  _GuaranteeCORSMiddleware (outermost) → CORSMiddleware → FastAPI internals

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_CORS_ORIGINS) + [settings.FRONTEND_URL, settings.WIDGET_URL],
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Added LAST → becomes OUTERMOST (wraps CORSMiddleware)
app.add_middleware(_GuaranteeCORSMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(memory.router)
app.include_router(voice.router)
app.include_router(stripe.router)
app.include_router(embed.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")

    # Also add CORS headers here as a second layer of defence — in case the
    # exception was caught by ExceptionMiddleware but the CORS-wrapped send
    # was somehow bypassed.
    origin = request.headers.get("origin", "")
    extra_headers: dict[str, str] = {}
    if origin in _CORS_ORIGINS or origin.endswith(".onrender.com"):
        extra_headers["access-control-allow-origin"] = origin
        extra_headers["access-control-allow-credentials"] = "true"
        extra_headers["vary"] = "origin"

    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
        headers=extra_headers or None,
    )
