#!/usr/bin/env python3
"""
AI Gateway - Universal Bridge to Local RTX (Ollama)
Manages delegation of tasks from Claude Code to local Llama 3 on RTX GPU.

WORKFLOW:
1. Claude receives task → writes prompt for Ollama
2. ai_gateway sends to RTX (0 Claude tokens)
3. Ollama generates draft/analysis (runs on GPU)
4. Claude reads output and polishes (minimal tokens)

SAVINGS: 90-95% token reduction for bulk/draft work
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests


class LocalAI:
    """Universal gateway to local Llama 3 on RTX GPU"""

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        output_dir: str = "C:\\ClaudeAgent\\outputs",
        enable_cache: bool = True,
        cache_ttl: int = 300,  # 5 minutes
    ):
        """
        Args:
            model: Ollama model name
            base_url: Ollama API endpoint
            output_dir: Where to save RTX outputs
            enable_cache: Enable smart caching for read/bash results
            cache_ttl: Cache time-to-live in seconds (default 300 = 5 min)
        """
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.log_file = Path("C:\\ClaudeAgent\\ai_gateway.log")
        self.usage_log = Path("C:\\ClaudeAgent\\usage_stats.jsonl")

        # Smart cache for read/bash results
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Any] = {}  # {key: (result, timestamp)}
        self._cache_hits = 0
        self._cache_misses = 0

        # File snapshots for diff mode
        self._file_snapshots: Dict[str, str] = {}  # {file_path: last_content}

    def _get_cache(self, key: str) -> Optional[str]:
        """Get from cache if exists and not expired"""
        if not self.enable_cache:
            return None

        if key in self._cache:
            result, timestamp = self._cache[key]
            age = time.time() - timestamp

            if age < self.cache_ttl:
                self._cache_hits += 1
                self.log(f"[CACHE HIT] {key[:50]}... (age: {age:.1f}s)")
                return result
            else:
                # Expired
                del self._cache[key]

        self._cache_misses += 1
        return None

    def _set_cache(self, key: str, value: str):
        """Set cache with timestamp"""
        if not self.enable_cache:
            return

        # LRU: limit cache size to 50 items
        if len(self._cache) >= 50:
            # Remove oldest
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
            self.log("[CACHE] Evicted oldest entry")

        self._cache[key] = (value, time.time())

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0

        return {
            "enabled": self.enable_cache,
            "size": len(self._cache),
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "ttl_seconds": self.cache_ttl,
        }

    def log(self, message: str, level: str = "INFO"):
        """Write to log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"

        print(log_line.strip())

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def log_usage(self, stats: Dict[str, Any]):
        """Track token savings and RTX usage"""
        stats["timestamp"] = datetime.now().isoformat()

        with open(self.usage_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(stats) + "\n")

    def ask_rtx(
        self,
        prompt: str,
        system_context: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        save_to_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        MAIN METHOD: Ask RTX to process task (via Ollama)

        Args:
            prompt: The actual question/task for RTX
            system_context: System instructions (role, constraints)
            temperature: 0.0 (deterministic) to 1.0 (creative)
            max_tokens: Max response length
            save_to_file: Optional filename to save response

        Returns:
            {
                "success": bool,
                "response": str,
                "gpu_time_seconds": float,
                "tokens_saved_estimate": int,
                "output_file": str | None
            }
        """
        start_time = time.time()

        # Build full prompt
        full_prompt = prompt
        if system_context:
            full_prompt = f"{system_context}\n\n{prompt}"

        self.log(f"[RTX] Delegating to RTX: {prompt[:80]}...")

        try:
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }

            response = requests.post(self.api_url, json=payload, timeout=300)  # 5min for large tasks

            if response.status_code != 200:
                self.log(f"[ERROR] API error: {response.status_code}", "ERROR")
                return {"success": False, "response": None, "error": f"HTTP {response.status_code}"}

            result = response.json()
            generated_text = result.get("response", "")
            gpu_time = result.get("total_duration", 0) / 1e9  # nanoseconds → seconds

            elapsed = time.time() - start_time

            # Estimate Claude tokens saved
            # Assumption: 1 token ≈ 4 chars
            estimated_tokens_saved = len(generated_text) // 4

            self.log(f"[OK] RTX complete: {len(generated_text)} chars in {gpu_time:.2f}s GPU")
            self.log(f"[SAVE] Estimated tokens saved: ~{estimated_tokens_saved}")

            # Save to file if requested
            output_file = None
            if save_to_file:
                output_file = self.output_dir / save_to_file
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(generated_text)
                self.log(f"[FILE] Saved to: {output_file}")

            # Log usage stats
            self.log_usage(
                {
                    "prompt_preview": prompt[:100],
                    "response_chars": len(generated_text),
                    "gpu_time_seconds": gpu_time,
                    "wall_time_seconds": elapsed,
                    "estimated_tokens_saved": estimated_tokens_saved,
                    "temperature": temperature,
                    "output_file": str(output_file) if output_file else None,
                }
            )

            return {
                "success": True,
                "response": generated_text,
                "gpu_time_seconds": gpu_time,
                "tokens_saved_estimate": estimated_tokens_saved,
                "output_file": str(output_file) if output_file else None,
            }

        except requests.exceptions.Timeout:
            self.log("[ERROR] Request timed out", "ERROR")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            self.log(f"[ERROR] {e}", "ERROR")
            return {"success": False, "error": str(e)}

    def batch_ask(self, prompts: list[str], system_context: str = "", **kwargs) -> list[Dict[str, Any]]:
        """Process multiple prompts sequentially"""
        self.log(f"[BATCH] Batch processing {len(prompts)} prompts on RTX")

        results = []
        total_tokens_saved = 0

        for i, prompt in enumerate(prompts, 1):
            self.log(f"[BATCH] Batch {i}/{len(prompts)}")
            result = self.ask_rtx(prompt, system_context, **kwargs)
            results.append(result)

            if result.get("success"):
                total_tokens_saved += result.get("tokens_saved_estimate", 0)

        self.log(f"[OK] Batch complete: {sum(1 for r in results if r.get('success'))} successful")
        self.log(f"[SAVE] TOTAL tokens saved: ~{total_tokens_saved}")

        return results

    def health_check(self) -> bool:
        """Check if Ollama service is reachable"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                self.log("[OK] RTX gateway healthy")
                return True
            return False
        except Exception as e:
            self.log(f"[ERROR] RTX gateway unreachable: {e}", "ERROR")
            return False

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get cumulative token savings"""
        if not self.usage_log.exists():
            return {"total_requests": 0, "total_tokens_saved": 0}

        total_requests = 0
        total_tokens_saved = 0
        total_gpu_time = 0

        with open(self.usage_log, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    total_requests += 1
                    total_tokens_saved += entry.get("estimated_tokens_saved", 0)
                    total_gpu_time += entry.get("gpu_time_seconds", 0)
                except:
                    continue

        # Estimate cost savings (Claude Sonnet 4.5: ~$3/1M input + $15/1M output)
        # Conservative: assume 50% input, 50% output = avg $9/1M tokens
        cost_saved_usd = (total_tokens_saved / 1_000_000) * 9

        return {
            "total_requests": total_requests,
            "total_tokens_saved": total_tokens_saved,
            "total_gpu_time_hours": total_gpu_time / 3600,
            "estimated_cost_saved_usd": round(cost_saved_usd, 2),
        }

    def delegate_batch_read(self, file_paths: list[str], goal: str, max_output_chars: int = 2000) -> Dict[str, str]:
        """
        Read multiple files at once via RTX.

        More efficient than calling delegate_read() multiple times.
        RTX processes all files in one task.

        Args:
            file_paths: List of file paths to read
            goal: What to find across all files
            max_output_chars: Max chars per file result

        Returns:
            Dict mapping file_path -> extracted_content

        Example:
            results = delegate_batch_read(
                ["/c/ClaudeAgent/ai_gateway.py", "/c/ClaudeAgent/rtx_agent.py"],
                "find all class definitions"
            )
            # Returns: {"ai_gateway.py": "class LocalAI...", "rtx_agent.py": "class ReactAgent..."}
        """
        try:
            files_str = "\n".join(f"- {fp}" for fp in file_paths)
            task = f"""Read multiple files and extract relevant information:

Files to read:
{files_str}

Goal: {goal}

Steps:
1. For each file, use read_file(path) to read it
2. Extract sections relevant to: {goal}
3. Keep each result under {max_output_chars} chars
4. Provide Final Answer as JSON dict: {{"file1": "content1", "file2": "content2"}}

Format: Return valid JSON only.
"""

            from rtx_agent import ReactAgent

            agent = ReactAgent(model=self.model, max_iterations=len(file_paths) + 3)
            result = agent.run(task)

            if result.get("success"):
                import json

                final_answer = result.get("final_answer", "{}")

                # Try to parse JSON
                try:
                    # Extract JSON from response
                    json_start = final_answer.find("{")
                    json_end = final_answer.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = final_answer[json_start:json_end]
                        results_dict = json.loads(json_str)
                    else:
                        # Fallback: create simple dict
                        results_dict = {fp: final_answer[:max_output_chars] for fp in file_paths}
                except:
                    results_dict = {fp: final_answer[:max_output_chars] for fp in file_paths}

                total_chars = sum(len(v) for v in results_dict.values())
                self.log(f"[BATCH READ] {len(file_paths)} files -> {total_chars} total chars")
                return results_dict
            else:
                error = result.get("error", "Unknown error")
                self.log(f"[ERROR] Batch read failed: {error}", "ERROR")
                return {fp: f"ERROR: {error}" for fp in file_paths}

        except Exception as e:
            self.log(f"[ERROR] delegate_batch_read exception: {e}", "ERROR")
            return {fp: f"ERROR: {str(e)}" for fp in file_paths}

    def delegate_batch_bash(
        self, commands: list[str], task_context: str, max_output_chars: int = 1000
    ) -> Dict[str, str]:
        """
        Execute multiple bash commands at once via RTX.

        More efficient than calling delegate_bash() multiple times.

        Args:
            commands: List of bash commands
            task_context: What we're trying to achieve
            max_output_chars: Max chars per command result

        Returns:
            Dict mapping command -> summary

        Example:
            results = delegate_batch_bash(
                ["git status", "git log -5", "git diff"],
                "understand current git state"
            )
        """
        try:
            cmds_str = "\n".join(f"{i + 1}. {cmd}" for i, cmd in enumerate(commands))
            task = f"""Execute multiple bash commands and summarize results:

Commands:
{cmds_str}

Context: {task_context}

Steps:
1. For each command, use execute_shell(command=cmd)
2. Analyze each output based on context
3. Keep each summary under {max_output_chars} chars
4. Provide Final Answer as JSON dict: {{"cmd1": "summary1", "cmd2": "summary2"}}

Format: Return valid JSON only.
"""

            from rtx_agent import ReactAgent

            agent = ReactAgent(model=self.model, max_iterations=len(commands) + 3)
            result = agent.run(task)

            if result.get("success"):
                import json

                final_answer = result.get("final_answer", "{}")

                # Try to parse JSON
                try:
                    json_start = final_answer.find("{")
                    json_end = final_answer.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = final_answer[json_start:json_end]
                        results_dict = json.loads(json_str)
                    else:
                        results_dict = {cmd: final_answer[:max_output_chars] for cmd in commands}
                except:
                    results_dict = {cmd: final_answer[:max_output_chars] for cmd in commands}

                self.log(f"[BATCH BASH] {len(commands)} commands executed")
                return results_dict
            else:
                error = result.get("error", "Unknown error")
                self.log(f"[ERROR] Batch bash failed: {error}", "ERROR")
                return {cmd: f"ERROR: {error}" for cmd in commands}

        except Exception as e:
            self.log(f"[ERROR] delegate_batch_bash exception: {e}", "ERROR")
            return {cmd: f"ERROR: {str(e)}" for cmd in commands}

    def delegate_read(self, file_path: str, goal: str, max_output_chars: int = 2000, use_cache: bool = True) -> str:
        """
        Read file via RTX and extract only relevant parts (with smart caching).

        Instead of returning full file (10k-50k tokens), RTX:
        1. Reads the file using read_file tool
        2. Analyzes content based on goal
        3. Returns only relevant sections with context

        Args:
            file_path: Path to file to read
            goal: What to find (e.g., "find login function", "how does X work?")
            max_output_chars: Max chars in result (default 2000)

        Returns:
            Relevant file excerpts with line numbers and context

        Example:
            # Before (Claude directly):
            content = Read("/c/ClaudeAgent/rtx_agent.py")  # 20,000 tokens!

            # After (via RTX):
            content = delegate_read(
                "/c/ClaudeAgent/rtx_agent.py",
                "how does the ReAct loop work?"
            )  # ~500 tokens: only ReAct loop code + explanation
        """
        try:
            # Check cache first
            cache_key = f"read:{file_path}:{goal}"
            if use_cache:
                cached = self._get_cache(cache_key)
                if cached:
                    return cached

            # Build task for RTX autonomous agent
            task = f"""Read file and extract relevant information:

File to read: {file_path}

Goal: {goal}

Steps:
1. Use read_file("{file_path}") to read the file
2. Analyze the content
3. Extract ONLY sections relevant to: {goal}
4. Include line numbers and brief context
5. Provide Final Answer with extracted code/text (max {max_output_chars} chars)

Important:
- Do NOT return the entire file
- Extract only relevant functions/classes/sections
- Include line numbers for reference
- Add brief explanations of what each section does
"""

            # Use autonomous agent (has access to read_file tool)
            from rtx_agent import ReactAgent

            agent = ReactAgent(model=self.model, max_iterations=5)
            result = agent.run(task)

            if result.get("success"):
                final_answer = result.get("final_answer", "No content found")

                # Sanitize encoding
                try:
                    final_answer = final_answer.encode("cp1250", errors="replace").decode("cp1250")
                except:
                    final_answer = "".join(c if ord(c) < 128 else "?" for c in final_answer)

                # Truncate if needed
                if len(final_answer) > max_output_chars:
                    final_answer = final_answer[: max_output_chars - 3] + "..."

                # Calculate savings
                try:
                    from pathlib import Path

                    actual_size = Path(file_path).stat().st_size
                    savings_pct = 100 * (1 - len(final_answer) / max(actual_size, 1))
                    self.log(
                        f"[READ] {Path(file_path).name} ({actual_size} bytes) -> {len(final_answer)} chars ({savings_pct:.0f}% reduction)"
                    )
                except:
                    self.log(f"[READ] {file_path} -> {len(final_answer)} chars extracted")

                # Cache result
                if use_cache:
                    self._set_cache(cache_key, final_answer)

                return final_answer
            else:
                error = result.get("error", "Unknown error")
                self.log(f"[ERROR] Read failed: {error}", "ERROR")
                return f"ERROR: {error}"

        except Exception as e:
            self.log(f"[ERROR] delegate_read exception: {e}", "ERROR")
            return f"ERROR: {str(e)}"

    def delegate_read_diff(self, file_path: str, goal: str = "show what changed") -> str:
        """
        Read file and show only changes since last read (diff mode).

        On first read: returns full content + saves snapshot
        On subsequent reads: returns only changed sections

        Args:
            file_path: Path to file
            goal: What to look for in changes

        Returns:
            Diff summary or full content on first read

        Example:
            # First read
            content1 = delegate_read_diff("file.py")  # Full file

            # ... file gets edited ...

            # Second read
            content2 = delegate_read_diff("file.py")  # Only changes!
        """
        try:
            # Read current file content
            with open(file_path, "r", encoding="utf-8") as f:
                current_content = f.read()

            # Check if we have a snapshot
            if file_path not in self._file_snapshots:
                # First read - save snapshot and return full content
                self._file_snapshots[file_path] = current_content
                self.log(f"[DIFF] First read (snapshot saved): {file_path}")
                return self.delegate_read(file_path, goal or "summarize main content")

            # Get previous snapshot
            previous_content = self._file_snapshots[file_path]

            # Check if file changed
            if current_content == previous_content:
                self.log(f"[DIFF] No changes: {file_path}")
                return "[NO CHANGES] File unchanged since last read."

            # File changed - delegate diff analysis to RTX
            task = f"""Analyze file changes and summarize:

Previous version:
```
{previous_content[:2000]}...
```

Current version:
```
{current_content[:2000]}...
```

Task: {goal}

Provide Final Answer with:
1. What sections were added
2. What sections were modified
3. What sections were removed
4. Brief summary of changes

Keep answer concise (max 1000 chars).
"""

            from rtx_agent import ReactAgent

            agent = ReactAgent(model=self.model, max_iterations=3)
            result = agent.run(task)

            if result.get("success"):
                diff_summary = result.get("final_answer", "No diff available")

                # Update snapshot
                self._file_snapshots[file_path] = current_content

                self.log(f"[DIFF] Changes detected: {file_path}")
                return diff_summary
            else:
                error = result.get("error", "Unknown error")
                return f"ERROR analyzing diff: {error}"

        except Exception as e:
            self.log(f"[ERROR] delegate_read_diff failed: {e}", "ERROR")
            return f"ERROR: {str(e)}"

    def delegate_git_commit(self, context: str = "") -> str:
        """Generate git commit message by analyzing changes"""
        try:
            task = f"""Analyze git changes and generate conventional commit message:

Context: {context}

Steps:
1. Run: git status, git diff --cached
2. Analyze staged changes
3. Generate commit message following conventional commits format:
   - feat: new feature
   - fix: bug fix
   - docs: documentation
   - chore: maintenance
4. Keep message concise (max 72 chars first line)

Return ONLY the commit message, nothing else.
"""
            from rtx_agent import ReactAgent

            agent = ReactAgent(model=self.model, max_iterations=3)
            result = agent.run(task)

            if result.get("success"):
                msg = result.get("final_answer", "chore: update files")
                self.log(f"[GIT] Generated commit: {msg[:50]}...")
                return msg.strip()
            return "chore: update files"
        except Exception as e:
            self.log(f"[ERROR] delegate_git_commit: {e}", "ERROR")
            return "chore: update files"

    def delegate_pr_description(self, branch: str, base: str = "main") -> str:
        """Generate PR description by analyzing branch changes"""
        try:
            task = f"""Analyze git branch and generate PR description:

Branch: {branch}
Base: {base}

Steps:
1. Run: git log {base}..{branch} --oneline
2. Run: git diff {base}...{branch} --stat
3. Generate PR description with:
   - Title (concise)
   - Summary paragraph
   - List of changes
   - Format as markdown

Return markdown PR description.
"""
            from rtx_agent import ReactAgent

            agent = ReactAgent(model=self.model, max_iterations=5)
            result = agent.run(task)

            if result.get("success"):
                desc = result.get("final_answer", "# PR Description\n\nChanges from branch.")
                self.log("[GIT] Generated PR description")
                return desc
            return "# PR Description\n\nChanges from branch."
        except Exception as e:
            self.log(f"[ERROR] delegate_pr_description: {e}", "ERROR")
            return f"# PR Description\n\nError: {e}"

    def delegate_git_summary(self, commits: int = 10) -> str:
        """Summarize recent git commits"""
        try:
            task = f"""Summarize recent git history:

Steps:
1. Run: git log -n {commits} --oneline --stat
2. Analyze commits
3. Generate concise summary:
   - Main themes/features
   - Key changes
   - Authors if multiple
4. Keep summary under 500 chars

Return summary.
"""
            from rtx_agent import ReactAgent

            agent = ReactAgent(model=self.model, max_iterations=3)
            result = agent.run(task)

            if result.get("success"):
                summary = result.get("final_answer", "Recent commits")
                self.log("[GIT] Generated summary")
                return summary
            return "Recent commits"
        except Exception as e:
            self.log(f"[ERROR] delegate_git_summary: {e}", "ERROR")
            return f"Error: {e}"

    def auto_delegate_read(self, file_path: str, goal: str = "", threshold_kb: int = 10) -> str:
        """
        Automatically decide whether to delegate file read to RTX.

        Decision logic:
        - Small file (<threshold_kb) → direct read (faster)
        - Large file (>=threshold_kb) → delegate to RTX (token savings)
        - Has specific goal → delegate to RTX (smart extraction)

        Args:
            file_path: Path to file
            goal: Optional extraction goal
            threshold_kb: File size threshold in KB (default 10KB)

        Returns:
            File content (direct or extracted via RTX)
        """
        try:
            from pathlib import Path

            file_size = Path(file_path).stat().st_size
            file_size_kb = file_size / 1024

            # Decision logic
            if goal:
                # Has specific goal → always delegate for smart extraction
                self.log(f"[AUTO] Delegating (has goal): {file_path}")
                return self.delegate_read(file_path, goal)
            elif file_size_kb >= threshold_kb:
                # Large file → delegate for token savings
                self.log(f"[AUTO] Delegating (large file: {file_size_kb:.1f}KB): {file_path}")
                return self.delegate_read(file_path, "extract main content and structure")
            else:
                # Small file → direct read (faster)
                self.log(f"[AUTO] Direct read (small file: {file_size_kb:.1f}KB): {file_path}")
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()

        except Exception as e:
            self.log(f"[ERROR] auto_delegate_read failed: {e}", "ERROR")
            return f"ERROR: {str(e)}"

    def auto_delegate_bash(self, command: str, task_context: str = "", threshold_lines: int = 20) -> str:
        """
        Automatically decide whether to delegate bash execution to RTX.

        Decision logic:
        - Output likely small → execute directly
        - Output likely large → delegate to RTX for summary
        - Has analysis task → delegate to RTX

        Args:
            command: Bash command to execute
            task_context: Optional analysis context
            threshold_lines: Expected output threshold (default 20 lines)

        Returns:
            Command output (direct or summarized via RTX)
        """
        try:
            # Heuristics for large output commands
            large_output_keywords = ["git log", "ls -la", "find", "grep -r", "cat", "history"]
            is_large_output = any(kw in command.lower() for kw in large_output_keywords)

            if task_context:
                # Has analysis task → delegate
                self.log(f"[AUTO] Delegating bash (has context): {command[:40]}...")
                return self.delegate_bash(command, task_context)
            elif is_large_output:
                # Likely large output → delegate for summary
                self.log(f"[AUTO] Delegating bash (large output): {command[:40]}...")
                return self.delegate_bash(command, "summarize key information")
            else:
                # Simple command → execute directly
                self.log(f"[AUTO] Direct bash: {command[:40]}...")
                import subprocess

                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                output = result.stdout or result.stderr
                # If output is still too large, truncate
                if len(output) > 5000:
                    output = output[:5000] + "\n... (truncated)"
                return output

        except Exception as e:
            self.log(f"[ERROR] auto_delegate_bash failed: {e}", "ERROR")
            return f"ERROR: {str(e)}"

    def delegate_bash(
        self, command: str, task_context: str, max_output_chars: int = 1000, use_cache: bool = True
    ) -> str:
        """
        Execute bash command via RTX and get smart summary.

        Instead of returning full command output (thousands of tokens),
        RTX executes the command and returns only relevant information.

        Args:
            command: bash command to execute (e.g., "ls -la /c/ClaudeAgent")
            task_context: what we're trying to find (e.g., "find Python files")
            max_output_chars: max chars in summary (default 1000)

        Returns:
            Smart summary of command output

        Example:
            # Before (Claude directly):
            result = Bash("git log --oneline -50")  # Returns 2000 tokens

            # After (via RTX):
            result = delegate_bash(
                "git log --oneline -50",
                "find last commit about authentication"
            )  # Returns 50 tokens: "Commit abc123: 'Fix auth bug' 2 days ago"
        """
        try:
            # Check cache first
            cache_key = f"bash:{command}:{task_context}"
            if use_cache:
                cached = self._get_cache(cache_key)
                if cached:
                    return cached

            # Use RTX autonomous agent with tools to execute bash
            task = f"""Execute bash command and analyze output:

Command to execute: {command}

Task: {task_context}

Steps:
1. Use execute_shell("{command}") to run the command
2. Analyze the output
3. Extract ONLY information relevant to: {task_context}
4. Provide Final Answer with concise summary (max {max_output_chars} chars)

Important: Run the ACTUAL command using execute_shell tool, don't just describe it!
"""

            # Use autonomous agent (has access to execute_shell tool)
            from rtx_agent import ReactAgent

            agent = ReactAgent(model=self.model, max_iterations=3)
            result = agent.run(task)

            if result.get("success"):
                final_answer = result.get("final_answer", "No output")

                # Sanitize encoding (Windows CP1250 issues)
                try:
                    final_answer = final_answer.encode("cp1250", errors="replace").decode("cp1250")
                except:
                    # Fallback: remove non-ASCII
                    final_answer = "".join(c if ord(c) < 128 else "?" for c in final_answer)

                # Truncate if needed
                if len(final_answer) > max_output_chars:
                    final_answer = final_answer[: max_output_chars - 3] + "..."

                self.log(f"[BASH] {command[:40]}... -> {len(final_answer)} chars summary")

                # Cache result
                if use_cache:
                    self._set_cache(cache_key, final_answer)

                return final_answer
            else:
                error = result.get("error", "Unknown error")
                self.log(f"[ERROR] Bash failed: {error}", "ERROR")
                return f"ERROR: {error}"

        except Exception as e:
            self.log(f"[ERROR] delegate_bash exception: {e}", "ERROR")
            return f"ERROR: {str(e)}"


# ====================
# CONVENIENCE FUNCTIONS
# ====================


def ask_rtx(prompt: str, system_context: str = "", **kwargs) -> Dict[str, Any]:
    """Quick access to RTX gateway"""
    gateway = LocalAI()
    return gateway.ask_rtx(prompt, system_context, **kwargs)


def delegate_to_rtx(
    task_description: str, role: str = "expert developer", save_as: Optional[str] = None, **kwargs
) -> str:
    """
    High-level delegation function

    Args:
        task_description: What you want RTX to do
        role: System role (e.g., "expert Python developer")
        save_as: Filename to save output
        **kwargs: Additional args for ask_rtx()

    Returns:
        Generated text from RTX
    """
    system_context = f"You are an {role}. Follow instructions precisely."

    gateway = LocalAI()
    result = gateway.ask_rtx(prompt=task_description, system_context=system_context, save_to_file=save_as, **kwargs)

    if result.get("success"):
        return result["response"]
    else:
        raise RuntimeError(f"RTX delegation failed: {result.get('error')}")


def claude_delegate_autonomous(task: str, max_iterations: int = 10, timeout: int = 300) -> Dict[str, Any]:
    """
    Claude delegates task to autonomous RTX agent (rtx_agent.py)

    This runs the full ReAct loop with tools (read_file, execute_shell, etc.)
    Use this for tasks that require autonomous tool usage.

    Args:
        task: Natural language task description
        max_iterations: Max ReAct iterations
        timeout: Max execution time in seconds

    Returns:
        {
            "success": bool,
            "final_answer": str,  # Model's final answer
            "iterations": int,    # How many ReAct iterations
            "raw_output": str     # Full stdout
        }

    Example:
        >>> result = claude_delegate_autonomous(
        ...     "Read ai_gateway.py and count the number of functions"
        ... )
        >>> if result["success"]:
        ...     print(result["final_answer"])
    """
    import subprocess
    from pathlib import Path

    agent_path = Path(__file__).parent / "rtx_agent.py"

    if not agent_path.exists():
        return {"success": False, "error": f"rtx_agent.py not found at {agent_path}"}

    cmd = ["python", str(agent_path), "--task", task, "--max-iterations", str(max_iterations)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=Path(__file__).parent)

        # Parse output
        stdout = result.stdout

        if "[SUCCESS]" in stdout:
            # Extract final answer (between success header and stats)
            lines = stdout.split("\n")
            answer_lines = []
            capture = False

            for line in lines:
                if "[SUCCESS]" in line:
                    capture = True
                    continue
                if "[STATS]" in line or "====" in line:
                    capture = False
                if capture and line.strip():
                    answer_lines.append(line)

            # Extract iteration count
            iterations = 0
            for line in lines:
                if "[STATS] Iterations:" in line:
                    try:
                        iterations = int(line.split(":")[-1].strip())
                    except:
                        pass

            return {
                "success": True,
                "final_answer": "\n".join(answer_lines).strip(),
                "iterations": iterations,
                "raw_output": stdout,
            }
        else:
            return {"success": False, "error": result.stderr or stdout, "raw_output": stdout}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Task timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delegate_git_commit(context: str = "") -> str:
    """Generate git commit message"""
    gateway = LocalAI()
    return gateway.delegate_git_commit(context)


def delegate_pr_description(branch: str, base: str = "main") -> str:
    """Generate PR description"""
    gateway = LocalAI()
    return gateway.delegate_pr_description(branch, base)


def delegate_git_summary(commits: int = 10) -> str:
    """Summarize recent commits"""
    gateway = LocalAI()
    return gateway.delegate_git_summary(commits)


def delegate_read_diff(file_path: str, goal: str = "show what changed") -> str:
    """Read file and show only changes since last read"""
    gateway = LocalAI()
    return gateway.delegate_read_diff(file_path, goal)


def auto_delegate_read(file_path: str, goal: str = "", threshold_kb: int = 10) -> str:
    """Auto-decide whether to delegate file read to RTX"""
    gateway = LocalAI()
    return gateway.auto_delegate_read(file_path, goal, threshold_kb)


def auto_delegate_bash(command: str, task_context: str = "", threshold_lines: int = 20) -> str:
    """Auto-decide whether to delegate bash execution to RTX"""
    gateway = LocalAI()
    return gateway.auto_delegate_bash(command, task_context, threshold_lines)


def delegate_batch_read(file_paths: list[str], goal: str, max_output_chars: int = 2000) -> Dict[str, str]:
    """Batch read multiple files via RTX"""
    gateway = LocalAI()
    return gateway.delegate_batch_read(file_paths, goal, max_output_chars)


def delegate_batch_bash(commands: list[str], task_context: str, max_output_chars: int = 1000) -> Dict[str, str]:
    """Batch execute multiple bash commands via RTX"""
    gateway = LocalAI()
    return gateway.delegate_batch_bash(commands, task_context, max_output_chars)


def delegate_read(file_path: str, goal: str, max_output_chars: int = 2000) -> str:
    """
    Convenience function: Read file via RTX with smart extraction.

    Args:
        file_path: Path to file
        goal: What to find
        max_output_chars: Max chars in result

    Returns:
        Relevant file excerpts

    Example:
        # Instead of:
        # content = Read("/c/ClaudeAgent/rtx_agent.py")  # 20,000 tokens

        # Use:
        content = delegate_read(
            "/c/ClaudeAgent/rtx_agent.py",
            "find the ReAct loop implementation"
        )  # ~500 tokens
    """
    gateway = LocalAI()
    return gateway.delegate_read(file_path, goal, max_output_chars)


def delegate_bash(command: str, task_context: str, max_output_chars: int = 1000) -> str:
    """
    Convenience function: Execute bash command via RTX with smart summary.

    Args:
        command: Bash command to execute
        task_context: What we're looking for
        max_output_chars: Max chars in summary

    Returns:
        Concise summary of command output

    Example:
        # Instead of:
        # result = Bash("ls -la /c/ClaudeAgent")  # 2000 tokens returned

        # Use:
        result = delegate_bash(
            "ls -la /c/ClaudeAgent",
            "find all Python files"
        )  # ~100 tokens returned
    """
    gateway = LocalAI()
    return gateway.delegate_bash(command, task_context, max_output_chars)


if __name__ == "__main__":
    # Test the gateway
    print("=" * 60)
    print("AI GATEWAY HEALTH CHECK")
    print("=" * 60)

    gateway = LocalAI()

    # Test 1: Health check
    print("\n[1/3] Checking RTX connection...")
    if not gateway.health_check():
        print("[ERROR] FAILED: Ollama not reachable")
        exit(1)

    # Test 2: Simple task
    print("\n[2/3] Testing simple delegation...")
    result = gateway.ask_rtx(
        prompt="Write a Python function that adds two numbers. Include docstring.",
        system_context="You are an expert Python developer.",
        temperature=0.3,
        save_to_file="test_output.txt",
    )

    if result["success"]:
        print(f"[OK] Success: {result['tokens_saved_estimate']} tokens saved")
        print(f"[FILE] Output: {result['output_file']}")
    else:
        print(f"[ERROR] Failed: {result.get('error')}")

    # Test 3: Usage stats
    print("\n[3/3] Checking usage statistics...")
    stats = gateway.get_usage_stats()
    print(f"[STATS] Total requests: {stats['total_requests']}")
    print(f"[SAVE] Tokens saved: ~{stats['total_tokens_saved']}")
    print(f"[COST] Cost saved: ${stats['estimated_cost_saved_usd']}")

    # Test 4: Autonomous agent
    print("\n[4/4] Testing autonomous RTX agent...")
    try:
        auto_result = claude_delegate_autonomous(task="What is 7 * 8? Just give me the number.", max_iterations=3)

        if auto_result["success"]:
            print("[OK] Autonomous task complete")
            print(f"[ANSWER] {auto_result['final_answer']}")
            print(f"[ITERS] {auto_result['iterations']} iterations")
        else:
            print(f"[WARN] Autonomous task failed: {auto_result.get('error')}")
    except Exception as e:
        print(f"[WARN] Autonomous agent not available: {e}")

    print("\n" + "=" * 60)
    print("[READY] AI GATEWAY READY")
    print("=" * 60)
