#!/usr/bin/env python3
"""
Quick Delegate - Ultra-fast RTX delegation wrapper
Use this for simple one-off delegations from command line or scripts.
"""

import sys
from ai_gateway import delegate_to_rtx

def main():
    if len(sys.argv) < 2:
        print("Usage: python quick_delegate.py 'task description' [output_file]")
        print("\nExample:")
        print("  python quick_delegate.py 'Create HTML contact form' contact.html")
        sys.exit(1)

    task = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"🔄 Delegating to RTX: {task[:80]}...")

    result = delegate_to_rtx(
        task_description=task,
        role="expert developer",
        temperature=0.5,
        save_as=output_file
    )

    if output_file:
        print(f"\n✅ Task complete. Output: C:\\ClaudeAgent\\outputs\\{output_file}")
    else:
        print(f"\n✅ Task complete. Output:\n\n{result}")

if __name__ == "__main__":
    main()
