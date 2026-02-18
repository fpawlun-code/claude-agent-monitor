"""Generate Token Guard wrapper script via RTX"""
from ai_gateway import delegate_to_rtx

task = """Create a WRAPPER SCRIPT that intercepts Claude Code CLI and enforces token rules.

ARCHITECTURE:
```
User types: python token_guard.py [args]
    ↓
token_guard.py intercepts and monitors
    ↓
Launches: claude-code [args]
    ↓
Monitors API calls in real-time
```

CORE FUNCTIONALITY:

1. **Launch Claude Code as subprocess**
   - Pass through all arguments
   - Capture stdout/stderr
   - Monitor in real-time

2. **Intercept tool calls** (detect in output stream)
   - Watch for Read() pattern in conversation
   - Watch for Bash() pattern
   - Detect when I'm about to use them

3. **Enforcement rules**
   ```python
   VIOLATIONS = {
       "Read(": "BLOCKED! Use delegate_read() instead",
       "Bash(": "WARNING! Should use delegate_bash() for long output",
   }
   ```

4. **Token tracking**
   - Parse API responses for token counts
   - Track per-turn usage
   - Alert at 500 tokens (warning)
   - Block at 1000 tokens (hard limit)

5. **Real-time alerts**
   - Print to terminal in RED when violation detected
   - Offer to auto-fix (suggest delegate_read instead)
   - Log everything to token_guard.log

6. **Statistics dashboard**
   - Session start: show rules loaded
   - Per turn: show token usage
   - Session end: show total savings

TECHNICAL REQUIREMENTS:
- Python 3.10+
- subprocess with real-time output capture
- Pattern matching for tool detection
- ANSI color codes for alerts
- Non-blocking I/O for monitoring
- Signal handling for clean shutdown

OUTPUT FILES:
1. token_guard.py (main wrapper)
2. token_guard_config.json (rules config)
3. Usage instructions
4. Test examples

Make it PRODUCTION-READY with proper error handling and logging."""

result = delegate_to_rtx(
    task_description=task,
    role="expert Python systems developer",
    temperature=0.3
)

# Save to file instead of printing (encoding issues)
with open('token_guard_output.txt', 'w', encoding='utf-8') as f:
    f.write(result)

print("[OK] Generated wrapper saved to token_guard_output.txt")
