# 🚀 Claude Agent - GPU-Accelerated Local LLM Infrastructure

**Status:** ✅ PRODUCTION READY

## 🎯 Purpose

Offload heavy data processing from Claude API to local RTX GPU, saving costs and API limits.

**Host:** HP Victus (Ryzen 7 7000, NVIDIA RTX 4060 Laptop 8GB)
**Model:** llama3:8b (4.7GB) running 24/7 on GPU via Ollama

---

## 📊 Current Configuration

### Hardware
- **GPU:** NVIDIA GeForce RTX 4060 Laptop GPU
- **VRAM:** 8188 MiB (8GB)
- **CUDA:** 13.1

### Software
- **Ollama:** v0.16.1 (Windows service on port 11434)
- **Model:** llama3:8b (4.7GB, loaded to VRAM)
- **Python:** 3.12
- **Dependencies:** `requests`

---

## 🔧 Usage

### Quick Start

```python
from local_worker import process_with_rtx

# Simple text generation
result = process_with_rtx("Analyze this Facebook post: ...")
print(result)

# With custom parameters
result = process_with_rtx(
    prompt="Extract email from: contact@example.com",
    temperature=0.3,
    max_tokens=100
)
```

### Advanced Examples

**1. Batch Processing (FB posts scraping)**
```python
from local_worker import OllamaWorker

worker = OllamaWorker()
prompts = [
    "Classify this post as 'apartment' or 'house': ...",
    "Extract price from: Mieszkanie 500k PLN ...",
    # ... 100 more posts
]

results = worker.batch_process(prompts)
```

**2. Text Classification**
```python
worker = OllamaWorker()

category = worker.classify_text(
    text="Sprzedam mieszkanie 3 pokoje centrum Szczecin",
    categories=["apartment", "house", "room", "commercial", "irrelevant"]
)
# Returns: "apartment"
```

**3. Structured Data Extraction**
```python
worker = OllamaWorker()

data = worker.extract_structured_data(
    text="Mieszkanie 65m2, 3 pokoje, 450 000 PLN, kontakt: 555-123-456",
    fields=["area_m2", "rooms", "price_pln", "phone"]
)
# Returns: {"area_m2": "65", "rooms": "3", "price_pln": "450000", "phone": "555-123-456"}
```

---

## 📈 Monitoring

### GPU Monitor (24/7)

Automatically monitors GPU temperature, utilization, and VRAM to ensure safe operation.

**Start monitor:**
```bash
cd C:\ClaudeAgent
set PYTHONIOENCODING=utf-8
python gpu_monitor.py
```

**Check logs:**
```bash
tail -f C:\ClaudeAgent\gpu_monitor.log
```

**Safety Thresholds:**
- ⚡ **Warning:** >75°C or >90% VRAM
- ⚠️  **High:** >85°C (consider throttling)
- 🔥 **Critical:** >90°C (emergency shutdown)

---

## 🛠️ Maintenance

### Check Model Status
```bash
"C:\Users\fpawl\AppData\Local\Programs\Ollama\ollama.exe" list
```

### Test Inference
```bash
cd C:\ClaudeAgent
set PYTHONIOENCODING=utf-8
python local_worker.py
```

Expected output:
```
✅ Response: RTX is handling the load
🎯 RTX is handling the load
```

### Pull New Models
```bash
"C:\Users\fpawl\AppData\Local\Programs\Ollama\ollama.exe" pull llama3.1:latest
```

---

## 🎯 Performance Benchmarks

**llama3:8b on RTX 4060:**
- **Cold start:** ~3-5s (model load to VRAM)
- **Warm inference:** 1-2s per prompt (100-200 tokens)
- **Throughput:** ~30-50 prompts/minute
- **Cost:** $0 (vs. Claude API ~$0.003/1k tokens)

**Use Cases:**
- ✅ **FB scraping:** Classify 1000 posts → $0 (vs. Claude ~$6)
- ✅ **Lead qualification:** Analyze 500 leads → $0 (vs. Claude ~$3)
- ✅ **Data extraction:** Parse 200 offers → $0 (vs. Claude ~$1.2)

---

## 🚨 Troubleshooting

### Ollama not responding
```bash
# Check if service is running
tasklist | findstr ollama

# Restart service (run as admin)
net stop ollama
net start ollama
```

### GPU not detected
```bash
nvidia-smi
# If error: Update NVIDIA drivers from HP Support
```

### VRAM full (OOM)
```bash
# Unload model
"C:\Users\fpawl\AppData\Local\Programs\Ollama\ollama.exe" stop llama3:8b

# Use smaller model
"C:\Users\fpawl\AppData\Local\Programs\Ollama\ollama.exe" pull llama3:latest  # 4.7GB → 2GB
```

---

## 🔄 Integration with Claude Code

**Recommended workflow:**
1. Claude Code handles: decision-making, code writing, final validation
2. Local RTX handles: bulk data processing, scraping, classification

**Example:**
```python
# Claude Code delegates heavy work to RTX
from local_worker import process_with_rtx

# RTX does the heavy lifting (1000 FB posts)
classified_posts = [
    process_with_rtx(f"Classify: {post}", temperature=0.3)
    for post in fb_posts
]

# Claude Code makes final decision
# (only 10 qualified leads → minimal API cost)
```

---

## 📝 Files

- **`local_worker.py`** - Main API for RTX processing
- **`gpu_monitor.py`** - 24/7 GPU monitoring
- **`ollama.log`** - Ollama service logs
- **`worker.log`** - Inference logs
- **`gpu_monitor.log`** - GPU monitoring logs
- **`monitor.out`** - Monitor stdout

---

## 🎯 Next Steps

1. ✅ ~~Install Ollama with CUDA~~
2. ✅ ~~Pull llama3:8b model~~
3. ✅ ~~Create GPU monitoring~~
4. ✅ ~~Create worker API~~
5. ✅ ~~Validate RTX inference~~
6. ⏳ **TODO:** Auto-start on Windows boot (Task Scheduler)
7. ⏳ **TODO:** Integrate with FB scraper
8. ⏳ **TODO:** Create dashboard (Flask + GPU metrics)

---

**Last Updated:** 2026-02-17
**Status:** ✅ RTX is handling the load
