# Prompt Processing System with React Dashboard

This repository now includes both the backend processing system and a React dashboard.

## Included features

### Backend
- FastAPI REST API
- Celery workers for durable parallel processing
- Redis broker and global rate limiter
- PostgreSQL job storage
- Semantic caching with similarity threshold
- Recovery of stale processing jobs after worker crashes

### Frontend dashboard
- React dashboard built with Vite
- Live request progress bars
- Request history table
- Rate limit visualization
- Cache hit indicator for current and historical jobs

## Architecture

```text
React Dashboard (Vite)
        |
        v
   FastAPI API  ------------------> PostgreSQL
        |
        +-------------------------> Redis
        |
        v
 Celery Workers  -----------------> LLM Provider / Mock Provider
```

## API endpoints

- `POST /prompts` submit a prompt
- `GET /jobs/{job_id}` get one job
- `GET /jobs?limit=20` get recent jobs
- `GET /dashboard/metrics` get dashboard counters and rate-limit usage
- `GET /health` health check

## Run the backend

### 1. Copy env file

```bash
cp .env.example .env
```

### 2. Start services

```bash
docker compose up --build
```

### 3. Initialize database

In a second terminal:

```bash
docker compose exec api python scripts/init_db.py
```

### 4. Open the API docs

```text
http://localhost:8000/docs
```

## Run the frontend

Open a new terminal and run:

```bash
cd frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

## Dashboard walkthrough

### Submit a prompt
Type any prompt into the textarea and click **Submit request**.

### Progress bars
The live request panel shows progress through stages:
- queued
- checking cache
- rate limit wait
- provider call
- saving response
- completed

### Request history
The table shows the latest 20 jobs. Click any row to inspect it in the live request panel.

### Rate limit visualization
The dashboard shows current requests used in the active Redis minute window, the remaining capacity, and seconds until reset.

### Cache hit indicator
Completed requests show one of two badges:
- `Cache hit`
- `Fresh call`



