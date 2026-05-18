# Amy Silverstein — The ADHD Girl Next Door

An AI companion and ADHD coach with a warm, Southern personality. Amy feels like a trusted friend sitting across the kitchen table — she listens without judgment, helps untangle the chaos of ADHD life, and gives you one doable next step at a time.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python), WebSocket streaming |
| AI | Anthropic Claude (Sonnet) |
| Database | PostgreSQL (Supabase-ready) |
| Cache / Queue | Redis + Celery |
| Voice | ElevenLabs TTS + OpenAI Whisper STT |
| Payments | Stripe subscriptions + credits |
| Frontend | React + Vite + Tailwind CSS |
| Widget | Embeddable React widget (Vite build) |
| Vector DB | Pinecone (memory bank) |

---

## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.11+
- Node.js 18+

### 1. Clone & configure environment

```bash
git clone <your-repo-url>
cd amy-chatbot
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `backend/.env` and fill in your API keys (see [Environment Variables](#environment-variables) below).

### 2. Start databases

```bash
docker-compose up postgres redis -d
```

### 3. Start everything

Double-click **`start.bat`** — it starts Docker, the backend, and the frontend in separate windows.

Or manually:

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## Environment Variables

### `backend/.env`

```env
# App
APP_NAME=Amy Chatbot
SECRET_KEY=                        # python -c "import secrets; print(secrets.token_hex(32))"
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173

# Database
DATABASE_URL=postgresql+asyncpg://amy_user:amy_password@localhost:5432/amy_chatbot

# Redis
REDIS_URL=redis://localhost:6379/0

# Anthropic / Claude
ANTHROPIC_API_KEY=sk-ant-...

# ElevenLabs (voice)
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=               # Amy's voice ID from elevenlabs.io

# OpenAI (Whisper STT)
OPENAI_API_KEY=sk-...

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PREMIUM_MONTHLY=price_...
STRIPE_PRICE_CREDITS_SINGLE=price_...
STRIPE_PRICE_CREDITS_BULK=price_...

# Pinecone (memory vector search)
PINECONE_API_KEY=
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=amy-memories

# Limits
FREE_DAILY_CONVERSATIONS=3
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### `frontend/.env`

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## Features

- **Streaming chat** — real-time responses over WebSocket
- **Memory bank** — Amy remembers past conversations, patterns, wins, and sensitivities
- **Voice mode** — ElevenLabs TTS output + Whisper speech-to-text input
- **Subscriptions** — free tier, credits, and premium via Stripe
- **Embeddable widget** — drop Amy into any website with a `<script>` tag
- **Admin dashboard** — analytics and user management

---

## Database

The schema lives in [`schema.sql`](schema.sql). Run it in Supabase's SQL Editor or against any PostgreSQL 16 instance to create all tables.

For local development, the FastAPI app auto-creates tables on startup via SQLAlchemy.

To test your database connection:

```bash
cd backend
python test_db.py
```

---

## Stripe Webhooks (local testing)

```bash
stripe listen --forward-to localhost:8000/stripe/webhook
```

Copy the printed webhook secret into `STRIPE_WEBHOOK_SECRET` in `backend/.env`.

---

## Build the Embeddable Widget

```bash
cd widget
npm install
npm run build
```

Output: `frontend/public/widget.js` — reference this in the embed `<script>` tag.

---

## Deployment

| Service | Recommended Platform |
|---|---|
| Backend | Railway, Render, or Fly.io |
| Frontend | Vercel (point at `/frontend`) |
| Database | Supabase or Railway Postgres |
| Redis | Upstash or Railway Redis |

Set all environment variables in your deployment dashboard. The Docker Compose file includes a full containerized stack for self-hosted deployments.

---

## Project Structure

```
amy-chatbot/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy models
│   │   ├── routers/         # FastAPI route handlers
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Claude, ElevenLabs, Stripe, memory
│   │   └── utils/           # Auth, filters
│   ├── alembic/             # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── stores/
├── widget/                  # Embeddable widget build
├── schema.sql               # Full PostgreSQL schema
├── docker-compose.yml
└── start.bat                # One-click dev launcher (Windows)
```
