# Systemd Deployment Checklist

Pre-flight checks and installation steps for running nanobot as a systemd service.

---

## Pre-Flight Checks

Run these commands **before** installing the service files:

### 1. Verify nanobot is installed

```bash
which nanobot
```

- If it prints a path (e.g., `/usr/local/bin/nanobot`) → you're good.
- If it prints nothing → install nanobot first: `pip install nanobot-ai`
- **Important**: if the path is NOT `/usr/local/bin/nanobot`, update the `ExecStart=` line in the service files to match.

### 2. Verify Node.js is installed (only if using WhatsApp bridge)

```bash
which node
which npm
```

- If both print paths → you're good.
- If not → install Node.js: `sudo apt install nodejs npm` or via [nodesource](https://github.com/nodesource/distributions).
- If installed via **nvm**, the default PATH in the service file won't find it. Update the `Environment=PATH=` line in `nanobot-bridge.service` to include your nvm node path (e.g., `/home/nanobot/.nvm/versions/node/v20.x.x/bin`).

### 3. Check if the `nanobot` system user exists

```bash
id nanobot
```

- If it shows user info → you're good.
- If it says "no such user" → create it (see Setup below).

---

## Setup (One-Time)

### Step 1: Create a dedicated system user

```bash
sudo useradd -r -m -s /bin/bash nanobot
```

This creates:
- A system user named `nanobot`
- A home directory at `/home/nanobot`
- Bash as the default shell (needed for nanobot shell tools)

### Step 2: Create the config directory

```bash
sudo -u nanobot mkdir -p /home/nanobot/.nanobot
```

### Step 3: Copy your config

```bash
sudo cp ~/.nanobot/config.json /home/nanobot/.nanobot/config.json
sudo chown nanobot:nanobot /home/nanobot/.nanobot/config.json
sudo chmod 600 /home/nanobot/.nanobot/config.json
```

### Step 4: Install the service files

```bash
sudo cp nanobot-gateway.service /etc/systemd/system/
sudo cp nanobot-bridge.service /etc/systemd/system/    # only if using WhatsApp
sudo systemctl daemon-reload
```

### Step 5: Enable and start

```bash
# Gateway (always needed)
sudo systemctl enable nanobot-gateway
sudo systemctl start nanobot-gateway

# Bridge (only if using WhatsApp)
sudo systemctl enable nanobot-bridge
sudo systemctl start nanobot-bridge
```

---

## Post-Install Verification

| Check | Command | Expected |
|-------|---------|----------|
| Service is running | `sudo systemctl status nanobot-gateway` | "active (running)" |
| Logs look normal | `journalctl -u nanobot-gateway -f` | nanobot output, no errors |
| Auto-restart works | `sudo kill -9 $(pgrep -f "nanobot gateway")` | Comes back in ~5 seconds |
| Clean stop works | `sudo systemctl stop nanobot-gateway` | Stays stopped |
| Boot start works | Reboot, then `systemctl status nanobot-gateway` | "active (running)" |

---

## Troubleshooting

### "nanobot: command not found" in service logs

The `ExecStart` path doesn't match where nanobot is installed. Fix:

```bash
which nanobot
# Update ExecStart= in the .service file to match
sudo systemctl daemon-reload
sudo systemctl restart nanobot-gateway
```

### "Permission denied" errors

Check ownership of the config directory:

```bash
ls -la /home/nanobot/.nanobot/
# Everything should be owned by nanobot:nanobot
sudo chown -R nanobot:nanobot /home/nanobot/.nanobot/
```

### Bridge can't find node/npm

If Node.js was installed via nvm, update the PATH in the bridge service:

```bash
sudo nano /etc/systemd/system/nanobot-bridge.service
# Update the Environment=PATH= line to include your node path
sudo systemctl daemon-reload
sudo systemctl restart nanobot-bridge
```

### Service keeps restarting (crash loop)

Check the logs for the root cause:

```bash
journalctl -u nanobot-gateway -n 50 --no-pager
```

Common causes:
- Missing or invalid `config.json`
- API key expired or wrong
- Port 18790 already in use (`sudo lsof -i :18790`)
