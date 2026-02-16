# Code Review Report — Commits `7d98e49` and `41e6b06`

**Reviewed by:** Rovo Dev (AI Code Reviewer)
**Date:** 2026-02-16
**Scope:** All files created/modified in commits `7d98e49` (feat: add prefix formatting utilities) and `41e6b06` (Refactor codebase for improved readability and maintainability)
**Tools used:** Manual code inspection, `ruff check .`, `pytest -v` (55 tests — all passing)

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical (Security / Data Loss) | 4 |
| 🟠 High (Bugs / Logic Errors) | 8 |
| 🟡 Medium (Code Quality / Misleading) | 10 |
| 🔵 Low (Style / Minor) | 7 |

---

## 🔴 Critical Issues

### C1. Error Messages Leak Internal State to End Users

**File:** `nanobot/agent/loop.py`, line 229
**What:** When the agent encounters an exception processing a message, the raw exception string is sent directly to the user:
```python
content=f"Sorry, I encountered an error: {str(e)}"
```
**Why this is a problem:** Exception messages can contain sensitive information — file paths, API keys (if embedded in connection strings), stack traces from third-party libraries, database URIs, internal hostnames, etc. This is a classic information disclosure vulnerability (CWE-209).
**Recommendation:** Log the full error internally but send a generic message to the user:
```python
logger.error(f"Error processing message: {e}", exc_info=True)
await self.bus.publish_outbound(
    OutboundMessage(
        channel=msg.channel,
        chat_id=msg.chat_id,
        content="Sorry, I encountered an internal error. Please try again.",
    )
)
```

---

### C2. Shell Command Safety Guard is Trivially Bypassable

**File:** `nanobot/agent/tools/shell.py`, lines 24–33, 104–137
**What:** The deny-pattern guard uses simple regex on the lowercased command string. It can be bypassed with:
- Base64 encoding: `echo "cm0gLXJmIC8=" | base64 -d | sh`
- Variable indirection: `cmd="rm"; $cmd -rf /`
- Hex escapes, aliasing, backtick substitution, `eval`, `python -c`, `perl -e`, etc.
- Path traversal check only looks for literal `../` or `..\` — symlinks, `readlink`, `cd ..;`, and URL-encoded paths bypass it entirely.

**Why this is a problem:** The LLM agent has shell access and could be manipulated via prompt injection to execute destructive commands. The guard provides a false sense of security (CWE-78: OS Command Injection).
**Recommendation:**
1. Document that this is a **best-effort** guard, not a security boundary.
2. Consider running commands in a sandboxed environment (Docker container, `nsjail`, `firejail`).
3. Add more bypass patterns: `eval`, `exec`, `python -c`, `perl -e`, `base64`, `bash -c`, `source`, pipe to `sh`/`bash`.
4. For `restrict_to_workspace` mode, resolve symlinks before checking paths.

---

### C3. Path Traversal in Filesystem Tools via `str.startswith()`

**File:** `nanobot/agent/tools/filesystem.py`, line 11
**What:** The path restriction check uses string prefix matching:
```python
if allowed_dir and not str(resolved).startswith(str(allowed_dir.resolve())):
```
**Why this is a problem:** This fails for sibling directories with similar names. For example, if `allowed_dir` is `/home/user/workspace`, then `/home/user/workspace-evil/malicious.txt` would pass the check because the string starts with the allowed directory path. This is a classic path traversal vulnerability (CWE-22).
**Recommendation:** Use `Path.is_relative_to()` (Python 3.9+) or check `parents`:
```python
if allowed_dir:
    allowed = allowed_dir.resolve()
    if not (resolved == allowed or allowed in resolved.parents):
        raise PermissionError(f"Path {path} is outside allowed directory {allowed_dir}")
```

---

### C4. Ruff Lint Rules Aggressively Suppressed to Hide Real Issues

**File:** `pyproject.toml`, line 91
**What:** The refactoring commit added many new ignore rules:
```toml
# Before (7d98e49):
ignore = ["E501"]
# After (41e6b06):
ignore = ["E501", "W293", "E741", "E731", "N803", "N806", "F541", "F841"]
```
Of particular concern:
- **`F841`** (unused variables) — Hides actual bugs. Ruff found 2 real unused variables (`level` in feishu.py:283, `response` in cron/service.py:237).
- **`F821`** (undefined names) — Was NOT added to ignore but ruff found 3 instances of this error. Ignoring `F841` means real bugs go undetected.
- **`E741`** (ambiguous variable names like `l`, `O`, `I`) — Hiding this can lead to confusion between `l` and `1`, `O` and `0`.
- **`F541`** (f-string without placeholders) — Hides wasted f-string usage.

**Why this is a problem:** Suppressing lint rules to make the codebase "pass" without actually fixing the issues defeats the purpose of CI linting. The CI workflow added in this same commit will now pass with real bugs hidden.
**Recommendation:**
1. Remove `F841` from the ignore list and fix the 2 unused variable issues.
2. Remove `F541` from the ignore list and fix any f-strings without placeholders.
3. Keep `E501` (line length) as the project uses its own `line-length = 100`.
4. Evaluate whether `E741`, `E731`, `N803`, `N806` are actually needed or if the code should be fixed.

---

## 🟠 High Issues

### H1. `format_prefix()` Ignores Its `model_full` Parameter — Dead Code

**File:** `nanobot/utils/prefix.py`, lines 3–14
**What:** The function signature accepts `model_full` but never uses it:
```python
def format_prefix(model_full: str, thinking_level: str = "off") -> str:
    return f"thinking level: {thinking_level}\n\n"
```
Additionally, `get_model_short()` and `get_provider_name()` are exported in `__init__.py` and `__all__` but are never called anywhere in the codebase.
**Why this is a problem:**
1. The unused parameter is misleading — callers pass `self.model` (line 315 of loop.py) expecting it to matter.
2. Every user-visible response is now prepended with `"thinking level: off\n\n"` — this leaks internal debugging/implementation details to end users, polluting all chat messages.
3. Three exported functions with two being dead code add unnecessary API surface.

**Recommendation:**
1. Either use `model_full` in the output or remove the parameter.
2. Remove the hardcoded "thinking level: off" prefix from user-visible output — it belongs in internal logging, not in chat responses.
3. Remove `get_model_short` and `get_provider_name` from `__all__` until they are actually used.

---

### H2. Prefix Prepended to ALL Responses Including System Messages

**File:** `nanobot/agent/loop.py`, lines 315–316
**What:**
```python
prefix = format_prefix(self.model) or ""
final_content = prefix + final_content
```
This is applied in `_process_message()` which handles ALL messages, including system messages (subagent announcements). The prefix `"thinking level: off\n\n"` is prepended even when:
- The user sends `/help` or `/new` (though those return early — this specific path doesn't hit them).
- A subagent completes and announces its result.

**Why this is a problem:** System messages routed back to users will contain the prefix, making the bot appear broken or leaking debug info.
**Recommendation:** Either remove the prefix entirely from user-facing output, or apply it only conditionally (e.g., only for non-system messages, and only when thinking is actually enabled).

---

### H3. `format_prefix()` Can Return Empty String But Caller Adds `or ""`

**File:** `nanobot/agent/loop.py`, line 315
**What:**
```python
prefix = format_prefix(self.model) or ""
```
`format_prefix()` currently always returns a non-empty string (`"thinking level: off\n\n"`), so the `or ""` is dead code. But if someone modifies `format_prefix()` to return `""` when thinking is off (the logical fix), the `or ""` would silently mask the change without any test catching it.
**Why this is a problem:** This indicates the code was written without a clear contract between `format_prefix` and its caller. There's no test for this behavior at all.
**Recommendation:** Add unit tests for `format_prefix()` and its integration with `_process_message()`. Define a clear contract: should it return `""` when there's nothing to show, or always return a prefix?

---

### H4. Unused Import Removed But Forward Reference Still Used (F821)

**File:** `nanobot/agent/loop.py`, lines 51–52
**What:** The refactoring commit removed `from nanobot.cron.service import CronService` (the deferred import inside `__init__`), but the type annotation `"CronService | None"` still references it. Ruff reports F821 (undefined name).
```python
cron_service: "CronService | None" = None,
```
Same issue in `nanobot/agent/subagent.py`, line 38 with `"ExecToolConfig | None"`.
**Why this is a problem:** While Python doesn't evaluate string annotations at runtime (PEP 563), this breaks:
- Type checkers (mypy, pyright) — they will report errors.
- `typing.get_type_hints()` calls — they will raise `NameError`.
- IDE autocompletion and refactoring tools.

**Recommendation:** Re-add the import inside the `__init__` method (where it was before), or use `from __future__ import annotations` and import at the module level with `TYPE_CHECKING`:
```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from nanobot.cron.service import CronService
```

---

### H5. Unused Variable `level` in Feishu Channel

**File:** `nanobot/channels/feishu.py`, line 283 (also line 282)
**What:**
```python
level = len(m.group(1))  # assigned but never used
text = m.group(2).strip()
```
**Why this is a problem:** This was likely intended to produce different formatting for different heading levels (h1–h6) but was never implemented. All headings are rendered identically as `**bold**` text regardless of level. This is a functional bug — heading hierarchy is lost in Feishu card rendering.
**Recommendation:** Use the `level` variable to apply appropriate formatting, or remove the assignment if heading levels are intentionally ignored and document why.

---

### H6. Unused Variable `response` in Cron Service

**File:** `nanobot/cron/service.py`, lines 234–237
**What:**
```python
response = None
if self.on_job:
    response = await self.on_job(job)

job.state.last_status = "ok"
```
**Why this is a problem:** The job execution result (`response`) is captured but never used. This means:
- Job output is silently discarded — there's no way to know what the job actually returned.
- The job is always marked as `"ok"` regardless of the response content.
- If the callback returns an error string, it's lost.

**Recommendation:** Either use the response (e.g., store it in `job.state`, log it, or check for error indicators), or use `await self.on_job(job)` without assignment if the response is genuinely unneeded.

---

### H7. `_consolidate_memory` Fire-and-Forget Task Has No Error Reporting

**File:** `nanobot/agent/loop.py`, lines 286, 300
**What:**
```python
asyncio.create_task(_consolidate_and_cleanup())
# ...
asyncio.create_task(self._consolidate_memory(session))
```
**Why this is a problem:** `asyncio.create_task()` without saving the reference or adding an error callback means:
1. If the task raises an exception, it produces only a warning in the asyncio event loop logs (easily missed).
2. The task can be garbage-collected before completion.
3. On line 286, the `_consolidate_and_cleanup` closure captures `messages_to_archive` and `session` — if the session object is modified before the task runs, it could produce inconsistent results (though the `.copy()` on line 276 mitigates the messages part).

**Recommendation:** Store task references and add error callbacks:
```python
task = asyncio.create_task(_consolidate_and_cleanup())
task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
```

---

### H8. Bridge Server Warning-Only for Insecure Binding

**File:** `bridge/src/server.ts`, lines 29–31
**What:**
```typescript
if (host !== '127.0.0.1' && host !== 'localhost' && !this.token) {
    console.warn('⚠️  WARNING: Server binding to non-loopback address without token authentication');
}
```
**Why this is a problem:** When binding to `0.0.0.0` without a token, the server is publicly accessible with no authentication. A `console.warn` is insufficient — anyone on the network can connect and send/receive WhatsApp messages through the bridge. This is a security issue (CWE-306: Missing Authentication).
**Recommendation:** Either:
1. Refuse to start without a token when binding to non-loopback addresses (throw an error).
2. At minimum, make this a very prominent warning with instructions on how to set a token.

---

## 🟡 Medium Issues

### M1. `GatewayConfig` Binds to `0.0.0.0` by Default

**File:** `nanobot/config/schema.py`, line 225
**What:**
```python
class GatewayConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 18790
```
**Why this is a problem:** Binding to all interfaces by default exposes the service to the network. For a personal AI assistant, the default should be `127.0.0.1` (loopback only). Users who need network access can explicitly configure it.
**Recommendation:** Change default to `"127.0.0.1"` and document how to bind to `0.0.0.0` for Docker/remote scenarios.

---

### M2. API Keys Stored in Plain Text Config with No Encryption

**File:** `nanobot/config/schema.py`, lines 195–219
**What:** All provider configs store `api_key` as plain `str` fields:
```python
class ProviderConfig(BaseModel):
    api_key: str = ""
    api_base: str | None = None
```
**Why this is a problem:** API keys in `config.json` are stored in plain text on disk. If the workspace or home directory is shared, version-controlled, or backed up to cloud storage, keys are exposed.
**Recommendation:**
1. Support environment variable references in config (e.g., `"api_key": "$ANTHROPIC_API_KEY"`).
2. Add documentation warning users not to commit `config.json`.
3. Consider adding `config.json` to the default `.gitignore`.

---

### M3. `os.environ` Modified Globally in LiteLLM Provider

**File:** `nanobot/providers/litellm_provider.py`, lines 51–73
**What:** `_setup_env()` modifies `os.environ` directly:
```python
os.environ[spec.env_key] = api_key
os.environ.setdefault(env_name, resolved)
```
**Why this is a problem:** Modifying global environment variables is a side effect that:
- Persists across tests (can cause test pollution).
- Is not thread-safe.
- Can leak API keys to child processes spawned by `ExecTool`.
- Makes it impossible to run multiple provider instances with different keys.

**Recommendation:** Pass API keys directly via LiteLLM's function parameters (which is already partly done in lines 142–148 of the same file) instead of relying on environment variables.

---

### M4. No Input Validation on `WebFetchTool` URL Could Enable SSRF

**File:** `nanobot/agent/tools/web.py`, lines 32–42, 127–131
**What:** While there is URL scheme validation (http/https only), there is no check for:
- Private/internal IP ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.169.254)
- DNS rebinding attacks
- `localhost`, `metadata.google.internal`, cloud metadata endpoints

**Why this is a problem:** The LLM agent can be prompted to fetch internal URLs, potentially accessing cloud metadata services (AWS IMDSv1 at 169.254.169.254), internal APIs, or other services not meant to be publicly accessible (CWE-918: SSRF).
**Recommendation:** Add private IP range filtering:
```python
import ipaddress
resolved_ip = socket.getaddrinfo(parsed.hostname, None)[0][4][0]
if ipaddress.ip_address(resolved_ip).is_private:
    return json.dumps({"error": "Access to private/internal addresses is blocked", "url": url})
```

---

### M5. WhatsApp Channel Has Typo in Comment

**File:** `nanobot/channels/whatsapp.py`, line 102
**What:**
```python
# Deprecated by whatsapp: old phone number style typically: <phone>@s.whatspp.net
```
`whatspp` should be `whatsapp`.
**Why this is a problem:** While just a typo, it could cause confusion when grepping for "whatsapp" references in the codebase.
**Recommendation:** Fix to `whatsapp.net`.

---

### M6. Session Key Parsing in `list_sessions()` is Lossy

**File:** `nanobot/session/manager.py`, line 170
**What:**
```python
"key": path.stem.replace("_", ":"),
```
**Why this is a problem:** The `safe_filename` function replaces `:` with `_` when saving, but the reverse mapping replaces ALL underscores with colons. If the original key contained underscores (e.g., `telegram_bot:12345`), the reconstructed key would be wrong (`telegram:bot:12345`).
**Recommendation:** Use a reversible encoding (e.g., URL-encoding or a delimiter that can't appear in keys) or store the original key in the metadata line (which is already available).

---

### M7. `docker-compose.yml` Config Editing Instructions Are Confusing

**File:** `deploy/docker-compose.yml`, lines 9–13
**What:** The comment instructs users to edit config with:
```yaml
#   3. Config:   Edit ~/.nanobot/config.json (when using the named volume 'nanobot-data', the config lives inside the container/volume, not on the host). Use the following command to edit/view the config:
#               docker compose exec gateway vi /root/.nanobot/config.json
```
**Why this is a problem:** The comment mentions `~/.nanobot/config.json` (host path) but then says it's actually inside the container volume — this is contradictory and confusing. Also, `vi` may not be available in the Docker image.
**Recommendation:** Restructure the comment to clearly state the config is inside the volume and provide a reliable way to edit it (e.g., `docker cp` workflow or a bind-mount alternative).

---

### M8. CI Workflow Missing Dependency Caching

**File:** `.github/workflows/ci.yml`, lines 8–76
**What:** The CI workflow installs dependencies from scratch on every run without pip caching.
**Why this is a problem:** The project has many dependencies (telegram-bot, lark-oapi, slack-sdk, etc.). Without caching, CI runs are slow and wasteful.
**Recommendation:** Add pip caching:
```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: ${{ matrix.python-version }}
    cache: 'pip'
```

---

### M9. CI Lint Job Installs Only `ruff`, Not Project Dependencies

**File:** `.github/workflows/ci.yml`, lines 20–22
**What:**
```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install ruff
```
**Why this is a problem:** Ruff's `F821` (undefined name) checks require knowing the project's imports. Without installing the project, some import-related checks may not work correctly. More importantly, the lint and format steps operate on the code without the project context.
**Recommendation:** Install the project in the lint job as well: `pip install -e ".[dev]"` (which already includes ruff).

---

### M10. `typing.Any` Import Removed from `transcription.py` but Still Needed Conceptually

**File:** `nanobot/providers/transcription.py`, line 5 (removed)
**What:** The diff shows `from typing import Any` was removed in the refactoring commit.
**Why this is a problem:** While the current code doesn't use `Any`, this removal alongside a large number of other import reorderings suggests automated changes were applied without individual verification. The risk is that similar removals in other files may have broken things.
**Recommendation:** No action needed for this specific file, but it highlights the need to run full type checking (`mypy`) as part of CI, not just ruff.

---

## 🔵 Low Issues

### L1. `WebSearchTool` and `WebFetchTool` Use Class-Level Property Override Pattern

**File:** `nanobot/agent/tools/web.py`, lines 48–62, 100–110
**What:** These tools define `name`, `description`, and `parameters` as class-level attributes instead of `@property` methods (unlike other tools like `ExecTool`, `ReadFileTool`, etc.).
**Why this is a problem:** While this works due to Python's descriptor protocol, it's inconsistent with the rest of the codebase. The `Tool` ABC declares these as `@abstractmethod @property`, but class-level attributes satisfy the abstract method requirement. This inconsistency could confuse developers.
**Recommendation:** Either make all tools use class-level attributes (and update the ABC) or make these use `@property` for consistency.

---

### L2. Hardcoded User-Agent String in Web Tools

**File:** `nanobot/agent/tools/web.py`, line 14
**What:**
```python
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36"
```
**Why this is a problem:** This is a truncated User-Agent that identifies as a Mac browser. Some websites may reject it as suspicious (incomplete UA), and it misrepresents the client identity.
**Recommendation:** Use a complete, honest User-Agent like `"nanobot/0.1 (Python; +https://github.com/...)"` or make it configurable.

---

### L3. `_is_heartbeat_empty` Checks for Completed Checkboxes as "Empty"

**File:** `nanobot/heartbeat/service.py`, lines 26–33
**What:**
```python
skip_patterns = {"- [ ]", "* [ ]", "- [x]", "* [x]"}
```
**Why this is a problem:** Both unchecked (`- [ ]`) and checked (`- [x]`) checkboxes are treated as "skip" patterns, meaning a HEARTBEAT.md that contains only completed tasks would be considered empty. This is probably intentional but could be surprising.
**Recommendation:** Add a comment explaining the rationale: completed checkboxes are skipped because they represent already-handled tasks.

---

### L4. Magic Numbers Without Named Constants

**File:** Multiple locations
**What:**
- `nanobot/agent/loop.py:218`: `timeout=1.0` — inbound message poll interval
- `nanobot/agent/tools/shell.py:95`: `max_len = 10000` — output truncation limit
- `nanobot/channels/whatsapp.py:67`: `await asyncio.sleep(5)` — reconnect delay
- `nanobot/channels/telegram.py:142`: `connection_pool_size=16`

**Why this is a problem:** Magic numbers make the code harder to understand and tune.
**Recommendation:** Extract to named constants at module or class level.

---

### L5. `Claude.md` Header Changed from `# AGENTS.md` to `# Claude.md`

**File:** `Claude.md`, line 1
**What:** The file previously had `# AGENTS.md` as its header (matching the other AGENTS.md file). It was changed to `# Claude.md`.
**Why this is a problem:** Minor — the file content is identical to `AGENTS.md`. Having two identical guidance files is redundant and could lead to drift.
**Recommendation:** Either delete `Claude.md` and use only `AGENTS.md`, or differentiate their content if they serve different purposes.

---

### L6. `pyproject.toml` Missing Python 3.13 Classifier

**File:** `pyproject.toml`, lines 10–16
**What:** The classifiers list Python 3.11 and 3.12, but the CI matrix tests on 3.13 as well:
```toml
classifiers = [
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
```
**Why this is a problem:** Users looking at PyPI won't know 3.13 is supported.
**Recommendation:** Add `"Programming Language :: Python :: 3.13"` to classifiers.

---

### L7. Inconsistent Blank Line Removal in `bridge/src/server.ts`

**File:** `bridge/src/server.ts`, line 34–35
**What:** The refactoring commit removed a blank line between `console.log('🔒 Token...')` and the `// Initialize WhatsApp client` comment, reducing readability.
**Why this is a problem:** Minor readability regression — the blank line provided visual separation between the server startup log and the WhatsApp client initialization.
**Recommendation:** Restore the blank line for readability.

---

## Ruff Lint Results Summary

Running `ruff check .` on the current codebase produces **5 errors**:

| Rule | File | Line | Description |
|------|------|------|-------------|
| F821 | `nanobot/agent/loop.py` | 51 | Undefined name `ExecToolConfig` |
| F821 | `nanobot/agent/loop.py` | 52 | Undefined name `CronService` |
| F821 | `nanobot/agent/subagent.py` | 38 | Undefined name `ExecToolConfig` |
| F841 | `nanobot/channels/feishu.py` | 283 | Local variable `level` assigned but never used |
| F841 | `nanobot/cron/service.py` | 237 | Local variable `response` assigned but never used |

Note: `F841` would be hidden if the `pyproject.toml` ignore list (which includes `F841`) were applied during CI. The fact that ruff still reports them suggests the CI lint step may use different config or the rule was added to ignore AFTER these issues were introduced.

---

## Test Results Summary

All **55 tests pass** (pytest -v, Python 3.13):
- `tests/test_cli_input.py` — 3 tests ✅
- `tests/test_commands.py` — 4 tests ✅
- `tests/test_consolidate_offset.py` — 26 tests ✅
- `tests/test_email_channel.py` — 6 tests ✅
- `tests/test_tool_validation.py` — 6 tests ✅

**Missing test coverage for changes in these commits:**
- No tests for `format_prefix()`, `get_model_short()`, `get_provider_name()`.
- No tests for the prefix prepending behavior in `_process_message()`.
- No tests for `_guard_command()` bypass scenarios in `ExecTool`.
- No tests for `_resolve_path()` path traversal edge cases.
- No integration tests for the CI workflow itself.

---

## Recommendations Summary (Priority Order)

1. **Fix path traversal** in `filesystem.py` — use `is_relative_to()` instead of `startswith()`.
2. **Stop leaking error details** to users in `loop.py` error handler.
3. **Remove or fix `format_prefix()`** — don't prepend debug info to user-facing messages.
4. **Re-add the `CronService` import** in `loop.py` to fix F821 undefined name errors.
5. **Fix the unused variable** `level` in `feishu.py` — implement heading-level formatting.
6. **Remove `F841` from the ruff ignore list** and fix the actual issues.
7. **Add SSRF protection** to `WebFetchTool` — block private IP ranges.
8. **Require auth token** when bridge binds to non-loopback addresses.
9. **Add pip caching** to CI workflow for faster builds.
10. **Add tests** for new prefix utilities and security-critical path/command guards.
