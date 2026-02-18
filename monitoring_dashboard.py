"""
Monitoring Dashboard - PHASE 4A Week 3 (Day 15-17)
Real-time terminal dashboard using rich. Shows KPIs, trends, alerts.
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

PROJECT_DIR = Path("C:/ClaudeAgent")
REPORTS_DIR = PROJECT_DIR / "reports"
REFRESH_INTERVAL = 30  # seconds

console = Console()

TARGETS = {
    "test_pass_rate": 0.90,
    "pylint_score": 8.0,
    "drift_ratio": 0.0,
}


def _status_color(val: float, target: float, higher_better: bool = True) -> str:
    ok = val >= target if higher_better else val <= target
    return "green" if ok else "red"


def load_metrics_history() -> List[Dict[str, Any]]:
    f = REPORTS_DIR / "metrics_history.json"
    return json.loads(f.read_text()) if f.exists() else []


def load_drift_report() -> Dict[str, Any]:
    f = REPORTS_DIR / "drift_report.json"
    return json.loads(f.read_text()) if f.exists() else {}


def load_auto_fix_report() -> Dict[str, Any]:
    f = REPORTS_DIR / "auto_fix_report.json"
    return json.loads(f.read_text()) if f.exists() else {}


def run_quick_tests() -> Dict[str, int]:
    """Fast test run (no coverage)."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--no-cov", "--tb=no", "-q"],
        capture_output=True, text=True, cwd=str(PROJECT_DIR),
    )
    import re
    output = result.stdout + result.stderr
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    for key in counts:
        m = re.search(rf"(\d+) {key}", output)
        if m:
            counts[key] = int(m.group(1))
    return counts


def build_kpi_table(history: List[Dict[str, Any]]) -> Table:
    table = Table(title="KPI Status", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="white", width=22)
    table.add_column("Current", justify="right", width=10)
    table.add_column("Target", justify="right", width=10)
    table.add_column("Trend", justify="center", width=8)
    table.add_column("Status", justify="center", width=8)

    if not history:
        table.add_row("[dim]No data yet - run self_improvement.py --run[/dim]", "", "", "", "")
        return table

    current = history[-1]
    prev = history[-2] if len(history) >= 2 else None

    tests = current["tests"]
    pylint = current["pylint"]
    drift = current["drift"]

    def trend(curr: float, prev_val: float | None, higher_better: bool = True) -> str:
        if prev_val is None:
            return "-"
        delta = curr - prev_val
        if abs(delta) < 0.001:
            return "~"
        up = delta > 0
        return ("+" if up == higher_better else "-") + f"{abs(delta):.2f}"

    # Test pass rate
    rate = tests["pass_rate"]
    prev_rate = prev["tests"]["pass_rate"] if prev else None
    color = _status_color(rate, TARGETS["test_pass_rate"])
    table.add_row(
        "Test Pass Rate",
        f"{rate:.1%}",
        f"{TARGETS['test_pass_rate']:.0%}",
        trend(rate, prev_rate),
        Text("PASS" if color == "green" else "FAIL", style=color),
    )

    # Tests passing / skipped
    table.add_row(
        "  Passing / Skipped",
        f"{tests['passed']}/{tests['skipped']}",
        f"{tests['total']}/0",
        "",
        "",
    )

    # Pylint
    pyl = pylint["average"]
    prev_pyl = prev["pylint"]["average"] if prev else None
    color = _status_color(pyl, TARGETS["pylint_score"])
    table.add_row(
        "Pylint Score",
        f"{pyl:.2f}/10",
        f"{TARGETS['pylint_score']:.1f}/10",
        trend(pyl, prev_pyl),
        Text("PASS" if color == "green" else "FAIL", style=color),
    )

    # Drift
    dr = drift["drift_ratio"]
    color = _status_color(dr, TARGETS["drift_ratio"], higher_better=False)
    drift_alert = "[bold red]ALERT[/bold red]" if drift.get("alert") else (Text("PASS", style="green"))
    table.add_row(
        "Drift Ratio",
        f"{dr:.1%}",
        "0.0%",
        "-",
        drift_alert,  # type: ignore[arg-type]
    )

    return table


def build_trend_table(history: List[Dict[str, Any]]) -> Table:
    table = Table(title="History (last 5 snapshots)", show_header=True, header_style="bold cyan")
    table.add_column("#", width=4)
    table.add_column("Time", width=18)
    table.add_column("Pass Rate", justify="right", width=10)
    table.add_column("Pylint", justify="right", width=8)
    table.add_column("Drift", justify="right", width=8)

    for i, snap in enumerate(history[-5:], 1):
        ts = snap["timestamp"][:16].replace("T", " ")
        rate = snap["tests"]["pass_rate"]
        pyl = snap["pylint"]["average"]
        dr = snap["drift"]["drift_ratio"]
        rate_color = "green" if rate >= TARGETS["test_pass_rate"] else "yellow"
        pyl_color = "green" if pyl >= TARGETS["pylint_score"] else "yellow"
        table.add_row(
            str(i),
            ts,
            Text(f"{rate:.1%}", style=rate_color),
            Text(f"{pyl:.2f}", style=pyl_color),
            f"{dr:.1%}",
        )

    if not history:
        table.add_row("-", "No data", "-", "-", "-")

    return table


def build_alerts_panel(history: List[Dict[str, Any]], drift: Dict[str, Any]) -> Panel:
    alerts: List[str] = []

    if drift.get("alert"):
        changed = drift.get("changed", [])
        alerts.append(f"[bold red]DRIFT ALERT:[/bold red] {len(changed)} file(s) changed: {', '.join(changed)}")

    if history:
        current = history[-1]
        if current["tests"]["failed"] > 0:
            alerts.append(f"[red]{current['tests']['failed']} test(s) FAILING[/red]")
        if len(history) >= 2:
            prev = history[-2]
            if current["tests"]["pass_rate"] < prev["tests"]["pass_rate"] - 0.05:
                alerts.append("[yellow]REGRESSION: Test pass rate dropped >5%[/yellow]")
            if current["pylint"]["average"] < prev["pylint"]["average"] - 0.5:
                alerts.append("[yellow]REGRESSION: Pylint score dropped >0.5[/yellow]")

    if not alerts:
        content = Text("No alerts. All systems nominal.", style="green")
    else:
        content = Text("\n".join(alerts))

    return Panel(content, title="[bold]Alerts[/bold]", border_style="red" if alerts else "green")


def build_layout(history: List[Dict[str, Any]], drift: Dict[str, Any], last_refresh: str) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    layout["main"].split_row(
        Layout(name="kpi"),
        Layout(name="right"),
    )
    layout["right"].split_column(
        Layout(name="trend"),
        Layout(name="alerts"),
    )

    layout["header"].update(Panel(
        Text(f"ClaudeAgent Monitor  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Refresh: {REFRESH_INTERVAL}s", justify="center"),
        style="bold blue",
    ))
    layout["kpi"].update(Panel(build_kpi_table(history), border_style="blue"))
    layout["trend"].update(Panel(build_trend_table(history), border_style="blue"))
    layout["alerts"].update(build_alerts_panel(history, drift))
    layout["footer"].update(Panel(
        Text(f"Last refresh: {last_refresh}  |  Press Ctrl+C to exit", justify="center"),
        style="dim",
    ))
    return layout


def snapshot(console_out: Console) -> None:
    """Print a one-shot snapshot (non-interactive)."""
    history = load_metrics_history()
    drift = load_drift_report()
    console_out.print(build_kpi_table(history))
    console_out.print(build_trend_table(history))
    console_out.print(build_alerts_panel(history, drift))


def live_dashboard() -> None:
    """Run the live auto-refreshing dashboard."""
    last_refresh = datetime.now().strftime("%H:%M:%S")
    history = load_metrics_history()
    drift = load_drift_report()

    with Live(build_layout(history, drift, last_refresh), refresh_per_second=1, screen=True) as live:
        while True:
            time.sleep(REFRESH_INTERVAL)
            history = load_metrics_history()
            drift = load_drift_report()
            last_refresh = datetime.now().strftime("%H:%M:%S")
            live.update(build_layout(history, drift, last_refresh))


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="ClaudeAgent Monitoring Dashboard")
    parser.add_argument("--live", action="store_true", help=f"Live dashboard (refreshes every {REFRESH_INTERVAL}s)")
    parser.add_argument("--snapshot", action="store_true", help="Print one-shot snapshot and exit")
    args = parser.parse_args()

    if args.live:
        try:
            live_dashboard()
        except KeyboardInterrupt:
            console.print("\n[dim]Dashboard stopped.[/dim]")
    elif args.snapshot:
        snapshot(console)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
