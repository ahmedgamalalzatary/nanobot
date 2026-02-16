# nanobot Auto-Start Guide

This guide covers how to run nanobot 24/7 with automatic startup, restart on crash, and survival through SSH disconnections.

## The Problem

When running commands directly in an SSH session:
- Processes are **children of the SSH session**
- When SSH disconnects → processes receive `SIGHUP` → they **terminate**
- VM reboot → manual restart required

---

## Method 1: Docker (Recommended)

Docker provides the simplest way to achieve 24/7 operation with auto-restart capabilities.

### Build the Image

```bash
docker build -t nanobot .
```

### Initialize Config (First Time Only)

```bash
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot onboard
```

### Edit Config

```bash
vim ~/.nanobot/config.json
```

### Run with Auto-Restart

```bash
docker run -d \
  --name nanobot \
  --restart unless-stopped \
  -v ~/.nanobot:/root/.nanobot \
  -p 18790:18790 \
  nanobot gateway
```

### Docker Restart Policies

| Policy | Behavior |
|--------|----------|
| `--restart no` | Never auto-restart (default) |
| `--restart on-failure` | Restart only on non-zero exit code |
| `--restart always` | Always restart, regardless of exit code |
| `--restart unless-stopped` | Always restart unless manually stopped |

### Docker Commands

```bash
# View logs
docker logs -f nanobot

# Stop container
docker stop nanobot

# Start container
docker start nanobot

# Remove container
docker rm -f nanobot
```

### What This Provides

| Feature | Status |
|---------|--------|
| Auto-start on VM boot | ✅ Yes (via Docker daemon) |
| Auto-restart on crash | ✅ Yes (`--restart unless-stopped`) |
| Survives SSH disconnect | ✅ Yes (runs in background) |

### ⚠️ WhatsApp Note

For WhatsApp, you need **two processes**:

| Process | Docker? | Notes |
|---------|---------|-------|
| `nanobot gateway` | ✅ Yes | Main AI agent |
| `nanobot channels login` | ❌ Not in Dockerfile | WhatsApp bridge (Node.js) |

**Options for WhatsApp:**
1. Run bridge on host separately: `nanobot channels login` (in tmux)
2. Create a `docker-compose.yml` to run both services
3. Use Telegram/Discord instead (simpler - only gateway needed)

---

## Method 2: systemd (Production)

systemd provides the most robust solution for production deployments on Linux.

### Create Bridge Service

Create `/etc/systemd/system/nanobot-bridge.service`:

```ini
[Unit]
Description=nanobot WhatsApp Bridge
After=network.target

[Service]
Type=simple
User=alzatary
WorkingDirectory=/home/alzatary/Documents/nanobot
ExecStart=/usr/bin/npm run start --prefix /home/alzatary/Documents/nanobot/bridge
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Create Gateway Service

Create `/etc/systemd/system/nanobot-gateway.service`:

```ini
[Unit]
Description=nanobot Gateway
After=network.target

[Service]
Type=simple
User=alzatary
WorkingDirectory=/home/alzatary/Documents/nanobot
ExecStart=/home/alzatary/.local/bin/nanobot gateway
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Enable and Start Services

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable services (auto-start on boot)
sudo systemctl enable nanobot-bridge
sudo systemctl enable nanobot-gateway

# Start services now
sudo systemctl start nanobot-bridge
sudo systemctl start nanobot-gateway
```

### systemd Commands

```bash
# Check status
sudo systemctl status nanobot-gateway
sudo systemctl status nanobot-bridge

# View logs
journalctl -u nanobot-gateway -f
journalctl -u nanobot-bridge -f

# Stop services
sudo systemctl stop nanobot-gateway
sudo systemctl stop nanobot-bridge

# Restart services
sudo systemctl restart nanobot-gateway
sudo systemctl restart nanobot-bridge

# Disable auto-start
sudo systemctl disable nanobot-gateway
sudo systemctl disable nanobot-bridge
```

### What This Provides

| Feature | Status |
|---------|--------|
| Auto-start on VM boot | ✅ Yes |
| Auto-restart on crash | ✅ Yes (`Restart=always`) |
| Survives SSH disconnect | ✅ Yes |
| Logging to journalctl | ✅ Yes |
| Dependency management | ✅ Yes (`After=network.target`) |

---

## Comparison Table

| Method | Auto-start on boot | Survives SSH disconnect | Auto-restart on crash | Complexity |
|--------|-------------------|------------------------|----------------------|------------|
| Direct commands | ❌ No | ❌ No | ❌ No | Low |
| tmux/screen | ❌ No | ✅ Yes | ❌ No | Low |
| **Docker** | ✅ Yes | ✅ Yes | ✅ Yes | Medium |
| **systemd** | ✅ Yes | ✅ Yes | ✅ Yes | Medium |

---

## Quick Decision Guide

### Use Docker if:
- You want the simplest setup
- You're already using Docker
- You don't need WhatsApp (or don't mind running bridge separately)

### Use systemd if:
- You want production-grade reliability
- You need WhatsApp (both services as systemd units)
- You want logging to journalctl
- You're on a bare-metal server or VM without Docker

### Use tmux if:
- You're developing/debugging
- You need quick temporary setup
- You don't care about auto-start on boot

---

## tmux Quick Reference (Development Only)

```bash
# Create new session
tmux new -s nanobot

# Run bridge
nanobot channels login

# Split pane: Ctrl+B then "
# Run gateway
nanobot gateway

# Detach: Ctrl+B then D
# Reattach: tmux attach -t nanobot
# Kill session: tmux kill-session -t nanobot
```

**Note:** tmux does NOT provide auto-start on boot or auto-restart on crash.
