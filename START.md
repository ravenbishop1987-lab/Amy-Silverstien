# Amy Chatbot — Start Guide

## Prerequisites
- Docker Desktop (for PostgreSQL + Redis)
- Python 3.11+
- Node.js 18+

---

## 1. Configure API Keys

Edit `backend/.env` and fill in:
- `ANTHROPIC_API_KEY` — get at console.anthropic.com
- `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` — get at elevenlabs.io
- `OPENAI_API_KEY` — for Whisper speech-to-text
- `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` + price IDs — get at dashboard.stripe.com
- `SECRET_KEY` — generate with: `python -c "import secrets; print(secrets.token_hex(32))"`

---

## 2. Start Database + Redis (Docker)

```bash
docker-compose up postgres redis -d
```

---

## 3. Start Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The FastAPI app auto-creates all tables on startup.
API docs available at: http://localhost:8000/docs

---

## 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at: http://localhost:5173

---

## 5. Build Widget (optional)

```bash
cd widget
npm install
npm run build
```

The widget.js bundle is output to `frontend/public/widget.js`.

---

## Stripe Webhook (local testing)

Install Stripe CLI and forward webhooks:
```bash
stripe listen --forward-to localhost:8000/stripe/webhook
```
Copy the webhook secret it gives you into `STRIPE_WEBHOOK_SECRET` in `.env`.

---

## Deployment

**Backend**: Deploy to Railway, Render, or Fly.io
**Frontend**: Deploy to Vercel (connect the `/frontend` folder)
**Database**: Railway Postgres or Supabase
**Redis**: Railway Redis or Upstash

Set all environment variables in your deployment dashboard.

---

## Phase Roadmap

| Phase | What's Built | Status |
|-------|-------------|--------|
| 1 | Text chat, memory bank, auth, subscriptions | ✅ Built |
| 2 | Voice (11 Labs), Whisper STT, embeddable widget | ✅ Built (needs API keys) |
| 3 | Credits model, admin analytics, YouTube vector search | ✅ Scaffolded |
| 4 | Mobile app, marketing push | Future |
