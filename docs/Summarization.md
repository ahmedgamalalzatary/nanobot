
# nanobot Project Structure - Comprehensive Summary

## Overview
**nanobot** is an ultra-lightweight personal AI assistant framework (~4,000 lines of core code). It's a Python-based agent system that can interact through multiple chat platforms (Telegram, Discord, WhatsApp, Feishu, Slack, Email, QQ, DingTalk, Mochat) and uses LLM providers (OpenRouter, OpenAI, DeepSeek, etc.) for intelligence.

---

## Root Directory Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python project config - dependencies, entry points (`nanobot` CLI), build settings |
| `README.md` | Comprehensive documentation with installation, setup, and channel configuration guides |
| `Dockerfile` | Docker containerization for deployment |
| `core_agent_lines.sh` / `core_agent_lines.ps1` | Script to count core agent lines (~3,668 lines) |
| `LICENSE` | MIT License |
| `SECURITY.md` | Security policy and guidelines |
| `COMMUNICATION.md` | Community contact info (Feishu, WeChat, Discord) |

---

## Core Package: `nanobot/`

### Entry Points
| File | Purpose |
|------|---------|
| `__init__.py` | Package init - version, logo emoji (🐈 kitten) |
| `__main__.py` | Module entry point - delegates to CLI |

### Agent Core: `nanobot/agent/`
The heart of the AI assistant:

| File | Purpose |
|------|---------|
| `loop.py` | **`AgentLoop`** - Core processing engine: receives messages, builds context, calls LLM, executes tools, sends responses |
| `context.py` | **`ContextBuilder`** - Assembles system prompts from bootstrap files, memory, skills, and conversation history |
| `memory.py` | **`MemoryStore`** - Two-layer memory: `MEMORY.md` (long-term facts) + `HISTORY.md` (grep-searchable log) |
| `skills.py` | **`SkillsLoader`** - Loads skill definitions from `SKILL.md` files with progressive loading |
| `subagent.py` | **`SubagentManager`** - Spawns background agents for independent tasks |

### Agent Tools: `nanobot/agent/tools/`
Capabilities the agent can use:

| File | Tool | Purpose |
|------|------|---------|
| `base.py` | **`Tool`** | Abstract base class with JSON schema validation |
| `registry.py` | **`ToolRegistry`** | Dynamic tool registration and execution |
| `filesystem.py` | `read_file`, `write_file`, `edit_file`, `list_dir` | File operations with optional workspace restriction |
| `shell.py` | `exec` | Shell command execution with safety guards (blocks rm -rf, etc.) |
| `web.py` | `web_search`, `web_fetch` | Brave Search API + URL content extraction with Readability |
| `message.py` | `message` | Send messages to chat channels |
| `cron.py` | `cron` | Schedule reminders (one-time, recurring, cron expressions) |
| `spawn.py` | `spawn` | Spawn subagents for background tasks |
| `mcp.py` | MCP tools | Model Context Protocol integration for external tools |

### Message Bus: `nanobot/bus/`
Decouples channels from agent:

| File | Purpose |
|------|---------|
| `events.py` | **`InboundMessage`**, **`OutboundMessage`** - Data classes for message routing |
| `queue.py` | **`MessageBus`** - Async queues for inbound/outbound messages with subscriber pattern |

### Chat Channels: `nanobot/channels/`
Platform integrations:

| File | Channel | Protocol |
|------|---------|----------|
| `base.py` | **`BaseChannel`** | Abstract interface for all channels |
| `manager.py` | **`ChannelManager`** | Initializes and coordinates enabled channels |
| `telegram.py` | Telegram | python-telegram-bot with proxy support |
| `discord.py` | Discord | WebSocket gateway with intents |
| `whatsapp.py` | WhatsApp | WebSocket bridge to Node.js service |
| `feishu.py` | Feishu/Lark | WebSocket long connection |
| `slack.py` | Slack | Socket Mode (no public URL needed) |
| `email.py` | Email | IMAP receive + SMTP send |
| `qq.py` | QQ | botpy SDK with WebSocket |
| `dingtalk.py` | DingTalk | Stream Mode |
| `mochat.py` | Mochat | Socket.IO WebSocket |

### LLM Providers: `nanobot/providers/`
Multi-provider LLM support:

| File | Purpose |
|------|---------|
| `base.py` | **`LLMProvider`** - Abstract interface with **`LLMResponse`** data class |
| `registry.py` | **`PROVIDERS`** - Metadata for 15+ providers (OpenRouter, OpenAI, DeepSeek, Qwen, etc.) |
| `litellm_provider.py` | LiteLLM-based implementation (most providers) |
| `openai_codex_provider.py` | OpenAI Codex with OAuth flow |
| `transcription.py` | Audio transcription support |

### Configuration: `nanobot/config/`
| File | Purpose |
|------|---------|
| `schema.py` | Pydantic models for all config: channels, providers, agents, tools |
| `loader.py` | Config loading from `~/.nanobot/config.json` |

### CLI: `nanobot/cli/`
| File | Purpose |
|------|---------|
| `commands.py` | **Typer app** with commands: `agent`, `gateway`, `onboard`, `status`, `cron`, `channels` |

### Scheduling: `nanobot/cron/`
| File | Purpose |
|------|---------|
| `service.py` | **`CronService`** - Job scheduling with cron expressions, intervals, one-time |
| `types.py` | Data types: **`CronJob`**, **`CronSchedule`**, **`CronPayload`** |

### Session Management: `nanobot/session/`
| File | Purpose |
|------|---------|
| `manager.py` | **`SessionManager`** + **`Session`** - Conversation history in JSONL format |

### Heartbeat: `nanobot/heartbeat/`
| File | Purpose |
|------|---------|
| `service.py` | Periodic task execution (checks `HEARTBEAT.md` every 30 min) |

### Utilities: `nanobot/utils/`
| File | Purpose |
|------|---------|
| `helpers.py` | Helper functions: `ensure_dir`, `safe_filename`, etc. |

### Built-in Skills: `nanobot/skills/`
Pre-defined capabilities:

| Skill | Purpose |
|-------|---------|
| `github/SKILL.md` | GitHub CLI (`gh`) integration |
| `weather/SKILL.md` | Weather via wttr.in and Open-Meteo |
| `summarize/SKILL.md` | Summarize URLs, files, YouTube |
| `tmux/SKILL.md` | Remote-control tmux sessions |
| `memory/SKILL.md` | Memory management guidance |
| `cron/SKILL.md` | Scheduling guidance |
| `skill-creator/SKILL.md` | Meta-skill for creating new skills |

---

## Bridge: `bridge/`
Node.js WhatsApp bridge (required for WhatsApp channel):

| File | Purpose |
|------|---------|
| `src/index.ts` | Entry point - starts WebSocket server |
| `src/server.ts` | **`BridgeServer`** - WebSocket server for Python-Node.js communication |
| `src/whatsapp.ts` | **`WhatsAppClient`** - Baileys-based WhatsApp Web client |
| `package.json` | npm config with `@whiskeysockets/baileys` dependency |

---

## Workspace: `workspace/`
User-configurable agent behavior:

| File | Purpose |
|------|---------|
| `AGENTS.md` | Agent instructions, tool usage guidelines, memory system |
| `SOUL.md` | Personality, values, communication style |
| `USER.md` | User profile template (name, preferences, work context) |
| `TOOLS.md` | Tool documentation for the agent |
| `HEARTBEAT.md` | Periodic task checklist (checked every 30 min) |
| `memory/MEMORY.md` | Long-term memory (facts, preferences) |
| `memory/HISTORY.md` | Event log (grep-searchable) |

---

## Data Flow Summary

```text
User Message (Telegram/Discord/etc.)
    ↓
    Channel Implementation
        ↓
        MessageBus.publish_inbound()
            ↓
            AgentLoop.run() [consumes from bus]
                ↓
                ContextBuilder.build_messages() [system prompt + history]
                    ↓
                    LLMProvider.chat() [calls LLM API]
                        ↓
                        ToolRegistry.execute() [if tool calls]
                            ↓
                            Response
        ↓
        MessageBus.publish_outbound()
    ↓
    Channel.send()
    ↓
User receives response
```

---

## Key Design Principles

1. **Ultra-lightweight**: ~4,000 lines of core code
2. **Decoupled architecture**: Channels ↔ Agent via MessageBus
3. **Progressive skill loading**: Skills summarized, loaded on-demand
4. **Two-layer memory**: Facts (MEMORY.md) + Events (HISTORY.md)
5. **Session persistence**: JSONL files in `~/.nanobot/sessions/`
6. **Multi-provider support**: 15+ LLM providers via registry pattern
7. **Safety guards**: Shell command blocking, workspace restriction options