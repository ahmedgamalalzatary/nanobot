# Docker Deployment Guide

Complete guide for deploying nanobot on a VM using Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Step-by-Step Deployment](#step-by-step-deployment)
- [WhatsApp Setup](#whatsapp-setup)
- [Common Issues](#common-issues)
- [VM-Specific Setup](#vm-specific-setup)

## Prerequisites

- Docker installed on your system
- API key from a supported provider (OpenRouter, Gemini, OpenAI, etc.)
- (Optional) Node.js 20+ for WhatsApp bridge

## Quick Start

```bash
# Clone repository
git clone https://github.com/HKUDS/nanobot.git
cd nanobot

# Build and start
docker compose -f deploy/docker-compose.yml up -d

# Initialize config
docker compose -f deploy/docker-compose.yml run --rm gateway onboard

# Configure (add your API key)
docker compose -f deploy/docker-compose.yml run --rm --entrypoint sh gateway -c "cat /root/.nanobot/config.json" > deploy/config.json
nano deploy/config.json

# Copy config back and restart
docker compose -f deploy/docker-compose.yml up -d gateway
docker cp deploy/config.json nanobot-gateway:/root/.nanobot/config.json
docker compose -f deploy/docker-compose.yml restart

# Watch logs
docker compose -f deploy/docker-compose.yml logs -f
```

## Step-by-Step Deployment

### Step 1: Clean Up (Fresh Install)

If you have existing containers/volumes and want a fresh start:

```bash
cd ~/nanobot
docker compose -f deploy/docker-compose.yml down -v
docker system prune -f
```

### Step 2: Build Docker Images

Build all images fresh:

```bash
docker compose -f deploy/docker-compose.yml --profile whatsapp build --no-cache
```

> **Note**: `--profile whatsapp` includes the WhatsApp bridge service. Omit it if you don't need WhatsApp.

### Step 3: Initialize Configuration

Create the default config file:

```bash
docker compose -f deploy/docker-compose.yml run --rm gateway onboard
# Press 'y' to overwrite when prompted
```

### Step 4: Export and Edit Config

Extract the config file to edit locally:

```bash
docker compose -f deploy/docker-compose.yml run --rm --entrypoint sh gateway -c "cat /root/.nanobot/config.json" > deploy/config.json
nano deploy/config.json
```

**Required changes:**

1. **Add API key** (choose one provider):
   ```json
   "providers": {
     "gemini": {
       "apiKey": "YOUR_GEMINI_API_KEY"
     }
   }
   ```

2. **Set model** (must match your provider):
   ```json
   "agents": {
     "defaults": {
       "model": "gemini/gemini-3-pro-preview"
     }
   }
   ```

3. **Enable WhatsApp** (if using):
   ```json
   "channels": {
     "whatsapp": {
       "enabled": true,
       "bridgeUrl": "ws://nanobot-bridge:3001"
     }
   }
   ```

### Step 5: Copy Config and Start Gateway

```bash
# Start gateway container
docker compose -f deploy/docker-compose.yml up -d gateway

# Copy edited config into container
docker cp deploy/config.json nanobot-gateway:/root/.nanobot/config.json

# Restart to apply changes
docker compose -f deploy/docker-compose.yml restart gateway
```

### Step 6: Verify Gateway is Running

```bash
docker compose -f deploy/docker-compose.yml logs gateway
```

You should see:
```
✓ Channels enabled: ...
✓ Heartbeat: every 30m
✓ Agent loop started
```

## WhatsApp Setup

WhatsApp requires scanning a QR code for authentication. This must be done interactively.

### Step 1: Scan QR Code

```bash
docker compose -f deploy/docker-compose.yml run --rm -it bridge channels login
```

1. A QR code will appear in your terminal
2. Open WhatsApp on your phone → Settings → Linked Devices → Link a Device
3. Scan the QR code
4. Wait for `✅ Connected to WhatsApp`
5. Press `Ctrl+C` to exit

### Step 2: Start Everything

```bash
docker compose -f deploy/docker-compose.yml down
docker compose -f deploy/docker-compose.yml --profile whatsapp up -d
docker compose -f deploy/docker-compose.yml logs -f
```

### Step 3: Verify WhatsApp Connection

```bash
docker compose -f deploy/docker-compose.yml logs bridge
```

You should see:
```
✅ Connected to WhatsApp
```

And the gateway logs should show:
```
Connected to WhatsApp bridge
WhatsApp status: connected
```

## Common Issues

### No API Key Configured

**Error:**
```
Error: No API key configured.
Set one in ~/.nanobot/config.json under providers section
```

**Fix:** Add your API key to `deploy/config.json` and copy it into the container:
```bash
docker cp deploy/config.json nanobot-gateway:/root/.nanobot/config.json
docker compose -f deploy/docker-compose.yml restart
```

### WhatsApp Bridge Connection Error

**Error:**
```
WhatsApp bridge connection error: [Errno 111] Connect call failed
```

**Fix:** Ensure `bridgeUrl` is set to `ws://nanobot-bridge:3001` (not `localhost`) in your config.

### WhatsApp Status 401 (Invalid Session)

**Error:**
```
Connection closed. Status: 401, Will reconnect: false
```

**Fix:** The old session is invalid. Clear auth and re-scan:
```bash
docker compose -f deploy/docker-compose.yml down
docker volume rm deploy_nanobot-data
docker compose -f deploy/docker-compose.yml run --rm -it bridge channels login
# Scan QR again, then start
docker compose -f deploy/docker-compose.yml --profile whatsapp up -d
```

### WhatsApp Status 440 (Connection Loop)

**Error:**
```
Connection closed. Status: 440, Will reconnect: true
```

**Fix:** This indicates a connection conflict. Clear auth data and re-scan QR code:
```bash
docker compose -f deploy/docker-compose.yml down
docker run --rm -v deploy_nanobot-data:/data alpine rm -rf /data/whatsapp-auth
docker compose -f deploy/docker-compose.yml run --rm -it bridge channels login
```

### Config Changes Not Applied

If you edited `deploy/config.json` but changes aren't reflected:

```bash
# Copy config into running container
docker cp deploy/config.json nanobot-gateway:/root/.nanobot/config.json

# Restart to apply
docker compose -f deploy/docker-compose.yml restart
```

## VM-Specific Setup

### GCP (Google Cloud Platform)

1. **Install Docker:**
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **Clone and deploy** (follow steps above)

3. **Open firewall port:**
   ```bash
   gcloud compute firewall-rules create allow-nanobot \
     --allow tcp:18790 \
     --source-ranges 0.0.0.0/0 \
     --target-tags nanobot

   gcloud compute instances add-tags YOUR_VM_NAME --tags=nanobot --zone=YOUR_ZONE
   ```

### AWS EC2

1. **Install Docker:**
   ```bash
   sudo yum install -y docker
   sudo service docker start
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

2. **Open security group:** Add inbound rule for port 18790

### Azure VM

1. **Install Docker:** Follow [Azure Docker installation guide](https://docs.microsoft.com/en-us/azure/virtual-machines/linux/docker-deployment)

2. **Open network security group:** Add inbound rule for port 18790

## Useful Commands

### View Logs

```bash
# All services
docker compose -f deploy/docker-compose.yml logs -f

# Gateway only
docker compose -f deploy/docker-compose.yml logs -f gateway

# Bridge only
docker compose -f deploy/docker-compose.yml logs -f bridge
```

### Restart Services

```bash
# Restart all
docker compose -f deploy/docker-compose.yml restart

# Restart gateway only
docker compose -f deploy/docker-compose.yml restart gateway
```

### Stop Everything

```bash
docker compose -f deploy/docker-compose.yml down
```

### Stop and Remove Volumes (Fresh Start)

```bash
docker compose -f deploy/docker-compose.yml down -v
```

### Check Container Status

```bash
docker compose -f deploy/docker-compose.yml ps
```

### Run One-off Commands

```bash
# Check status
docker compose -f deploy/docker-compose.yml run --rm gateway status

# Chat with agent
docker compose -f deploy/docker-compose.yml run --rm gateway agent -m "Hello!"

# View config inside container
docker compose -f deploy/docker-compose.yml run --rm --entrypoint sh gateway -c "cat /root/.nanobot/config.json"
```

## File Structure

```
deploy/
├── docker-compose.yml      # Main compose file
├── config.json             # Local config copy (created during setup)
└── systemd/
    ├── nanobot-gateway.service  # Systemd unit (alternative deployment)
    └── nanobot-bridge.service   # Systemd unit for WhatsApp bridge
```

## Docker Compose Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| (default) | gateway only | Telegram, Discord, Slack, etc. |
| `whatsapp` | gateway + bridge | WhatsApp support |

**Commands:**
```bash
# Gateway only
docker compose -f deploy/docker-compose.yml up -d

# With WhatsApp
docker compose -f deploy/docker-compose.yml --profile whatsapp up -d
```