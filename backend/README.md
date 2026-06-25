---
title: ForensicX Backend
emoji: 🔬
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
---

# ForensicX Backend

FastAPI service for the ForensicX forensic image-enhancement web app
(forensic analysis + super-resolution model comparison).

This Space is built from the `Dockerfile` in this repo and serves the API on
port `8000`. The React frontend is deployed separately (Vercel) and points at
this Space's URL via its `VITE_API_BASE` environment variable.

## Configuration (Space → Settings → Variables and secrets)

| Name | Example | Notes |
|------|---------|-------|
| `JWT_SECRET` | (64-char random hex) | **Secret.** Signs auth tokens. |
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app` | CORS allowlist (comma-separated). |
| `MODEL_DEVICE` | `cpu` | This Space runs on CPU. |

## Health check

`GET /health` → `{"status": "ok"}`
