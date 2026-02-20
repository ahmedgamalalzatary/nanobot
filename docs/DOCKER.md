# 🐳 Docker Operations Guide

Step-by-step reference for building, running, and maintaining nanobot with Docker.

---

## Table of Contents

1. [First-Time Setup](#1-first-time-setup)
2. [Build the Image](#2-build-the-image)
3. [Initialize Config](#3-initialize-config)
4. [Edit config.json (copy out → edit → copy back)](#4-edit-configjson)
5. [Connect WhatsApp (QR Login)](#5-connect-whatsapp-qr-login)
6. [Start the Gateway](#6-start-the-gateway)
7. [View Logs](#7-view-logs)
8. [Clear WhatsApp Auth Cache](#8-clear-whatsapp-auth-cache)
9. [Update / Rebuild Image](#9-update--rebuild-image)
10. [Full Nuclear Cleanup](#10-full-nuclear-cleanup)

---

## 1. First-Time Setup

Clone the repo and enter it:

```bash
git clone https://github.com/HKUDS/nanobot.git
cd nanobot
```

Check what's currently running:

```bash
docker ps -a
```

---

## 2. Build the Image

```bash
docker build -t nanobot .
```

> This takes a few minutes the first time — it installs Python deps, Node.js 20, and compiles the WhatsApp bridge.

Verify the image was created:

```bash
docker images | grep nanobot
```

---

## 3. Initialize Config

Run `onboard` once to generate `~/.nanobot/config.json` on your host:

```bash
# Docker Compose
docker compose run --rm nanobot-cli onboard

# Plain Docker
docker run -v ~/.nanobot:/root/.nanobot --rm -it nanobot onboard
```

> **Windows (PowerShell):** replace `~/.nanobot` with `$HOME\.nanobot` in all commands below.

---

## 4. Edit config.json

The config file lives on your **host** at `~/.nanobot/config.json` and is mounted into the container.

> ⚠️ **"File is unwritable" error?**  
> Docker runs as `root` inside the container, so files it creates are owned by `root` on the host.  
> Run these **one at a time** (do not paste with the comment lines):
> ```bash
> sudo chown $USER ~/.nanobot/config.json
> ```
> Or fix the entire directory:
> ```bash
> sudo chown -R $USER ~/.nanobot/
> ```
> After that, edit normally without `sudo`.  
> ⚠️ **Paste commands one line at a time** — pasting a command and a `#` comment together causes a bash syntax error.

```bash
# Linux / macOS
nano ~/.nanobot/config.json

# Windows (PowerShell) — no permission issues on Windows
notepad $HOME\.nanobot\config.json
```

### Alternative: copy out → edit → copy back (avoids permission issues entirely)

```bash
# Copy OUT of container to host
docker cp nanobot-gateway:/root/.nanobot/config.json ./config.json

# Edit on host
nano ./config.json

# Copy back INTO container
docker cp ./config.json nanobot-gateway:/root/.nanobot/config.json
```

### Minimum working config example

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx"
    }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5"
    }
  },
  "channels": {
    "whatsapp": {
      "enabled": true,
      "bridgeUrl": "ws://localhost:3001",
      "allowFrom": ["+1234567890"]
    }
  }
}
```

After editing config, **restart the gateway** to pick up changes:

```bash
# If the gateway container is already running:
docker compose restart nanobot-gateway

# If the container does not exist yet (first time or after cleanup), start it:
docker compose up -d nanobot-gateway

# Verify it started:
docker compose ps
docker compose logs -f nanobot-gateway
```

> ℹ️ `docker restart` / `docker compose restart` only work on **already-running** containers.  
> If you see `Error: No such container`, use `docker compose up -d` to create and start it first.

---

## 5. Connect WhatsApp (QR Login)

> ⚠️ This is a **one-time step**. Auth files are saved to `~/.nanobot/whatsapp-auth/` and reused automatically on next start.

Run the bridge interactively — `-it` is required to display the QR code:

```bash
# Docker Compose
docker compose run --rm -it nanobot-cli channels login

```

You will see output like:

```
📱 Scan this QR code with WhatsApp (Linked Devices):

▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
█ ▄▄▄▄▄ █ ▄▄▄▄█
█ █   █ █▀█ ▄▄█
...
```

On your phone: **WhatsApp → Settings → Linked Devices → Link a Device → scan the QR**.

When you see `✅ Connected to WhatsApp` — press **Ctrl+C**. Login is complete.

---

## 6. Start the Gateway

### Docker Compose (recommended)

```bash
# Gateway only (Telegram, Discord, Feishu, etc.)
docker compose up -d nanobot-gateway

# Gateway + WhatsApp bridge together
docker compose --profile whatsapp up -d

# Check running services
docker compose ps
```

### Plain Docker

```bash
# Gateway only
docker run -d \
  --name nanobot-gateway \
  -v ~/.nanobot:/root/.nanobot \
  -p 18790:18790 \
  nanobot gateway

# WhatsApp bridge (separate terminal, required alongside gateway)
# 1. Remove the broken old container
docker rm -f nanobot-whatsapp-bridge

# 2. Start it correctly with --entrypoint to override the nanobot entrypoint
docker run -d \
  --name nanobot-whatsapp-bridge \
  -v ~/.nanobot:/root/.nanobot \
  --network container:nanobot-gateway \
  -e BRIDGE_PORT=3001 \
  -e AUTH_DIR=/root/.nanobot/whatsapp-auth \
  --entrypoint node \
  nanobot \
  /app/bridge/dist/index.js
```

### Send a test message via CLI

```bash
docker compose run --rm nanobot-cli agent -m "Hello!"
# or
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot agent -m "Hello!"
```

### Check status

```bash
docker compose run --rm nanobot-cli status
# or
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot status
```

---

## 7. View Logs

```bash
# Follow all services (Compose)
docker compose logs -f

# Gateway only
docker compose logs -f nanobot-gateway

# WhatsApp bridge only
docker compose logs -f nanobot-whatsapp-bridge

# Last 100 lines from both
docker compose logs --tail=100 nanobot-gateway nanobot-whatsapp-bridge

# Plain Docker (by container name)
docker logs -f nanobot-gateway
docker logs -f nanobot-whatsapp-bridge
docker logs --tail=50 nanobot-gateway
```

### What healthy logs look like

**Bridge logs:**
```
🐈 nanobot WhatsApp Bridge
🌉 Bridge server listening on ws://127.0.0.1:3001
✅ Connected to WhatsApp
🔗 Python client authenticated
```

**Gateway logs:**
```
✓ Channels enabled: whatsapp
Connecting to WhatsApp bridge at ws://localhost:3001...
Connected to WhatsApp bridge
WhatsApp status: connected
```

---

## 8. Clear WhatsApp Auth Cache

Do this if WhatsApp shows as logged out, the QR scan fails, or you want to link a different account.

```bash
# Stop running services first
docker compose down
# or
docker stop nanobot-gateway nanobot-whatsapp-bridge

# Delete auth files from the host volume
rm -rf ~/.nanobot/whatsapp-auth/

# Windows (PowerShell)
Remove-Item -Recurse -Force $HOME\.nanobot\whatsapp-auth\
```

Then redo [Step 5](#5-connect-whatsapp-qr-login) to scan a fresh QR code.

---

## 9. Update / Rebuild Image

When you pull new code or change source files:

```bash
# Pull latest code
git pull

# Rebuild image (no cache)
docker build --no-cache -t nanobot .

# Or with Compose (rebuilds and restarts)
docker compose build --no-cache
docker compose --profile whatsapp up -d
```

### Force stop and replace a running container

```bash
# Stop + remove old container, start fresh
docker stop nanobot-gateway && docker rm nanobot-gateway
docker run -d \
  --name nanobot-gateway \
  -v ~/.nanobot:/root/.nanobot \
  -p 18790:18790 \
  nanobot gateway
```

---

## 10. Full Nuclear Cleanup

Use this to **completely wipe** all nanobot containers, images, build cache, volumes, and orphan networks. Useful when rebuilding from scratch or troubleshooting a broken state.

> ⚠️ This removes **all** Docker containers/images on the machine, not just nanobot ones. Use carefully on shared machines.

```bash
# 1. List all containers (running and stopped)
docker ps -a

# 2. Stop and remove ALL containers
docker rm -f $(docker ps -aq)

# 3. Remove ALL images
docker rmi -f $(docker images -aq)

# 4. Purge all build cache
docker builder prune -a -f

# 5. Remove all volumes
docker volume rm $(docker volume ls -q)

# 6. Remove orphan networks
docker network prune -f
```

### Nanobot-only cleanup (safer, targeted)

```bash
# Stop and remove only nanobot containers
docker rm -f nanobot-gateway nanobot-whatsapp-bridge 2>/dev/null || true

# Remove only the nanobot image
docker rmi -f nanobot 2>/dev/null || true

# Remove Compose project containers + networks
docker compose down --volumes --remove-orphans
```

After cleanup, start fresh from [Step 2](#2-build-the-image).

---

## Quick Reference Card

| Action | Command |
|---|---|
| Build image | `docker build -t nanobot .` |
| Init config | `docker compose run --rm nanobot-cli onboard` |
| Edit config (host) | `sudo chown $USER ~/.nanobot/config.json && nano ~/.nanobot/config.json` |
| Copy config out | `docker cp nanobot-gateway:/root/.nanobot/config.json ./config.json` |
| Copy config in | `docker cp ./config.json nanobot-gateway:/root/.nanobot/config.json` |
| WhatsApp QR login | `docker compose run --rm -it nanobot-cli channels login` |
| Start gateway | `docker compose up -d nanobot-gateway` |
| Start gateway + WhatsApp | `docker compose --profile whatsapp up -d` |
| Stop all | `docker compose down` |
| View logs (follow) | `docker compose logs -f` |
| Check status | `docker compose run --rm nanobot-cli status` |
| Clear WhatsApp auth | `rm -rf ~/.nanobot/whatsapp-auth/` |
| Rebuild image | `docker build --no-cache -t nanobot .` |
| List all containers | `docker ps -a` |
| Remove all containers | `docker rm -f $(docker ps -aq)` |
| Remove all images | `docker rmi -f $(docker images -aq)` |
| Purge build cache | `docker builder prune -a -f` |
| Remove all volumes | `docker volume rm $(docker volume ls -q)` |
| Prune networks | `docker network prune -f` |
