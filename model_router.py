"""
Multi-Model Router - PHASE 4B Week 3
Auto-selects the best Ollama model per task type.
Falls back gracefully if a model is unavailable.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b"

# Model capability profiles
MODEL_PROFILES: Dict[str, Dict[str, Any]] = {
    "qwen2.5:7b": {
        "strengths": ["code", "analysis", "general"],
        "context_len": 32768,
        "speed": "fast",
        "priority": 1,
    },
    "qwen2.5:14b": {
        "strengths": ["code", "complex_reasoning", "analysis"],
        "context_len": 32768,
        "speed": "medium",
        "priority": 2,
    },
    "qwen2.5:3b": {
        "strengths": ["simple", "fast_response"],
        "context_len": 8192,
        "speed": "very_fast",
        "priority": 0,
    },
    "llama3.2:3b": {
        "strengths": ["general", "creative"],
        "context_len": 8192,
        "speed": "very_fast",
        "priority": 0,
    },
    "mistral:7b": {
        "strengths": ["code", "analysis", "instruction_following"],
        "context_len": 32768,
        "speed": "fast",
        "priority": 1,
    },
    "codellama:7b": {
        "strengths": ["code", "debugging", "refactoring"],
        "context_len": 16384,
        "speed": "fast",
        "priority": 1,
    },
    "phi3:mini": {
        "strengths": ["simple", "fast_response", "general"],
        "context_len": 4096,
        "speed": "very_fast",
        "priority": 0,
    },
}

# Task-type → preferred capabilities
TASK_ROUTING: Dict[str, List[str]] = {
    "code_generation": ["code"],
    "code_review": ["code", "analysis"],
    "debugging": ["debugging", "code"],
    "refactoring": ["refactoring", "code"],
    "analysis": ["analysis", "complex_reasoning"],
    "documentation": ["instruction_following", "general"],
    "creative": ["creative", "general"],
    "simple": ["fast_response", "simple"],
    "general": ["general"],
}


@dataclass
class RouteResult:
    model: str
    task_type: str
    reason: str
    available_models: List[str] = field(default_factory=list)
    fallback: bool = False


@dataclass
class ModelCallResult:
    model: str
    response: str
    elapsed_ms: int
    success: bool
    error: Optional[str] = None


def get_available_models() -> List[str]:
    """Query Ollama for installed models."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        pass
    return []


def detect_task_type(prompt: str) -> str:
    """Infer task type from prompt content."""
    prompt_lower = prompt.lower()

    patterns = {
        "code_generation": [r"\bwrite\b.*\b(function|class|script|code)\b", r"\bgenerate\b.*\bcode\b", r"\bimplement\b"],
        "debugging": [r"\bbug\b", r"\berror\b", r"\bfix\b.*\bcode\b", r"\bdebug\b", r"\bcrash\b"],
        "refactoring": [r"\brefactor\b", r"\bclean up\b", r"\boptimize\b.*\bcode\b"],
        "code_review": [r"\breview\b.*\bcode\b", r"\bcheck\b.*\bcode\b", r"\banalyze\b.*\bcode\b"],
        "analysis": [r"\banalyze\b", r"\bexplain\b", r"\bsummarize\b", r"\bcompare\b"],
        "documentation": [r"\bdocument\b", r"\bwrite.*doc\b", r"\bcomment\b", r"\breadme\b"],
        "creative": [r"\bwrite.*story\b", r"\bcreate.*content\b", r"\bblog\b", r"\bideate\b"],
        "simple": [r"\bwhat is\b", r"\bhow to\b", r"\bdefine\b", r"\blist\b"],
    }

    scores: Dict[str, int] = {}
    for task, pats in patterns.items():
        scores[task] = sum(1 for p in pats if re.search(p, prompt_lower))

    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "general"


def select_model(task_type: str, available: List[str], prefer_speed: bool = False) -> RouteResult:
    """Choose the best available model for the task type."""
    wanted = TASK_ROUTING.get(task_type, ["general"])

    candidates = []
    for model, profile in MODEL_PROFILES.items():
        if model not in available:
            continue
        # Score by matching strengths
        score = sum(1 for w in wanted if w in profile["strengths"])
        speed_bonus = {"very_fast": 2, "fast": 1, "medium": 0}.get(profile["speed"], 0)
        if prefer_speed:
            score += speed_bonus
        candidates.append((score, profile["priority"], model))

    if not candidates:
        return RouteResult(
            model=DEFAULT_MODEL,
            task_type=task_type,
            reason=f"No matching model available, using default ({DEFAULT_MODEL})",
            available_models=available,
            fallback=True,
        )

    # Sort by (score desc, priority desc)
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best_model = candidates[0][2]
    profile = MODEL_PROFILES[best_model]

    return RouteResult(
        model=best_model,
        task_type=task_type,
        reason=f"Matched strengths {profile['strengths']} for task '{task_type}'",
        available_models=available,
        fallback=False,
    )


def call_model(model: str, prompt: str, temperature: float = 0.3, max_tokens: int = 1000) -> ModelCallResult:
    """Send prompt to Ollama model."""
    start = time.time()
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        elapsed = int((time.time() - start) * 1000)
        if resp.status_code == 200:
            text = resp.json().get("response", "")
            return ModelCallResult(model=model, response=text, elapsed_ms=elapsed, success=True)
        return ModelCallResult(
            model=model, response="", elapsed_ms=elapsed, success=False,
            error=f"HTTP {resp.status_code}",
        )
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return ModelCallResult(model=model, response="", elapsed_ms=elapsed, success=False, error=str(e))


def route_and_call(
    prompt: str,
    task_type: Optional[str] = None,
    prefer_speed: bool = False,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """
    Full pipeline: detect task → select model → call → return result.
    Falls back to DEFAULT_MODEL if Ollama is unreachable.
    """
    available = get_available_models()

    if task_type is None:
        task_type = detect_task_type(prompt)

    if not available:
        # Ollama offline – return routing info without calling
        return {
            "model": DEFAULT_MODEL,
            "task_type": task_type,
            "response": None,
            "error": "Ollama not reachable",
            "routing": {"fallback": True, "reason": "Ollama offline"},
        }

    route = select_model(task_type, available, prefer_speed=prefer_speed)
    result = call_model(route.model, prompt, temperature=temperature)

    return {
        "model": result.model,
        "task_type": task_type,
        "response": result.response if result.success else None,
        "error": result.error,
        "elapsed_ms": result.elapsed_ms,
        "routing": {
            "fallback": route.fallback,
            "reason": route.reason,
            "available_models": available,
        },
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Model Router")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--detect", metavar="PROMPT", help="Detect task type from prompt")
    parser.add_argument("--route", metavar="PROMPT", help="Show routing decision (no call)")
    parser.add_argument("--call", metavar="PROMPT", help="Route + call model")
    parser.add_argument("--task", default=None, help="Override task type")
    parser.add_argument("--speed", action="store_true", help="Prefer faster models")
    args = parser.parse_args()

    if args.list:
        models = get_available_models()
        if models:
            print(f"Available models ({len(models)}):")
            for m in models:
                profile = MODEL_PROFILES.get(m, {})
                strengths = ", ".join(profile.get("strengths", ["unknown"]))
                speed = profile.get("speed", "unknown")
                print(f"  {m:<25} [{speed}]  strengths: {strengths}")
        else:
            print("No models found (Ollama offline or no models installed)")

    elif args.detect:
        task = detect_task_type(args.detect)
        print(f"Task type: {task}")

    elif args.route:
        available = get_available_models()
        task = args.task or detect_task_type(args.route)
        route = select_model(task, available, prefer_speed=args.speed)
        print(f"Task type  : {route.task_type}")
        print(f"Model      : {route.model}")
        print(f"Reason     : {route.reason}")
        print(f"Fallback   : {route.fallback}")
        print(f"Available  : {route.available_models}")

    elif args.call:
        result = route_and_call(args.call, task_type=args.task, prefer_speed=args.speed)
        print(f"Model    : {result['model']}")
        print(f"Task     : {result['task_type']}")
        print(f"Routing  : {result['routing']['reason']}")
        if result.get("response"):
            print(f"Response : {result['response'][:500]}")
        elif result.get("error"):
            print(f"Error    : {result['error']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
