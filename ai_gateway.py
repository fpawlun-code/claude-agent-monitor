#!/usr/bin/env python3
"""
AI Gateway - Universal Bridge to Local RTX (Ollama)
Manages delegation of tasks from Claude Code to local Llama 3 on RTX GPU.

WORKFLOW:
1. Claude receives task → writes prompt for Ollama
2. ai_gateway sends to RTX (0 Claude tokens)
3. Ollama generates draft/analysis (runs on GPU)
4. Claude reads output and polishes (minimal tokens)

SAVINGS: 90-95% token reduction for bulk/draft work
"""

import requests
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

class LocalAI:
    """Universal gateway to local Llama 3 on RTX GPU"""

    def __init__(
        self,
        model: str = "llama3:8b",
        base_url: str = "http://localhost:11434",
        output_dir: str = "C:\\ClaudeAgent\\outputs"
    ):
        """
        Args:
            model: Ollama model name
            base_url: Ollama API endpoint
            output_dir: Where to save RTX outputs
        """
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.log_file = Path("C:\\ClaudeAgent\\ai_gateway.log")
        self.usage_log = Path("C:\\ClaudeAgent\\usage_stats.jsonl")

    def log(self, message: str, level: str = "INFO"):
        """Write to log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"

        print(log_line.strip())

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def log_usage(self, stats: Dict[str, Any]):
        """Track token savings and RTX usage"""
        stats["timestamp"] = datetime.now().isoformat()

        with open(self.usage_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(stats) + "\n")

    def ask_rtx(
        self,
        prompt: str,
        system_context: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        save_to_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        MAIN METHOD: Ask RTX to process task (via Ollama)

        Args:
            prompt: The actual question/task for RTX
            system_context: System instructions (role, constraints)
            temperature: 0.0 (deterministic) to 1.0 (creative)
            max_tokens: Max response length
            save_to_file: Optional filename to save response

        Returns:
            {
                "success": bool,
                "response": str,
                "gpu_time_seconds": float,
                "tokens_saved_estimate": int,
                "output_file": str | None
            }
        """
        start_time = time.time()

        # Build full prompt
        full_prompt = prompt
        if system_context:
            full_prompt = f"{system_context}\n\n{prompt}"

        self.log(f"🔄 Delegating to RTX: {prompt[:80]}...")

        try:
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=300  # 5min for large tasks
            )

            if response.status_code != 200:
                self.log(f"❌ API error: {response.status_code}", "ERROR")
                return {
                    "success": False,
                    "response": None,
                    "error": f"HTTP {response.status_code}"
                }

            result = response.json()
            generated_text = result.get("response", "")
            gpu_time = result.get("total_duration", 0) / 1e9  # nanoseconds → seconds

            elapsed = time.time() - start_time

            # Estimate Claude tokens saved
            # Assumption: 1 token ≈ 4 chars
            estimated_tokens_saved = len(generated_text) // 4

            self.log(f"✅ RTX complete: {len(generated_text)} chars in {gpu_time:.2f}s GPU")
            self.log(f"💰 Estimated tokens saved: ~{estimated_tokens_saved}")

            # Save to file if requested
            output_file = None
            if save_to_file:
                output_file = self.output_dir / save_to_file
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(generated_text)
                self.log(f"📁 Saved to: {output_file}")

            # Log usage stats
            self.log_usage({
                "prompt_preview": prompt[:100],
                "response_chars": len(generated_text),
                "gpu_time_seconds": gpu_time,
                "wall_time_seconds": elapsed,
                "estimated_tokens_saved": estimated_tokens_saved,
                "temperature": temperature,
                "output_file": str(output_file) if output_file else None
            })

            return {
                "success": True,
                "response": generated_text,
                "gpu_time_seconds": gpu_time,
                "tokens_saved_estimate": estimated_tokens_saved,
                "output_file": str(output_file) if output_file else None
            }

        except requests.exceptions.Timeout:
            self.log("⏱️  ERROR: Request timed out", "ERROR")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            self.log(f"❌ ERROR: {e}", "ERROR")
            return {"success": False, "error": str(e)}

    def batch_ask(
        self,
        prompts: list[str],
        system_context: str = "",
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Process multiple prompts sequentially"""
        self.log(f"📦 Batch processing {len(prompts)} prompts on RTX")

        results = []
        total_tokens_saved = 0

        for i, prompt in enumerate(prompts, 1):
            self.log(f"🔄 Batch {i}/{len(prompts)}")
            result = self.ask_rtx(prompt, system_context, **kwargs)
            results.append(result)

            if result.get("success"):
                total_tokens_saved += result.get("tokens_saved_estimate", 0)

        self.log(f"✅ Batch complete: {sum(1 for r in results if r.get('success'))} successful")
        self.log(f"💰 TOTAL tokens saved: ~{total_tokens_saved}")

        return results

    def health_check(self) -> bool:
        """Check if Ollama service is reachable"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                self.log("✅ RTX gateway healthy")
                return True
            return False
        except Exception as e:
            self.log(f"❌ RTX gateway unreachable: {e}", "ERROR")
            return False

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get cumulative token savings"""
        if not self.usage_log.exists():
            return {"total_requests": 0, "total_tokens_saved": 0}

        total_requests = 0
        total_tokens_saved = 0
        total_gpu_time = 0

        with open(self.usage_log, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    total_requests += 1
                    total_tokens_saved += entry.get("estimated_tokens_saved", 0)
                    total_gpu_time += entry.get("gpu_time_seconds", 0)
                except:
                    continue

        # Estimate cost savings (Claude Sonnet 4.5: ~$3/1M input + $15/1M output)
        # Conservative: assume 50% input, 50% output = avg $9/1M tokens
        cost_saved_usd = (total_tokens_saved / 1_000_000) * 9

        return {
            "total_requests": total_requests,
            "total_tokens_saved": total_tokens_saved,
            "total_gpu_time_hours": total_gpu_time / 3600,
            "estimated_cost_saved_usd": round(cost_saved_usd, 2)
        }

# ====================
# CONVENIENCE FUNCTIONS
# ====================

def ask_rtx(prompt: str, system_context: str = "", **kwargs) -> Dict[str, Any]:
    """Quick access to RTX gateway"""
    gateway = LocalAI()
    return gateway.ask_rtx(prompt, system_context, **kwargs)

def delegate_to_rtx(
    task_description: str,
    role: str = "expert developer",
    save_as: Optional[str] = None,
    **kwargs
) -> str:
    """
    High-level delegation function

    Args:
        task_description: What you want RTX to do
        role: System role (e.g., "expert Python developer")
        save_as: Filename to save output
        **kwargs: Additional args for ask_rtx()

    Returns:
        Generated text from RTX
    """
    system_context = f"You are an {role}. Follow instructions precisely."

    gateway = LocalAI()
    result = gateway.ask_rtx(
        prompt=task_description,
        system_context=system_context,
        save_to_file=save_as,
        **kwargs
    )

    if result.get("success"):
        return result["response"]
    else:
        raise RuntimeError(f"RTX delegation failed: {result.get('error')}")

if __name__ == "__main__":
    # Test the gateway
    print("="*60)
    print("🔍 AI GATEWAY HEALTH CHECK")
    print("="*60)

    gateway = LocalAI()

    # Test 1: Health check
    print("\n[1/3] Checking RTX connection...")
    if not gateway.health_check():
        print("❌ FAILED: Ollama not reachable")
        exit(1)

    # Test 2: Simple task
    print("\n[2/3] Testing simple delegation...")
    result = gateway.ask_rtx(
        prompt="Write a Python function that adds two numbers. Include docstring.",
        system_context="You are an expert Python developer.",
        temperature=0.3,
        save_to_file="test_output.txt"
    )

    if result["success"]:
        print(f"✅ Success: {result['tokens_saved_estimate']} tokens saved")
        print(f"📁 Output: {result['output_file']}")
    else:
        print(f"❌ Failed: {result.get('error')}")

    # Test 3: Usage stats
    print("\n[3/3] Checking usage statistics...")
    stats = gateway.get_usage_stats()
    print(f"📊 Total requests: {stats['total_requests']}")
    print(f"💰 Tokens saved: ~{stats['total_tokens_saved']}")
    print(f"💵 Cost saved: ${stats['estimated_cost_saved_usd']}")

    print("\n" + "="*60)
    print("🎯 AI GATEWAY READY")
    print("="*60)
