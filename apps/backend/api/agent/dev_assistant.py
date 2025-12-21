#!/usr/bin/env python3
"""
Software Developer Assistant Agent
Works alongside CN and Aider to handle parallel development tasks
"""

import asyncio
import subprocess
import json
import os
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import threading
import queue
from dataclasses import dataclass
from enum import Enum

# LlamaIndex for RAG capabilities
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, ServiceContext
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding

# CrewAI for agent orchestration
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

# AutoGen for advanced agent interactions
from autogen_agentchat import UserProxyAgent, AssistantAgent

# ChromaDB for memory/context storage
import chromadb


class TaskType(Enum):
    CODE_REVIEW = "code_review"
    BUG_FIX = "bug_fix"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    REFACTORING = "refactoring"
    RESEARCH = "research"
    FILE_ANALYSIS = "file_analysis"


@dataclass
class DevelopmentTask:
    task_type: TaskType
    description: str
    files: List[str] = None
    priority: int = 5
    context: Dict[str, Any] = None


class DevAssistant:
    """Main Developer Assistant Agent"""
    
    def __init__(self, project_path: str = ".", model: str = "qwen2.5-coder:32b-instruct"):
        self.project_path = Path(project_path)
        self.model = model
        self.task_queue = queue.Queue()
        self.results_queue = queue.Queue()
        self.running = False
        
        # Initialize Ollama LLM
        self.llm = Ollama(model=model, request_timeout=120.0)
        self.embeddings = OllamaEmbedding(model_name="nomic-embed-text")
        
        # Initialize ChromaDB for memory
        self.chroma_client = chromadb.Client()
        self.memory_collection = self.chroma_client.create_collection(
            name="dev_assistant_memory",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize knowledge base
        self.knowledge_base = None
        self.build_knowledge_base()
        
        # Initialize agents
        self.setup_agents()
        
    def build_knowledge_base(self) -> None:
        """Build a knowledge base from the project files"""
        print("Building knowledge base from project files...")
        
        # Find all code files
        code_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.go', '.rs']
        code_files = []
        
        for ext in code_extensions:
            code_files.extend(self.project_path.glob(f"**/*{ext}"))
        
        if code_files:
            # Create documents from code files
            documents = SimpleDirectoryReader(
                input_files=[str(f) for f in code_files[:50]]  # Limit to 50 files for speed
            ).load_data()
            
            # Create vector index
            self.knowledge_base = VectorStoreIndex.from_documents(
                documents,
                embed_model=self.embeddings
            )
            print(f"Knowledge base built with {len(documents)} documents")
        else:
            print("No code files found in project")
    
    def setup_agents(self) -> None:
        """Setup CrewAI agents for different tasks"""
        
        # Code Reviewer Agent
        self.code_reviewer = Agent(
            role='Senior Code Reviewer',
            goal='Review code for bugs, security issues, and best practices',
            backstory='You are an experienced developer who catches issues before they reach production',
            tools=[self.analyze_code_tool, self.suggest_improvements_tool],
            llm=self.llm,
            verbose=True
        )
        
        # Bug Fixer Agent
        self.bug_fixer = Agent(
            role='Bug Fix Specialist',
            goal='Identify and fix bugs in the codebase',
            backstory='You excel at debugging and finding root causes of issues',
            tools=[self.find_bug_tool, self.generate_fix_tool],
            llm=self.llm,
            verbose=True
        )
        
        # Documentation Agent
        self.doc_writer = Agent(
            role='Technical Documentation Writer',
            goal='Create clear and comprehensive documentation',
            backstory='You make complex code understandable through excellent documentation',
            tools=[self.generate_docs_tool],
            llm=self.llm,
            verbose=True
        )
        
        # Test Writer Agent
        self.test_writer = Agent(
            role='Test Engineer',
            goal='Write comprehensive test cases',
            backstory='You ensure code quality through thorough testing',
            tools=[self.generate_tests_tool],
            llm=self.llm,
            verbose=True
        )
    
    @tool("Analyze Code")
    def analyze_code_tool(self, file_path: str) -> str:
        """Analyze a code file for issues"""
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            # Use LLM to analyze
            response = self.llm.complete(
                f"Analyze this code for potential issues:\n\n{code[:2000]}\n\nProvide specific issues found."
            )
            return response.text
        except Exception as e:
            return f"Error analyzing {file_path}: {str(e)}"
    
    @tool("Suggest Improvements")
    def suggest_improvements_tool(self, code: str) -> str:
        """Suggest improvements for code"""
        response = self.llm.complete(
            f"Suggest specific improvements for this code:\n\n{code[:2000]}"
        )
        return response.text
    
    @tool("Find Bug")
    def find_bug_tool(self, error_message: str, context: str) -> str:
        """Find the root cause of a bug"""
        response = self.llm.complete(
            f"Given this error: {error_message}\n\nAnd this context: {context[:1000]}\n\nIdentify the root cause."
        )
        return response.text
    
    @tool("Generate Fix")
    def generate_fix_tool(self, bug_description: str, code: str) -> str:
        """Generate a fix for a bug"""
        response = self.llm.complete(
            f"Bug: {bug_description}\n\nCode:\n{code[:2000]}\n\nProvide the fixed code:"
        )
        return response.text
    
    @tool("Generate Documentation")
    def generate_docs_tool(self, code: str) -> str:
        """Generate documentation for code"""
        response = self.llm.complete(
            f"Generate comprehensive documentation for:\n\n{code[:2000]}"
        )
        return response.text
    
    @tool("Generate Tests")
    def generate_tests_tool(self, code: str, framework: str = "pytest") -> str:
        """Generate test cases for code"""
        response = self.llm.complete(
            f"Generate {framework} test cases for:\n\n{code[:2000]}"
        )
        return response.text
    
    def add_task(self, task: DevelopmentTask) -> None:
        """Add a task to the queue"""
        self.task_queue.put(task)
        print(f"Task added: {task.task_type.value} - {task.description}")
    
    def process_task(self, task: DevelopmentTask) -> Dict[str, Any]:
        """Process a single task"""
        print(f"\nProcessing: {task.task_type.value} - {task.description}")
        
        result = {
            "task": task,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "output": None
        }
        
        try:
            if task.task_type == TaskType.CODE_REVIEW:
                crew = Crew(
                    agents=[self.code_reviewer],
                    tasks=[
                        Task(
                            description=f"Review the following files: {task.files}",
                            agent=self.code_reviewer,
                            expected_output="Detailed code review with issues and suggestions"
                        )
                    ],
                    process=Process.sequential
                )
                result["output"] = crew.kickoff()
                
            elif task.task_type == TaskType.BUG_FIX:
                crew = Crew(
                    agents=[self.bug_fixer],
                    tasks=[
                        Task(
                            description=task.description,
                            agent=self.bug_fixer,
                            expected_output="Root cause analysis and fix"
                        )
                    ],
                    process=Process.sequential
                )
                result["output"] = crew.kickoff()
                
            elif task.task_type == TaskType.DOCUMENTATION:
                crew = Crew(
                    agents=[self.doc_writer],
                    tasks=[
                        Task(
                            description=f"Document {task.files}",
                            agent=self.doc_writer,
                            expected_output="Complete documentation"
                        )
                    ],
                    process=Process.sequential
                )
                result["output"] = crew.kickoff()
                
            elif task.task_type == TaskType.TESTING:
                crew = Crew(
                    agents=[self.test_writer],
                    tasks=[
                        Task(
                            description=f"Write tests for {task.files}",
                            agent=self.test_writer,
                            expected_output="Test cases"
                        )
                    ],
                    process=Process.sequential
                )
                result["output"] = crew.kickoff()
                
            elif task.task_type == TaskType.RESEARCH:
                # Use knowledge base for research
                if self.knowledge_base:
                    query_engine = self.knowledge_base.as_query_engine()
                    response = query_engine.query(task.description)
                    result["output"] = str(response)
                else:
                    result["output"] = "Knowledge base not available"
                    
            # Store result in memory
            self.memory_collection.add(
                documents=[json.dumps(result)],
                metadatas=[{"task_type": task.task_type.value}],
                ids=[f"task_{datetime.now().timestamp()}"]
            )
            
        except Exception as e:
            result["status"] = "error"
            result["output"] = str(e)
            print(f"Error processing task: {e}")
        
        return result
    
    def worker_thread(self) -> None:
        """Worker thread to process tasks"""
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                result = self.process_task(task)
                self.results_queue.put(result)
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")
    
    def start(self) -> None:
        """Start the assistant"""
        self.running = True
        self.worker = threading.Thread(target=self.worker_thread)
        self.worker.start()
        print("Dev Assistant started! Ready to help with your coding tasks.")
    
    def stop(self) -> None:
        """Stop the assistant"""
        self.running = False
        if hasattr(self, 'worker'):
            self.worker.join()
        print("Dev Assistant stopped.")
    
    def get_results(self) -> List[Dict[str, Any]]:
        """Get completed task results"""
        results = []
        while not self.results_queue.empty():
            results.append(self.results_queue.get())
        return results
    
    def interactive_mode(self) -> None:
        """Run in interactive mode"""
        print("\n🤖 Dev Assistant Interactive Mode")
        print("=" * 50)
        print("Commands:")
        print("  review <file>    - Review a code file")
        print("  fix <desc>       - Fix a bug")
        print("  doc <file>       - Generate documentation")
        print("  test <file>      - Generate tests")
        print("  research <query> - Research in codebase")
        print("  status           - Check task status")
        print("  results          - Get completed results")
        print("  quit             - Exit")
        print("=" * 50)
        
        self.start()
        
        try:
            while True:
                command = input("\n> ").strip()
                
                if command == "quit":
                    break
                elif command == "status":
                    print(f"Tasks in queue: {self.task_queue.qsize()}")
                    print(f"Completed results: {self.results_queue.qsize()}")
                elif command == "results":
                    results = self.get_results()
                    for r in results:
                        print(f"\nTask: {r['task'].description}")
                        print(f"Status: {r['status']}")
                        if r['output']:
                            print(f"Output: {r['output'][:500]}...")
                elif command.startswith("review "):
                    file = command[7:]
                    self.add_task(DevelopmentTask(
                        TaskType.CODE_REVIEW,
                        f"Review {file}",
                        files=[file]
                    ))
                elif command.startswith("fix "):
                    desc = command[4:]
                    self.add_task(DevelopmentTask(
                        TaskType.BUG_FIX,
                        desc
                    ))
                elif command.startswith("doc "):
                    file = command[4:]
                    self.add_task(DevelopmentTask(
                        TaskType.DOCUMENTATION,
                        f"Document {file}",
                        files=[file]
                    ))
                elif command.startswith("test "):
                    file = command[5:]
                    self.add_task(DevelopmentTask(
                        TaskType.TESTING,
                        f"Write tests for {file}",
                        files=[file]
                    ))
                elif command.startswith("research "):
                    query = command[9:]
                    self.add_task(DevelopmentTask(
                        TaskType.RESEARCH,
                        query
                    ))
                else:
                    print("Unknown command. Type 'quit' to exit.")
        finally:
            self.stop()


# CLI integration
def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Software Developer Assistant")
    parser.add_argument("--project", default=".", help="Project path")
    parser.add_argument("--model", default="qwen2.5-coder:32b-instruct", help="Ollama model to use")
    parser.add_argument("--task", choices=["review", "fix", "doc", "test", "research"], help="Task type")
    parser.add_argument("--file", help="File to process")
    parser.add_argument("--desc", help="Task description")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    
    args = parser.parse_args()
    
    assistant = DevAssistant(project_path=args.project, model=args.model)
    
    if args.interactive:
        assistant.interactive_mode()
    elif args.task:
        assistant.start()
        
        if args.task == "review" and args.file:
            assistant.add_task(DevelopmentTask(
                TaskType.CODE_REVIEW,
                f"Review {args.file}",
                files=[args.file]
            ))
        elif args.task == "fix" and args.desc:
            assistant.add_task(DevelopmentTask(
                TaskType.BUG_FIX,
                args.desc
            ))
        elif args.task == "doc" and args.file:
            assistant.add_task(DevelopmentTask(
                TaskType.DOCUMENTATION,
                f"Document {args.file}",
                files=[args.file]
            ))
        elif args.task == "test" and args.file:
            assistant.add_task(DevelopmentTask(
                TaskType.TESTING,
                f"Write tests for {args.file}",
                files=[args.file]
            ))
        elif args.task == "research" and args.desc:
            assistant.add_task(DevelopmentTask(
                TaskType.RESEARCH,
                args.desc
            ))
        
        # Wait for task to complete
        import time
        time.sleep(5)
        while assistant.task_queue.qsize() > 0:
            time.sleep(1)
        
        # Get results
        results = assistant.get_results()
        for r in results:
            print(f"\nResult: {r['output']}")
        
        assistant.stop()
    else:
        print("Use --interactive mode or specify --task with required arguments")


if __name__ == "__main__":
    main()