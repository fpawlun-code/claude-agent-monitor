import json
import os
from datetime import datetime
from pathlib import Path

class AgentMemory:
    def __init__(self, memory_file="memory/memory.json"):
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(exist_ok=True)
        if not self.memory_file.exists():
            self.memory_file.write_text("[]")

    def store(self, task, result):
        """Store task + result"""
        memories = json.loads(self.memory_file.read_text())
        memories.append({
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "result": result
        })
        self.memory_file.write_text(json.dumps(memories, indent=2))

    def search_similar(self, query, limit=3):
        """Find recent tasks matching keywords"""
        memories = json.loads(self.memory_file.read_text())
        query_lower = query.lower()

        # Simple keyword match
        matches = [
            m for m in memories
            if query_lower in m["task"].lower()
        ]

        # Return most recent matches
        return matches[-limit:] if matches else memories[-limit:]
