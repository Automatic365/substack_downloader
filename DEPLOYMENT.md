# Deployment Guide 🚀

## Quick Start - Deploy in 5 Minutes

### Option 1: Streamlit Cloud (Easiest, FREE)

**Perfect for your Streamlit web interface**

1. **Go to Streamlit Cloud**
   ```
   https://share.streamlit.io
   ```

2. **Sign in with GitHub**

3. **Click "New app"**

4. **Configure:**
   - Repository: `Automatic365/substack_downloader`
   - Branch: `flamboyant-shockley`
   - Main file path: `app.py`

5. **Add environment variables** (optional):
   - `SUBSTACK_LOG_LEVEL` = `INFO`
   - `SUBSTACK_MAX_WORKERS` = `3`

6. **Click "Deploy"**

7. **Wait 2-3 minutes** ⏳

8. **Done!** Your app is live at: `https://your-app.streamlit.app` 🎉

---

### Option 2: Render (More Control, FREE)

**Good for API or background jobs**

1. **Go to Render**
   ```
   https://render.com
   ```

2. **Sign up with GitHub**

3. **New → Web Service**

4. **Connect repository:**
   - Select: `Automatic365/substack_downloader`
   - Branch: `flamboyant-shockley`

5. **Render will auto-detect `render.yaml`**

6. **Click "Create Web Service"**

7. **App will deploy automatically**

---

### Option 3: Railway (Quick Deploy, $5 FREE)

1. **Go to Railway**
   ```
   https://railway.app
   ```

2. **Sign in with GitHub**

3. **New Project → Deploy from GitHub**

4. **Select your repository**

5. **Add environment variables:**
   ```
   SUBSTACK_LOG_LEVEL=INFO
   SUBSTACK_MAX_WORKERS=3
   ```

6. **Deploy!**

---

## Environment Variables

### Required
None! App works out of the box.

### Optional (Recommended for Production)
```bash
SUBSTACK_LOG_LEVEL=INFO           # Logging level
SUBSTACK_MAX_WORKERS=3            # Concurrent downloads (lower for free tier)
SUBSTACK_ENABLE_CACHE=false       # Disable caching in production
SUBSTACK_TIMEOUT=60               # Request timeout (seconds)
SUBSTACK_MAX_RETRIES=5            # Retry attempts
SUBSTACK_RATE_LIMIT_DELAY=1.0     # Delay between requests
```

### For Authentication (Paywalled Content)
```bash
SUBSTACK_COOKIE=your-cookie-here  # Set in deployment settings, NOT in code!
```

---

## Platform Comparison

| Platform | Free Tier | Best For | Setup Time | Uptime |
|----------|-----------|----------|------------|--------|
| **Streamlit Cloud** | ✅ Unlimited | Web UI | 5 min | 99% |
| **Render** | ✅ 750h/mo | Full app | 10 min | 99% |
| **Railway** | ✅ $5 credit/mo | Testing | 5 min | 99% |
| **Fly.io** | ✅ 3 VMs | CLI/API | 20 min | 99.9% |

---

## Free Tier Limitations

### Streamlit Cloud
- ✅ Unlimited hours
- ✅ 1 GB RAM
- ✅ 1 CPU core
- ✅ Free SSL
- ⚠️ Public repos only (or $20/mo for private)

### Render
- ✅ 750 hours/month free
- ✅ Free SSL
- ⚠️ Spins down after 15 min inactivity
- ⚠️ Cold start: ~30 seconds

### Railway
- ✅ $5 free credit/month
- ✅ Fast deploys
- ⚠️ Credit expires monthly
- ⚠️ Needs credit card

---

## Deployment Files Included

### `.streamlit/config.toml`
Streamlit configuration for deployment

### `render.yaml`
Render.com deployment configuration

### `requirements.txt`
All Python dependencies

### `README_ENHANCED.md`
Complete user documentation

---

## Post-Deployment Checklist

### ✅ After Deploying

1. **Test the app**
   - Try downloading a public newsletter
   - Check progress bars work
   - Verify output formats

2. **Configure environment variables**
   - Set `SUBSTACK_LOG_LEVEL=INFO`
   - Set `SUBSTACK_MAX_WORKERS=3` (for free tier)

3. **Monitor usage**
   - Check logs for errors
   - Monitor resource usage
   - Adjust workers if needed

4. **Share your app!**
   - Get the public URL
   - Share with users
   - Add to your README

---

## Troubleshooting

### App Won't Start
```bash
# Check logs in platform dashboard
# Common issues:
- Missing dependencies: Check requirements.txt
- Wrong Python version: Needs 3.9+
- Port issues: Use $PORT environment variable
```

### Out of Memory
```bash
# Reduce concurrent workers:
export SUBSTACK_MAX_WORKERS=1

# Disable caching:
export SUBSTACK_ENABLE_CACHE=false
```

### Slow Performance
```bash
# Cold starts on free tier:
- First request takes 30-60 seconds
- Keep app warm with uptime monitoring (e.g., UptimeRobot)

# Reduce timeout for free tier:
export SUBSTACK_TIMEOUT=30
```

### App Crashes
```bash
# Check logs:
1. Go to platform dashboard
2. View logs
3. Look for error messages

# Common fixes:
- Increase timeout
- Reduce workers
- Disable caching
```

---

## Security Best Practices

### ✅ DO:
1. Set environment variables in platform settings
2. Use HTTPS (automatic on all platforms)
3. Keep dependencies updated
4. Monitor logs for issues

### ❌ DON'T:
1. Commit secrets to git
2. Enable DEBUG logging in production
3. Use cookies in command-line args
4. Share log files publicly

---

## Monitoring & Maintenance

### Free Monitoring Tools

**UptimeRobot** (Recommended)
```
https://uptimerobot.com
- Free tier: 50 monitors
- Ping your app every 5 minutes
- Keeps free tier apps alive
```

**Cronitor**
```
https://cronitor.io
- Monitor API endpoints
- Alert on failures
- Free tier available
```

---

## Scaling Beyond Free Tier

### When to Upgrade

**Signs you need paid tier:**
- App spins down too often
- Running out of free hours
- Need more CPU/RAM
- Need faster cold starts

### Paid Options
- **Streamlit:** $20/mo for private repos
- **Render:** $7/mo for always-on instance
- **Railway:** Pay as you go ($0.01/GB-hour)
- **Fly.io:** $5/mo per VM

---

## Advanced: Docker Deployment

If you want to deploy anywhere with Docker:

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Build & Run
```bash
docker build -t substack-downloader .
docker run -p 8501:8501 substack-downloader
```

---

## CI/CD (Optional)

### GitHub Actions for Auto-Deploy

`.github/workflows/deploy.yml`:
```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Render
        run: |
          curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}
```

---

## Performance Tips

### For Free Tier

1. **Reduce workers:**
   ```bash
   export SUBSTACK_MAX_WORKERS=2
   ```

2. **Increase timeout:**
   ```bash
   export SUBSTACK_TIMEOUT=90
   ```

3. **Disable caching:**
   ```bash
   export SUBSTACK_ENABLE_CACHE=false
   ```

4. **Use progress bars:**
   Already included! Shows users progress.

---

## Support

### Platform Support
- **Streamlit:** https://docs.streamlit.io/
- **Render:** https://render.com/docs
- **Railway:** https://docs.railway.app/

### App Issues
- GitHub Issues: Your repo issues page
- Documentation: README_ENHANCED.md
- Security: SECURITY_ANALYSIS.md

---

## Quick Reference

### Deploy Commands

**Streamlit Cloud:**
```bash
# No commands needed - deploy via web UI
```

**Render:**
```bash
# No commands needed - auto-deploys from GitHub
```

**Railway:**
```bash
# Optional CLI
npm install -g @railway/cli
railway login
railway up
```

**Fly.io:**
```bash
fly launch
fly deploy
```

---

## Next Steps

1. **Choose a platform** (Streamlit Cloud recommended)
2. **Deploy your app** (5-10 minutes)
3. **Test it works**
4. **Share the URL!**
5. **Monitor and iterate**

---

**Happy Deploying!** 🚀

Your production-grade Substack downloader is ready to go live!
