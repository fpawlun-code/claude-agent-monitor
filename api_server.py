"""
REST API Server - PHASE 4B Week 2
FastAPI endpoints exposing monitoring data, KPIs, alerts.
Run: uvicorn api_server:app --host 0.0.0.0 --port 8765 --reload
"""

import json
import sqlite3
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


def _load_leads(limit: int = 10) -> List[Dict[str, Any]]:
    db_path = PROJECT_DIR / "fb_data" / "consulting.db"
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, need_type, est_budget, status, author, source_url, post_text, found_at FROM consulting_leads "
            "WHERE status != 'demo' AND (source_url LIKE '%/posts/%' OR source_url LIKE '%useme.com/pl/jobs/%,%') ORDER BY est_budget DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


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


# ── Monetization helpers ──────────────────────────────────────

def _load_monetization() -> Dict[str, Any]:
    path = REPORTS_DIR / "monetization_status.json"
    return _load_json(path) or {
        "phase": "1", "useme": {}, "olx": {}, "monitor": {}, "earnings": {"total_pln": 0}
    }


def _monetization_html() -> str:
    m = _load_monetization()
    useme = m.get("useme", {})
    monitor = m.get("monitor", {})
    earnings = m.get("earnings", {})

    pct = useme.get("profile_pct", 0)
    pct_color = "green" if pct >= 90 else ("yellow" if pct >= 60 else "red")
    gh_active = monitor.get("github_actions_active", False)
    tg_configured = monitor.get("telegram_configured", False)
    monitor_status = "✅ Aktywny" if (gh_active and tg_configured) else (
        "⚠️ Częściowy" if (gh_active or tg_configured) else "❌ Nieaktywny"
    )
    monitor_color = "green" if (gh_active and tg_configured) else ("yellow" if (gh_active or tg_configured) else "red")
    bids = useme.get("bids_sent", 0)
    earned = earnings.get("total_pln", 0)

    bio = "✓" if useme.get("bio_done") else "✗"
    cats = "✓" if useme.get("categories_done") else "✗"
    portfolio = useme.get("portfolio_items", 0)

    return f"""<div class="section">
  <h2>&#x1F4B0; Monetyzacja &mdash; Faza 1: Pierwsze pieniadze</h2>
  <p class="section-desc">Status platnosci i aktywnosci na platformach freelancerskich</p>
  <div class="grid">
    <div class="card">
      <h3>Profil Useme</h3>
      <div class="val {pct_color}">{pct}%</div>
      <div class="hint">Bio: {bio} | Kategorie: {cats} | Portfolio: {portfolio} poz.</div>
    </div>
    <div class="card">
      <h3>Monitor ofert</h3>
      <div class="val {monitor_color}" style="font-size:18px">{monitor_status}</div>
      <div class="hint">GitHub Actions + Telegram</div>
    </div>
    <div class="card">
      <h3>Wyslane oferty</h3>
      <div class="val {'green' if bids >= 10 else 'yellow'}">{bids}</div>
      <div class="hint">Cel: 10 / tydzien</div>
    </div>
    <div class="card">
      <h3>Zarobki</h3>
      <div class="val green">{earned} PLN</div>
      <div class="hint">Cel miesiąc 2: 1500 PLN</div>
    </div>
  </div>
  <div style="margin-top:12px;font-size:13px">
    <a href="https://useme.com/pl/roles/contractor/profile/" target="_blank"
       style="color:#58a6ff;margin-right:20px">&#x1F4DD; Edytuj profil Useme &rarr;</a>
    <a href="https://useme.com/pl/jobs/?category=100" target="_blank"
       style="color:#58a6ff;margin-right:20px">&#x1F50D; Przegladaj oferty Useme &rarr;</a>
    <a href="https://www.olx.pl/uslugi/komputery-i-internet/" target="_blank"
       style="color:#58a6ff">&#x1F4CC; OLX IT &rarr;</a>
  </div>
</div>"""


# ── Routes ────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def root() -> str:
    """Web dashboard."""
    history_data = _load_json_list(REPORTS_DIR / "metrics_history.json")
    alerts_data = _load_json(REPORTS_DIR / "active_alerts.json") or {}
    drift_data = _load_json(REPORTS_DIR / "drift_report.json") or {}
    leads = _load_leads(10)

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
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>ClaudeAgent - Panel sterowania</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0d1117; color: #c9d1d9; margin: 0; padding: 24px; max-width: 1100px; margin: 0 auto; padding: 24px; }}
  h1 {{ color: #58a6ff; margin-bottom: 2px; font-size: 26px; }}
  .hero-sub {{ color: #8b949e; font-size: 14px; margin-bottom: 6px; }}
  .hero-desc {{ color: #c9d1d9; font-size: 13px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px 16px; margin-bottom: 24px; line-height: 1.6; }}
  .hero-desc strong {{ color: #58a6ff; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 18px; }}
  .card h3 {{ margin: 0 0 6px; font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }}
  .card .val {{ font-size: 30px; font-weight: bold; }}
  .card .hint {{ font-size: 11px; color: #8b949e; margin-top: 2px; }}
  .card .explain {{ font-size: 12px; color: #6e7681; margin-top: 8px; padding-top: 8px; border-top: 1px solid #21262d; line-height: 1.4; }}
  .green {{ color: #3fb950; }}
  .red {{ color: #f85149; }}
  .yellow {{ color: #d29922; }}
  .section {{ margin-top: 32px; }}
  .section h2 {{ color: #58a6ff; font-size: 15px; border-bottom: 1px solid #30363d; padding-bottom: 8px; margin-bottom: 14px; }}
  .section-desc {{ font-size: 12px; color: #6e7681; margin: -8px 0 14px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 12px; color: #8b949e; border-bottom: 1px solid #21262d; font-size: 12px; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #1c2128; }}
  tr:hover td {{ background: #1c2128; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }}
  .badge-green {{ background: #1a3a1a; color: #3fb950; }}
  .badge-red {{ background: #3a1a1a; color: #f85149; }}
  .badge-yellow {{ background: #3a2d0d; color: #d29922; }}
  .badge-gray {{ background: #21262d; color: #8b949e; }}
  /* Status chips */
  .status-row {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:8px; }}
  .stat-chip {{ background:#21262d; border:1px solid #30363d; border-radius:6px; padding:6px 12px; font-size:12px; }}
  .stat-chip span {{ color:#58a6ff; font-weight:bold; }}
  /* Timeline */
  .tl-legend {{ display:flex; gap:16px; font-size:11px; color:#8b949e; margin-bottom:16px; }}
  .tl-legend-dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; vertical-align:middle; }}
  .timeline {{ position: relative; padding-left: 28px; }}
  .timeline::before {{ content:''; position:absolute; left:10px; top:0; bottom:0; width:2px; background:#30363d; }}
  .tl-item {{ position:relative; margin-bottom:16px; padding-left:16px; }}
  .tl-item::before {{ content:''; position:absolute; left:-22px; top:5px; width:12px; height:12px; border-radius:50%; border:2px solid; }}
  .tl-done::before {{ background:#1a3a1a; border-color:#3fb950; }}
  .tl-progress::before {{ background:#3a2d0d; border-color:#d29922; }}
  .tl-planned::before {{ background:#21262d; border-color:#484f58; }}
  .tl-phase {{ font-size:12px; font-weight:bold; margin-bottom:3px; }}
  .tl-done .tl-phase {{ color:#3fb950; }}
  .tl-progress .tl-phase {{ color:#d29922; }}
  .tl-planned .tl-phase {{ color:#484f58; }}
  .tl-desc {{ font-size:12px; color:#8b949e; line-height:1.5; }}
  /* Empty state */
  .empty-state {{ text-align:center; padding:28px; color:#484f58; font-size:13px; background:#161b22; border-radius:8px; border:1px dashed #30363d; }}
  .empty-state .empty-title {{ font-size:15px; color:#6e7681; margin-bottom:6px; }}
  .empty-state code {{ background:#21262d; padding:2px 8px; border-radius:4px; font-size:12px; color:#8b949e; }}
</style>
</head>
<body>

<h1>ClaudeAgent &mdash; Panel sterowania</h1>
<p class="hero-sub">Odswiezanie co 60s &nbsp;|&nbsp; {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
<div class="hero-desc">
  <strong>Co to jest ClaudeAgent?</strong> To Twoj osobisty system AI zbudowany na domowym komputerze z karta RTX.
  Skladaja sie na niego dwa elementy: <strong>silnik AI (RTX + qwen2.5:7b)</strong> ktory przetwarza zadania lokalnie (bez plac&#281;nia za API),
  oraz <strong>pipeline zarabiania</strong> ktory skanuje grupy FB w poszukiwaniu zlecen IT i generuje oferty konsultingowe.
  Ten panel pokazuje aktualny stan obu czesci.
</div>

<div class="grid">
  <div class="card">
    <h3>Testy automatyczne</h3>
    <div class="val {'green' if tests.get('pass_rate', 0) >= 0.9 else 'yellow'}">{tests.get('pass_rate', 0)*100:.1f}%</div>
    <div class="hint">{tests.get('passed', 0)} z {tests.get('total', 0)} testow zdanych</div>
    <div class="explain">Ile % automatycznych testow przechodzi poprawnie. Powyzej 90% = system dziala stabilnie.</div>
  </div>
  <div class="card">
    <h3>Jakosc kodu</h3>
    <div class="val {'green' if pylint.get('average', 0) >= 8 else 'yellow'}">{pylint.get('average', 0):.2f}<span style="font-size:15px">/10</span></div>
    <div class="hint">Ocena czytelnosci i poprawnosci kodu</div>
    <div class="explain">Automatyczna ocena kodu (skala 1-10). Powyzej 8.0 = dobra jakosc, mala szansa na bledy.</div>
  </div>
  <div class="card">
    <h3>Nieoczekiwane zmiany</h3>
    <div class="val" style="color:{drift_color}">{'UWAGA' if drift_data.get('alert') else 'OK'}</div>
    <div class="hint">{drift_data.get('drift_ratio', 0)*100:.1f}% plikow zmienionych</div>
    <div class="explain">Wykrywa czy ktos (lub cos) zmienil pliki systemu bez wiedzy. OK = wszystko jak bylo.</div>
  </div>
  <div class="card">
    <h3>Aktywne alerty</h3>
    <div class="val" style="color:{alert_color}">{len(active_alerts)}</div>
    <div class="hint">{'Brak problemow' if not active_alerts else ', '.join(active_alerts[:2])}</div>
    <div class="explain">Liczba aktywnych ostrzezen systemowych. Zero = wszystko w porzadku.</div>
  </div>
  <div class="card">
    <h3>Historia pomiarow</h3>
    <div class="val green">{len(history_data)}</div>
    <div class="hint">Zapisanych migawek stanu systemu</div>
    <div class="explain">Ile razy system zrobil zdjecie swojego stanu. Wiecej = lepszy przeglad trendow.</div>
  </div>
</div>

<div class="section">
  <h2>Aktualny etap projektu</h2>
  <p class="section-desc">Gdzie jestesmy teraz i co jest gotowe do uzycia</p>
  <div class="status-row">
    <div class="stat-chip">Projekt: <span>ClaudeAgent</span></div>
    <div class="stat-chip">Faza: <span>5 &mdash; Zarabianie</span></div>
    <div class="stat-chip">Model AI: <span>qwen2.5:7b (RTX 4060)</span></div>
    <div class="stat-chip">Scraper FB: <span>gotowy</span></div>
    <div class="stat-chip">Modul konsultingowy: <span>gotowy</span></div>
    <div class="stat-chip">Realne leady: <span>{len(leads)} znalezionych</span></div>
  </div>
</div>

<div class="section">
  <h2>Mapa drogi projektu</h2>
  <p class="section-desc">Od czego zaczelismy i dokad zmierzamy</p>
  <div class="tl-legend">
    <span><span class="tl-legend-dot" style="background:#3fb950;border:2px solid #3fb950"></span>Gotowe</span>
    <span><span class="tl-legend-dot" style="background:#3a2d0d;border:2px solid #d29922"></span>W toku</span>
    <span><span class="tl-legend-dot" style="background:#21262d;border:2px solid #484f58"></span>Planowane</span>
  </div>
  <div class="timeline">
    <div class="tl-item tl-done">
      <div class="tl-phase">Faza 1 &mdash; Pamiec i wiedza</div>
      <div class="tl-desc">Podlaczenie bazy wektorowej (Qdrant) i lokalnego modelu AI (qwen2.5:7b na karcie RTX). System zaczal "pamietac" poprzednie rozmowy.</div>
    </div>
    <div class="tl-item tl-done">
      <div class="tl-phase">Faza A+B &mdash; Delegowanie zadan</div>
      <div class="tl-desc">Claude przestal robic wszystko sam &mdash; zaczal zlecac ciezka robote do RTX. Oszczednosc: 90%+ zuzycia tokenow API.</div>
    </div>
    <div class="tl-item tl-done">
      <div class="tl-phase">Faza C &mdash; Zaawansowane funkcje</div>
      <div class="tl-desc">Cache odpowiedzi (5 min), operacje wsadowe, automatyczne decydowanie co delegowac. System stał sie znacznie szybszy.</div>
    </div>
    <div class="tl-item tl-done">
      <div class="tl-phase">Faza 3 &mdash; Testy i CI/CD</div>
      <div class="tl-desc">30 testow automatycznych, ocena kodu Pylint 8.87/10, pipeline GitHub Actions. Kod jest sprawdzany automatycznie przy kazdej zmianie.</div>
    </div>
    <div class="tl-item tl-done">
      <div class="tl-phase">Faza 4A &mdash; Samoleczenie</div>
      <div class="tl-desc">System sam wykrywa zmiany w plikach (drift), sam diagnozuje bledy testow i generuje raporty o swoim stanie zdrowia.</div>
    </div>
    <div class="tl-item tl-done">
      <div class="tl-phase">Faza 4B &mdash; API i routing modeli</div>
      <div class="tl-desc">Ten panel (FastAPI), 9 endpointow REST, inteligentny router ktory dobiera model AI do rodzaju zadania.</div>
    </div>
    <div class="tl-item tl-progress">
      <div class="tl-phase">Faza 5 &mdash; Zarabianie (AKTUALNY ETAP)</div>
      <div class="tl-desc">Scraper grup FB szuka zlecen IT. Modul konsultingowy (ai_consulting.py) analizuje posty i generuje gotowe oferty. Cel: pierwsze zlecenia i przychod.</div>
    </div>
    <div class="tl-item tl-planned">
      <div class="tl-phase">Faza 6 &mdash; Pelna autonomia</div>
      <div class="tl-desc">System sam wysyla oferty, sledzi odpowiedzi, liczy zarobki i uczy sie na podstawie wynikow. Dziala 24/7 bez ingerencji.</div>
    </div>
  </div>
</div>

{_monetization_html()}

<div class="section">
  <h2>Top 10 najlepszych leadow z FB</h2>
  <p class="section-desc">Najlepiej platne zlecenia znalezione przez skaner grup Facebook &mdash; posortowane po budzecie</p>
  {'<p style="text-align:right;font-size:12px;margin-bottom:8px"><a href="/leads" style="color:#58a6ff">Zobacz wszystkie leady &rarr;</a> &nbsp;|&nbsp; <a href="/leads/export" style="color:#58a6ff">Pobierz CSV</a></p><table><tr><th>Budzet</th><th>Rodzaj zlecenia</th><th>Autor</th><th>Link do posta</th><th>Data</th></tr>' + ''.join(
    f'<tr>'
    f'<td class="green" style="font-weight:bold;white-space:nowrap">{int(l["est_budget"])} PLN</td>'
    f'<td>{l["need_type"].replace("_"," ").replace("|",", ").title()}</td>'
    f'<td>{l["author"] or "&mdash;"}</td>'
    f'<td><a href="{l["source_url"]}" target="_blank" style="color:#58a6ff;font-size:12px">Otworz post &rarr;</a></td>'
    f'<td style="color:#8b949e;font-size:11px">{(l["found_at"] or "")[:10]}</td>'
    f'</tr>'
    for l in leads
  ) + '</table>' if leads else '<div class="empty-state"><div class="empty-title">Brak realnych leadow</div>Uruchom skaner zeby znalezc zlecenia z grup Facebook:<br><br><code>python ai_consulting.py --scan</code></div>'}
</div>

<div class="section">
  <h2>Historia stanu systemu</h2>
  <p class="section-desc">Ostatnie 10 automatycznych pomiarow &mdash; mozesz sledzic czy system sie poprawia</p>
  <table>
    <tr><th>#</th><th>Data i godzina</th><th>Testy zdane</th><th>Jakosc kodu</th><th>Zmiany w plikach</th></tr>
    {''.join(
        f'<tr><td style="color:#8b949e">{i+1}</td><td>{s["timestamp"][:16].replace("T"," ")}</td>'
        f'<td><span class="badge badge-{"green" if s["tests"]["pass_rate"]>=0.9 else "yellow"}">'
        f'{s["tests"]["pass_rate"]*100:.1f}%</span></td>'
        f'<td>{s["pylint"]["average"]:.2f}/10</td>'
        f'<td>{s["drift"]["drift_ratio"]*100:.1f}%</td></tr>'
        for i, s in enumerate(history_data[-10:])
    ) if history_data else '<tr><td colspan="5" style="color:#484f58;padding:20px">Brak danych. Uruchom: python self_improvement.py --run</td></tr>'}
  </table>
</div>

<div class="section">
  <h2>Dostepne komendy systemowe</h2>
  <p class="section-desc">Endpointy API &mdash; mozna wywolac recznie lub przez automatyzacje</p>
  <table>
    <tr><th>Metoda</th><th>Adres</th><th>Co robi</th></tr>
    <tr><td><span class="badge badge-green">GET</span></td><td>/health</td><td>Sprawdza czy serwer dziala</td></tr>
    <tr><td><span class="badge badge-green">GET</span></td><td>/metrics</td><td>Aktualny stan systemu (testy, pylint, drift)</td></tr>
    <tr><td><span class="badge badge-green">GET</span></td><td>/metrics/history</td><td>Historia ostatnich 30 pomiarow</td></tr>
    <tr><td><span class="badge badge-green">GET</span></td><td>/drift</td><td>Raport zmian w plikach systemu</td></tr>
    <tr><td><span class="badge badge-green">GET</span></td><td>/alerts</td><td>Lista aktywnych alertow</td></tr>
    <tr><td><span class="badge badge-green">GET</span></td><td>/monetization</td><td>Status monetyzacji: Useme, OLX, monitor, zarobki (JSON)</td></tr>
    <tr><td><span class="badge badge-yellow">POST</span></td><td>/run</td><td>Uruchamia zadanie: drift_check / self_improvement / auto_fix</td></tr>
    <tr><td><span class="badge badge-green">GET</span></td><td>/docs</td><td>Interaktywna dokumentacja API (Swagger)</td></tr>
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


@app.get("/leads", response_class=HTMLResponse)
def get_all_leads() -> str:
    """Strona ze wszystkimi leadami."""
    db_path = PROJECT_DIR / "fb_data" / "consulting.db"
    leads = []
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        leads = [dict(r) for r in conn.execute(
            "SELECT id, need_type, est_budget, status, author, source_url, post_text, found_at, complexity "
            "FROM consulting_leads WHERE status != 'demo' AND (source_url LIKE '%/posts/%' OR source_url LIKE '%useme.com/pl/jobs/%,%') ORDER BY est_budget DESC"
        ).fetchall()]
        conn.close()
    rows_html = "".join(
        f'<tr>'
        f'<td class="green" style="font-weight:bold;white-space:nowrap">{int(l["est_budget"])} PLN</td>'
        f'<td>{l["need_type"].replace("_"," ").replace("|",", ").title()}</td>'
        f'<td>{l["complexity"] or "&mdash;"}</td>'
        f'<td>{l["author"] or "&mdash;"}</td>'
        f'<td style="max-width:300px;font-size:12px;color:#8b949e">{(l["post_text"] or "")[:120]}...</td>'
        f'<td><a href="{l["source_url"]}" target="_blank" style="color:#58a6ff;white-space:nowrap">Otworz &rarr;</a></td>'
        f'<td style="color:#8b949e;font-size:11px;white-space:nowrap">{(l["found_at"] or "")[:10]}</td>'
        f'</tr>'
        for l in leads
    ) if leads else '<tr><td colspan="7" style="color:#484f58;padding:20px;text-align:center">Brak leadow. Uruchom: python ai_consulting.py --scan</td></tr>'
    return f"""<!DOCTYPE html>
<html lang="pl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wszystkie leady - ClaudeAgent</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0d1117;color:#c9d1d9;margin:0;padding:24px}}
  h1{{color:#58a6ff;margin-bottom:4px}} .sub{{color:#8b949e;font-size:13px;margin-bottom:20px}}
  a.back{{color:#8b949e;font-size:13px;text-decoration:none}} a.back:hover{{color:#58a6ff}}
  table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:16px}}
  th{{text-align:left;padding:8px 12px;color:#8b949e;border-bottom:1px solid #21262d;font-size:12px}}
  td{{padding:8px 12px;border-bottom:1px solid #1c2128;vertical-align:top}}
  tr:hover td{{background:#1c2128}}
  .green{{color:#3fb950}} .info{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:13px}}
  .dl{{display:inline-block;background:#21262d;border:1px solid #30363d;border-radius:6px;padding:6px 14px;font-size:12px;color:#58a6ff;text-decoration:none;margin-left:12px}}
</style></head><body>
<a href="/" class="back">&larr; Powrot do panelu</a>
<h1 style="margin-top:12px">Wszystkie leady z FB <a href="/leads/export" class="dl">Pobierz CSV</a></h1>
<p class="sub">Lacznie: {len(leads)} zlecen | posortowane po budzecie</p>
<div class="info">Kliknij "Otworz" zeby zobaczyc oryginalny post na Facebooku. Leady znalezione automatycznie przez AI z polskich grup zlecen IT.</div>
<table>
  <tr><th>Budzet</th><th>Rodzaj</th><th>Zlozonosc</th><th>Autor</th><th>Fragment posta</th><th>Link</th><th>Data</th></tr>
  {rows_html}
</table>
</body></html>"""


@app.get("/leads/export")
def export_leads_csv():
    """Pobierz wszystkie leady jako CSV."""
    import csv
    import io

    from fastapi.responses import StreamingResponse
    db_path = PROJECT_DIR / "fb_data" / "consulting.db"
    leads = []
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        leads = [dict(r) for r in conn.execute(
            "SELECT id, need_type, est_budget, status, author, source_url, post_text, found_at, complexity "
            "FROM consulting_leads WHERE status != 'demo' AND (source_url LIKE '%/posts/%' OR source_url LIKE '%useme.com/pl/jobs/%,%') ORDER BY est_budget DESC"
        ).fetchall()]
        conn.close()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id","need_type","est_budget","status","author","source_url","post_text","found_at","complexity"])
    writer.writeheader()
    writer.writerows(leads)
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leady_fb.csv"})


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


@app.get("/monetization")
def get_monetization() -> Dict[str, Any]:
    """Status monetyzacji — Useme, OLX, monitor, zarobki."""
    return _load_monetization()


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
