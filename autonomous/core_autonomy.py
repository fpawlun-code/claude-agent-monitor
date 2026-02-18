import os
import sys
import time
import json
import re
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_gateway import delegate_to_rtx

PROGRESS_FILE = "autonomous/progress.json"
STOP_FILE = "autonomous/STOP"
LOG_FILE = "autonomous/rtx_log.txt"
FIXES_LOG = "autonomous/fixes.log"

def check_logs_for_errors():
    """Scan logs for errors and return list of error info"""
    log_files = [
        "ai_gateway.log",
        "autonomous/rtx_log.txt"
    ]

    errors = []
    error_patterns = [
        r'Traceback \(most recent call last\):',
        r'\[ERROR\]',
        r'\[CRITICAL\]',
        r'Exception:',
        r'Error:',
        r'failed',
        r'crash'
    ]

    for log_file in log_files:
        if not os.path.exists(log_file):
            continue

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            for i, line in enumerate(lines[-100:]):  # Check last 100 lines only
                for pattern in error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Get context (3 lines before and after)
                        context_start = max(0, i-3)
                        context_end = min(len(lines), i+4)
                        context = ''.join(lines[context_start:context_end])

                        errors.append({
                            'file': log_file,
                            'line': i + 1,
                            'error_text': line.strip(),
                            'context': context,
                            'timestamp': datetime.now().isoformat()
                        })
                        break
        except Exception as e:
            print(f"Error reading {log_file}: {e}")

    return errors

def auto_fix_error(error_info):
    """Use RTX to analyze error and propose fix"""
    try:
        prompt = f"""Analyze this error and propose a fix:

File: {error_info['file']}
Error: {error_info['error_text']}

Context:
{error_info['context']}

Provide:
1. Root cause analysis
2. Proposed fix (code or config change)
3. Confidence score (0.0-1.0)

Format: JSON with keys: analysis, fix, confidence
"""

        response = delegate_to_rtx(prompt, role='debugging expert', temperature=0.2)

        # Try to parse JSON response
        try:
            fix_info = json.loads(response)
        except:
            # If not JSON, create structured response
            fix_info = {
                'analysis': response[:200],
                'fix': response,
                'confidence': 0.6
            }

        return fix_info

    except Exception as e:
        print(f"Error in auto_fix_error: {e}")
        return {'analysis': str(e), 'fix': '', 'confidence': 0.0}

def log_fix(error_info, fix_info, applied=False):
    """Log fix attempt to fixes.log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"""
{'='*60}
[{timestamp}] Fix {'Applied' if applied else 'Proposed'}
Error: {error_info['error_text']}
File: {error_info['file']}
Analysis: {fix_info.get('analysis', 'N/A')}
Fix: {fix_info.get('fix', 'N/A')}
Confidence: {fix_info.get('confidence', 0.0)}
{'='*60}
"""

    with open(FIXES_LOG, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def main():
    print("RTX Autonomous Mission Started (v2 - Error Detection)")
    iteration_count = 0

    # Load previous progress if exists
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            prev_progress = json.load(f)
            iteration_count = prev_progress.get("iterations", 0)

    while True:
        # Check stop signal
        if os.path.exists(STOP_FILE):
            print("STOP file detected. Shutting down.")
            break

        # Increment iteration
        iteration_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Log current iteration
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] Loop iteration {iteration_count}\n")

        # ERROR DETECTION (NEW!)
        print(f"[{timestamp}] Checking for errors...")
        errors = check_logs_for_errors()

        if errors:
            print(f"Found {len(errors)} error(s)")
            for error in errors[:3]:  # Process max 3 errors per iteration
                print(f"  - {error['error_text'][:80]}")

                # Auto-fix
                fix_info = auto_fix_error(error)

                # Log the fix
                if fix_info.get('confidence', 0) > 0.7:
                    log_fix(error, fix_info, applied=True)
                    print(f"  ✓ High confidence fix logged ({fix_info['confidence']})")
                else:
                    log_fix(error, fix_info, applied=False)
                    print(f"  ⚠ Low confidence, logged for review")

        # Update progress
        progress = {
            "last_run": timestamp,
            "status": "running",
            "iterations": iteration_count,
            "errors_found": len(errors),
            "errors_fixed": sum(1 for e in errors if e.get('fixed', False))
        }

        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)

        print(f"[{timestamp}] Iteration {iteration_count} complete")

        # Sleep 30 minutes
        time.sleep(1800)

if __name__ == "__main__":
    main()
