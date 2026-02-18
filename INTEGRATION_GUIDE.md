# Claude Code + RTX Agent - Integration Guide

## System Status

✅ **rtx_agent.py** - ReAct agent deployed
✅ **ai_gateway.py** - Bridge to Ollama ready
⚠️ **Action parsing** - Requires fine-tuning for complex tool usage

## Quick Start

### 1. Test RTX Agent Standalone
```bash
cd C:\ClaudeAgent
python rtx_agent.py --task "Calculate 5 * 8"
```

### 2. Test with File Operations
```bash
python rtx_agent.py --task "Read ai_gateway.py and count lines"
```

### 3. Integration with Claude Code

**Before (100% Claude tokens):**
```python
# User asks: "Analyze storage.json"
# Claude:
#   - Reads file (tokens)
#   - Analyzes data (tokens)
#   - Generates report (tokens)
```

**After (5-10% Claude tokens):**
```python
# Claude receives: "Analyze storage.json"

# Step 1: Claude delegates to RTX (writes task JSON)
import subprocess
import json

task = "Read C:\\ClaudeAgent\\storage.json and analyze its structure"
result = subprocess.run(
    ["python", "C:\\ClaudeAgent\\rtx_agent.py", "--task", task],
    capture_output=True,
    text=True
)

# Step 2: RTX executes autonomously (0 Claude tokens)
# - Llama 3 on RTX GPU
# - Uses tools (read_file, etc.)
# - Returns final answer

# Step 3: Claude polishes output (minimal tokens)
rtx_output = result.stdout
print(f"Analysis: {rtx_output}")
```

## Integration Function for Claude

Add to `ai_gateway.py`:

```python
def claude_delegate_autonomous(task: str, max_iterations: int = 10) -> Dict[str, Any]:
    """
    Claude delegates task to autonomous RTX agent

    Args:
        task: Natural language task description
        max_iterations: Max ReAct iterations

    Returns:
        {
            "success": bool,
            "final_answer": str,
            "iterations": int
        }
    """
    import subprocess

    cmd = [
        "python",
        "C:\\ClaudeAgent\\rtx_agent.py",
        "--task", task,
        "--max-iterations", str(max_iterations)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    # Parse output
    if "[SUCCESS]" in result.stdout:
        # Extract final answer (between success header and stats)
        lines = result.stdout.split('\n')
        answer_lines = []
        capture = False

        for line in lines:
            if "[SUCCESS]" in line:
                capture = True
                continue
            if "[STATS]" in line or "====" in line:
                capture = False
            if capture and line.strip():
                answer_lines.append(line)

        return {
            "success": True,
            "final_answer": '\n'.join(answer_lines).strip(),
            "raw_output": result.stdout
        }
    else:
        return {
            "success": False,
            "error": result.stderr or result.stdout
        }
```

## Usage in Claude Code

```python
# In your Claude workflow:
from ai_gateway import claude_delegate_autonomous

# User: "Read config.json and extract the API key"
result = claude_delegate_autonomous(
    task="Read C:\\MyProject\\config.json and extract the value of 'api_key' field"
)

if result["success"]:
    print(result["final_answer"])  # Uses minimal tokens to display
else:
    print("RTX agent failed:", result["error"])
```

## Current Limitations

### ⚠️ Action Parser Needs Improvement

**Problem:**
- Llama 3 8B sometimes generates wrong format
- Expected: `Action: tool_name(arg="value")`
- Actual: `Action: tool_name()` or narrative text

**Solutions:**
1. **Use larger model:**
   ```bash
   python rtx_agent.py --model "llama3:70b" --task "..."
   ```

2. **Fine-tune prompt:** Modify system prompt in `rtx_agent.py` to be more explicit

3. **Use for simple tasks first:** Math, text generation, summaries work well

4. **Fallback to ai_gateway.py:** For complex tool usage, use simple delegation:
   ```python
   from ai_gateway import ask_rtx

   # Generate code (no tools needed)
   result = ask_rtx("Write a Python function to validate email")
   ```

## Best Use Cases Right Now

### ✅ Works Well:
- Mathematical calculations
- Code generation (drafts)
- Text summarization
- Simple Q&A
- Creative writing

### ⚠️ Needs Improvement:
- Complex file operations (multiple tool calls)
- Shell scripting automation
- Multi-step research

## Recommended Workflow

**Phase 1: Simple Delegation (Current)**
```python
# Use for: code gen, math, summaries
from ai_gateway import ask_rtx

draft = ask_rtx("Generate FastAPI boilerplate for user auth")
# Claude polishes output
```

**Phase 2: Autonomous Tools (After Fine-tuning)**
```python
# Use for: file ops, research, automation
from ai_gateway import claude_delegate_autonomous

result = claude_delegate_autonomous(
    "Read all .md files in C:\\Docs and create a summary"
)
```

## Next Steps

1. **Test current functionality:**
   - Math/calculation tasks ✅
   - Code generation ✅
   - Simple file reads ⚠️

2. **Improve action parsing:**
   - Fine-tune system prompt
   - Add examples to model context
   - Consider llama3:70b for better reasoning

3. **Add more tools:**
   - Git operations
   - Database queries
   - API calls

4. **Monitor token savings:**
   ```bash
   tail -f C:\ClaudeAgent\usage_stats.jsonl
   ```

## Summary

| Component | Status | Use Case |
|-----------|--------|----------|
| **ai_gateway.py** | ✅ Production | Simple delegation, code gen, drafts |
| **rtx_agent.py** | ⚠️ Beta | Math, Q&A, simple tool usage |
| **ReAct Loop** | ⚠️ Needs tuning | Complex multi-tool workflows |

**Recommendation:** Start with `ai_gateway.py` for immediate 90% token savings. Use `rtx_agent.py` for tasks that don't require complex tool chaining.

---

Last Updated: 2026-02-17
