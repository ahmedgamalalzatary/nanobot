# Code Review & Problem Report

**Target:** Commit `7d98e49` to HEAD
**Scope:** Updated/Created files only
**Date:** 2026-02-16

## 1. Critical Security Issues

### 1.1. Shell Command Injection Risk
*   **Location:** `nanobot/agent/tools/shell.py` (Lines 66-93, `_guard_command` method)
*   **Problem:** Weak regex-based sanitization for shell commands.
*   **Reason:** The `ExecTool` relies on a list of "deny patterns" (e.g., `rm -rf`) to prevent destructive commands. This is easily bypassed using encoding (e.g., `echo "cm0gLXJmIC8=" | base64 -d | sh`), obfuscation, or alternative commands. Since `asyncio.create_subprocess_shell` (implied by `shell=True` behavior or direct usage) invokes the system shell, the agent is vulnerable to executing arbitrary malicious code if the LLM is tricked or hallucinates.
*   **Recommendation:** 
    1.  Switch to `asyncio.create_subprocess_exec` (no shell) where possible to avoid shell injection.
    2.  If shell features (pipes, redirects) are required, run the agent in a strictly sandboxed container (Docker/Podman).
    3.  Add a clear warning to the user that this tool permits arbitrary code execution.

### 1.2. Blocking I/O in Async Event Loop
*   **Location:** `nanobot/session/manager.py` (Line 104, `save` method; Line 78, `_load` method)
*   **Problem:** Synchronous file I/O operations inside the main async event loop.
*   **Reason:** The `save` method uses `with open(path, "w")` to write session logs. This is a blocking operation. Since `SessionManager.save` is called after *every* message in `nanobot/agent/loop.py`, this will block the entire asyncio event loop, causing the bot to freeze for all concurrent users/tasks while the disk write completes. This degrades performance significantly as session files grow.
*   **Recommendation:** Use `aiofiles` for asynchronous file I/O or offload these operations to a thread pool using `asyncio.to_thread`.

### 1.3. Uncontrolled Resource Consumption (Disk Fill)
*   **Location:** `nanobot/channels/discord.py` (Line 161, `_handle_message_create`)
*   **Problem:** Unbounded download of attachments.
*   **Reason:** The bot downloads *every* attachment from every allowed message to `~/.nanobot/media` without any size limit (other than per-file 20MB check) or retention policy. Over time, this will fill the host's disk storage, potentially causing a Denial of Service (DoS) for the entire system.
*   **Recommendation:** 
    1.  Implement a total storage quota.
    2.  Add a cron job or logic to delete files older than X days.
    3.  Only download attachments when explicitly requested or required by the current task.

## 2. Code Quality & Bugs

### 2.1. Broken Web Search Implementation
*   **Location:** `nanobot/agent/tools/web.py` (Lines 44-67, `WebSearchTool.execute`)
*   **Problem:** Brittle API response parsing.
*   **Reason:** The code assumes the Brave Search API response structure `r.json().get("web", {}).get("results", [])` will always exist. If the API returns an error or a different structure (e.g., rate limit, schema change), `results` might be `None` or keys might be missing, causing a runtime exception.
*   **Recommendation:** Add robust error handling and response validation. Check `r.status_code` explicitly before parsing JSON. Use `.get()` with defaults safer or `try/except` blocks around the iteration.

### 2.2. Inconsistent Tool Definitions
*   **Location:** `nanobot/agent/tools/web.py` vs `nanobot/agent/tools/shell.py`
*   **Problem:** Inconsistent use of class attributes vs. properties.
*   **Reason:** `WebSearchTool` defines `name`, `description`, and `parameters` as class attributes, whereas `ExecTool` and the base `Tool` class define them as properties (`@property`). While Python handles both, this inconsistency makes the codebase harder to maintain and violates the abstract base class contract style.
*   **Recommendation:** Standardize all tools to use `@property` methods as defined in the `Tool` base class.

### 2.3. Brittle Date Handling in Cron Tool
*   **Location:** `nanobot/agent/tools/cron.py` (Line 68, `_add_job`)
*   **Problem:** Strict ISO 8601 requirement for `at` parameter.
*   **Reason:** The tool uses `datetime.fromisoformat(at)`. If the LLM generates a natural language date (e.g., "2026-02-16 10:00" or "tomorrow"), this will raise a `ValueError`, causing the tool call to fail. LLMs often struggle with strict format adherence without retry logic.
*   **Recommendation:** 
    1.  Use a robust date parsing library like `dateutil.parser`.
    2.  Update the tool description (system prompt) to be extremely explicit about the required format.
    3.  Add error handling to catch `ValueError` and return a helpful message to the agent so it can retry with the correct format.

### 2.4. Hardcoded Secrets & Insecure Defaults
*   **Location:** `nanobot/config/schema.py`
*   **Problem:** Hardcoded values and insecure defaults.
    *   `DiscordConfig`: `intents: int = 37377` (Line 50). Hardcoding magic numbers makes upgrades/changes difficult.
    *   `EmailConfig`: `smtp_use_ssl: bool = False` (Line 70). Defaulting to non-SSL is insecure.
*   **Reason:** Hardcoded configuration limits flexibility and "secure by default" principles.
*   **Recommendation:** 
    *   Move the Discord intents calculation to a method or allow list-based configuration.
    *   Change `smtp_use_ssl` (or TLS) default to `True`.

## 3. Miscellaneous

### 3.1. Bridge Server Binding Warning
*   **Location:** `bridge/src/server.ts` (Line 20)
*   **Problem:** Potential security warning bypass.
*   **Reason:** The check `host !== '127.0.0.1' && host !== 'localhost'` is used to warn about insecure binding. However, this misses IPv6 loopback (`::1`).
*   **Recommendation:** Check against a comprehensive list of loopback addresses or simplify the warning logic.

### 3.2. Missing Dependency in Tool
*   **Location:** `nanobot/agent/tools/cron.py`
*   **Problem:** Implicit dependency on `croniter`.
*   **Reason:** The tool uses `CronSchedule(kind="cron", ...)` which relies on `nanobot/cron/service.py` using `croniter`. While `croniter` is in `pyproject.toml`, it is not imported/checked in the tool file itself, which might lead to runtime errors if the environment is partially set up.
*   **Recommendation:** Ensure all dependencies are verified or imports are handled gracefully.

## 4. Tests

No automated tests were found covering these specific edge cases (shell injection, blocking I/O). The existing `tests/` directory structure was observed but not executed as the environment setup for full integration testing (requiring API keys/services) is not available. Manual code analysis was the primary method used.
