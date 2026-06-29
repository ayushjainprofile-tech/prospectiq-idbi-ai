# Deployment Guide

This guide covers the manual steps required to initialize your repository, publish it to GitHub, and deploy your frontend and backend separately or together.

## 1. Git & GitHub Initialization (Manual Steps)

Since terminal access is currently restricted, follow these steps in your local terminal to securely publish your project:

```bash
# Initialize a new Git repository
git init

# Add all files (the newly created .gitignore will prevent sensitive files from being added)
git add .

# Commit the initial state
git commit -m "Initial commit: Set up full-stack project with frontend and FastAPI backend"

# Create a new public repository on GitHub (Make sure the GitHub CLI 'gh' is installed and authenticated)
gh repo create nova-ai --public --source=. --remote=origin

# Push the code to GitHub
git branch -M main
git push -u origin main
```

**Verification:** Go to `https://github.com/your-username/nova-ai` in your browser to verify it's publicly accessible and that no sensitive files (like `.env`) were uploaded.

## 2. Vercel Deployment (Frontend + Serverless Backend)

Vercel is ideal for hosting both the React/Vite frontend and the FastAPI backend (using Serverless Functions via `vercel.json`).

### Steps:
1. Go to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New... > Project**.
3. Import the GitHub repository you just created.
4. **Framework Preset:** Vite (Vercel usually detects this automatically).
5. **Root Directory:** `./`
6. **Environment Variables:** Add `GOOGLE_API_KEY` in the Environment Variables section.
7. Click **Deploy**.

*Note: Your `vercel.json` already contains the necessary rewrite rules to route `/api/*` requests to your FastAPI Python backend (`api/index.py`).*

## 3. Railway Deployment (Alternative for Dedicated Backend)

If you prefer to host the backend separately (e.g., if you need WebSockets, background tasks, or run into Vercel's serverless timeout limits), you can use Railway.

### Steps:
1. Log in to [Railway](https://railway.app/).
2. Click **New Project** > **Deploy from GitHub repo**.
3. Select your `nova-ai` repository.
4. Railway will automatically detect the `api/requirements.txt`.
5. **Important Configuration:**
   - Go to the **Variables** tab and add your `GOOGLE_API_KEY`.
   - Go to the **Settings** tab and configure the Start Command if needed: `uvicorn api.index:app --host 0.0.0.0 --port $PORT`
6. Once deployed, Railway will provide a public URL. Update your Vite frontend API calls to point to this new URL if necessary.
