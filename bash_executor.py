#!/usr/bin/env python3
import subprocess
import sys
import json

def execute_commands(commands):
    """Execute multiple bash commands, return results"""
    results = {}
    for i, cmd in enumerate(commands):
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            results[f"cmd_{i}"] = {
                "command": cmd,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            results[f"cmd_{i}"] = {
                "command": cmd,
                "error": str(e)
            }
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bash_executor.py 'cmd1' 'cmd2' ...")
        sys.exit(1)

    commands = sys.argv[1:]
    results = execute_commands(commands)
    print(json.dumps(results, indent=2))
