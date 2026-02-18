"""
Integration Test - PHASE 4A Week 3 (Day 20-21)
Full system test: runs all PHASE 4A components together.
Reports pass/fail for each subsystem.
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_DIR = Path("C:/ClaudeAgent")
REPORT_FILE = PROJECT_DIR / "reports" / "integration_test_report.json"


def run(cmd: List[str], timeout: int = 60) -> Tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_DIR), timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def header(msg: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print("=" * 60)


def check(name: str, passed: bool, detail: str = "") -> Dict[str, Any]:
    symbol = "[PASS]" if passed else "[FAIL]"
    line = f"  {symbol} {name}"
    if detail:
        line += f" - {detail}"
    print(line)
    return {"name": name, "passed": passed, "detail": detail}


# ── Subsystem Tests ──────────────────────────────────────────

def test_pytest_suite() -> List[Dict[str, Any]]:
    header("1. Pytest Suite")
    results = []
    code, out = run([sys.executable, "-m", "pytest", "tests/", "--no-cov", "--tb=no", "-q"])
    import re
    counts = {k: 0 for k in ("passed", "failed", "skipped")}
    for key in counts:
        m = re.search(rf"(\d+) {key}", out)
        if m:
            counts[key] = int(m.group(1))
    total = sum(counts.values())
    rate = counts["passed"] / total if total > 0 else 0

    results.append(check("Tests collected", total >= 25, f"{total} tests"))
    results.append(check("Pass rate >= 83%", rate >= 0.83, f"{rate:.1%}"))
    results.append(check("No failures", counts["failed"] == 0, f"{counts['failed']} failed"))
    return results


def test_drift_detector() -> List[Dict[str, Any]]:
    header("2. Drift Detector")
    results = []
    # Check snapshot exists
    snap = PROJECT_DIR / ".drift_snapshot.json"
    results.append(check("Snapshot file exists", snap.exists(), str(snap)))

    # Run --check
    code, out = run([sys.executable, "drift_detector.py", "--check"])
    results.append(check("drift_detector.py --check", code == 0, out[:80]))

    # Validate report
    report = PROJECT_DIR / "reports" / "drift_report.json"
    if report.exists():
        data = json.loads(report.read_text())
        results.append(check("Drift report valid", "drift_ratio" in data, ""))
        results.append(check("No unexpected drift", not data.get("alert", False),
                             f"drift={data.get('drift_ratio', 0):.1%}"))
    else:
        results.append(check("Drift report exists", False, "not found"))
    return results


def test_auto_fix() -> List[Dict[str, Any]]:
    header("3. Auto-Fix Tests")
    results = []
    code, out = run([sys.executable, "auto_fix_tests.py", "--diagnose"])
    results.append(check("auto_fix_tests.py runs", code == 0, ""))
    results.append(check("No unknown failures",
                         "UNKNOWN" not in out or "No failures detected" in out,
                         out[:80] if "UNKNOWN" in out else "OK"))
    return results


def test_self_improvement() -> List[Dict[str, Any]]:
    header("4. Self-Improvement Loop")
    results = []
    code, out = run([sys.executable, "self_improvement.py", "--run"])
    results.append(check("self_improvement.py runs", code == 0, ""))

    history = PROJECT_DIR / "reports" / "metrics_history.json"
    results.append(check("Metrics history saved", history.exists(), ""))

    if history.exists():
        data = json.loads(history.read_text())
        results.append(check("History not empty", len(data) > 0, f"{len(data)} snapshot(s)"))
    return results


def test_alerting() -> List[Dict[str, Any]]:
    header("5. Alerting System")
    results = []
    # Init config
    code, out = run([sys.executable, "alerting.py", "--init"])
    results.append(check("Config created", (PROJECT_DIR / "alerting_config.json").exists(), ""))

    # Fire test alert
    code, out = run([sys.executable, "alerting.py", "--test"])
    results.append(check("Test alert fires", code == 0, ""))

    # Check rules
    code, out = run([sys.executable, "alerting.py", "--check"])
    results.append(check("Alert check runs", code == 0, out[:80]))

    # Verify log
    log = PROJECT_DIR / "reports" / "alert_history.log"
    results.append(check("Alert log exists", log.exists(), ""))
    return results


def test_monitoring_dashboard() -> List[Dict[str, Any]]:
    header("6. Monitoring Dashboard")
    results = []
    code, out = run([sys.executable, "monitoring_dashboard.py", "--snapshot"])
    results.append(check("Dashboard snapshot runs", code == 0, ""))
    results.append(check("KPI table rendered", "KPI Status" in out or "Metric" in out, out[:60]))
    return results


def test_ci_cd() -> List[Dict[str, Any]]:
    header("7. CI/CD Hooks")
    results = []
    # Check workflows exist
    workflows = list((PROJECT_DIR / ".github" / "workflows").glob("*.yml"))
    results.append(check("GitHub Actions workflows exist", len(workflows) >= 2, f"{len(workflows)} files"))

    # Check pre-commit installed
    pre_commit_config = PROJECT_DIR / ".pre-commit-config.yaml"
    results.append(check("Pre-commit config exists", pre_commit_config.exists(), ""))

    # Verify mypy passes on main files
    code, out = run([sys.executable, "-m", "mypy", "ai_gateway.py", "rtx_agent.py",
                     "--ignore-missing-imports", "--no-strict-optional"])
    results.append(check("Mypy clean on source files", code == 0, out[:60] if code != 0 else "0 errors"))
    return results


# ── Main ──────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="PHASE 4A Integration Test")
    parser.add_argument("--full", action="store_true", help="Run full integration test")
    parser.add_argument("--fast", action="store_true", help="Skip slow subtests (pytest)")
    args = parser.parse_args()

    if not args.full and not args.fast:
        parser.print_help()
        return

    print(f"\nPHASE 4A Integration Test")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    start = time.time()

    all_results: List[Dict[str, Any]] = []

    if args.full:
        all_results.extend(test_pytest_suite())

    all_results.extend(test_drift_detector())
    all_results.extend(test_auto_fix())
    all_results.extend(test_self_improvement())
    all_results.extend(test_alerting())
    all_results.extend(test_monitoring_dashboard())
    all_results.extend(test_ci_cd())

    # Summary
    passed = sum(1 for r in all_results if r["passed"])
    total = len(all_results)
    elapsed = time.time() - start

    header("SUMMARY")
    print(f"  Results : {passed}/{total} checks passed")
    print(f"  Duration: {elapsed:.1f}s")
    print(f"  Status  : {'ALL PASS' if passed == total else f'{total-passed} FAILED'}")

    if passed < total:
        print("\nFailed checks:")
        for r in all_results:
            if not r["passed"]:
                print(f"  - {r['name']}: {r['detail']}")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "passed": passed,
        "total": total,
        "elapsed_seconds": round(elapsed, 2),
        "results": all_results,
    }
    REPORT_FILE.parent.mkdir(exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2))
    print(f"\nReport: {REPORT_FILE}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
