# CodeViva Deployment Guide

This guide explains how to deploy CodeViva to production.

## Architecture

CodeViva consists of two parts:
- **Frontend**: Next.js 15 + React 19 + TypeScript (deployed to Vercel)
- **Backend**: FastAPI + Python + PostgreSQL (deployed to Render/Railway)

---

## Part 1: Deploy Backend to Render (Recommended)

### Prerequisites
- A Render account (free tier available)
- A PostgreSQL database (Render provides free PostgreSQL)
- Your GitHub repository connected to Render

### Step 1: Prepare Backend for Deployment

1. **Create `backend/requirements.txt`** (already exists)
2. **Create `backend/Dockerfile`** (optional but recommended):

```dockerfile
FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

3. **Create `backend/.env.production`** (DO NOT commit this file):

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
ENVIRONMENT=production
JWT_SECRET=your-production-jwt-secret-min-32-chars
JWT_EXPIRE_MINUTES=480
TEACHER_INVITE_CODE=your-secure-teacher-code
AGNES_API_KEY=your-agnes-api-key
AGNES_API_BASE_URL=https://apihub.agnes-ai.com/v1
CODEVIVA_AI_MODE=live
CODEVIVA_AI_PROVIDER_PRACTICE=agnes
CODEVIVA_AI_PROVIDER_EXAM=agnes
CODEVIVA_AI_PROVIDER_GRADING=agnes
AGNES_MODEL=agnes-2.5-flash
MODEL_PRACTICE=agnes-2.5-flash
MODEL_EXAM=agnes-2.5-flash
ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app
COOKIE_SECURE=true
GENERATION_LEAD_MINUTES=30
CONFIDENCE_REVIEW_THRESHOLD=0.6
```

### Step 2: Deploy to Render

1. Go to [render.com](https://render.com) and sign up
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name**: codeviva-backend
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Runtime**: Python 3
   - **Instance Type**: Free (or paid for production)

5. Add Environment Variables (from `.env.production` above)
6. Deploy

### Step 3: Set Up PostgreSQL on Render

1. Click **New +** → **PostgreSQL**
2. Choose free tier
3. Copy the **Internal Database URL** to your `.env.production`
4. Add to Render web service environment variables

### Step 4: Run Database Migrations

Render doesn't automatically run migrations. You have two options:

**Option A: SSH into Render and run manually**
```bash
# Render dashboard → Web Service → SSH
cd /opt/render/project/src
python -m alembic upgrade head
```

**Option B: Add migration to startup** (modify `backend/app/main.py`):

```python
@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_runtime_settings(settings)
    # Run migrations on startup
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()
```

---

## Part 2: Deploy Frontend to Vercel

### Prerequisites
- A Vercel account (free tier available)
- Your GitHub repository connected to Vercel

### Step 1: Deploy to Vercel

1. Go to [vercel.com](https://vercel.com) and sign up
2. Click **Add New Project**
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)

5. Add Environment Variables:
   - `API_BASE_URL`: Your Render backend URL (e.g., `https://codeviva-backend.onrender.com`)
   - `NEXT_PUBLIC_API_BASE_URL`: Same as above (for client-side access)

6. Deploy

### Step 2: Update Next.js Config

The `frontend/next.config.js` already has the rewrites configured. Ensure the `API_BASE_URL` environment variable is set in Vercel.

### Step 3: Update Backend CORS

After deployment, update your backend's `ALLOWED_ORIGINS` in Render environment variables to include your Vercel domain:
```
ALLOWED_ORIGINS=https://your-project.vercel.app
```

---

## Part 3: Alternative Deployment Options

### Option A: Deploy Both to Railway

Railway supports both Python and Node.js on the same platform:

1. Create a `railway.json` in the root:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "bash start.sh",
    "healthcheckPath": "/health"
  }
}
```

2. Create `start.sh`:
```bash
#!/bin/bash
# Start backend in background
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
# Start frontend
cd ../frontend && npm run dev
```

### Option B: Deploy Backend to Vercel Serverless Functions

Convert FastAPI to serverless functions (more complex, not recommended for beginners).

### Option C: Self-Hosted (VPS)

Deploy both to a VPS (DigitalOcean, Linode, AWS EC2):

1. Use Docker Compose:
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/codecomp
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - API_BASE_URL=http://localhost:8000

  db:
    image: postgres:16
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=codecomp
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## Part 4: Post-Deployment Checklist

- [ ] Backend is accessible and health check returns 200
- [ ] Frontend loads and redirects correctly
- [ ] Student registration works
- [ ] Teacher registration works (with invite code)
- [ ] Code upload and AI question generation works
- [ ] Practice sessions generate questions
- [ ] Answer evaluation returns scores
- [ ] Database migrations ran successfully
- [ ] Environment variables are all set (no defaults in production)
- [ ] CORS is configured correctly
- [ ] Cookies are set with `secure=true` in production
- [ ] SSL/HTTPS is enabled (automatic on Vercel/Render)

---

## Part 5: Monitoring and Logs

### Backend (Render)
- Go to your web service → **Logs** tab
- Check for startup errors
- Monitor API response times

### Frontend (Vercel)
- Go to your project → **Deployments** → View logs
- Check build errors
- Monitor client-side errors in browser console

---

## Troubleshooting

### Backend won't start
- Check Render logs for missing environment variables
- Verify DATABASE_URL is correct
- Ensure all Python dependencies are in requirements.txt

### Frontend can't reach backend
- Check API_BASE_URL environment variable
- Verify CORS ALLOWED_ORIGINS includes your Vercel domain
- Check backend is running and accessible

### Database connection fails
- Verify DATABASE_URL format
- Check PostgreSQL is running
- Ensure database exists

### AI questions not generating
- Verify CODEVIVA_AI_MODE=live
- Check AGNES_API_KEY is valid
- Ensure AGNES_MODEL is set correctly
- Check backend logs for AI provider errors

---

## Cost Estimates

### Free Tier (Recommended for Development)
- **Render**: Free (Backend + PostgreSQL)
- **Vercel**: Free (Frontend)
- **Total**: $0/month

### Production (Recommended)
- **Render**: $7-25/month (Backend)
- **Render PostgreSQL**: $7-15/month
- **Vercel**: $0-20/month (Frontend, scales with usage)
- **Total**: ~$14-60/month

---

## Security Notes

1. **Never commit `.env` files** to Git
2. **Use strong JWT secrets** in production (min 32 characters)
3. **Enable `COOKIE_SECURE=true`** in production
4. **Use strong teacher invite codes**
5. **Rotate API keys regularly**
6. **Enable rate limiting** (already configured in backend)
7. **Keep dependencies updated**
8. **Monitor logs for suspicious activity**

---

## Support

If you encounter issues:
1. Check the logs on both platforms
2. Verify all environment variables are set
3. Test locally with production-like settings first
4. Consult platform documentation:
   - [Render Docs](https://render.com/docs)
   - [Vercel Docs](https://vercel.com/docs)
