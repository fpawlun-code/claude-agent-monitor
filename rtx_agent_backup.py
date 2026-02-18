#!/usr/bin/env python3
"""
RTX Agent - Autonomous ReAct (Reasoning + Acting) Agent
Uses local Llama 3 on RTX GPU with file, shell, and web tools.

WORKFLOW:
1. Receive task from Claude (or CLI)
2. Model reasons about task (Thought)
3. Model chooses action (Action: tool_name(args))
4. Execute tool and return observation (Observation)
5. Repeat until Final Answer

INTEGRATION:
Claude → JSON task → rtx_agent.py → autonomous execution → result
"""

import os
import json
import argparse
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import re

# ==================== TOOLKIT ====================

class LocalToolkit:
    """Tools available to RTX Agent for autonomous execution"""

    def __init__(self, safe_mode: bool = True):
        """
        Args:
            safe_mode: If True, blocks dangerous shell commands
        """
        self.safe_mode = safe_mode
        self.tools = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_dir": self.list_dir,
            "execute_shell": self.execute_shell,
            "web_search": self.web_search,
        }

        self.log_file = Path("C:\\ClaudeAgent\\rtx_agent.log")

    def log(self, message: str):
        """Write to log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        print(log_line.strip())

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def read_file(self, file_path: str) -> str:
        """Read file contents"""
        try:
            path = Path(file_path).resolve()

            if not path.exists():
                return f"ERROR: File not found: {path}"

            if not path.is_file():
                return f"ERROR: Not a file: {path}"

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            self.log(f"[OK] Read {len(content)} chars from {path}")
            return content

        except Exception as e:
            return f"ERROR: {str(e)}"

    def write_file(self, file_path: str, content: str) -> str:
        """Write content to file"""
        try:
            path = Path(file_path).resolve()

            # Create parent dirs if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            self.log(f"[OK] Wrote {len(content)} chars to {path}")
            return f"SUCCESS: Wrote {len(content)} chars to {path}"

        except Exception as e:
            return f"ERROR: {str(e)}"

    def list_dir(self, dir_path: str = ".") -> str:
        """List directory contents"""
        try:
            path = Path(dir_path).resolve()

            if not path.exists():
                return f"ERROR: Directory not found: {path}"

            if not path.is_dir():
                return f"ERROR: Not a directory: {path}"

            items = []
            for item in sorted(path.iterdir()):
                size = item.stat().st_size if item.is_file() else 0
                item_type = "DIR" if item.is_dir() else "FILE"
                items.append(f"{item_type:4} {size:>10} {item.name}")

            result = f"Directory: {path}\n" + "\n".join(items)
            self.log(f"[OK] Listed {len(items)} items in {path}")
            return result

        except Exception as e:
            return f"ERROR: {str(e)}"

    def execute_shell(self, command: str) -> str:
        """Execute shell command (with safety checks)"""

        # Safety: block dangerous commands
        if self.safe_mode:
            dangerous_patterns = [
                r"rm\s+-rf",
                r"del\s+/s",
                r"format\s+",
                r"shutdown",
                r"reboot",
                r">.*nul",  # Windows delete
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return f"BLOCKED: Dangerous command detected: {command}"

        try:
            self.log(f"[EXEC] Executing: {command}")

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path.cwd()
            )

            output = result.stdout + result.stderr

            if result.returncode != 0:
                self.log(f"[WARN] Command failed (code {result.returncode})")
                return f"EXIT CODE {result.returncode}\n{output}"

            self.log(f"[OK] Command success")
            return output.strip() if output else "SUCCESS (no output)"

        except subprocess.TimeoutExpired:
            return "ERROR: Command timeout (>30s)"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def web_search(self, query: str) -> str:
        """Simple DuckDuckGo search (text-only)"""
        try:
            # Using DuckDuckGo Instant Answer API
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            }

            self.log(f"[SEARCH] Searching: {query}")

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            # Extract relevant info
            abstract = data.get("AbstractText", "")
            related = data.get("RelatedTopics", [])

            results = []

            if abstract:
                results.append(f"SUMMARY: {abstract}")

            for item in related[:3]:
                if isinstance(item, dict) and "Text" in item:
                    results.append(f"- {item['Text']}")

            if not results:
                return "No results found"

            return "\n".join(results)

        except Exception as e:
            return f"ERROR: {str(e)}"

    def get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for model"""
        return """Available Tools:

1. read_file(file_path: str) -> str
   Read contents of a file

2. write_file(file_path: str, content: str) -> str
   Write content to a file

3. list_dir(dir_path: str = ".") -> str
   List directory contents

4. execute_shell(command: str) -> str
   Execute shell command (safe mode enabled)

5. web_search(query: str) -> str
   Search the web using DuckDuckGo

USAGE FORMAT:
Action: tool_name(arg1="value1", arg2="value2")
"""

# ==================== REACT AGENT ====================

class ReactAgent:
    """ReAct (Reasoning + Acting) Agent using Ollama"""

    def __init__(
        self,
        model: str = "llama3:8b",
        base_url: str = "http://localhost:11434",
        max_iterations: int = 10,
        safe_mode: bool = True
    ):
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        self.max_iterations = max_iterations

        self.toolkit = LocalToolkit(safe_mode=safe_mode)
        self.conversation_history = []

        self.log_file = Path("C:\\ClaudeAgent\\rtx_agent.log")

    def log(self, message: str):
        """Write to log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        print(log_line.strip())

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def parse_action(self, text: str) -> Optional[tuple[str, Dict[str, Any]]]:
        """Parse action from model output"""
        # Look for pattern: Action: tool_name(arg1="val1", arg2="val2")
        action_pattern = r"Action:\s*(\w+)\((.*?)\)"
        match = re.search(action_pattern, text, re.IGNORECASE)

        if not match:
            return None

        tool_name = match.group(1)
        args_str = match.group(2)

        # Parse arguments
        kwargs = {}

        # Simple parser for arg="value" pairs
        arg_pattern = r'(\w+)\s*=\s*"([^"]*)"'
        for arg_match in re.finditer(arg_pattern, args_str):
            key = arg_match.group(1)
            value = arg_match.group(2)
            kwargs[key] = value

        return (tool_name, kwargs)

    def execute_action(self, tool_name: str, kwargs: Dict[str, Any]) -> str:
        """Execute tool with given arguments"""
        if tool_name not in self.toolkit.tools:
            return f"ERROR: Unknown tool '{tool_name}'"

        try:
            tool = self.toolkit.tools[tool_name]
            result = tool(**kwargs)
            return result
        except Exception as e:
            return f"ERROR: {str(e)}"

    def ask_model(self, prompt: str) -> str:
        """Ask Ollama model"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 1000
                }
            }

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=120
            )

            if response.status_code != 200:
                return f"ERROR: API returned {response.status_code}"

            result = response.json()
            return result.get("response", "")

        except Exception as e:
            return f"ERROR: {str(e)}"

    def run(self, task: str) -> Dict[str, Any]:
        """
        Run ReAct loop to complete task

        Returns:
            {
                "success": bool,
                "final_answer": str,
                "iterations": int,
                "conversation": list
            }
        """
        self.log(f"[START] Starting task: {task}")

        # Initialize conversation
        system_prompt = f"""You are an autonomous AI agent with access to tools.

{self.toolkit.get_tool_descriptions()}

REACT PROTOCOL:
For each step, output:
1. Thought: [Your reasoning about what to do next]
2. Action: tool_name(arg="value")
   OR
   Final Answer: [Your complete answer when task is done]

RULES:
- Think step by step
- Use tools to gather information
- Keep thoughts concise
- When you have the answer, output "Final Answer: ..."

TASK: {task}
"""

        self.conversation_history.append({
            "role": "system",
            "content": system_prompt
        })

        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            self.log(f"[ITER] Iteration {iteration}/{self.max_iterations}")

            # Build conversation prompt
            conv_text = "\n\n".join([
                msg["content"] for msg in self.conversation_history
            ])

            # Ask model
            response = self.ask_model(conv_text)

            if "ERROR:" in response:
                return {
                    "success": False,
                    "final_answer": response,
                    "iterations": iteration,
                    "conversation": self.conversation_history
                }

            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })

            self.log(f"[MODEL] Model: {response[:200]}...")

            # Check for Final Answer
            if "final answer:" in response.lower():
                # Extract final answer
                match = re.search(r"final answer:\s*(.*)", response, re.IGNORECASE | re.DOTALL)
                if match:
                    final_answer = match.group(1).strip()
                    self.log(f"[DONE] Task complete in {iteration} iterations")

                    return {
                        "success": True,
                        "final_answer": final_answer,
                        "iterations": iteration,
                        "conversation": self.conversation_history
                    }

            # Parse and execute action
            action = self.parse_action(response)

            if action:
                tool_name, kwargs = action
                self.log(f"[TOOL] Executing: {tool_name}({kwargs})")

                observation = self.execute_action(tool_name, kwargs)

                self.conversation_history.append({
                    "role": "user",
                    "content": f"Observation: {observation}"
                })

                self.log(f"[OBS] Observation: {observation[:200]}...")
            else:
                # No action found, prompt model to continue
                self.conversation_history.append({
                    "role": "user",
                    "content": "Continue with next thought and action, or provide Final Answer."
                })

        # Max iterations reached
        self.log(f"[WARN] Max iterations ({self.max_iterations}) reached")

        return {
            "success": False,
            "final_answer": "ERROR: Max iterations reached without Final Answer",
            "iterations": iteration,
            "conversation": self.conversation_history
        }

# ==================== CLI INTERFACE ====================

def main():
    parser = argparse.ArgumentParser(
        description="RTX Agent - Autonomous ReAct agent with tools"
    )
    parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="Task description for agent"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="llama3:8b",
        help="Ollama model to use (default: llama3:8b)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Max ReAct iterations (default: 10)"
    )
    parser.add_argument(
        "--unsafe",
        action="store_true",
        help="Disable shell command safety checks"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save result to file"
    )

    args = parser.parse_args()

    print("="*60)
    print("RTX AGENT - AUTONOMOUS EXECUTION")
    print("="*60)

    # Create agent
    agent = ReactAgent(
        model=args.model,
        max_iterations=args.max_iterations,
        safe_mode=not args.unsafe
    )

    # Run task
    result = agent.run(args.task)

    print("\n" + "="*60)
    if result["success"]:
        print("[SUCCESS] TASK COMPLETE")
        print("="*60)
        print(f"\n{result['final_answer']}\n")
        print(f"[STATS] Iterations: {result['iterations']}")
    else:
        print("[FAILED] TASK FAILED")
        print("="*60)
        print(f"\n{result['final_answer']}\n")

    # Save output if requested
    if args.output:
        output_path = Path(args.output)

        output_data = {
            "task": args.task,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

        print(f"[SAVED] Saved to: {output_path}")

    print("="*60)

    return 0 if result["success"] else 1

if __name__ == "__main__":
    exit(main())
