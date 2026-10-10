# Quick Deployment Guide (Vercel + Render)

This is the fastest way to get CodeViva running in production.

---

## 1. Deploy Backend to Render (10 minutes)

### Step 1: Prepare your repository
```bash
git add .
git commit -m "Add deployment configuration"
git push origin main
```

### Step 2: Set up PostgreSQL on Render
1. Go to [render.com](https://render.com) → Sign up
2. Click **New +** → **PostgreSQL**
3. Name: `codeviva-db`
4. Choose **Free** tier
5. Click **Create**
6. Copy the **Internal Database URL** (save it for later)

### Step 3: Deploy Backend
1. Click **New +** → **Web Service**
2. Connect your GitHub repository (select the new repo you just pushed to)
3. Configure:
   - **Name**: `codeviva-backend`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free

4. Add Environment Variables (from your backend/.env, but use production values):
   ```
   DATABASE_URL = [paste from Step 2]
   ENVIRONMENT = production
   JWT_SECRET = [generate a long random string, min 32 chars]
   JWT_EXPIRE_MINUTES = 480
   TEACHER_INVITE_CODE = AtriaTeacher2026
   AGNES_API_KEY = [your Agnes API key]
   AGNES_API_BASE_URL = https://apihub.agnes-ai.com/v1
   CODEVIVA_AI_MODE = live
   CODEVIVA_AI_PROVIDER_PRACTICE = agnes
   CODEVIVA_AI_PROVIDER_EXAM = agnes
   CODEVIVA_AI_PROVIDER_GRADING = agnes
   AGNES_MODEL = agnes-2.5-flash
   MODEL_PRACTICE = agnes-2.5-flash
   MODEL_EXAM = agnes-2.5-flash
   ALLOWED_ORIGINS = https://your-frontend-domain.vercel.app
   COOKIE_SECURE = true
   GENERATION_LEAD_MINUTES = 30
   CONFIDENCE_REVIEW_THRESHOLD = 0.6
   ```

5. Click **Create Web Service**
6. Wait for deployment (~2-3 minutes)
7. Copy the backend URL (e.g., `https://codeviva-backend.onrender.com`)

### Step 4: Run Database Migrations
1. Go to your backend service on Render
2. Click **SSH** → **Connect**
3. Run:
```bash
cd /opt/render/project/src
python -m alembic upgrade head
```

---

## 2. Deploy Frontend to Vercel (5 minutes)

### Step 1: Deploy to Vercel
1. Go to [vercel.com](https://vercel.com) → Sign up
2. Click **Add New Project**
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`

5. Add Environment Variables:
   ```
   API_BASE_URL = [paste your Render backend URL from Step 3]
   NEXT_PUBLIC_API_BASE_URL = [same as above]
   ```

6. Click **Deploy**
7. Wait for deployment (~1-2 minutes)
8. Copy the frontend URL (e.g., `https://codeviva.vercel.app`)

### Step 2: Update Backend CORS
1. Go back to Render → Backend service
2. Click **Environment**
3. Update `ALLOWED_ORIGINS`:
   ```
   ALLOWED_ORIGINS = https://codeviva.vercel.app
   ```
4. Click **Save Changes** (this will redeploy)

---

## 3. Test Your Deployment

### Test Backend
```bash
curl https://codeviva-backend.onrender.com/health
# Should return: {"status":"ok","service":"codeviva-api"}
```

### Test Frontend
1. Open your Vercel URL in browser
2. Try student registration
3. Try code upload and AI question generation

---

## 4. Common Issues & Fixes

### Issue: Backend won't start
**Fix**: Check Render logs for missing environment variables

### Issue: Frontend can't reach backend
**Fix**: 
- Verify `API_BASE_URL` in Vercel environment variables
- Update `ALLOWED_ORIGINS` in Render to include your Vercel domain

### Issue: Database connection fails
**Fix**: Verify `DATABASE_URL` format in Render environment variables

### Issue: AI questions not generating
**Fix**: 
- Verify `CODEVIVA_AI_MODE=live`
- Check `AGNES_API_KEY` is valid
- Check backend logs for AI errors

---

## 5. Cost

- **Render (Free)**: $0/month (Backend + PostgreSQL)
- **Vercel (Free)**: $0/month (Frontend)
- **Total**: $0/month for development

For production, upgrade to paid tiers:
- **Render**: ~$7-25/month
- **Vercel**: ~$0-20/month (scales with traffic)

---

## 6. Next Steps

1. ✅ Test all user flows (registration, login, code upload, practice)
2. ✅ Monitor logs on both platforms
3. ✅ Set up custom domains (optional)
4. ✅ Configure error tracking (Sentry, etc.)
5. ✅ Set up CI/CD (automated testing on push)

---

## Need Help?

- [Render Documentation](https://render.com/docs)
- [Vercel Documentation](https://vercel.com/docs)
- Check logs in both platforms for errors
