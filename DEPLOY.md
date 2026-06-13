# MedBand Railway Deployment

## Step 1: Install Railway CLI

```bash
npm install -g @railway/cli
```

## Step 2: Login to Railway

```bash
railway login
```

## Step 3: Create new project

```bash
railway init
```

## Step 4: Add environment variables on Railway dashboard

Go to your Railway project > Variables tab.
Add every variable from `.env.railway` with real values.

## Step 5: Deploy the web service (Flask form)

```bash
railway up
```

## Step 6: Create 4 worker services for Band agents

On Railway dashboard:

- New Service > Empty Service > name it: coordinator
- Set start command: `python agents/coordinator.py`
- Add all environment variables
- Repeat for: intake, verification, resource

## Step 7: Get your public URL

Railway gives you a URL like: `tbr-medband.up.railway.app`
This is your live web form URL.

## Step 8: Deploy Streamlit dashboard separately

Go to [streamlit.io/cloud](https://streamlit.io/cloud)
Connect your GitHub repo
Set main file: `dashboard/dashboard.py`
Add environment variables in Streamlit Cloud settings
