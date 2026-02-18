"""Generate Token Guard MCP server via RTX delegation"""
from ai_gateway import delegate_to_rtx

task = """Create a complete MCP server called 'token-guard' that intercepts Claude Code tool calls.

REQUIREMENTS:
1. MCP Server Protocol (stdio-based)
2. Intercept tool calls BEFORE execution
3. Block violations:
   - Direct Read() usage → redirect to delegate_read()
   - Direct Bash() for long output → redirect to delegate_bash()
   - Responses >1000 tokens → warning/block
4. Token tracking per session
5. Auto-redirect capability
6. Logging system

TECHNICAL SPECS:
- Python 3.10+
- MCP SDK for tool interception
- Token estimation (rough: chars/4)
- Session state tracking
- Config file support

OUTPUT:
1. token_guard_server.py (main server)
2. token_guard_config.json (config)
3. Instructions for claude.json integration
4. Test examples

Make it production-ready, well-documented, with error handling."""

result = delegate_to_rtx(
    task_description=task,
    role="expert Python MCP server developer",
    temperature=0.3
)

print(result)
