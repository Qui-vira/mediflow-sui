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

Required for web service:
- `BAND_MODE=true`
- `INTAKE_AGENT_ID` / `INTAKE_API_KEY`
- `COORDINATOR_AGENT_ID`
- `ANTHROPIC_API_KEY`

## Step 5: Deploy the web service (Flask form)

```bash
railway up -s web -d
```

## Step 6: Deploy 4 Band agent services

```bash
railway up -s coordinator -d
railway up -s intake -d
railway up -s verification -d
railway up -s resource -d
```

Or use `railway-start.py` with `SERVICE_TYPE` env var per service.

## Step 7: Get your public URL

Railway gives you a URL like: `web-production-6d13b.up.railway.app`
This is your live web form URL.

## Step 8: Human approval via Band

No separate dashboard deploy needed. Approvers log in at [app.band.ai](https://app.band.ai) and respond in MedBand case rooms.

See [demo_flow.md](../demo_flow.md) for the full demo script.
