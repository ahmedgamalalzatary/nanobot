# nanobot Upgrade Ideas

This document outlines planned features and improvements for nanobot.

---

## Priority Order

1. Slash Commands
2. Model Prefix Variables
3. Long Term Memory
4. TUI (Terminal User Interface)
5. Dashboard

---

## 1. Slash Commands

### Overview

Slash commands work everywhere. Gateway detects "/" at the start of a message, checks if it's a valid command, executes it, and returns the result. If the command doesn't exist, return "no command available".

### Commands

| Command | Arguments | Description | Persistence |
|---------|-----------|-------------|-------------|
| `/new` | None | Create new session | - |
| `/reasoning` | `low`, `medium`, `high` | Change reasoning effort | Permanent (config) |
| `/status` | None | Show current state | - |
| `/think` | `on`, `off` | Show/hide thinking process after completion | Session |
| `/commands` | None | List all available commands | - |
| `/config` | None | Display config.json content | - |
| `/usage` | None | Show current session token usage | - |
| `/models` | None | List all available models | - |
| `/model` | `model_id` | Change current working model | Permanent (config) |
| `/logs` | None | Show current session logs | - |

### Behavior

**Command Detection:**
- Gateway checks if message starts with "/"
- If valid command: execute and return success/failure state
- If invalid command: return "no command available"
- Commands with arguments return success/failure state

**Examples:**
```
/reasoning high        → "Reasoning level set to: high" (saved to config)
/think on              → "Thinking display: on" (session only)
/status                → Shows current state
/unknowncommand        → "No command available"
```

### Implementation Notes

- Commands should work across all channels (CLI, Telegram, Discord, WhatsApp, etc.)
- `/think` requires access to reasoning tokens from models that support it (Claude, o1, etc.)
- `/usage` tracks current session only

---

## 2. Model Prefix Variables

### Overview

Variables added to every response from the AI for message formatting.

### Available Variables

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `{model}` | Short model name | `claude-opus-4-5` |
| `{modelFull}` | Full model identifier | `anthropic/claude-opus-4-5` |
| `{provider}` | Provider name | `anthropic` |
| `{thinkingLevel}` | Current thinking level | `high`, `medium`, `low`, `off` |

### Behavior

**Value Sources:**
- `{thinkingLevel}` comes from `/reasoning` command setting
- If model doesn't support thinking levels, value is `off`

**Format:**
```
thinking level: {thinkingLevel}

[actual model response here]
```

**Example Output:**
```
thinking level: high

To solve this problem, I'll break it down into steps...
```

**When `off`:**
```
thinking level: off

Hello! How can I help you today?
```

### Implementation Notes

- Prefix added by gateway after receiving response from AI
- Parse model name from full identifier for `{model}`
- Determine `{provider}` from model prefix or config
- `{thinkingLevel}` read from config (set by `/reasoning`)

---

## 3. Long Term Memory

### Overview

Every session creates a markdown file that stores all messages between user and AI. The agent can read and retrieve from these files.

### File Structure

```
{workspace}/memory/
├── 2026-02-15/
│   ├── 16-04.md
│   ├── 18-30.md
│   └── 22-15.md
├── 2026-02-16/
│   ├── 09-00.md
│   └── 14-22.md
```

**Path format:** `{workspace}/memory/YYYY-MM-DD/HH-MM.md`

Where `{workspace}` is the nanobot workspace directory from config.

### File Content Format

```markdown
# Session: 2026-02-15 16:04

**User**: hello
**Assistant**: Hi! How can I help you?

**User**: what's the weather?
**Assistant**: Let me check...

**User**: remember to check the docs
**Assistant**: I'll keep that in mind.
```

### Behavior

- New session → new file created
- Every message (user and assistant) appended to file by system
- Files stored in workspace so agent can read/edit them
- User can ask agent to retrieve from memory (grep, read files)
- Files kept forever (no auto-deletion)

### Implementation Notes

- Create `{workspace}/memory/` directory if not exists
- Create dated subdirectory on session start
- Append messages in real-time or on session end
- Agent tools already have file read capabilities
- Consider: metadata at top of file (model used, session ID)

---

## 4. TUI (Terminal User Interface)

### Overview

Replace `nanobot agent` command with an interactive TUI for chatting.

### MVP Features

- Chat interface (send/receive messages)
- Message history scrolling
- Working slash commands
- Header with info

### Header Info

Display at top of TUI:
- Current model name
- Context percentage (e.g., "45% context used")

**Example header:**
```
┌─ Model: claude-opus-4-5 │ Context: 45% ────────────────────────────┐
```

### Future Enhancements (Not MVP)

- Split panes (chat + logs + status)
- Multiple sessions
- File attachments
- Rich message rendering (markdown, code highlighting)

### Tech Stack

- **Textual** - Modern async TUI framework for Python
- Good for chat-style interfaces
- Built-in scrolling, input, layout widgets

### Implementation Notes

- Replace current `nanobot agent` interactive mode
- Keep `nanobot agent -m "message"` for one-off messages
- New command or same command? Replace existing.
- Slash commands work same as in other channels

---

## 5. Dashboard

### Overview

Modern web interface to interact with the entire nanobot application. Dashboard provides a non-nerd way to manage configs, providers, sessions, and chat.

### Tech Stack

- **Backend:** FastAPI
- **Frontend:** React

### Tabs

| Tab | Description |
|-----|-------------|
| **Chat** | Chat with the agent |
| **Models** | View/change current model |
| **Sessions** | History of sessions (browse `.md` files) |
| **Logs** | View system logs |
| **Providers** | View/configure connected providers |

### Features

- View and edit config.json
- Add/remove providers
- Switch models
- Browse session history
- View logs

### Security

- Dashboard only accessible from localhost
- No authentication needed (local endpoints only)
- Single user (owner)

### Implementation Notes

- Run dashboard as separate command: `nanobot dashboard`
- Or integrate with gateway (same process, different port)
- React build output served by FastAPI
- API endpoints for all actions
- WebSocket for real-time chat

---

## File Structure Additions

```
nanobot/
├── cli/
│   ├── commands.py          # Existing
│   ├── slash_commands.py    # NEW: slash command handlers
│   └── tui.py               # NEW: TUI implementation
├── dashboard/                # NEW
│   ├── backend/             # FastAPI backend
│   │   ├── main.py
│   │   ├── routes/
│   │   └── ...
│   └── frontend/            # React frontend
│       ├── src/
│       ├── package.json
│       └── ...
├── agent/
│   ├── memory.py            # Existing (short-term)
│   ├── long_term_memory.py  # NEW: session file management
│   └── ...
├── utils/
│   └── prefix.py            # NEW: model prefix formatting
```

---

## Dependencies to Add

```toml
[project.dependencies]
textual = ">=0.47.0"          # TUI framework

[project.optional-dependencies]
dashboard = [
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "websockets>=12.0",
]
```

---

## Questions / Open Items

1. `/think` - need to verify which providers expose thinking tokens
2. Dashboard - embed React build in package or require separate build step?
3. Memory files - real-time append or batch on session end?

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-16 | Initial document created |
