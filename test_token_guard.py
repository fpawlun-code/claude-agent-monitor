"""Test Token Guard wrapper with mock Claude"""
import subprocess
import sys
import os

# Modify token_guard.py temporarily to use mock_claude.py
test_wrapper = """import subprocess
import re
import sys
import json
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

CONFIG_FILE = 'token_guard_config.json'

with open(CONFIG_FILE) as f:
    VIOLATIONS = json.load(f)['VIOLATIONS']

TOKEN_LIMIT_WARNING = 500
TOKEN_LIMIT_HARD = 1000
current_tokens = 0

def delegate_read():
    print(Fore.RED + ">>> WARNING: Use delegate_read() instead of Read()" + Style.RESET_ALL)

def delegate_bash():
    print(Fore.YELLOW + ">>> INFO: Should use delegate_bash() for long output" + Style.RESET_ALL)

def monitor_output(process):
    global current_tokens
    for line in iter(process.stdout.readline, b''):
        try:
            decoded_line = line.decode('utf-8').strip()
            if decoded_line:
                print(decoded_line)

            for pattern, message in VIOLATIONS.items():
                if re.search(pattern, decoded_line):
                    print(Fore.RED + f">>> VIOLATION DETECTED: {message}" + Style.RESET_ALL)
                    if "Read(" in decoded_line:
                        delegate_read()
                    elif "Bash(" in decoded_line:
                        delegate_bash()

            if 'tokens=' in decoded_line:
                tokens = int(decoded_line.split('=')[1])
                current_tokens += tokens
                print(Fore.GREEN + f">>> Token Count: {current_tokens}/{TOKEN_LIMIT_HARD}" + Style.RESET_ALL)
                if current_tokens >= TOKEN_LIMIT_WARNING and current_tokens < TOKEN_LIMIT_HARD:
                    print(Fore.YELLOW + ">>> WARNING: Approaching token limit!" + Style.RESET_ALL)
                if current_tokens >= TOKEN_LIMIT_HARD:
                    print(Fore.RED + ">>> ERROR: Token limit exceeded! Stopping." + Style.RESET_ALL)
                    process.terminate()
                    break

        except (UnicodeDecodeError, ValueError):
            continue

    print(Fore.GREEN + f"\\n>>> SESSION COMPLETE: {current_tokens} total tokens" + Style.RESET_ALL)

def main():
    # Use mock_claude.py for testing
    process = subprocess.Popen(['python', 'mock_claude.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    try:
        monitor_output(process)
    except KeyboardInterrupt:
        print(Fore.RED + ">>> Process interrupted." + Style.RESET_ALL)
        process.terminate()
    finally:
        with open('token_guard.log', 'a') as log_file:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_file.write(f"\\nTEST SESSION: {now}\\n")
            log_file.write(f"Total Tokens: {current_tokens}\\n")

if __name__ == "__main__":
    main()
"""

with open('token_guard_test_temp.py', 'w') as f:
    f.write(test_wrapper)

print("Running Token Guard Test...")
print("=" * 60)
subprocess.run(['python', 'token_guard_test_temp.py'])
print("=" * 60)
print("\nTest complete! Check output above for violations detected.")
