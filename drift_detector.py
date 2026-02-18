"""
Drift Detector - PHASE 4A Week 2
Monitors critical files for unexpected changes and tracks test regression.
"""

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

CRITICAL_FILES = [
    "ai_gateway.py",
    "rtx_agent.py",
    "memory_system.py",
    "tests/test_ai_gateway.py",
    "tests/test_integration.py",
    "tests/test_rtx_agent.py",
    "pyproject.toml",
    "pytest.ini",
    ".flake8",
]

SNAPSHOT_FILE = Path("C:/ClaudeAgent/.drift_snapshot.json")
LOG_FILE = Path("C:/ClaudeAgent/reports/drift_log.txt")
DRIFT_THRESHOLD = 0.15  # 15% of monitored files changed = alert


def file_hash(path: str) -> Optional[str]:
    """SHA256 hash of file, None if missing."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def load_snapshot() -> Dict[str, str]:
    if SNAPSHOT_FILE.exists():
        return json.loads(SNAPSHOT_FILE.read_text())
    return {}


def save_snapshot(snapshot: Dict[str, str]) -> None:
    SNAPSHOT_FILE.write_text(json.dumps(snapshot, indent=2))


def create_snapshot() -> Dict[str, str]:
    base = "C:/ClaudeAgent"
    return {f: h for f in CRITICAL_FILES if (h := file_hash(f"{base}/{f}")) is not None}


def run_tests() -> Dict[str, int]:
    """Run pytest and return pass/fail/skip counts."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--no-cov", "-q", "--tb=no"],
        capture_output=True,
        text=True,
        cwd="C:/ClaudeAgent",
    )
    output = result.stdout + result.stderr
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    for line in output.splitlines():
        for key in counts:
            if key in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == key and i > 0:
                        try:
                            counts[key] = int(parts[i - 1])
                        except ValueError:
                            pass
    return counts


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def check_drift() -> Dict[str, object]:
    """Compare current files against snapshot. Returns drift report."""
    old = load_snapshot()
    new = create_snapshot()

    changed: List[str] = []
    added: List[str] = []
    removed: List[str] = []

    for f, h in new.items():
        if f not in old:
            added.append(f)
        elif old[f] != h:
            changed.append(f)

    for f in old:
        if f not in new:
            removed.append(f)

    total = len(new)
    drift_count = len(changed) + len(removed)
    drift_ratio = drift_count / total if total > 0 else 0
    alert = drift_ratio >= DRIFT_THRESHOLD

    report = {
        "timestamp": datetime.now().isoformat(),
        "changed": changed,
        "added": added,
        "removed": removed,
        "drift_ratio": round(drift_ratio, 3),
        "alert": alert,
        "total_monitored": total,
    }
    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ClaudeAgent Drift Detector")
    parser.add_argument("--init", action="store_true", help="Create initial snapshot")
    parser.add_argument("--check", action="store_true", help="Check for drift")
    parser.add_argument("--status", action="store_true", help="Show snapshot status")
    args = parser.parse_args()

    if args.init:
        snap = create_snapshot()
        save_snapshot(snap)
        log(f"[INIT] Snapshot created: {len(snap)} files")
        for f in snap:
            print(f"  [ok] {f}")

    elif args.check:
        if not SNAPSHOT_FILE.exists():
            print("[ERROR] No snapshot found. Run: python drift_detector.py --init")
            sys.exit(1)

        report = check_drift()
        log(f"[CHECK] drift={report['drift_ratio']:.1%} alert={report['alert']}")

        if report["changed"]:
            log(f"[CHANGED] {', '.join(report['changed'])}")
        if report["added"]:
            log(f"[ADDED] {', '.join(report['added'])}")
        if report["removed"]:
            log(f"[REMOVED] {', '.join(report['removed'])}")

        if not report["changed"] and not report["added"] and not report["removed"]:
            log("[OK] No drift detected")
        elif report["alert"]:
            log(f"[ALERT] Drift {report['drift_ratio']:.1%} >= {DRIFT_THRESHOLD:.0%} threshold!")
            # Also run tests to check regression
            log("[TESTS] Running tests to check for regression...")
            counts = run_tests()
            log(f"[TESTS] passed={counts['passed']} failed={counts['failed']} skipped={counts['skipped']}")
            if counts["failed"] > 0:
                log(f"[ALERT] {counts['failed']} tests FAILING after drift!")

        # Save report
        report_path = Path("C:/ClaudeAgent/reports/drift_report.json")
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2))
        print(f"\nReport saved: {report_path}")

    elif args.status:
        if not SNAPSHOT_FILE.exists():
            print("[NO SNAPSHOT] Run --init first")
        else:
            snap = load_snapshot()
            print(f"Snapshot: {len(snap)} files monitored")
            for f, h in snap.items():
                current = file_hash(f"C:/ClaudeAgent/{f}")
                status = "[ok]" if current == h else "[CHANGED]"
                print(f"  {status}  {f}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
