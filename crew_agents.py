#!/usr/bin/env python3
"""Multi-Agent System using CrewAI"""

import sys
import argparse
from crewai import Agent, Task, Crew, Process
from langchain_ollama import ChatOllama

# Initialize Ollama LLM for all agents
llm = ChatOllama(model="llama3:8b", base_url="http://localhost:11434")

# Define specialized agents
researcher = Agent(
    role="Research Specialist",
    goal="Gather and analyze information from web and APIs",
    backstory="Expert researcher with deep knowledge of information gathering",
    llm=llm,
    verbose=True
)

coder = Agent(
    role="Software Developer",
    goal="Write, debug and optimize code",
    backstory="Senior developer with expertise in multiple languages",
    llm=llm,
    verbose=True
)

tester = Agent(
    role="QA Engineer",
    goal="Test, validate and ensure quality",
    backstory="Meticulous tester focused on reliability",
    llm=llm,
    verbose=True
)

def create_crew(task_description: str, task_type: str = "auto"):
    """Create crew based on task type"""

    # Auto-detect task type
    if task_type == "auto":
        if any(word in task_description.lower() for word in ["research", "find", "search", "analyze"]):
            task_type = "research"
        elif any(word in task_description.lower() for word in ["code", "write", "build", "develop"]):
            task_type = "code"
        elif any(word in task_description.lower() for word in ["test", "validate", "check"]):
            task_type = "test"
        else:
            task_type = "code"  # default

    # Create task
    if task_type == "research":
        task = Task(
            description=task_description,
            agent=researcher,
            expected_output="Detailed research findings"
        )
        crew = Crew(agents=[researcher], tasks=[task], process=Process.sequential)

    elif task_type == "code":
        task = Task(
            description=task_description,
            agent=coder,
            expected_output="Working code implementation"
        )
        crew = Crew(agents=[coder], tasks=[task], process=Process.sequential)

    elif task_type == "test":
        task = Task(
            description=task_description,
            agent=tester,
            expected_output="Test results and validation"
        )
        crew = Crew(agents=[tester], tasks=[task], process=Process.sequential)

    else:  # complex task - use all agents
        research_task = Task(
            description=f"Research requirements for: {task_description}",
            agent=researcher,
            expected_output="Requirements analysis"
        )
        code_task = Task(
            description=f"Implement: {task_description}",
            agent=coder,
            expected_output="Code implementation"
        )
        test_task = Task(
            description=f"Test implementation of: {task_description}",
            agent=tester,
            expected_output="Test results"
        )
        crew = Crew(
            agents=[researcher, coder, tester],
            tasks=[research_task, code_task, test_task],
            process=Process.sequential
        )

    return crew

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Task Execution")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--type", default="auto", choices=["auto", "research", "code", "test", "full"],
                       help="Task type")

    args = parser.parse_args()

    print("="*60)
    print("MULTI-AGENT SYSTEM")
    print("="*60)

    crew = create_crew(args.task, args.type)
    result = crew.kickoff()

    print("\n" + "="*60)
    print("RESULT")
    print("="*60)
    print(result)

    return 0

if __name__ == "__main__":
    sys.exit(main())
