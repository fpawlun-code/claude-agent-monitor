# 🎯 OLLAMA-FIRST WORKFLOW

**Status:** ✅ ACTIVE (2026-02-17)

**Philosophy:** Claude Code = Manager | Ollama (RTX) = Worker

---

## 🔄 **NEW ARCHITECTURE**

### Before (Token-Heavy)
```
User → Claude Code (Sonnet 4.5) → Full code generation
                                 → Full analysis
                                 → Bulk processing
        ↓
    Expensive (all tokens)
```

### After (Ollama-First)
```
User → Claude Code (Manager)
        ↓
    1. Writes prompt for RTX
    2. Delegates to ai_gateway.py
        ↓
    Ollama (RTX Worker)
        ↓
    3. Generates draft/boilerplate ($0)
    4. Processes bulk data ($0)
        ↓
    Claude Code (Finisher)
        ↓
    5. Reads RTX output
    6. Polishes & validates (minimal tokens)
```

**Savings:** 90-95% tokens for bulk/draft work

---

## 📊 **USE CASES**

### ✅ Delegate to RTX (Ollama)

**When:**
- Bulk processing (100+ items)
- Initial code drafts / boilerplate
- Data extraction / parsing
- Classification tasks
- Research / summarization
- Repetitive analysis

**Example:**
```python
from ai_gateway import delegate_to_rtx

# RTX generates boilerplate (0 Claude tokens)
html_draft = delegate_to_rtx(
    task_description="Create HTML structure for brewery website with header, hero, and footer",
    role="expert web developer",
    save_as="brewery_draft.html"
)

# Claude only polishes the draft (minimal tokens)
```

### ❌ Keep with Claude

**When:**
- Final decision making
- Complex architecture design
- Creative work (UI/UX)
- Code review & validation
- Security-critical code
- Small tasks (<100 tokens)

---

## 🛠️ **PRACTICAL EXAMPLES**

### Example 1: Website Building

**OLD WAY (Token-Heavy):**
```
User: "Create a landing page for brewery"
Claude: *generates 500 lines of HTML/CSS directly* (2000+ tokens)
```

**NEW WAY (Ollama-First):**
```python
# Step 1: Claude delegates to RTX
from ai_gateway import delegate_to_rtx

html = delegate_to_rtx(
    task_description="""Create a modern landing page HTML structure:
    - Header with logo and nav
    - Hero section with image
    - About section
    - Products grid
    - Contact form
    - Footer

    Use semantic HTML5, modern CSS Grid/Flexbox.
    """,
    role="expert frontend developer",
    temperature=0.5,
    save_as="brewery_landing.html"
)

# Step 2: Claude reads and polishes (100-200 tokens)
# - Fix edge cases
# - Add specific brewery branding
# - Validate accessibility

# Savings: ~1800 tokens (90%)
```

### Example 2: FB Lead Generation

**OLD WAY:**
```
User: "Analyze 1000 FB posts and find apartments"
Claude: *processes each post manually* (500k+ tokens = ~$4.50)
```

**NEW WAY:**
```python
from fb_monitor_engine import FBMonitorEngine

engine = FBMonitorEngine()

# RTX processes 1000 posts (0 Claude tokens)
qualified_leads = engine.process_batch(fb_posts)  # $0

# Claude only validates final 50 leads (2500 tokens = ~$0.02)

# Savings: $4.48 (99.5%)
```

### Example 3: Code Generation

**OLD WAY:**
```
User: "Create a FastAPI backend with user auth"
Claude: *writes entire codebase* (5000+ tokens)
```

**NEW WAY:**
```python
# Step 1: RTX generates structure
boilerplate = delegate_to_rtx(
    task_description="""Create FastAPI backend structure:
    - main.py with app initialization
    - routes/users.py with CRUD endpoints
    - models/user.py with SQLAlchemy User model
    - auth/jwt.py with JWT authentication
    - database.py with connection setup

    Include type hints and docstrings.
    """,
    role="expert Python backend developer",
    temperature=0.3
)

# Step 2: Claude reviews and adds:
# - Security best practices
# - Error handling
# - Specific business logic

# Savings: ~4000 tokens (80%)
```

---

## 🎯 **WHEN TO USE WHICH MODEL**

| Task Type | Use | Reason |
|---|---|---|
| **Boilerplate code** | RTX | Generic, repeatable |
| **Initial drafts** | RTX | Quantity over quality |
| **Bulk data processing** | RTX | 1000+ items, simple logic |
| **Classification** | RTX | Pattern matching |
| **Extraction** | RTX | Structured data parsing |
| **Research** | RTX | Summarization, info gathering |
| **Final polish** | Claude | Quality, nuance, decisions |
| **Security review** | Claude | Critical thinking required |
| **Architecture** | Claude | Complex trade-offs |
| **Creative UI/UX** | Claude | Aesthetics, user experience |

---

## 💰 **COST COMPARISON**

### Scenario: Build E-commerce Website

**Full Claude (Old):**
- HTML/CSS/JS generation: 10,000 tokens = $0.15
- Backend API: 8,000 tokens = $0.12
- Database models: 3,000 tokens = $0.045
- Testing: 2,000 tokens = $0.03
- **Total: $0.345**

**Ollama-First (New):**
- RTX generates drafts: 0 tokens = $0
- Claude polishes (10%): 2,300 tokens = $0.035
- **Total: $0.035**
- **Savings: $0.31 (90%)**

### Scenario: 1000 FB Posts Analysis

**Full Claude:**
- 1000 posts × 500 tokens = 500,000 tokens
- Cost: ~$4.50

**Ollama-First:**
- RTX processes 1000 posts: $0
- Claude validates 50 leads: ~2,500 tokens = $0.02
- **Savings: $4.48 (99.5%)**

---

## 🚀 **HOW TO USE**

### Quick Start

```python
from ai_gateway import delegate_to_rtx

# Simple delegation
result = delegate_to_rtx(
    task_description="Write a Python function to sort a list",
    role="expert Python developer"
)

print(result)
```

### Advanced Usage

```python
from ai_gateway import LocalAI

gateway = LocalAI()

# Custom parameters
result = gateway.ask_rtx(
    prompt="Analyze this text and extract key points: ...",
    system_context="You are an expert data analyst",
    temperature=0.3,  # Lower = more deterministic
    max_tokens=2000,
    save_to_file="analysis_output.txt"
)

if result["success"]:
    print(f"Tokens saved: {result['tokens_saved_estimate']}")
    print(f"Output: {result['output_file']}")
```

### Batch Processing

```python
from ai_gateway import LocalAI

gateway = LocalAI()

prompts = [
    "Classify: Sprzedam mieszkanie...",
    "Classify: Dom na sprzedaż...",
    # ... 1000 more
]

results = gateway.batch_ask(
    prompts=prompts,
    system_context="You are a real estate classifier",
    temperature=0.2
)

# Check usage stats
stats = gateway.get_usage_stats()
print(f"Total saved: ${stats['estimated_cost_saved_usd']}")
```

---

## 📈 **USAGE STATISTICS**

Track your savings:

```python
from ai_gateway import LocalAI

gateway = LocalAI()
stats = gateway.get_usage_stats()

print(f"""
📊 RTX Usage Statistics:
- Total requests: {stats['total_requests']}
- Tokens saved: ~{stats['total_tokens_saved']:,}
- GPU time: {stats['total_gpu_time_hours']:.2f} hours
- Cost saved: ${stats['estimated_cost_saved_usd']}
""")
```

Logs saved to:
- `C:\ClaudeAgent\ai_gateway.log` - Activity log
- `C:\ClaudeAgent\usage_stats.jsonl` - Usage tracking

---

## ⚡ **PERFORMANCE**

**RTX 4060 Laptop (8GB VRAM):**
- **Cold start:** 3-5s (model load)
- **Warm inference:** 0.3-2s per prompt
- **Throughput:** 30-50 prompts/min
- **Cost:** $0 (electricity only)

**vs. Claude API:**
- **Latency:** Similar (1-3s)
- **Quality:** 80-90% for simple tasks, 60-70% for complex
- **Cost:** 99% cheaper

**Best for:**
- High volume (>100 items)
- Low-medium complexity
- Draft/boilerplate generation

---

## 🎯 **BEST PRACTICES**

1. **Start with RTX** - Default to Ollama for initial work
2. **Claude finishes** - Use Claude for polish & validation
3. **Monitor quality** - Check RTX output, adjust temperature
4. **Track savings** - Review `usage_stats.jsonl` regularly
5. **Iterate prompts** - Refine prompts for better RTX results

---

## 🔧 **TROUBLESHOOTING**

**RTX too slow:**
- Lower `max_tokens` parameter
- Increase `temperature` (faster but less accurate)
- Use smaller model: `llama3:latest` (4.7GB → 2GB)

**RTX quality too low:**
- Lower `temperature` (0.1-0.3 for deterministic)
- Improve prompt specificity
- Use Claude for this task instead

**Out of VRAM:**
- Close other GPU apps
- Use smaller model
- Restart Ollama service

---

## 📝 **FILES**

- `ai_gateway.py` - Universal RTX bridge
- `fb_monitor_engine.py` - Real estate scraping engine
- `outputs/` - RTX generated files
- `fb_data/` - Processed leads
- `ai_gateway.log` - Activity log
- `usage_stats.jsonl` - Token savings tracking

---

**Last Updated:** 2026-02-17
**Status:** ✅ Production Ready
**Savings:** 90-95% tokens on bulk/draft work
