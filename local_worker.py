#!/usr/bin/env python3
"""
Local LLM Worker - GPU-Accelerated Processing
Bridge between Claude Code and Ollama (llama3:8b on RTX GPU)
Handles heavy data processing tasks to offload Claude API limits.
"""

import requests
import json
from typing import Optional, Dict, List
from datetime import datetime

class OllamaWorker:
    """Interface to local Ollama LLM running on RTX GPU"""

    def __init__(self, model: str = "llama3:8b", base_url: str = "http://localhost:11434"):
        """
        Args:
            model: Ollama model name (default: llama3:8b)
            base_url: Ollama API endpoint
        """
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        self.log_file = "C:\\ClaudeAgent\\worker.log"

    def log(self, message: str):
        """Write to log file with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"

        print(log_line.strip())

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def is_gpu_active(self) -> bool:
        """Check if Ollama is using GPU (CUDA)"""
        try:
            # Query Ollama for loaded models
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                self.log("✅ Ollama service is running")
                return True
            return False
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Ollama not reachable: {e}")
            return False

    def process_with_rtx(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Main processing function - uses RTX GPU via Ollama

        Args:
            prompt: Text to process
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum response length

        Returns:
            Generated text or None if error
        """
        self.log(f"🔄 Processing with RTX (model: {self.model})")
        self.log(f"📝 Prompt preview: {prompt[:100]}...")

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=120  # 2min timeout for large prompts
            )

            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("response", "")

                self.log(f"✅ RTX processing complete ({len(generated_text)} chars)")
                self.log(f"📊 GPU time: {result.get('total_duration', 0) / 1e9:.2f}s")

                return generated_text
            else:
                self.log(f"❌ API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            self.log("⏱️  ERROR: Request timed out")
            return None
        except Exception as e:
            self.log(f"❌ ERROR: {e}")
            return None

    def batch_process(self, prompts: List[str]) -> List[Optional[str]]:
        """Process multiple prompts in sequence"""
        self.log(f"📦 Batch processing {len(prompts)} prompts")
        results = []

        for i, prompt in enumerate(prompts, 1):
            self.log(f"🔄 Processing {i}/{len(prompts)}")
            result = self.process_with_rtx(prompt)
            results.append(result)

        self.log(f"✅ Batch complete: {sum(1 for r in results if r)} successful")
        return results

    def classify_text(self, text: str, categories: List[str]) -> Optional[str]:
        """
        Classify text into one of the provided categories
        Useful for: FB post filtering, lead qualification, etc.
        """
        prompt = f"""Classify the following text into ONE of these categories: {', '.join(categories)}

Text: {text}

Respond with ONLY the category name, nothing else."""

        result = self.process_with_rtx(prompt, temperature=0.3)

        if result and result.strip() in categories:
            return result.strip()
        return None

    def extract_structured_data(self, text: str, fields: List[str]) -> Optional[Dict]:
        """
        Extract structured data from unstructured text
        Useful for: scraping FB posts, parsing offers, etc.
        """
        prompt = f"""Extract the following fields from this text: {', '.join(fields)}

Text: {text}

Respond with ONLY a JSON object containing the extracted fields. If a field is not found, use null."""

        result = self.process_with_rtx(prompt, temperature=0.2)

        if result:
            try:
                # Try to parse JSON response
                data = json.loads(result.strip())
                return data
            except json.JSONDecodeError:
                self.log("⚠️  WARNING: Failed to parse JSON response")
                return None
        return None

# ====================
# CONVENIENCE FUNCTIONS
# ====================

def process_with_rtx(prompt: str, **kwargs) -> Optional[str]:
    """
    Quick access function for RTX processing
    Use this as the main entry point from other scripts.
    """
    worker = OllamaWorker()
    return worker.process_with_rtx(prompt, **kwargs)

def verify_gpu_setup() -> bool:
    """Verify RTX is ready and Ollama is using GPU"""
    worker = OllamaWorker()

    print("🔍 Verifying GPU setup...")

    # Check Ollama service
    if not worker.is_gpu_active():
        print("❌ Ollama service not running")
        return False

    # Test inference
    print("🧪 Testing inference with RTX...")
    test_prompt = "Respond with exactly: RTX is handling the load"
    result = worker.process_with_rtx(test_prompt, temperature=0.0, max_tokens=50)

    if result:
        print(f"✅ Response: {result.strip()}")
        print("🎯 RTX is handling the load")
        return True
    else:
        print("❌ Inference test failed")
        return False

if __name__ == "__main__":
    # Run verification
    verify_gpu_setup()
