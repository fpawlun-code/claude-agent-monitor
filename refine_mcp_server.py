"""Refine Token Guard to proper MCP protocol"""
from ai_gateway import delegate_to_rtx

task = """Refine the Token Guard implementation to PROPER MCP SERVER PROTOCOL.

CRITICAL FIXES NEEDED:
1. Use stdio-based JSON-RPC protocol (MCP standard)
2. Implement tool interception via MCP hooks
3. Add proper request/response handling
4. Tool call format: {"jsonrpc": "2.0", "method": "tools/call", ...}

MCP PROTOCOL STRUCTURE:
- Initialize handshake
- Handle tool list requests
- Intercept tool calls BEFORE execution
- Return modified calls or errors

INTERCEPTION LOGIC:
```python
def intercept_tool_call(tool_name, params):
    if tool_name == "Read":
        return {
            "error": "Use delegate_read() instead",
            "redirect": "delegate_read",
            "params": params
        }

    if tool_name == "Bash" and is_long_output(params["command"]):
        return {
            "error": "Use delegate_bash() instead",
            "redirect": "delegate_bash",
            "params": params
        }

    # Track tokens
    if session_tokens > 1000:
        return {"error": "Token budget exceeded"}

    return {"allow": True}
```

REQUIREMENTS:
- stdio communication (read from stdin, write to stdout)
- JSON-RPC 2.0 format
- Stateful session tracking
- Token counting per request/response
- Logging to file (not stdout - that's for protocol)

Return COMPLETE, PRODUCTION-READY implementation with:
1. token_guard_server.py (proper MCP protocol)
2. Example requests/responses
3. claude.json integration
4. Testing script"""

result = delegate_to_rtx(
    task_description=task,
    role="expert MCP protocol developer",
    temperature=0.2  # Low temp for precise protocol implementation
)

print(result)
