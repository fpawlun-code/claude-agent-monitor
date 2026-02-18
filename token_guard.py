import subprocess
import re
import sys
import json
import os
from datetime import datetime
from colorama import Fore, Style, init

# Initialize Colorama for cross-platform ANSI color support
init(autoreset=True)

# Configuration file path (in same directory as this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'token_guard_config.json')

# Load configuration rules
with open(CONFIG_FILE) as f:
    VIOLATIONS = json.load(f)['VIOLATIONS']

# Token tracking variables
TOKEN_LIMIT_WARNING = 500
TOKEN_LIMIT_HARD = 1000
current_tokens = 0

def delegate_read():
    print(Fore.RED + "WARNING: Use delegate_read() instead of Read()" + Style.RESET_ALL)

def delegate_bash():
    print(Fore.YELLOW + "INFO: Should use delegate_bash() for long output" + Style.RESET_ALL)

def monitor_output(process):
    global current_tokens
    for line in iter(process.stdout.readline, b''):
        try:
            decoded_line = line.decode('utf-8').strip()
            if decoded_line:
                print(decoded_line)

            # Check for violations
            for pattern, message in VIOLATIONS.items():
                if re.search(pattern, decoded_line):
                    print(Fore.RED + f"VIOLATION: {message}" + Style.RESET_ALL)
                    if "Read(" in decoded_line:
                        delegate_read()
                    elif "Bash(" in decoded_line:
                        delegate_bash()

            # Track tokens
            if 'tokens=' in decoded_line and 'total' not in decoded_line:
                current_tokens += int(decoded_line.split(' ')[-1])
                print(Fore.GREEN + f"Current Tokens: {current_tokens}" + Style.RESET_ALL)
                if current_tokens >= TOKEN_LIMIT_WARNING:
                    print(Fore.YELLOW + "WARNING: Token usage is close to the warning limit." + Style.RESET_ALL)
                if current_tokens >= TOKEN_LIMIT_HARD:
                    print(Fore.RED + "ERROR: Token usage exceeded the hard limit. Stopping process." + Style.RESET_ALL)
                    process.terminate()
                    break

        except UnicodeDecodeError:
            continue

    # Final token count at end of session
    print(Fore.GREEN + f"Final Tokens: {current_tokens}" + Style.RESET_ALL)

def main():
    if len(sys.argv) < 2:
        print("Usage: python token_guard.py [args]")
        sys.exit(1)

    args = sys.argv[1:]
    process = subprocess.Popen(['claude'] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    try:
        monitor_output(process)
    except KeyboardInterrupt:
        print(Fore.RED + "Process interrupted. Terminating." + Style.RESET_ALL)
        process.terminate()
    finally:
        # Log session details
        log_file_path = os.path.join(SCRIPT_DIR, 'token_guard.log')
        with open(log_file_path, 'a') as log_file:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_file.write(f"Session started at {now}\n")
            for pattern, message in VIOLATIONS.items():
                log_file.write(f"Violation Pattern: {pattern} -> {message}\n")
            log_file.write(f"Total Tokens Used: {current_tokens}\n")
            log_file.write("Session ended.\n")

if __name__ == "__main__":
    main()
