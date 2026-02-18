"""
REST API Server - PHASE 4B Week 2
FastAPI endpoints exposing monitoring data, KPIs, alerts.
Run: uvicorn api_server:app --host 0.0.0.0 --port 8765 --reload
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

PROJECT_DIR = Path("C:/ClaudeAgent")
REPORTS_DIR = PROJECT_DIR / "reports"

app = FastAPI(
    title="ClaudeAgent Monitor API",
    description="Real-time KPI, metrics, drift and alerting data",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────

class RunCommandRequest(BaseModel):
    command: str  # "drift_check" | "self_improvement" | "auto_fix"


class AlertResolveRequest(BaseModel):
    rule: str


# ── Helpers ───────────────────────────────────────────────────

def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    return json.loads(path.read_text()) if path.exists() else None


def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return data if isinstance(data, list) else [data]


def _run_script(script: str, args: List[str]) -> Dict[str, Any]:
    result = subprocess.run(
        [sys.executable, script] + args,
        capture_output=True, text=True, cwd=str(PROJECT_DIR), timeout=120,
    )
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-500:],
        "success": result.returncode == 0,
    }


# ── Routes ────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def root() -> str:
    """Web dashboard."""
    history_data = _load_json_list(REPORTS_DIR / "metrics_history.json")
    alerts_data = _load_json(REPORTS_DIR / "active_alerts.json") or {}
    drift_data = _load_json(REPORTS_DIR / "drift_report.json") or {}

    current = history_data[-1] if history_data else {}
    tests = current.get("tests", {})
    pylint = current.get("pylint", {})

    active_alerts = [k for k, v in alerts_data.items() if not v.get("resolved")]
    alert_color = "#dc3545" if active_alerts else "#28a745"
    drift_color = "#dc3545" if drift_data.get("alert") else "#28a745"

    snapshots_js = json.dumps([
        {
            "t": s["timestamp"][:16].replace("T", " "),
            "rate": round(s["tests"]["pass_rate"] * 100, 1),
            "pylint": s["pylint"]["average"],
        }
        for s in history_data[-20:]
    ])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>ClaudeAgent Monitor</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
  h1 {{ color: #58a6ff; margin-bottom: 4px; }}
  .sub {{ color: #8b949e; font-size: 13px; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }}
  .card h3 {{ margin: 0 0 8px; font-size: 13px; color: #8b949e; text-transform: uppercase; }}
  .card .val {{ font-size: 32px; font-weight: bold; }}
  .card .label {{ font-size: 12px; color: #8b949e; margin-top: 4px; }}
  .green {{ color: #3fb950; }}
  .red {{ color: #f85149; }}
  .yellow {{ color: #d29922; }}
  .section {{ margin-top: 28px; }}
  .section h2 {{ color: #58a6ff; font-size: 16px; border-bottom: 1px solid #30363d; padding-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 12px; color: #8b949e; border-bottom: 1px solid #21262d; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #161b22; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }}
  .badge-green {{ background: #1a3a1a; color: #3fb950; }}
  .badge-red {{ background: #3a1a1a; color: #f85149; }}
  .badge-yellow {{ background: #3a2d0d; color: #d29922; }}
  canvas {{ max-width: 100%; }}
</style>
</head>
<body>
<h1>ClaudeAgent Monitor</h1>
<p class="sub">Auto-refresh: 60s &nbsp;|&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<div class="grid">
  <div class="card">
    <h3>Test Pass Rate</h3>
    <div class="val {'green' if tests.get('pass_rate', 0) >= 0.9 else 'yellow'}">{tests.get('pass_rate', 0)*100:.1f}%</div>
    <div class="label">{tests.get('passed', 0)}/{tests.get('total', 0)} tests</div>
  </div>
  <div class="card">
    <h3>Pylint Score</h3>
    <div class="val {'green' if pylint.get('average', 0) >= 8 else 'yellow'}">{pylint.get('average', 0):.2f}<span style="font-size:16px">/10</span></div>
    <div class="label">Code quality</div>
  </div>
  <div class="card">
    <h3>Drift Status</h3>
    <div class="val" style="color:{drift_color}">{'ALERT' if drift_data.get('alert') else 'CLEAN'}</div>
    <div class="label">{drift_data.get('drift_ratio', 0)*100:.1f}% changed</div>
  </div>
  <div class="card">
    <h3>Active Alerts</h3>
    <div class="val" style="color:{alert_color}">{len(active_alerts)}</div>
    <div class="label">{'No issues' if not active_alerts else ', '.join(active_alerts[:2])}</div>
  </div>
  <div class="card">
    <h3>Snapshots</h3>
    <div class="val green">{len(history_data)}</div>
    <div class="label">Metrics recorded</div>
  </div>
</div>

<div class="section">
  <h2>History (last 10 snapshots)</h2>
  <table>
    <tr><th>#</th><th>Time</th><th>Pass Rate</th><th>Pylint</th><th>Drift</th></tr>
    {''.join(
        f'<tr><td>{i+1}</td><td>{s["timestamp"][:16].replace("T"," ")}</td>'
        f'<td><span class="badge badge-{"green" if s["tests"]["pass_rate"]>=0.9 else "yellow"}">'
        f'{s["tests"]["pass_rate"]*100:.1f}%</span></td>'
        f'<td>{s["pylint"]["average"]:.2f}</td>'
        f'<td>{s["drift"]["drift_ratio"]*100:.1f}%</td></tr>'
        for i, s in enumerate(history_data[-10:])
    ) if history_data else '<tr><td colspan="5" style="color:#8b949e">No data. Run: python self_improvement.py --run</td></tr>'}
  </table>
</div>

<div class="section">
  <h2>API Endpoints</h2>
  <table>
    <tr><th>Method</th><th>Path</th><th>Description</th></tr>
    <tr><td>GET</td><td>/health</td><td>Health check</td></tr>
    <tr><td>GET</td><td>/metrics</td><td>Latest KPI metrics</td></tr>
    <tr><td>GET</td><td>/metrics/history</td><td>Full history (last 30)</td></tr>
    <tr><td>GET</td><td>/drift</td><td>Drift report</td></tr>
    <tr><td>GET</td><td>/alerts</td><td>Active alerts</td></tr>
    <tr><td>POST</td><td>/run</td><td>Trigger drift_check / self_improvement / auto_fix</td></tr>
    <tr><td>GET</td><td>/docs</td><td>Interactive API docs (Swagger)</td></tr>
  </table>
</div>
</body>
</html>"""


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}


@app.get("/metrics")
def get_metrics() -> Dict[str, Any]:
    history = _load_json_list(REPORTS_DIR / "metrics_history.json")
    if not history:
        raise HTTPException(status_code=404, detail="No metrics yet. Run: python self_improvement.py --run")
    return history[-1]


@app.get("/metrics/history")
def get_metrics_history(limit: int = 30) -> List[Dict[str, Any]]:
    history = _load_json_list(REPORTS_DIR / "metrics_history.json")
    return history[-limit:]


@app.get("/drift")
def get_drift() -> Dict[str, Any]:
    data = _load_json(REPORTS_DIR / "drift_report.json")
    if data is None:
        raise HTTPException(status_code=404, detail="No drift report. Run: python drift_detector.py --check")
    return data


@app.get("/alerts")
def get_alerts(active_only: bool = True) -> Dict[str, Any]:
    data = _load_json(REPORTS_DIR / "active_alerts.json") or {}
    if active_only:
        data = {k: v for k, v in data.items() if not v.get("resolved")}
    return {"count": len(data), "alerts": data}


@app.get("/integration-test")
def get_integration_test() -> Dict[str, Any]:
    data = _load_json(REPORTS_DIR / "integration_test_report.json")
    if data is None:
        raise HTTPException(status_code=404, detail="No integration test report found.")
    return data


@app.get("/models")
def get_models() -> Dict[str, Any]:
    """List available Ollama models with routing profiles."""
    from model_router import MODEL_PROFILES, get_available_models
    available = get_available_models()
    result = {}
    for m in available:
        profile = MODEL_PROFILES.get(m, {"strengths": [], "speed": "unknown"})
        result[m] = {"strengths": profile.get("strengths", []), "speed": profile.get("speed", "?")}
    return {"available": len(available), "models": result}


@app.post("/run")
def run_command(req: RunCommandRequest) -> Dict[str, Any]:
    commands = {
        "drift_check": ("drift_detector.py", ["--check"]),
        "self_improvement": ("self_improvement.py", ["--run"]),
        "auto_fix": ("auto_fix_tests.py", ["--diagnose"]),
        "alert_check": ("alerting.py", ["--check"]),
    }
    if req.command not in commands:
        raise HTTPException(status_code=400, detail=f"Unknown command. Valid: {list(commands)}")
    script, args = commands[req.command]
    return {"command": req.command, **_run_script(script, args)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
