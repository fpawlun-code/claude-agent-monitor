#!/usr/bin/env python3
"""
Command Center - Centrum Dowodzenia
Automated online income management dashboard.
Port: 8766  |  Run: python command_center.py

Modules:
  - FB Freelance Pipeline (scraping + RTX proposals)
  - OLX Arbitrage Scanner
  - Income Streams overview
  - Real-time activity log (SSE)
  - Scheduler (auto-run every N hours)
"""

import asyncio
import json
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

# ── Paths ─────────────────────────────────────────────────────────────────────

PROJECT_DIR = Path("C:/ClaudeAgent")
DB_PATH = PROJECT_DIR / "fb_data" / "jobs.db"
sys.path.insert(0, str(PROJECT_DIR))

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Command Center", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── DB ────────────────────────────────────────────────────────────────────────

def db():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    from fb_scraper import init_db as init_jobs_db
    (PROJECT_DIR / "fb_data").mkdir(exist_ok=True)
    init_jobs_db()
    conn = db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS earnings (
            id         TEXT PRIMARY KEY,
            job_id     TEXT,
            amount_pln REAL,
            paid_at    TEXT,
            note       TEXT
        );
        CREATE TABLE IF NOT EXISTS activity_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source    TEXT,
            level     TEXT,
            message   TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key        TEXT PRIMARY KEY,
            value      TEXT,
            updated_at TEXT
        );
    """)
    conn.commit()
    conn.close()

def log(source: str, level: str, message: str):
    try:
        conn = db()
        conn.execute(
            "INSERT INTO activity_log (timestamp, source, level, message) VALUES (?,?,?,?)",
            (datetime.now().isoformat(), source, level, message)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_setting(key: str, default: str = "") -> str:
    conn = db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key: str, value: str):
    conn = db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?,?,?)",
        (key, value, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

# ── Subprocess runner ─────────────────────────────────────────────────────────

_procs: Dict[str, subprocess.Popen] = {}

def run_bg(name: str, script: str, args: List[str]):
    if name in _procs and _procs[name].poll() is None:
        log("command_center", "warn", f"{name} already running")
        return False

    def _run():
        log(name, "info", f"Starting {script} {' '.join(args)}")
        proc = subprocess.Popen(
            [sys.executable, str(PROJECT_DIR / script)] + args,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            cwd=str(PROJECT_DIR)
        )
        _procs[name] = proc
        for line in proc.stdout:
            line = line.strip()
            if line and "[INFO]" not in line and line != "":
                log(name, "info", line[:200])
        proc.wait()
        lvl = "success" if proc.returncode == 0 else "error"
        log(name, lvl, f"{script} finished (code {proc.returncode})")

    threading.Thread(target=_run, daemon=True).start()
    return True

# ── Models ────────────────────────────────────────────────────────────────────

class SettingReq(BaseModel):
    key: str
    value: str

class EarnReq(BaseModel):
    amount_pln: float
    note: str = ""

class EditProposalReq(BaseModel):
    proposal: str

# ── Scheduler ─────────────────────────────────────────────────────────────────

_sched_timer: Optional[threading.Timer] = None

def sched_tick():
    global _sched_timer
    log("scheduler", "info", "Scheduled run triggered")
    run_bg("fb_scraper", "fb_scraper.py", ["--scrape"])
    time.sleep(45)
    # Process unscraped posts
    try:
        from fb_scraper import get_unprocessed_posts
        from freelance_pipeline import FreelancePipeline
        posts = get_unprocessed_posts(limit=50)
        if posts:
            pipeline = FreelancePipeline()
            jobs = pipeline.process_posts(posts)
            log("scheduler", "success", f"Pipeline: {len(jobs)} new proposals generated")
    except Exception as e:
        log("scheduler", "error", f"Pipeline error: {e}")
    # Reschedule
    interval_h = float(get_setting("scheduler_interval_hours", "4"))
    if get_setting("scheduler_enabled", "false") == "true" and interval_h > 0:
        _sched_timer = threading.Timer(interval_h * 3600, sched_tick)
        _sched_timer.daemon = True
        _sched_timer.start()

def sched_start():
    global _sched_timer
    if _sched_timer:
        _sched_timer.cancel()
    interval_h = float(get_setting("scheduler_interval_hours", "4"))
    if get_setting("scheduler_enabled", "false") == "true" and interval_h > 0:
        _sched_timer = threading.Timer(interval_h * 3600, sched_tick)
        _sched_timer.daemon = True
        _sched_timer.start()
        log("scheduler", "info", f"Scheduler armed: every {interval_h}h")
        return True
    return False

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    init_db()
    log("command_center", "info", "Command Center started on :8766")
    sched_start()

# ── API: Stats ────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def api_stats():
    today = date.today().isoformat()
    conn = db()
    posts_today   = conn.execute("SELECT COUNT(*) FROM posts WHERE scraped_at LIKE ?", (f"{today}%",)).fetchone()[0]
    posts_total   = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    pending       = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0]
    approved      = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='approved'").fetchone()[0]
    sent          = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='sent'").fetchone()[0]
    skipped       = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='skipped'").fetchone()[0]
    total_jobs    = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    earnings      = conn.execute("SELECT COALESCE(SUM(amount_pln),0) FROM earnings").fetchone()[0]
    by_cat        = conn.execute("SELECT category, COUNT(*) FROM jobs GROUP BY category ORDER BY COUNT(*) DESC").fetchall()
    week_posts    = conn.execute("""
        SELECT date(scraped_at) as d, COUNT(*) FROM posts
        WHERE scraped_at >= date('now','-6 days')
        GROUP BY d ORDER BY d
    """).fetchall()
    conn.close()

    rtx_ok = False
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        rtx_ok = r.status_code == 200
    except Exception:
        pass

    scraper_running = "fb_scraper" in _procs and _procs["fb_scraper"].poll() is None
    pipeline_running = "pipeline" in _procs and _procs["pipeline"].poll() is None

    return {
        "posts_today": posts_today,
        "posts_total": posts_total,
        "pending": pending,
        "approved": approved,
        "sent": sent,
        "skipped": skipped,
        "total_jobs": total_jobs,
        "earnings_pln": round(earnings, 2),
        "rtx_ok": rtx_ok,
        "scraper_running": scraper_running,
        "pipeline_running": pipeline_running,
        "by_category": [{"cat": r[0], "count": r[1]} for r in by_cat],
        "week_posts": [{"date": r[0], "count": r[1]} for r in week_posts],
    }

# ── API: Jobs ─────────────────────────────────────────────────────────────────

@app.get("/api/jobs")
def api_jobs(status: str = "pending", limit: int = 50):
    conn = db()
    rows = conn.execute("""
        SELECT j.id, j.category, j.budget_pln, j.contact, j.proposal,
               j.status, j.created_at,
               p.text, p.post_url, p.author, p.group_url
        FROM jobs j JOIN posts p ON j.post_id = p.id
        WHERE j.status = ?
        ORDER BY j.created_at DESC
        LIMIT ?
    """, (status, limit)).fetchall()
    conn.close()
    return [
        {
            "id": r[0], "category": r[1], "budget_pln": r[2],
            "contact": r[3], "proposal": r[4], "status": r[5],
            "created_at": r[6][:16] if r[6] else "",
            "post_text": r[7], "post_url": r[8],
            "author": r[9], "group_url": r[10],
            "group_name": (r[10] or "").split("/")[-1],
        }
        for r in rows
    ]

@app.post("/api/jobs/{job_id}/approve")
def api_approve(job_id: str):
    from freelance_pipeline import FreelancePipeline
    FreelancePipeline().update_job_status(job_id, "approved")
    log("command_center", "success", f"Job approved: {job_id}")
    return {"ok": True}

@app.post("/api/jobs/{job_id}/skip")
def api_skip(job_id: str):
    from freelance_pipeline import FreelancePipeline
    FreelancePipeline().update_job_status(job_id, "skipped")
    log("command_center", "info", f"Job skipped: {job_id}")
    return {"ok": True}

@app.post("/api/jobs/{job_id}/sent")
def api_sent(job_id: str):
    from freelance_pipeline import FreelancePipeline
    FreelancePipeline().update_job_status(job_id, "sent")
    log("command_center", "success", f"Offer sent: {job_id}")
    return {"ok": True}

@app.post("/api/jobs/{job_id}/earn")
def api_earn(job_id: str, req: EarnReq):
    conn = db()
    conn.execute(
        "INSERT INTO earnings (id, job_id, amount_pln, paid_at, note) VALUES (?,?,?,?,?)",
        (f"earn_{int(time.time())}", job_id, req.amount_pln, datetime.now().isoformat(), req.note)
    )
    conn.commit()
    conn.close()
    log("command_center", "success", f"Earned {req.amount_pln} PLN from {job_id}")
    return {"ok": True}

@app.post("/api/jobs/{job_id}/proposal")
def api_edit_proposal(job_id: str, req: EditProposalReq):
    conn = db()
    conn.execute("UPDATE jobs SET proposal=? WHERE id=?", (req.proposal, job_id))
    conn.commit()
    conn.close()
    return {"ok": True}

# ── API: Actions ──────────────────────────────────────────────────────────────

@app.post("/api/run/scrape")
def api_scrape():
    ok = run_bg("fb_scraper", "fb_scraper.py", ["--scrape"])
    return {"ok": ok, "msg": "Scraper started" if ok else "Already running"}

@app.post("/api/run/pipeline")
def api_pipeline(bg: BackgroundTasks):
    def _process():
        try:
            from fb_scraper import get_unprocessed_posts
            from freelance_pipeline import FreelancePipeline
            posts = get_unprocessed_posts(limit=50)
            log("pipeline", "info", f"Processing {len(posts)} posts via RTX...")
            if not posts:
                log("pipeline", "info", "No unprocessed posts found")
                return
            jobs = FreelancePipeline().process_posts(posts)
            log("pipeline", "success", f"{len(jobs)} new proposals generated")
        except Exception as e:
            log("pipeline", "error", str(e))
    bg.add_task(_process)
    return {"ok": True, "msg": "Pipeline started"}

@app.post("/api/run/olx")
def api_olx():
    ok = run_bg("olx", "market_sniper.py", [])
    return {"ok": ok}

@app.post("/api/run/scheduler")
def api_scheduler():
    set_setting("scheduler_enabled", "true")
    sched_start()
    return {"ok": True}

@app.post("/api/stop/scheduler")
def api_stop_scheduler():
    global _sched_timer
    set_setting("scheduler_enabled", "false")
    if _sched_timer:
        _sched_timer.cancel()
    log("scheduler", "info", "Scheduler stopped")
    return {"ok": True}

# ── API: Settings ─────────────────────────────────────────────────────────────

@app.get("/api/settings")
def api_settings():
    conn = db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

@app.post("/api/settings")
def api_set(req: SettingReq):
    set_setting(req.key, req.value)
    if req.key in ("scheduler_enabled", "scheduler_interval_hours"):
        sched_start()
    return {"ok": True}

# ── API: Activity log ─────────────────────────────────────────────────────────

@app.get("/api/log")
def api_log(limit: int = 100):
    conn = db()
    rows = conn.execute(
        "SELECT id, timestamp, source, level, message FROM activity_log ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "ts": r[1][:19], "source": r[2], "level": r[3], "message": r[4]} for r in rows]

@app.get("/events")
async def sse_events():
    async def gen():
        last_id = 0
        # Bootstrap: send last 30 entries
        conn = db()
        rows = conn.execute(
            "SELECT id, timestamp, source, level, message FROM activity_log ORDER BY id DESC LIMIT 30"
        ).fetchall()
        conn.close()
        for r in reversed(rows):
            last_id = max(last_id, r[0])
            data = json.dumps({"id": r[0], "ts": r[1][:19], "source": r[2], "level": r[3], "message": r[4]})
            yield f"data: {data}\n\n"
        # Stream new entries
        while True:
            await asyncio.sleep(2)
            try:
                conn = db()
                rows = conn.execute(
                    "SELECT id, timestamp, source, level, message FROM activity_log WHERE id > ? ORDER BY id",
                    (last_id,)
                ).fetchall()
                conn.close()
                for r in rows:
                    last_id = r[0]
                    data = json.dumps({"id": r[0], "ts": r[1][:19], "source": r[2], "level": r[3], "message": r[4]})
                    yield f"data: {data}\n\n"
            except Exception:
                pass
    return StreamingResponse(gen(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ── Frontend HTML ─────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Command Center</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #0d1117; --card: #161b22; --border: #30363d;
  --text: #c9d1d9; --muted: #8b949e; --blue: #58a6ff;
  --green: #3fb950; --red: #f85149; --yellow: #d29922;
  --sidebar: #010409;
}
body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; display: flex; min-height: 100vh; }

/* ── Sidebar ── */
.sidebar { width: 220px; min-height: 100vh; background: var(--sidebar); border-right: 1px solid var(--border); display: flex; flex-direction: column; flex-shrink: 0; position: fixed; top: 0; left: 0; bottom: 0; overflow-y: auto; z-index: 100; }
.sidebar-header { padding: 20px 16px 16px; border-bottom: 1px solid var(--border); }
.sidebar-header h1 { font-size: 16px; color: var(--blue); font-weight: 700; }
.sidebar-header p { font-size: 11px; color: var(--muted); margin-top: 2px; }
.nav-item { padding: 10px 16px; cursor: pointer; color: var(--muted); display: flex; align-items: center; gap: 10px; border-left: 3px solid transparent; transition: all .15s; user-select: none; }
.nav-item:hover { color: var(--text); background: #161b22; }
.nav-item.active { color: var(--blue); background: #161b22; border-left-color: var(--blue); }
.nav-icon { font-size: 16px; width: 20px; text-align: center; }
.nav-badge { margin-left: auto; background: var(--red); color: #fff; border-radius: 10px; padding: 1px 7px; font-size: 11px; font-weight: 700; }
.sidebar-footer { margin-top: auto; padding: 12px 16px; border-top: 1px solid var(--border); font-size: 11px; color: var(--muted); }
.rtx-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--red); margin-right: 6px; }
.rtx-dot.on { background: var(--green); }

/* ── Main ── */
.main { margin-left: 220px; flex: 1; padding: 24px; min-height: 100vh; }
.section { display: none; }
.section.active { display: block; }
.page-title { font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 20px; }

/* ── Cards ── */
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
.card-label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }
.card-value { font-size: 26px; font-weight: 700; color: var(--text); }
.card-value.green { color: var(--green); }
.card-value.blue { color: var(--blue); }
.card-value.yellow { color: var(--yellow); }
.card-value.red { color: var(--red); }

/* ── Buttons ── */
.btn { padding: 6px 14px; border-radius: 6px; border: 1px solid var(--border); cursor: pointer; font-size: 13px; font-weight: 500; background: var(--card); color: var(--text); transition: all .15s; }
.btn:hover { background: #21262d; }
.btn-blue { border-color: var(--blue); color: var(--blue); }
.btn-blue:hover { background: #1c2a3a; }
.btn-green { border-color: var(--green); color: var(--green); }
.btn-green:hover { background: #1a3a1a; }
.btn-red { border-color: var(--red); color: var(--red); }
.btn-red:hover { background: #3a1a1a; }
.btn-yellow { border-color: var(--yellow); color: var(--yellow); }
.btn-yellow:hover { background: #3a2a10; }
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn-group { display: flex; gap: 8px; flex-wrap: wrap; }
.btn-lg { padding: 10px 20px; font-size: 14px; }

/* ── Quick actions ── */
.actions-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 24px; }

/* ── Job cards ── */
.job-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 12px; transition: border-color .15s; }
.job-card:hover { border-color: var(--blue); }
.job-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.cat-badge { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 12px; text-transform: uppercase; letter-spacing: .5px; }
.cat-web_dev { background: #1c2a3a; color: var(--blue); }
.cat-scripting { background: #1a3a2a; color: #39d353; }
.cat-design { background: #3a1a3a; color: #d2a8ff; }
.cat-seo { background: #3a2a10; color: var(--yellow); }
.cat-content { background: #3a2a1a; color: #ffa657; }
.cat-data { background: #1a2a3a; color: #79c0ff; }
.cat-mobile_app { background: #3a1a2a; color: #ff7b72; }
.cat-other_it { background: #21262d; color: var(--muted); }
.budget-badge { font-size: 12px; color: var(--green); font-weight: 600; }
.group-badge { font-size: 11px; color: var(--muted); }
.job-post { background: #010409; border-radius: 4px; padding: 10px; font-size: 13px; color: var(--muted); margin-bottom: 10px; max-height: 80px; overflow: hidden; line-height: 1.5; }
.job-post.expanded { max-height: none; }
.proposal-label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }
.proposal-textarea { width: 100%; background: #010409; color: var(--text); border: 1px solid var(--border); border-radius: 4px; padding: 10px; font-family: inherit; font-size: 13px; resize: vertical; min-height: 90px; line-height: 1.5; }
.proposal-textarea:focus { outline: none; border-color: var(--blue); }
.job-actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; align-items: center; }
.job-url { font-size: 11px; color: var(--muted); margin-left: auto; }
.job-url a { color: var(--blue); text-decoration: none; }
.earn-form { display: none; align-items: center; gap: 8px; margin-top: 8px; }
.earn-form input { background: var(--bg); border: 1px solid var(--border); border-radius: 4px; padding: 5px 8px; color: var(--text); font-size: 13px; width: 100px; }

/* ── Filters ── */
.filters { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.filter-tab { padding: 5px 14px; border-radius: 20px; border: 1px solid var(--border); cursor: pointer; font-size: 12px; color: var(--muted); background: none; }
.filter-tab.active { border-color: var(--blue); color: var(--blue); background: #1c2a3a; }
.empty-state { text-align: center; padding: 60px; color: var(--muted); }
.empty-icon { font-size: 48px; margin-bottom: 12px; }

/* ── Income streams ── */
.stream-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 10px; }
.stream-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.stream-title { font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); }
.status-dot.active { background: var(--green); box-shadow: 0 0 6px var(--green); }
.status-dot.idle { background: var(--muted); }
.status-dot.building { background: var(--yellow); box-shadow: 0 0 6px var(--yellow); }
.stream-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 8px; }
.stream-stat { background: #010409; border-radius: 4px; padding: 8px; }
.stream-stat-label { font-size: 10px; color: var(--muted); text-transform: uppercase; }
.stream-stat-value { font-size: 18px; font-weight: 700; color: var(--text); margin-top: 2px; }
.stream-actions { margin-top: 12px; display: flex; gap: 8px; }
.progress-bar { background: var(--border); border-radius: 4px; height: 4px; margin-top: 10px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 4px; transition: width .5s; }

/* ── Activity log ── */
#activity-log { background: #010409; border: 1px solid var(--border); border-radius: 6px; height: 600px; overflow-y: auto; padding: 10px; font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.6; }
.log-entry { padding: 2px 0; border-bottom: 1px solid #161b22; }
.log-entry .ts { color: #4a5568; }
.log-entry .src { color: #58a6ff; }
.log-entry.success .msg { color: var(--green); }
.log-entry.info .msg { color: var(--text); }
.log-entry.warn .msg { color: var(--yellow); }
.log-entry.error .msg { color: var(--red); }

/* ── Settings ── */
.settings-section { margin-bottom: 24px; }
.settings-section h3 { font-size: 14px; font-weight: 600; color: var(--blue); margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid var(--border); }
.form-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.form-label { width: 200px; color: var(--muted); font-size: 13px; flex-shrink: 0; }
.form-input { background: var(--card); border: 1px solid var(--border); border-radius: 4px; padding: 6px 10px; color: var(--text); font-size: 13px; width: 240px; }
.form-input:focus { outline: none; border-color: var(--blue); }
textarea.form-input { width: 400px; min-height: 120px; font-family: monospace; resize: vertical; }
.toggle-wrapper { display: flex; align-items: center; gap: 10px; }
.toggle { appearance: none; width: 36px; height: 20px; background: var(--border); border-radius: 10px; cursor: pointer; position: relative; transition: background .2s; }
.toggle:checked { background: var(--green); }
.toggle::after { content: ''; position: absolute; width: 16px; height: 16px; background: #fff; border-radius: 50%; top: 2px; left: 2px; transition: left .2s; }
.toggle:checked::after { left: 18px; }

/* ── Chart ── */
.chart-wrap { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 24px; }
.chart-title { font-size: 13px; color: var(--muted); margin-bottom: 12px; }
.mini-bars { display: flex; align-items: flex-end; gap: 8px; height: 60px; }
.mini-bar-wrap { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.mini-bar { width: 100%; background: var(--blue); border-radius: 2px 2px 0 0; opacity: .8; min-height: 2px; transition: height .3s; }
.mini-bar-label { font-size: 10px; color: var(--muted); }

/* ── Toast ── */
.toast { position: fixed; bottom: 24px; right: 24px; padding: 12px 20px; border-radius: 8px; font-size: 13px; font-weight: 500; z-index: 9999; display: none; animation: slideIn .2s ease; }
.toast.success { background: #1a3a1a; color: var(--green); border: 1px solid var(--green); }
.toast.error { background: #3a1a1a; color: var(--red); border: 1px solid var(--red); }
.toast.info { background: #1c2a3a; color: var(--blue); border: 1px solid var(--blue); }
@keyframes slideIn { from { transform: translateY(20px); opacity:0; } to { transform: translateY(0); opacity:1; } }

/* ── Misc ── */
.section-subheader { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.divider { border: none; border-top: 1px solid var(--border); margin: 20px 0; }
.tag { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #21262d; color: var(--muted); }
</style>
</head>
<body>

<!-- ── Sidebar ── -->
<nav class="sidebar">
  <div class="sidebar-header">
    <h1>Command Center</h1>
    <p>Online Income Automation</p>
  </div>
  <div class="nav-item active" data-section="dashboard">
    <span class="nav-icon">📊</span> Dashboard
  </div>
  <div class="nav-item" data-section="opportunities">
    <span class="nav-icon">💼</span> Opportunities
    <span class="nav-badge" id="nav-pending">0</span>
  </div>
  <div class="nav-item" data-section="streams">
    <span class="nav-icon">💰</span> Income Streams
  </div>
  <div class="nav-item" data-section="activity">
    <span class="nav-icon">📡</span> Activity Log
  </div>
  <div class="nav-item" data-section="settings">
    <span class="nav-icon">⚙️</span> Settings
  </div>
  <div class="sidebar-footer">
    <div><span class="rtx-dot" id="rtx-dot"></span><span id="rtx-label">RTX Offline</span></div>
    <div style="margin-top:6px;color:var(--muted)">port 8766</div>
  </div>
</nav>

<!-- ── Main ── -->
<main class="main">

<!-- DASHBOARD -->
<section class="section active" id="sec-dashboard">
  <div class="page-title">Dashboard</div>

  <div class="cards">
    <div class="card">
      <div class="card-label">Scraped Today</div>
      <div class="card-value blue" id="stat-today">–</div>
    </div>
    <div class="card">
      <div class="card-label">Total Posts</div>
      <div class="card-value" id="stat-total">–</div>
    </div>
    <div class="card">
      <div class="card-label">Pending</div>
      <div class="card-value yellow" id="stat-pending">–</div>
    </div>
    <div class="card">
      <div class="card-label">Approved</div>
      <div class="card-value green" id="stat-approved">–</div>
    </div>
    <div class="card">
      <div class="card-label">Sent</div>
      <div class="card-value green" id="stat-sent">–</div>
    </div>
    <div class="card">
      <div class="card-label">Earned</div>
      <div class="card-value green" id="stat-earned">– PLN</div>
    </div>
  </div>

  <div class="actions-row">
    <button class="btn btn-blue btn-lg" onclick="runScrape()">🔍 Scrape FB Groups</button>
    <button class="btn btn-green btn-lg" onclick="runPipeline()">🤖 Process with RTX</button>
    <button class="btn btn-lg" onclick="runOLX()">📦 OLX Scan</button>
    <button class="btn btn-yellow btn-lg" onclick="showSection('opportunities')">💼 Review Proposals</button>
  </div>

  <div class="chart-wrap">
    <div class="chart-title">Posts scraped (last 7 days)</div>
    <div class="mini-bars" id="week-chart"></div>
  </div>

  <div class="card">
    <div class="card-label" style="margin-bottom:10px">Jobs by category</div>
    <div id="cat-bars"></div>
  </div>
</section>

<!-- OPPORTUNITIES -->
<section class="section" id="sec-opportunities">
  <div class="section-subheader">
    <div class="page-title" style="margin:0">Opportunities</div>
    <div class="btn-group">
      <button class="btn btn-sm" onclick="loadJobs('pending')">Refresh</button>
    </div>
  </div>

  <div class="filters">
    <button class="filter-tab active" onclick="filterJobs('pending',this)">Pending</button>
    <button class="filter-tab" onclick="filterJobs('approved',this)">Approved</button>
    <button class="filter-tab" onclick="filterJobs('sent',this)">Sent</button>
    <button class="filter-tab" onclick="filterJobs('skipped',this)">Skipped</button>
  </div>

  <div id="jobs-feed"></div>
</section>

<!-- INCOME STREAMS -->
<section class="section" id="sec-streams">
  <div class="page-title">Income Streams</div>

  <div class="stream-card">
    <div class="stream-header">
      <div class="stream-title">
        <div class="status-dot active"></div>
        FB Freelance Pipeline
      </div>
      <div class="tag">ACTIVE</div>
    </div>
    <div class="stream-stats">
      <div class="stream-stat"><div class="stream-stat-label">Posts scraped</div><div class="stream-stat-value" id="s1-posts">–</div></div>
      <div class="stream-stat"><div class="stream-stat-label">Jobs found</div><div class="stream-stat-value" id="s1-jobs">–</div></div>
      <div class="stream-stat"><div class="stream-stat-label">Approved</div><div class="stream-stat-value" id="s1-approved">–</div></div>
      <div class="stream-stat"><div class="stream-stat-label">Sent</div><div class="stream-stat-value" id="s1-sent">–</div></div>
      <div class="stream-stat"><div class="stream-stat-label">Earned</div><div class="stream-stat-value green" id="s1-earned">0 PLN</div></div>
    </div>
    <div class="stream-actions">
      <button class="btn btn-blue btn-sm" onclick="runScrape()">Run Scraper</button>
      <button class="btn btn-green btn-sm" onclick="runPipeline()">Process RTX</button>
      <button class="btn btn-sm" onclick="showSection('opportunities')">Review</button>
    </div>
    <div class="progress-bar"><div class="progress-fill" style="width:65%;background:var(--blue)"></div></div>
  </div>

  <div class="stream-card">
    <div class="stream-header">
      <div class="stream-title">
        <div class="status-dot idle"></div>
        OLX Arbitrage Scanner
      </div>
      <div class="tag">IDLE</div>
    </div>
    <div class="stream-stats">
      <div class="stream-stat"><div class="stream-stat-label">Last scan</div><div class="stream-stat-value" style="font-size:14px" id="s2-last">Never</div></div>
      <div class="stream-stat"><div class="stream-stat-label">Opportunities</div><div class="stream-stat-value" id="s2-opps">–</div></div>
      <div class="stream-stat"><div class="stream-stat-label">Avg spread</div><div class="stream-stat-value" id="s2-spread">–</div></div>
    </div>
    <div class="stream-actions">
      <button class="btn btn-sm" onclick="runOLX()">Run Scan</button>
    </div>
  </div>

  <div class="stream-card">
    <div class="stream-header">
      <div class="stream-title">
        <div class="status-dot building"></div>
        Content Writing (AI)
      </div>
      <div class="tag" style="color:var(--yellow);border-color:var(--yellow)">COMING SOON</div>
    </div>
    <p style="color:var(--muted);font-size:13px;margin-top:6px">Fiverr/Useme gigs where RTX writes articles, SEO content and translations. Zero delivery cost.</p>
    <div class="stream-actions">
      <button class="btn btn-sm" disabled style="opacity:.4;cursor:not-allowed">Configure</button>
    </div>
  </div>

  <div class="stream-card">
    <div class="stream-header">
      <div class="stream-title">
        <div class="status-dot building"></div>
        Crypto Arbitrage Bot
      </div>
      <div class="tag" style="color:var(--yellow);border-color:var(--yellow)">PLANNED</div>
    </div>
    <p style="color:var(--muted);font-size:13px;margin-top:6px">Price difference monitoring between Binance, Kraken, Bitbay. Auto-alert on spread &gt;0.5%.</p>
    <div class="stream-actions">
      <button class="btn btn-sm" disabled style="opacity:.4;cursor:not-allowed">Configure</button>
    </div>
  </div>

  <div class="stream-card">
    <div class="stream-header">
      <div class="stream-title">
        <div class="status-dot building"></div>
        Lead Generation (Real Estate)
      </div>
      <div class="tag" style="color:var(--yellow);border-color:var(--yellow)">READY</div>
    </div>
    <p style="color:var(--muted);font-size:13px;margin-top:6px">fb_monitor_engine.py – scrapes real estate leads from FB groups. Sell to agents.</p>
    <div class="stream-actions">
      <button class="btn btn-sm" onclick="showToast('Real estate module: run python fb_monitor_engine.py','info')">Info</button>
    </div>
  </div>
</section>

<!-- ACTIVITY LOG -->
<section class="section" id="sec-activity">
  <div class="section-subheader">
    <div class="page-title" style="margin:0">Activity Log</div>
    <button class="btn btn-sm btn-red" onclick="clearLog()">Clear</button>
  </div>
  <div id="activity-log"></div>
</section>

<!-- SETTINGS -->
<section class="section" id="sec-settings">
  <div class="page-title">Settings</div>

  <div class="settings-section">
    <h3>Scheduler</h3>
    <div class="form-row">
      <div class="form-label">Auto-run enabled</div>
      <div class="toggle-wrapper">
        <input type="checkbox" class="toggle" id="sched-enabled">
        <label for="sched-enabled" style="color:var(--muted);font-size:13px">Run scraper + pipeline automatically</label>
      </div>
    </div>
    <div class="form-row">
      <div class="form-label">Interval (hours)</div>
      <input type="number" class="form-input" id="sched-interval" value="4" min="0.5" max="24" step="0.5" style="width:100px">
    </div>
  </div>

  <div class="settings-section">
    <h3>RTX / Ollama</h3>
    <div class="form-row">
      <div class="form-label">Model</div>
      <input type="text" class="form-input" id="rtx-model" value="qwen2.5:7b">
    </div>
    <div class="form-row">
      <div class="form-label">Max posts per group</div>
      <input type="number" class="form-input" id="max-posts" value="20" min="5" max="100" style="width:100px">
    </div>
  </div>

  <div class="settings-section">
    <h3>FB Scraper</h3>
    <div class="form-row">
      <div class="form-label">Target groups (one per line)</div>
      <textarea class="form-input" id="target-groups"></textarea>
    </div>
  </div>

  <div class="settings-section">
    <h3>Auto-approve</h3>
    <div class="form-row">
      <div class="form-label">Min budget (PLN) to auto-approve</div>
      <input type="number" class="form-input" id="auto-threshold" value="0" min="0" step="100" style="width:120px">
      <span style="color:var(--muted);font-size:12px">0 = disabled</span>
    </div>
  </div>

  <button class="btn btn-blue btn-lg" onclick="saveSettings()">Save Settings</button>
</section>

</main>

<!-- Toast -->
<div class="toast" id="toast"></div>

<script>
// ── Navigation ────────────────────────────────────────────────
function showSection(id) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('sec-' + id).classList.add('active');
  document.querySelector(`[data-section="${id}"]`).classList.add('active');
  if (id === 'opportunities') loadJobs('pending');
  if (id === 'activity') setupSSE();
  if (id === 'settings') loadSettings();
  if (id === 'streams') refreshStats();
}
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => showSection(item.dataset.section));
});

// ── Toast ─────────────────────────────────────────────────────
let toastTimer;
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type}`;
  t.style.display = 'block';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.style.display = 'none', 3000);
}

// ── Stats ─────────────────────────────────────────────────────
let lastStats = {};
async function refreshStats() {
  const s = await fetch('/api/stats').then(r => r.json()).catch(() => null);
  if (!s) return;
  lastStats = s;
  document.getElementById('stat-today').textContent = s.posts_today;
  document.getElementById('stat-total').textContent = s.posts_total;
  document.getElementById('stat-pending').textContent = s.pending;
  document.getElementById('stat-approved').textContent = s.approved;
  document.getElementById('stat-sent').textContent = s.sent;
  document.getElementById('stat-earned').textContent = s.earnings_pln.toFixed(0) + ' PLN';
  document.getElementById('nav-pending').textContent = s.pending;
  // RTX status
  const dot = document.getElementById('rtx-dot');
  const lbl = document.getElementById('rtx-label');
  dot.className = 'rtx-dot' + (s.rtx_ok ? ' on' : '');
  lbl.textContent = s.rtx_ok ? 'RTX Online' : 'RTX Offline';
  // Streams
  if (document.getElementById('s1-posts')) {
    document.getElementById('s1-posts').textContent = s.posts_total;
    document.getElementById('s1-jobs').textContent = s.total_jobs;
    document.getElementById('s1-approved').textContent = s.approved;
    document.getElementById('s1-sent').textContent = s.sent;
    document.getElementById('s1-earned').textContent = s.earnings_pln.toFixed(0) + ' PLN';
  }
  // Week chart
  renderWeekChart(s.week_posts);
  renderCatBars(s.by_category);
}

function renderWeekChart(data) {
  const el = document.getElementById('week-chart');
  if (!el || !data.length) return;
  const max = Math.max(...data.map(d => d.count), 1);
  const days = ['Nd','Pn','Wt','Sr','Cz','Pt','So'];
  el.innerHTML = data.map(d => {
    const h = Math.max(Math.round((d.count / max) * 56), 2);
    const day = days[new Date(d.date).getDay()];
    return `<div class="mini-bar-wrap">
      <div class="mini-bar" style="height:${h}px" title="${d.count} posts"></div>
      <div class="mini-bar-label">${day}</div>
    </div>`;
  }).join('');
}

function renderCatBars(data) {
  const el = document.getElementById('cat-bars');
  if (!el || !data.length) return;
  const max = Math.max(...data.map(d => d.count), 1);
  const colors = {web_dev:'var(--blue)',scripting:'var(--green)',design:'#d2a8ff',seo:'var(--yellow)',content:'#ffa657',data:'#79c0ff',mobile_app:'#ff7b72',other_it:'var(--muted)'};
  el.innerHTML = data.map(d => `
    <div style="margin-bottom:8px">
      <div style="display:flex;justify-content:space-between;margin-bottom:3px">
        <span style="font-size:12px;color:var(--muted)">${d.cat}</span>
        <span style="font-size:12px;color:var(--text)">${d.count}</span>
      </div>
      <div style="background:var(--border);border-radius:3px;height:6px">
        <div style="width:${Math.round(d.count/max*100)}%;height:100%;border-radius:3px;background:${colors[d.cat]||'var(--muted)'}"></div>
      </div>
    </div>`).join('');
}

setInterval(refreshStats, 15000);
refreshStats();

// ── Jobs ──────────────────────────────────────────────────────
let currentStatus = 'pending';

async function loadJobs(status = 'pending') {
  currentStatus = status;
  const feed = document.getElementById('jobs-feed');
  feed.innerHTML = '<div style="color:var(--muted);padding:20px">Loading...</div>';
  const jobs = await fetch(`/api/jobs?status=${status}`).then(r => r.json()).catch(() => []);
  if (!jobs.length) {
    feed.innerHTML = `<div class="empty-state"><div class="empty-icon">📭</div><div>No ${status} jobs</div></div>`;
    return;
  }
  feed.innerHTML = jobs.map(j => buildJobCard(j)).join('');
}

function filterJobs(status, btn) {
  document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadJobs(status);
}

function buildJobCard(j) {
  const budget = j.budget_pln ? `<span class="budget-badge">${j.budget_pln} PLN</span>` : '';
  const contact = j.contact ? `<span class="tag">📧 ${j.contact}</span>` : '';
  const postUrl = j.post_url && j.post_url.includes('facebook.com') && !j.post_url.includes('/test/')
    ? `<a href="${j.post_url}" target="_blank">Open Post ↗</a>` : '';

  const isPending = currentStatus === 'pending';
  const isApproved = currentStatus === 'approved';

  const actions = isPending ? `
    <button class="btn btn-green btn-sm" onclick="approveJob('${j.id}')">✓ Approve</button>
    <button class="btn btn-red btn-sm" onclick="skipJob('${j.id}')">✗ Skip</button>
    <button class="btn btn-blue btn-sm" onclick="copyProposal('${j.id}')">Copy</button>
  ` : isApproved ? `
    <button class="btn btn-blue btn-sm" onclick="markSent('${j.id}')">Sent ✓</button>
    <button class="btn btn-sm" onclick="copyProposal('${j.id}')">Copy</button>
    <button class="btn btn-green btn-sm" onclick="toggleEarn('${j.id}')">+ Log Earning</button>
  ` : `<button class="btn btn-sm" onclick="copyProposal('${j.id}')">Copy</button>`;

  return `<div class="job-card" id="job-${j.id}">
    <div class="job-header">
      <span class="cat-badge cat-${j.category}">${j.category}</span>
      ${budget}
      <span class="group-badge">📍 ${j.group_name}</span>
      ${contact}
      <span style="margin-left:auto;font-size:11px;color:var(--muted)">${j.created_at}</span>
    </div>
    <div class="job-post" id="post-${j.id}" onclick="togglePost('${j.id}')" style="cursor:pointer" title="Click to expand">
      ${j.post_text.replace(/</g,'&lt;').replace(/\n/g,'<br>')}
    </div>
    <div class="proposal-label">Propozycja oferty (edytowalna)</div>
    <textarea class="proposal-textarea" id="proposal-${j.id}" oninput="saveProposal('${j.id}')">${j.proposal || ''}</textarea>
    <div class="job-actions">
      ${actions}
      <span class="job-url">${postUrl}</span>
    </div>
    <div class="earn-form" id="earn-${j.id}">
      <input type="number" placeholder="Kwota PLN" id="earn-amt-${j.id}" min="1">
      <input type="text" placeholder="Notatka" id="earn-note-${j.id}" style="width:200px">
      <button class="btn btn-green btn-sm" onclick="logEarning('${j.id}')">Zapisz</button>
    </div>
  </div>`;
}

function togglePost(id) {
  document.getElementById('post-' + id).classList.toggle('expanded');
}

let saveTimers = {};
function saveProposal(id) {
  clearTimeout(saveTimers[id]);
  saveTimers[id] = setTimeout(async () => {
    const txt = document.getElementById('proposal-' + id).value;
    await fetch(`/api/jobs/${id}/proposal`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({proposal: txt})});
  }, 1000);
}

async function approveJob(id) {
  await fetch(`/api/jobs/${id}/approve`, {method:'POST'});
  document.getElementById('job-' + id).style.opacity = '.4';
  setTimeout(() => { document.getElementById('job-' + id)?.remove(); }, 400);
  showToast('Zatwierdzone! Skopiuj i wyślij ofertę.');
  refreshStats();
}

async function skipJob(id) {
  await fetch(`/api/jobs/${id}/skip`, {method:'POST'});
  document.getElementById('job-' + id).style.opacity = '.2';
  setTimeout(() => { document.getElementById('job-' + id)?.remove(); }, 300);
}

async function markSent(id) {
  await fetch(`/api/jobs/${id}/sent`, {method:'POST'});
  showToast('Oznaczono jako wysłane!');
  loadJobs(currentStatus);
}

function copyProposal(id) {
  const txt = document.getElementById('proposal-' + id).value;
  navigator.clipboard.writeText(txt).then(() => showToast('Skopiowano do schowka!'));
}

function toggleEarn(id) {
  const el = document.getElementById('earn-' + id);
  el.style.display = el.style.display === 'flex' ? 'none' : 'flex';
}

async function logEarning(id) {
  const amount = parseFloat(document.getElementById('earn-amt-' + id).value);
  const note = document.getElementById('earn-note-' + id).value;
  if (!amount) return showToast('Podaj kwotę', 'error');
  await fetch(`/api/jobs/${id}/earn`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({amount_pln: amount, note})});
  showToast(`Zarobek ${amount} PLN zapisany!`);
  document.getElementById('earn-' + id).style.display = 'none';
  refreshStats();
}

// ── Actions ───────────────────────────────────────────────────
async function runScrape() {
  const r = await fetch('/api/run/scrape', {method:'POST'}).then(r => r.json());
  showToast(r.msg || 'Scraper started', r.ok ? 'info' : 'error');
  setTimeout(() => { showSection('activity'); }, 500);
}

async function runPipeline() {
  const r = await fetch('/api/run/pipeline', {method:'POST'}).then(r => r.json());
  showToast('RTX pipeline started', 'info');
  setTimeout(() => { showSection('activity'); }, 500);
}

async function runOLX() {
  const r = await fetch('/api/run/olx', {method:'POST'}).then(r => r.json());
  showToast(r.ok ? 'OLX scan started' : 'Already running', r.ok ? 'info' : 'error');
}

// ── Activity Log (SSE) ────────────────────────────────────────
let sseSource = null;
const levelColors = {success: '#3fb950', info: '#c9d1d9', warn: '#d29922', error: '#f85149'};

function setupSSE() {
  if (sseSource) return;
  sseSource = new EventSource('/events');
  sseSource.onmessage = (e) => {
    const entry = JSON.parse(e.data);
    const log = document.getElementById('activity-log');
    const div = document.createElement('div');
    div.className = `log-entry ${entry.level}`;
    div.innerHTML = `<span class="ts">[${entry.ts.slice(11)}]</span> <span class="src">[${entry.source}]</span> <span class="msg">${entry.message}</span>`;
    log.insertBefore(div, log.firstChild);
    if (log.children.length > 300) log.lastChild.remove();
  };
}

function clearLog() {
  document.getElementById('activity-log').innerHTML = '';
}

// Auto-setup SSE on load
setTimeout(setupSSE, 500);

// ── Settings ──────────────────────────────────────────────────
async function loadSettings() {
  const s = await fetch('/api/settings').then(r => r.json()).catch(() => ({}));
  document.getElementById('sched-enabled').checked = s.scheduler_enabled === 'true';
  document.getElementById('sched-interval').value = s.scheduler_interval_hours || '4';
  document.getElementById('rtx-model').value = s.rtx_model || 'qwen2.5:7b';
  document.getElementById('max-posts').value = s.max_posts_per_group || '20';
  document.getElementById('target-groups').value = s.target_groups || '';
  document.getElementById('auto-threshold').value = s.auto_approve_threshold || '0';
}

async function saveSettings() {
  const settings = {
    scheduler_enabled: document.getElementById('sched-enabled').checked ? 'true' : 'false',
    scheduler_interval_hours: document.getElementById('sched-interval').value,
    rtx_model: document.getElementById('rtx-model').value,
    max_posts_per_group: document.getElementById('max-posts').value,
    target_groups: document.getElementById('target-groups').value,
    auto_approve_threshold: document.getElementById('auto-threshold').value,
  };
  for (const [key, value] of Object.entries(settings)) {
    await fetch('/api/settings', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({key, value})
    });
  }
  showToast('Ustawienia zapisane!');
}
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
def root():
    return HTML

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  COMMAND CENTER - Centrum Dowodzenia")
    print("  http://localhost:8766")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8766, log_level="warning")
