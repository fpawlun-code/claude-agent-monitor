#!/usr/bin/env python3
"""Simple Multi-Agent Coordinator"""

import sys
import argparse
from pathlib import Path

# Import base RTX agent
sys.path.insert(0, str(Path(__file__).parent))
from rtx_agent import ReactAgent

class MultiAgentCoordinator:
    """Coordinates multiple specialized agents"""

    AGENT_PROMPTS = {
        "researcher": "You are a research specialist. Focus on gathering information, web search, and analysis.",
        "coder": "You are a software developer. Focus on writing clean, working code with proper error handling.",
        "tester": "You are a QA engineer. Focus on testing, validation, and finding issues."
    }

    def __init__(self, agents: list):
        self.agents = agents
        self.results = {}

    def run(self, task: str):
        """Run task through agent pipeline"""
        context = task

        for agent_type in self.agents:
            print(f"\n[{agent_type.upper()}] Starting...")

            # Create specialized agent
            agent = ReactAgent(max_iterations=5)

            # Build prompt with context
            specialized_task = f"{self.AGENT_PROMPTS[agent_type]}\n\nTASK: {context}"

            # Run agent
            result = agent.run(specialized_task)

            if result["success"]:
                answer = result["final_answer"]
                self.results[agent_type] = answer
                context = f"{task}\n\nPREVIOUS WORK ({agent_type}): {answer}"
                print(f"[{agent_type.upper()}] Complete")
            else:
                print(f"[{agent_type.upper()}] Failed: {result.get('final_answer')}")
                return None

        return self.results

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent System")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--agents", default="coder", help="Comma-separated agents (researcher,coder,tester)")

    args = parser.parse_args()

    agents = [a.strip() for a in args.agents.split(",")]

    print("="*60)
    print("MULTI-AGENT COORDINATOR")
    print("="*60)
    print(f"Agents: {', '.join(agents)}")
    print(f"Task: {args.task}")

    coordinator = MultiAgentCoordinator(agents)
    results = coordinator.run(args.task)

    if results:
        print("\n" + "="*60)
        print("FINAL RESULTS")
        print("="*60)
        for agent, result in results.items():
            print(f"\n[{agent.upper()}]:")
            print(result[:500])

if __name__ == "__main__":
    sys.exit(main())
