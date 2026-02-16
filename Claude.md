# Claude.md
This file provides guidance to agents when working with code in this repository.

## Project Overview

nanobot is a lightweight personal AI assistant framework written in Python 3.11+.
It supports multiple chat channels (Telegram, WhatsApp, Slack, Discord, Feishu, etc.)
and multiple LLM providers via LiteLLM.

## Build/Test/Lint Commands

### Install Dependencies
```bash
pip install -e ".[dev]"
```

### Run All Tests
```bash
pytest
```

### Run a Single Test File
```bash
pytest tests/test_commands.py
```

### Run a Single Test Function
```bash
pytest tests/test_commands.py::test_onboard_fresh_install
```

### Run Tests with Verbose Output
```bash
pytest -v
```

### Run Specific Test with Pattern Matching
```bash
pytest -k "test_name_pattern"
```

### Lint with Ruff
```bash
ruff check .
```

### Auto-fix Lint Issues
```bash
ruff check --fix .
```

### Format Code
```bash
ruff format .
```

### Type Check (if mypy is configured)
```bash
mypy nanobot
```

## Code Style Guidelines

### Imports

Use absolute imports from the `nanobot` package root:
```python
from nanobot.config.schema import Config
from nanobot.agent.tools.base import Tool
from nanobot.bus.events import InboundMessage
```

Group imports in this order:
1. Standard library (alphabetically)
2. Third-party packages (alphabetically)
3. Local imports (alphabetically)

Separate groups with blank lines.

### Formatting

- Line length: 100 characters max
- Use 4 spaces for indentation
- No trailing whitespace
- Use double quotes for string literals (except when single quotes avoid escaping)

### Type Hints

Use modern Python 3.11+ type syntax:
```python
def process(items: list[str]) -> dict[str, Any]:
def get_value(key: str | None) -> str | None:
async def fetch() -> LLMResponse:
```

Do NOT use old-style typing module imports:
```python
from typing import List, Dict, Optional, Any
```

Use dataclasses for simple data containers. Use Pydantic models for
configuration and API schemas.

### Naming Conventions

- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`
- Module-level private: `_single_leading_underscore`
- Async functions: Use `async def` prefix, no special naming

### Docstrings

Use triple-double-quotes for docstrings. Keep them concise but informative:

```python
def send_message(channel: str, content: str) -> None:
    """Send a message to the specified channel.
    
    Args:
        channel: Channel identifier (e.g., 'telegram', 'slack').
        content: Message content to send.
    """
```

### Error Handling

- Use try/except for known error cases
- Log errors with loguru: `logger.error(f"Error description: {e}")`
- Return meaningful error messages from tools
- Use Pydantic validation for configuration

```python
from loguru import logger

try:
    result = await some_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return f"Error: {e}"
```

### Async Patterns

Use `asyncio` throughout with `async/await`:

```python
async def process_message(msg: InboundMessage) -> OutboundMessage | None:
    result = await self.provider.chat(messages=messages)
    return OutboundMessage(channel=msg.channel, content=result.content)
```

Run async code with `asyncio.run()` at entry point:
```python
if __name__ == "__main__":
    asyncio.run(main())
```

### Configuration

Configuration uses Pydantic models in `nanobot/config/schema.py`:
- All config classes inherit from `BaseModel`
- Use `Field(default_factory=...)` for mutable defaults
- Use `ConfigDict` for model configuration

```python
from pydantic import BaseModel, Field

class MyConfig(BaseModel):
    enabled: bool = False
    items: list[str] = Field(default_factory=list)
```

### Tool Implementation

Tools extend `nanobot.agent.tools.base.Tool`:

```python
from nanobot.agent.tools.base import Tool

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Description of what the tool does."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        }
    
    async def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query", "")
        return f"Result for: {query}"
```

### Testing

- Use pytest with `pytest-asyncio`
- Place tests in `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use fixtures for test setup

```python
import pytest
from unittest.mock import patch

@pytest.fixture
def mock_config():
    with patch("nanobot.config.loader.load_config") as mock:
        mock.return_value = Config()
        yield mock

def test_my_function(mock_config):
    result = my_function()
    assert result is not None

@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result == "expected"
```

## Project Structure

```
nanobot/
  agent/        # Core agent loop, tools, memory
  bus/          # Message bus for inter-component communication
  channels/     # Chat platform integrations
  cli/          # CLI commands (typer)
  config/       # Configuration schema and loader
  cron/         # Scheduled jobs
  heartbeat/    # Periodic heartbeat service
  providers/    # LLM provider implementations (LiteLLM, OpenAI Codex)
  session/      # Session management
  skills/       # Agent skills
  utils/        # Utility functions
tests/          # Test files
bridge/         # WhatsApp bridge (Node.js)
```

## Key Files

- `nanobot/agent/loop.py` - Main agent loop
- `nanobot/config/schema.py` - Configuration models
- `nanobot/cli/commands.py` - CLI entry points
- `nanobot/providers/litellm_provider.py` - LLM provider implementation
- `pyproject.toml` - Project configuration, dependencies, ruff settings
