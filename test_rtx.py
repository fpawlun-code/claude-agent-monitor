#!/usr/bin/env python3
"""Quick RTX validation test"""

import sys
from local_worker import OllamaWorker

def main():
    print("="*60)
    print("🔍 RTX VALIDATION TEST")
    print("="*60)

    worker = OllamaWorker()

    # Test 1: Service check
    print("\n[1/3] Checking Ollama service...")
    if not worker.is_gpu_active():
        print("❌ FAILED: Ollama not running")
        return False

    # Test 2: Simple inference
    print("\n[2/3] Testing simple inference...")
    result = worker.process_with_rtx(
        "Say 'Hello from RTX' and nothing else",
        temperature=0.0,
        max_tokens=20
    )

    if not result:
        print("❌ FAILED: Inference error")
        return False

    print(f"✅ Response: {result.strip()}")

    # Test 3: Classification task
    print("\n[3/3] Testing classification...")
    category = worker.classify_text(
        text="Sprzedam mieszkanie 3 pokoje centrum",
        categories=["apartment", "house", "room", "other"]
    )

    print(f"✅ Classified as: {category}")

    print("\n" + "="*60)
    print("🎯 ALL TESTS PASSED - RTX IS READY")
    print("="*60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
