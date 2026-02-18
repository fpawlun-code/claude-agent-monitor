"""
Auto-Fix Tests - PHASE 4A Week 2 (Day 11-12)
Runs pytest, parses failures, applies known fixes, re-runs.
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LOG_FILE = Path("C:/ClaudeAgent/reports/auto_fix_log.txt")
PROJECT_DIR = Path("C:/ClaudeAgent")

# Known fix patterns: (error_pattern, fix_description, fix_function_name)
KNOWN_FIXES = [
    (r"assert.*\"response\".*not in.*json", "Mock uses wrong API response key", "fix_mock_response_key"),
    (r"ImportError.*memory_system", "memory_system import fails", "fix_memory_import"),
    (r"ModuleNotFoundError.*(\w+)", "Missing module", "fix_missing_module"),
    (r"AssertionError.*blocked.*not in", "Safety pattern not matching", "fix_safety_pattern"),
    (r"F401.*imported but unused", "Flake8 unused import", "fix_unused_import"),
]


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_pytest(extra_args: Optional[List[str]] = None) -> Tuple[int, str, str]:
    """Run pytest, return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, "-m", "pytest", "tests/", "--no-cov", "--tb=short", "-q"]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_DIR))
    return result.returncode, result.stdout, result.stderr


def parse_failures(output: str) -> List[Dict[str, str]]:
    """Extract failing test info from pytest output."""
    failures = []
    # Match: FAILED tests/file.py::Class::method - reason
    pattern = r"FAILED (tests/\S+) - (.+)"
    for m in re.finditer(pattern, output):
        failures.append({"test": m.group(1), "reason": m.group(2).strip()})
    # Also match ERROR lines
    error_pattern = r"ERROR (tests/\S+)"
    for m in re.finditer(error_pattern, output):
        failures.append({"test": m.group(1), "reason": "collection error"})
    return failures


def parse_counts(output: str) -> Dict[str, int]:
    """Parse passed/failed/skipped from pytest summary line."""
    counts = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
    for line in (output + "").splitlines():
        for key in counts:
            m = re.search(rf"(\d+) {key}", line)
            if m:
                counts[key] = int(m.group(1))
    return counts


def diagnose_failure(failure: Dict[str, str], full_output: str) -> Optional[str]:
    """Return fix name if we know how to fix this failure."""
    combined = f"{failure['test']} {failure['reason']} {full_output}"
    for pattern, _, fix_name in KNOWN_FIXES:
        if re.search(pattern, combined, re.IGNORECASE):
            return fix_name
    return None


def apply_fix(fix_name: str, failure: Dict[str, str]) -> bool:
    """Apply a known fix. Returns True if fix was applied."""
    if fix_name == "fix_mock_response_key":
        log(f"  [FIX] Checking mock response keys in {failure['test']}")
        # Already fixed in current codebase - just note it
        return False

    if fix_name == "fix_memory_import":
        log(f"  [FIX] Adding pytest.skip for memory_system in {failure['test']}")
        # Pattern already applied - ReactAgent tests skip gracefully
        return False

    if fix_name == "fix_missing_module":
        m = re.search(r"ModuleNotFoundError.*'(\w+)'", failure["reason"])
        if m:
            module = m.group(1)
            log(f"  [FIX] Installing missing module: {module}")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", module, "-q"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0

    if fix_name == "fix_safety_pattern":
        log(f"  [FIX] Safety pattern issue - manual review needed for {failure['test']}")
        return False

    if fix_name == "fix_unused_import":
        log(f"  [FIX] Run: python -m autoflake --remove-all-unused-imports -i <file>")
        return False

    return False


def auto_fix_cycle(max_rounds: int = 3) -> Dict[str, object]:
    """
    Main auto-fix loop:
    1. Run tests
    2. Parse failures
    3. Apply known fixes
    4. Re-run (up to max_rounds)
    """
    log("[START] Auto-fix cycle starting")
    history = []

    for round_num in range(1, max_rounds + 1):
        log(f"\n[ROUND {round_num}/{max_rounds}] Running tests...")
        exit_code, stdout, stderr = run_pytest()
        output = stdout + stderr
        counts = parse_counts(output)
        failures = parse_failures(output)

        log(f"[ROUND {round_num}] passed={counts['passed']} failed={counts['failed']} skipped={counts['skipped']}")
        history.append({"round": round_num, "counts": counts.copy(), "failures": [f["test"] for f in failures]})

        if exit_code == 0 or counts["failed"] == 0:
            log(f"[SUCCESS] All tests passing after round {round_num}")
            break

        # Try to fix each failure
        fixes_applied = 0
        for failure in failures:
            fix = diagnose_failure(failure, output)
            if fix:
                log(f"  [DIAGNOSE] {failure['test']}: applying {fix}")
                if apply_fix(fix, failure):
                    fixes_applied += 1
                    log(f"  [FIXED] {failure['test']}")
                else:
                    log(f"  [SKIP] Fix not applicable automatically")
            else:
                log(f"  [UNKNOWN] No auto-fix for: {failure['test']} - {failure['reason'][:80]}")

        if fixes_applied == 0 and round_num < max_rounds:
            log("[STOP] No fixes could be applied, stopping early")
            break

    # Final summary
    final_counts = history[-1]["counts"] if history else {}
    total_tests = sum(final_counts.values())
    pass_rate = final_counts.get("passed", 0) / total_tests if total_tests > 0 else 0

    result = {
        "rounds": len(history),
        "final_counts": final_counts,
        "pass_rate": round(pass_rate, 3),
        "history": history,
        "timestamp": datetime.now().isoformat(),
    }

    log(f"\n[DONE] Final: {final_counts.get('passed', 0)}/{total_tests} passing ({pass_rate:.1%})")

    # Save report
    report_path = PROJECT_DIR / "reports" / "auto_fix_report.json"
    report_path.parent.mkdir(exist_ok=True)
    import json
    report_path.write_text(json.dumps(result, indent=2))
    log(f"[REPORT] Saved: {report_path}")

    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Auto-Fix Tests - ClaudeAgent")
    parser.add_argument("--run", action="store_true", help="Run auto-fix cycle")
    parser.add_argument("--diagnose", action="store_true", help="Diagnose failures (no fixes)")
    parser.add_argument("--rounds", type=int, default=3, help="Max fix rounds (default: 3)")
    args = parser.parse_args()

    if args.diagnose:
        log("[DIAGNOSE] Running tests to find failures...")
        _, stdout, stderr = run_pytest()
        output = stdout + stderr
        failures = parse_failures(output)
        counts = parse_counts(output)
        log(f"[STATUS] passed={counts['passed']} failed={counts['failed']} skipped={counts['skipped']}")
        if not failures:
            log("[OK] No failures detected")
        else:
            for f in failures:
                fix = diagnose_failure(f, output)
                fix_str = fix if fix else "UNKNOWN (manual review)"
                log(f"  FAIL: {f['test']}")
                log(f"       Reason: {f['reason'][:100]}")
                log(f"       Fix: {fix_str}")

    elif args.run:
        auto_fix_cycle(max_rounds=args.rounds)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
