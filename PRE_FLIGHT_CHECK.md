# Pre-Flight Check - Token Optimization

## MANDATORY CHECK BEFORE STARTING ANY TASK

### Step 1: Classify Task Type

**Code Generation?**
- [ ] Writing new file(s)
- [ ] Generating boilerplate
- [ ] Creating documentation
- [ ] Drafting functions/classes

**Data Processing?**
- [ ] Reading multiple files
- [ ] Analyzing data
- [ ] Transforming content
- [ ] Bulk operations

**Research/Analysis?**
- [ ] Web search + summarize
- [ ] Code analysis
- [ ] Documentation reading

**If ANY checked above → GO TO STEP 2**

---

### Step 2: Can RTX Do This?

```python
# ASK YOURSELF:
# "Can I describe this task in 1-2 sentences for RTX to execute?"

# YES → Use delegation (examples below)
# NO → Do it myself (rare: user communication, critical decisions)
```

---

### Step 3: Delegation Template

#### For Code Generation:
```python
from ai_gateway import delegate_to_rtx

code = delegate_to_rtx(
    task_description="""
    Generate [WHAT]:
    - Feature 1
    - Feature 2
    - Include docstrings, error handling
    """,
    role="expert Python developer",
    temperature=0.3  # Deterministic for code
)

# Then: Read result, test, minimal polish
```

#### For Documentation:
```python
docs = delegate_to_rtx(
    task_description="Write documentation for [TOPIC]. Include examples, API reference, usage guide.",
    role="technical writer"
)
```

#### For Analysis:
```python
analysis = delegate_to_rtx(
    task_description="Read [FILE] and analyze [ASPECT]. Provide summary with key findings.",
    role="code analyst"
)
```

---

### Step 4: Estimated Token Usage

| Approach | Token Cost | When to Use |
|----------|------------|-------------|
| **Delegate to RTX** | ~100-500 | DEFAULT (95% of tasks) |
| **Do it myself** | ~5k-50k | RARE (user communication, critical fixes) |

---

## Common Mistakes to Avoid

❌ **Writing code directly with Write/Edit tools**
✅ **Generate spec → delegate_to_rtx() → polish**

❌ **Multiple Edit calls to fix formatting**
✅ **Let RTX generate, then one Edit if needed**

❌ **Creating documentation manually**
✅ **delegate_to_rtx("Write docs for X")**

---

## Emergency Override

**Only skip delegation if:**
1. Task requires real-time user input (AskUserQuestion)
2. Critical security fix (immediate action needed)
3. RTX is unreachable (verified by health check)

**Otherwise → ALWAYS DELEGATE FIRST**

---

## Token Budget Per Task

| Task Complexity | Max Claude Tokens | Notes |
|----------------|------------------|-------|
| Simple (read + answer) | 500 | Just read files, answer question |
| Medium (analysis) | 1000 | Read, delegate analysis, polish |
| Complex (code gen) | 2000 | Spec + delegation + testing + polish |
| **NEVER EXCEED** | 5000 | If >5k, you're doing RTX's job |

---

**REMEMBER: You are a MANAGER, not an EXECUTOR.**

_Last Updated: 2026-02-17_
