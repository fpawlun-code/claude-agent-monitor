"""
Alerting System - PHASE 4A Week 3 (Day 18-19)
Configurable rules + notification channels (log, file, console).
Extensible: add email/Discord/Slack when needed.
"""

import json
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ALERTS_FILE = Path("C:/ClaudeAgent/reports/active_alerts.json")
ALERT_LOG = Path("C:/ClaudeAgent/reports/alert_history.log")
CONFIG_FILE = Path("C:/ClaudeAgent/alerting_config.json")

DEFAULT_CONFIG = {
    "channels": ["log", "file"],  # "log", "file", "email", "discord"
    "email": {
        "enabled": False,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "sender": "",
        "recipient": "",
        "password": "",
    },
    "discord": {
        "enabled": False,
        "webhook_url": "",
    },
    "rules": {
        "test_fail_threshold": 2,        # alert if >N tests failing
        "pass_rate_min": 0.80,           # alert if pass rate drops below
        "pylint_min": 7.5,              # alert if pylint drops below
        "drift_alert": True,            # alert on any drift
        "regression_threshold": 0.05,   # alert if metrics drop by this %
    },
    "cooldown_minutes": 60,  # don't re-alert same rule within N minutes
}

AlertHandler = Callable[[str, str, str], None]


def load_config() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        return {**DEFAULT_CONFIG, **json.loads(CONFIG_FILE.read_text())}
    return DEFAULT_CONFIG


def save_config(config: Dict[str, Any]) -> None:
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def load_active_alerts() -> Dict[str, Any]:
    if ALERTS_FILE.exists():
        return json.loads(ALERTS_FILE.read_text())
    return {}


def save_active_alerts(alerts: Dict[str, Any]) -> None:
    ALERTS_FILE.parent.mkdir(exist_ok=True)
    ALERTS_FILE.write_text(json.dumps(alerts, indent=2))


def _log_alert(rule: str, severity: str, message: str) -> None:
    ALERT_LOG.parent.mkdir(exist_ok=True)
    ts = datetime.now().isoformat()
    line = f"[{ts}] [{severity}] [{rule}] {message}\n"
    with open(ALERT_LOG, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"ALERT [{severity}] {rule}: {message}")


def _file_alert(rule: str, severity: str, message: str) -> None:
    alerts = load_active_alerts()
    alerts[rule] = {
        "severity": severity,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "resolved": False,
    }
    save_active_alerts(alerts)


def _email_alert(rule: str, severity: str, message: str, config: Dict[str, Any]) -> None:
    email_cfg = config.get("email", {})
    if not email_cfg.get("enabled"):
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = f"[ClaudeAgent {severity}] {rule}"
        msg["From"] = email_cfg["sender"]
        msg["To"] = email_cfg["recipient"]
        msg.set_content(f"Alert: {message}\n\nTimestamp: {datetime.now().isoformat()}")
        with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"]) as smtp:
            smtp.starttls()
            smtp.login(email_cfg["sender"], email_cfg["password"])
            smtp.send_message(msg)
        print(f"[EMAIL] Alert sent to {email_cfg['recipient']}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


def _discord_alert(rule: str, severity: str, message: str, config: Dict[str, Any]) -> None:
    discord_cfg = config.get("discord", {})
    if not discord_cfg.get("enabled") or not discord_cfg.get("webhook_url"):
        return
    try:
        import urllib.request
        payload = json.dumps({
            "content": f"**[{severity}] {rule}**\n{message}\n`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
        }).encode()
        req = urllib.request.Request(
            discord_cfg["webhook_url"],
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
        print("[DISCORD] Alert sent")
    except Exception as e:
        print(f"[DISCORD ERROR] {e}")


class AlertEngine:
    """Core alerting engine."""

    def __init__(self) -> None:
        self.config = load_config()
        self._last_fired: Dict[str, datetime] = {}

    def _is_cooled_down(self, rule: str) -> bool:
        """Return True if rule is ready to fire (not in cooldown)."""
        from datetime import timedelta
        if rule not in self._last_fired:
            return True
        cooldown = self.config.get("cooldown_minutes", 60)
        elapsed = datetime.now() - self._last_fired[rule]
        return elapsed.total_seconds() >= cooldown * 60

    def fire(self, rule: str, severity: str, message: str) -> bool:
        """Fire an alert. Returns True if sent (not in cooldown)."""
        if not self._is_cooled_down(rule):
            return False

        self._last_fired[rule] = datetime.now()
        channels = self.config.get("channels", ["log"])

        if "log" in channels:
            _log_alert(rule, severity, message)
        if "file" in channels:
            _file_alert(rule, severity, message)
        if "email" in channels:
            _email_alert(rule, severity, message, self.config)
        if "discord" in channels:
            _discord_alert(rule, severity, message, self.config)

        return True

    def resolve(self, rule: str) -> None:
        """Mark an alert as resolved."""
        alerts = load_active_alerts()
        if rule in alerts:
            alerts[rule]["resolved"] = True
            alerts[rule]["resolved_at"] = datetime.now().isoformat()
            save_active_alerts(alerts)
            print(f"[RESOLVED] {rule}")

    def check_metrics(self, metrics: Optional[Dict[str, Any]] = None) -> List[str]:
        """Check all rules against current metrics. Returns list of fired alerts."""
        fired = []
        rules = self.config.get("rules", {})

        if metrics is None:
            history_file = Path("C:/ClaudeAgent/reports/metrics_history.json")
            if not history_file.exists():
                print("[SKIP] No metrics history found. Run: python self_improvement.py --run")
                return fired
            history = json.loads(history_file.read_text())
            if not history:
                return fired
            metrics = history[-1]
            prev = history[-2] if len(history) >= 2 else None
        else:
            prev = None

        tests = metrics.get("tests", {})
        pylint = metrics.get("pylint", {})
        drift = metrics.get("drift", {})

        # Rule: test failures
        failed = tests.get("failed", 0)
        threshold = rules.get("test_fail_threshold", 2)
        if failed > threshold:
            if self.fire("test_failures", "CRITICAL", f"{failed} tests failing (threshold: {threshold})"):
                fired.append("test_failures")
        else:
            self.resolve("test_failures")

        # Rule: pass rate minimum
        rate = tests.get("pass_rate", 1.0)
        min_rate = rules.get("pass_rate_min", 0.80)
        if rate < min_rate:
            if self.fire("pass_rate_low", "WARNING", f"Pass rate {rate:.1%} below minimum {min_rate:.1%}"):
                fired.append("pass_rate_low")
        else:
            self.resolve("pass_rate_low")

        # Rule: pylint minimum
        pyl = pylint.get("average", 10.0)
        min_pyl = rules.get("pylint_min", 7.5)
        if pyl < min_pyl:
            if self.fire("pylint_low", "WARNING", f"Pylint score {pyl:.2f} below minimum {min_pyl:.1f}"):
                fired.append("pylint_low")
        else:
            self.resolve("pylint_low")

        # Rule: drift
        if rules.get("drift_alert") and drift.get("alert"):
            changed = drift.get("changed", [])
            if self.fire("drift_detected", "WARNING", f"Drift detected in: {', '.join(changed)}"):
                fired.append("drift_detected")

        # Rule: regression
        if prev:
            prev_rate = prev["tests"]["pass_rate"]
            reg_threshold = rules.get("regression_threshold", 0.05)
            if prev_rate - rate > reg_threshold:
                if self.fire("test_regression", "CRITICAL", f"Pass rate regression: {prev_rate:.1%} -> {rate:.1%}"):
                    fired.append("test_regression")

        return fired


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="ClaudeAgent Alerting System")
    parser.add_argument("--check", action="store_true", help="Check rules against latest metrics")
    parser.add_argument("--status", action="store_true", help="Show active (unresolved) alerts")
    parser.add_argument("--init", action="store_true", help="Create default config file")
    parser.add_argument("--test", action="store_true", help="Fire a test alert")
    args = parser.parse_args()

    engine = AlertEngine()

    if args.init:
        save_config(DEFAULT_CONFIG)
        print(f"Config created: {CONFIG_FILE}")

    elif args.check:
        print("[CHECK] Evaluating alert rules...")
        fired = engine.check_metrics()
        if fired:
            print(f"[FIRED] {len(fired)} alert(s): {', '.join(fired)}")
        else:
            print("[OK] No alerts triggered")

    elif args.status:
        alerts = load_active_alerts()
        active = {k: v for k, v in alerts.items() if not v.get("resolved")}
        if not active:
            print("[OK] No active alerts")
        else:
            print(f"Active alerts ({len(active)}):")
            for rule, info in active.items():
                print(f"  [{info['severity']}] {rule}: {info['message']}")
                print(f"    Since: {info['timestamp']}")

    elif args.test:
        engine.fire("test_alert", "INFO", "This is a test alert from alerting.py --test")
        print("[TEST] Alert fired. Check reports/alert_history.log")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
