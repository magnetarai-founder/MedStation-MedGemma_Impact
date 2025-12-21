#!/usr/bin/env python3
"""
Development Orchestrator
Coordinates between Dev Assistant, Aider, and Continue
"""

import subprocess
import json
import os
import asyncio
from pathlib import Path
from typing import List, Optional, Tuple
import sys

# Import our dev assistant
sys.path.append(str(Path(__file__).parent))
from dev_assistant import DevAssistant, DevelopmentTask, TaskType


class DevOrchestrator:
    """Orchestrates multiple development tools"""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.assistant = DevAssistant(project_path=project_path)
        self.aider_process = None
        self.continue_config = Path.home() / ".continue" / "config.yaml"
        
    def start_aider_session(self, model: str = "ollama/qwen2.5-coder:32b-instruct", files: List[str] = None) -> subprocess.Popen:
        """Start an Aider session in the background"""
        cmd = ["aider", "--model", model]
        if files:
            cmd.extend(files)
        
        self.aider_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.project_path,
            text=True
        )
        print(f"Started Aider with model {model}")
        return self.aider_process
    
    def send_to_aider(self, command: str) -> None:
        """Send a command to Aider"""
        if self.aider_process and self.aider_process.poll() is None:
            self.aider_process.stdin.write(command + "\n")
            self.aider_process.stdin.flush()
            print(f"Sent to Aider: {command}")
        else:
            print("Aider is not running")
    
    def parallel_workflow(self, main_task: str, support_tasks: List[DevelopmentTask]) -> None:
        """
        Execute a parallel workflow:
        - Main task goes to Aider
        - Support tasks go to Dev Assistant
        """
        print("\n🚀 Starting Parallel Workflow")
        print("=" * 50)
        print(f"Main Task (Aider): {main_task}")
        print(f"Support Tasks (Assistant): {len(support_tasks)} tasks")
        print("=" * 50)
        
        # Start assistant
        self.assistant.start()
        
        # Queue support tasks
        for task in support_tasks:
            self.assistant.add_task(task)
        
        # Start Aider with main task
        self.start_aider_session()
        self.send_to_aider(main_task)
        
        # Monitor progress
        import time
        while self.assistant.task_queue.qsize() > 0:
            print(f"\r⏳ Tasks remaining: {self.assistant.task_queue.qsize()}", end="")
            time.sleep(2)
        
        print("\n✅ All support tasks completed!")
        
        # Get results
        results = self.assistant.get_results()
        for r in results:
            print(f"\n📋 {r['task'].task_type.value}: {r['task'].description}")
            if r['status'] == 'completed':
                print(f"   ✓ {r['output'][:200]}...")
        
        self.assistant.stop()
        
        print("\n💡 Continue working with Aider for the main task")
        print("   or check the results above for insights")
    
    def smart_split(self, requirement: str) -> Tuple[str, List[DevelopmentTask]]:
        """
        Intelligently split a requirement into main and support tasks
        """
        print(f"\n🧠 Analyzing requirement: {requirement}")
        
        # Use LLM to analyze and split the task
        response = self.assistant.llm.complete(
            f"""Given this development requirement: {requirement}
            
            Split it into:
            1. A main implementation task (for Aider)
            2. Supporting tasks like: documentation, testing, code review, research
            
            Return as JSON with format:
            {{
                "main_task": "description",
                "support_tasks": [
                    {{"type": "documentation", "description": "...", "files": []}},
                    {{"type": "testing", "description": "...", "files": []}}
                ]
            }}"""
        )
        
        try:
            task_split = json.loads(response.text)
            
            # Convert to our task objects
            support_tasks = []
            for st in task_split.get("support_tasks", []):
                task_type = TaskType[st["type"].upper()]
                support_tasks.append(DevelopmentTask(
                    task_type=task_type,
                    description=st["description"],
                    files=st.get("files", [])
                ))
            
            return task_split.get("main_task", requirement), support_tasks
            
        except Exception as e:
            print(f"Error parsing task split: {e}")
            # Fallback to simple split
            return requirement, [
                DevelopmentTask(TaskType.DOCUMENTATION, f"Document changes for: {requirement}"),
                DevelopmentTask(TaskType.TESTING, f"Write tests for: {requirement}")
            ]
    
    def analyze_project(self):
        """Analyze the entire project and suggest improvements"""
        print("\n🔍 Analyzing project...")
        
        # Find all Python files
        py_files = list(self.project_path.glob("**/*.py"))[:10]  # Limit to 10 for demo
        
        tasks = []
        for file in py_files:
            tasks.append(DevelopmentTask(
                TaskType.CODE_REVIEW,
                f"Review {file.name}",
                files=[str(file)]
            ))
        
        self.assistant.start()
        for task in tasks:
            self.assistant.add_task(task)
        
        print(f"Queued {len(tasks)} files for review")
        
        # Wait for completion
        import time
        while self.assistant.task_queue.qsize() > 0:
            time.sleep(2)
        
        results = self.assistant.get_results()
        
        # Summarize findings
        issues = []
        for r in results:
            if r['status'] == 'completed' and r['output']:
                issues.append(r['output'])
        
        print(f"\n📊 Analysis Complete!")
        print(f"Found issues in {len(issues)} files")
        
        self.assistant.stop()
        return issues


def main():
    """Interactive orchestrator"""
    import argparse
    parser = argparse.ArgumentParser(description="Development Orchestrator")
    parser.add_argument("--project", default=".", help="Project path")
    parser.add_argument("--analyze", action="store_true", help="Analyze project")
    parser.add_argument("--parallel", help="Run parallel workflow with requirement")
    
    args = parser.parse_args()
    
    orchestrator = DevOrchestrator(project_path=args.project)
    
    if args.analyze:
        orchestrator.analyze_project()
    elif args.parallel:
        # Smart split the requirement
        main_task, support_tasks = orchestrator.smart_split(args.parallel)
        orchestrator.parallel_workflow(main_task, support_tasks)
    else:
        print("\n🎯 Dev Orchestrator - Interactive Mode")
        print("=" * 50)
        print("Commands:")
        print("  parallel <requirement> - Split and execute in parallel")
        print("  analyze               - Analyze entire project")
        print("  aider <command>       - Send command to Aider")
        print("  quit                  - Exit")
        print("=" * 50)
        
        while True:
            command = input("\n> ").strip()
            
            if command == "quit":
                break
            elif command == "analyze":
                orchestrator.analyze_project()
            elif command.startswith("parallel "):
                req = command[9:]
                main_task, support_tasks = orchestrator.smart_split(req)
                orchestrator.parallel_workflow(main_task, support_tasks)
            elif command.startswith("aider "):
                cmd = command[6:]
                if not orchestrator.aider_process:
                    orchestrator.start_aider_session()
                orchestrator.send_to_aider(cmd)
            else:
                print("Unknown command")


if __name__ == "__main__":
    main()