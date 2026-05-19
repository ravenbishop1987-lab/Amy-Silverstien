from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_supabase
from app.routers import auth, conversations, memory, voice, stripe, embed, admin


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        settings.WIDGET_URL,
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )
