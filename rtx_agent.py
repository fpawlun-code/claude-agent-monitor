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

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests

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
            "browser_screenshot": self.browser_screenshot,
            "install_dependency": self.install_dependency,
            "api_call": self.api_call,
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
                r":\(\)\{",  # Fork bomb
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return f"BLOCKED: Dangerous command detected: {command}"

        try:
            self.log(f"[EXEC] Executing: {command}")

            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, cwd=Path.cwd())

            output = result.stdout + result.stderr

            if result.returncode != 0:
                self.log(f"[WARN] Command failed (code {result.returncode})")
                return f"EXIT CODE {result.returncode}\n{output}"

            self.log("[OK] Command success")
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
            params: Dict[str, Any] = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}

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

    def browser_screenshot(self, url: str, save_path: str) -> str:
        """Capture screenshot of webpage using Playwright"""
        try:
            from playwright.sync_api import sync_playwright

            self.log(f"[BROWSER] Screenshotting: {url}")

            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context()
                page = context.new_page()
                page.goto(url, timeout=30000)
                page.screenshot(path=save_path)
                browser.close()

            self.log(f"[OK] Screenshot saved to {save_path}")
            return f"SUCCESS: Screenshot saved to {save_path}"

        except Exception as e:
            return f"ERROR: {str(e)}"

    def install_dependency(self, package_name: str) -> str:
        """Install Python package via pip"""
        try:
            import subprocess

            self.log(f"[INSTALL] Installing {package_name}")

            result = subprocess.run(["pip", "install", package_name], capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                self.log(f"[OK] Installed {package_name}")
                return f"SUCCESS: Installed {package_name}"
            else:
                return f"ERROR: {result.stderr}"

        except Exception as e:
            return f"ERROR: {str(e)}"

    def api_call(self, url: str, method: str = "GET", data: str = None) -> str:
        """Make HTTP API call"""
        try:
            self.log(f"[API] {method} {url}")

            if method.upper() == "POST":
                import json

                response = requests.post(url, json=json.loads(data) if data else None)
            else:
                response = requests.get(url)

            self.log(f"[OK] API call success ({response.status_code})")
            return response.text[:2000]  # Limit response size

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

6. browser_screenshot(url: str, save_path: str) -> str
   Capture screenshot of webpage

7. install_dependency(package_name: str) -> str
   Install Python package via pip

8. api_call(url: str, method: str = "GET", data: str = None) -> str
   Make HTTP API call

USAGE FORMAT:
Action: tool_name(arg1="value1", arg2="value2")
"""


# ==================== REACT AGENT ====================


class ReactAgent:
    """ReAct (Reasoning + Acting) Agent using Ollama"""

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        max_iterations: int = 10,
        safe_mode: bool = True,
    ):
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        self.max_iterations = max_iterations

        self.toolkit = LocalToolkit(safe_mode=safe_mode)
        self.conversation_history: list[Dict[str, Any]] = []

        # Initialize persistent memory (Qdrant + embeddings)
        from memory_system import QdrantMemory

        self.memory = QdrantMemory()

        self.log_file = Path("C:\\ClaudeAgent\\rtx_agent.log")

    def log(self, message: str):
        """Write to log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        print(log_line.strip())

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def parse_action(self, text: str) -> Optional[tuple[str, Dict[str, Any]]]:
        """Parse action from model output - flexible parser"""
        # Primary pattern: Action: tool_name(arg1="val1", arg2="val2")
        action_pattern = r"Action:\s*(\w+)\((.*?)\)"
        match = re.search(action_pattern, text, re.IGNORECASE)

        if not match:
            return None

        tool_name = match.group(1)
        args_str = match.group(2).strip()

        kwargs: Dict[str, Any] = {}

        if not args_str:
            # No arguments
            return (tool_name, kwargs)

        # Try parsing arg="value" pairs
        arg_pattern = r'(\w+)\s*=\s*"([^"]*)"'
        matches = list(re.finditer(arg_pattern, args_str))

        if matches:
            for arg_match in matches:
                key = arg_match.group(1)
                value = arg_match.group(2)
                kwargs[key] = value
        else:
            # Fallback: single positional arg without name
            # Action: tool_name("value") → assume first param
            simple_pattern = r'"([^"]*)"'
            simple_match = re.search(simple_pattern, args_str)
            if simple_match and tool_name in self.toolkit.tools:
                # Try to infer param name from tool signature
                value = simple_match.group(1)
                if tool_name == "execute_shell":
                    kwargs["command"] = value
                elif tool_name in ["read_file", "write_file"]:
                    kwargs["file_path"] = value
                elif tool_name == "web_search":
                    kwargs["query"] = value

        return (tool_name, kwargs)

    def execute_action(self, tool_name: str, kwargs: Dict[str, Any]) -> str:
        """Execute tool with given arguments"""
        if tool_name not in self.toolkit.tools:
            return f"ERROR: Unknown tool '{tool_name}'"

        try:
            tool = self.toolkit.tools[tool_name]
            result = tool(**kwargs)  # type: ignore[operator]
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
                "options": {"temperature": 0.7, "num_predict": 1000},
            }

            response = requests.post(self.api_url, json=payload, timeout=120)

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

        # Search memory for similar past tasks (semantic search)
        past_tasks = self.memory.search_memories(task, limit=2)
        memory_context = ""
        if past_tasks:
            memory_context = "\n\nPAST SIMILAR TASKS:\n"
            for pt in past_tasks:
                memory_context += f"- Task: {pt['task']}\n  Result: {pt['result'][:200]}\n"

        # Initialize conversation
        system_prompt = f"""You are an autonomous AI agent with access to tools.
{memory_context}

{self.toolkit.get_tool_descriptions()}

REACT PROTOCOL - FOLLOW EXACTLY:

Step 1: Thought: [reasoning]
Step 2: Action: tool_name(arg1="value1", arg2="value2")
        OR Final Answer: [answer]

EXAMPLE 1 (math):
Thought: I need to calculate 5*9
Action: execute_shell(command="python -c 'print(5*9)'")
Observation: 45
Thought: I have the answer
Final Answer: 45

EXAMPLE 2 (file read):
Thought: I need to read config.json
Action: read_file(file_path="config.json")
Observation: {{"key": "value"}}
Thought: File contains the data
Final Answer: Config has key=value

CRITICAL FORMAT:
- Action MUST be: tool_name(arg="value")
- Use EXACT tool names from list above
- Always include arg names: arg="value" NOT just "value"

TASK: {task}
"""

        self.conversation_history.append({"role": "system", "content": system_prompt})

        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            self.log(f"[ITER] Iteration {iteration}/{self.max_iterations}")

            # Build conversation prompt
            conv_text = "\n\n".join([msg["content"] for msg in self.conversation_history])

            # Ask model
            response = self.ask_model(conv_text)

            if "ERROR:" in response:
                return {
                    "success": False,
                    "final_answer": response,
                    "iterations": iteration,
                    "conversation": self.conversation_history,
                }

            self.conversation_history.append({"role": "assistant", "content": response})

            self.log(f"[MODEL] Model: {response[:200]}...")

            # Check for Final Answer
            if "final answer:" in response.lower():
                # Extract final answer
                match = re.search(r"final answer:\s*(.*)", response, re.IGNORECASE | re.DOTALL)
                if match:
                    final_answer = match.group(1).strip()
                    self.log(f"[DONE] Task complete in {iteration} iterations")

                    # Store in memory (Qdrant semantic memory)
                    self.memory.add_memory(task, final_answer)

                    return {
                        "success": True,
                        "final_answer": final_answer,
                        "iterations": iteration,
                        "conversation": self.conversation_history,
                    }

            # Parse and execute action
            action = self.parse_action(response)

            if action:
                tool_name, kwargs = action
                self.log(f"[TOOL] Executing: {tool_name}({kwargs})")

                observation = self.execute_action(tool_name, kwargs)

                self.conversation_history.append({"role": "user", "content": f"Observation: {observation}"})

                self.log(f"[OBS] Observation: {observation[:200]}...")
            else:
                # No action found, prompt model to continue
                self.conversation_history.append(
                    {"role": "user", "content": "Continue with next thought and action, or provide Final Answer."}
                )

        # Max iterations reached
        self.log(f"[WARN] Max iterations ({self.max_iterations}) reached")

        return {
            "success": False,
            "final_answer": "ERROR: Max iterations reached without Final Answer",
            "iterations": iteration,
            "conversation": self.conversation_history,
        }


# ==================== CLI INTERFACE ====================


def main():
    parser = argparse.ArgumentParser(description="RTX Agent - Autonomous ReAct agent with tools")
    parser.add_argument("--task", type=str, required=True, help="Task description for agent")
    parser.add_argument("--model", type=str, default="llama3:8b", help="Ollama model to use (default: llama3:8b)")
    parser.add_argument("--max-iterations", type=int, default=10, help="Max ReAct iterations (default: 10)")
    parser.add_argument("--unsafe", action="store_true", help="Disable shell command safety checks")
    parser.add_argument("--output", type=str, help="Save result to file")

    args = parser.parse_args()

    print("=" * 60)
    print("RTX AGENT - AUTONOMOUS EXECUTION")
    print("=" * 60)

    # Create agent
    agent = ReactAgent(model=args.model, max_iterations=args.max_iterations, safe_mode=not args.unsafe)

    # Run task
    result = agent.run(args.task)

    print("\n" + "=" * 60)
    if result["success"]:
        print("[SUCCESS] TASK COMPLETE")
        print("=" * 60)
        print(f"\n{result['final_answer']}\n")
        print(f"[STATS] Iterations: {result['iterations']}")
    else:
        print("[FAILED] TASK FAILED")
        print("=" * 60)
        print(f"\n{result['final_answer']}\n")

    # Save output if requested
    if args.output:
        output_path = Path(args.output)

        output_data = {"task": args.task, "result": result, "timestamp": datetime.now().isoformat()}

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

        print(f"[SAVED] Saved to: {output_path}")

    print("=" * 60)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
