"""
Self-Improvement Loop - PHASE 4A Week 2 (Day 13-14)
Collects metrics, tracks trends, generates improvement recommendations.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

METRICS_FILE = Path("C:/ClaudeAgent/reports/metrics_history.json")
LOG_FILE = Path("C:/ClaudeAgent/reports/self_improvement_log.txt")
PROJECT_DIR = Path("C:/ClaudeAgent")

# KPI targets
TARGETS = {
    "test_pass_rate": 0.90,   # 90%+ tests passing
    "pylint_score": 8.0,      # 8.0+ pylint score
    "coverage": 0.50,          # 50%+ test coverage
    "drift_ratio": 0.0,        # 0% unexpected drift
}


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def collect_test_metrics() -> Dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--no-cov", "--tb=no", "-q"],
        capture_output=True, text=True, cwd=str(PROJECT_DIR),
    )
    output = result.stdout + result.stderr
    import re
    counts: Dict[str, int] = {"passed": 0, "failed": 0, "skipped": 0}
    for key in counts:
        m = re.search(rf"(\d+) {key}", output)
        if m:
            counts[key] = int(m.group(1))
    total = sum(counts.values())
    return {
        "passed": counts["passed"],
        "failed": counts["failed"],
        "skipped": counts["skipped"],
        "total": total,
        "pass_rate": counts["passed"] / total if total > 0 else 0,
    }


def collect_pylint_metrics() -> Dict[str, Any]:
    scores: Dict[str, float] = {}
    for fname in ["ai_gateway.py", "rtx_agent.py"]:
        result = subprocess.run(
            ["python", "-m", "pylint", fname, "--score=yes", "-f", "text"],
            capture_output=True, text=True, cwd=str(PROJECT_DIR),
        )
        import re
        m = re.search(r"Your code has been rated at ([\d.]+)/10", result.stdout + result.stderr)
        if m:
            scores[fname] = float(m.group(1))
    avg = sum(scores.values()) / len(scores) if scores else 0.0
    return {"scores": scores, "average": round(avg, 2)}


def collect_drift_metrics() -> Dict[str, Any]:
    drift_report = PROJECT_DIR / "reports" / "drift_report.json"
    if drift_report.exists():
        data = json.loads(drift_report.read_text())
        return {
            "drift_ratio": data.get("drift_ratio", 0),
            "changed_files": len(data.get("changed", [])),
            "alert": data.get("alert", False),
        }
    return {"drift_ratio": 0, "changed_files": 0, "alert": False}


def collect_all_metrics() -> Dict[str, Any]:
    log("[COLLECT] Gathering metrics...")
    tests = collect_test_metrics()
    log(f"  Tests: {tests['passed']}/{tests['total']} ({tests['pass_rate']:.1%})")
    pylint = collect_pylint_metrics()
    log(f"  Pylint avg: {pylint['average']}/10")
    drift = collect_drift_metrics()
    log(f"  Drift: {drift['drift_ratio']:.1%}")
    return {
        "timestamp": datetime.now().isoformat(),
        "tests": tests,
        "pylint": pylint,
        "drift": drift,
    }


def load_history() -> List[Dict[str, Any]]:
    if METRICS_FILE.exists():
        return json.loads(METRICS_FILE.read_text())
    return []


def save_history(history: List[Dict[str, Any]]) -> None:
    METRICS_FILE.parent.mkdir(exist_ok=True)
    # Keep last 30 snapshots
    METRICS_FILE.write_text(json.dumps(history[-30:], indent=2))


def generate_recommendations(current: Dict[str, Any], history: List[Dict[str, Any]]) -> List[str]:
    recs = []
    tests = current["tests"]
    pylint = current["pylint"]
    drift = current["drift"]

    # Test pass rate
    if tests["pass_rate"] < TARGETS["test_pass_rate"]:
        gap = TARGETS["test_pass_rate"] - tests["pass_rate"]
        need = int(gap * tests["total"])
        recs.append(f"Fix {need} more tests to reach {TARGETS['test_pass_rate']:.0%} pass rate (currently {tests['pass_rate']:.1%})")

    # Skipped tests
    if tests["skipped"] > 0:
        recs.append(f"Resolve {tests['skipped']} skipped tests (ReactAgent dependency issue)")

    # Pylint
    if pylint["average"] < TARGETS["pylint_score"]:
        recs.append(f"Improve pylint score: {pylint['average']}/10 -> {TARGETS['pylint_score']}/10")
    for fname, score in pylint["scores"].items():
        if score < TARGETS["pylint_score"]:
            recs.append(f"  Fix pylint issues in {fname}: {score}/10")

    # Drift
    if drift["alert"]:
        recs.append(f"ALERT: Unexpected drift {drift['drift_ratio']:.1%} in critical files!")

    # Trend analysis (if history exists)
    if len(history) >= 2:
        prev = history[-1]
        prev_rate = prev["tests"]["pass_rate"]
        curr_rate = tests["pass_rate"]
        if curr_rate < prev_rate:
            recs.append(f"REGRESSION: Test pass rate dropped {prev_rate:.1%} -> {curr_rate:.1%}")
        prev_pylint = prev["pylint"]["average"]
        if pylint["average"] < prev_pylint:
            recs.append(f"REGRESSION: Pylint score dropped {prev_pylint}/10 -> {pylint['average']}/10")

    if not recs:
        recs.append("All KPIs on target. Keep monitoring.")

    return recs


def print_kpi_table(current: Dict[str, Any]) -> None:
    tests = current["tests"]
    pylint = current["pylint"]

    def status(val: float, target: float, higher_better: bool = True) -> str:
        ok = val >= target if higher_better else val <= target
        return "[PASS]" if ok else "[FAIL]"

    print("\n--- KPI Dashboard ---")
    print(f"{'Metric':<25} {'Current':>10} {'Target':>10} {'Status':>8}")
    print("-" * 57)
    print(f"{'Test Pass Rate':<25} {tests['pass_rate']:>9.1%} {TARGETS['test_pass_rate']:>9.0%} {status(tests['pass_rate'], TARGETS['test_pass_rate']):>8}")
    print(f"{'Tests Passing':<25} {tests['passed']:>10} {'-':>10} {'':>8}")
    print(f"{'Tests Skipped':<25} {tests['skipped']:>10} {'0':>10} {status(tests['skipped'], 0, False):>8}")
    print(f"{'Pylint Average':<25} {pylint['average']:>9.2f} {TARGETS['pylint_score']:>9.1f} {status(pylint['average'], TARGETS['pylint_score']):>8}")
    print("-" * 57)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Self-Improvement Loop - ClaudeAgent")
    parser.add_argument("--run", action="store_true", help="Collect metrics and generate report")
    parser.add_argument("--history", action="store_true", help="Show metrics history trend")
    args = parser.parse_args()

    if args.run:
        current = collect_all_metrics()
        history = load_history()
        recs = generate_recommendations(current, history)

        print_kpi_table(current)

        print("\n--- Recommendations ---")
        for i, rec in enumerate(recs, 1):
            print(f"{i}. {rec}")
            log(f"[REC] {rec}")

        # Save to history
        history.append(current)
        save_history(history)
        log(f"[SAVED] Metrics snapshot #{len(history)}")

    elif args.history:
        history = load_history()
        if not history:
            print("No history yet. Run: python self_improvement.py --run")
        else:
            print(f"{'#':<4} {'Timestamp':<22} {'Pass Rate':>10} {'Pylint':>8}")
            print("-" * 48)
            for i, snap in enumerate(history[-10:], 1):
                ts = snap["timestamp"][:19]
                rate = snap["tests"]["pass_rate"]
                pyl = snap["pylint"]["average"]
                print(f"{i:<4} {ts:<22} {rate:>9.1%} {pyl:>7.2f}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
