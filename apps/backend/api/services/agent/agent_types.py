#!/usr/bin/env python3
"""
Agent Type Definitions for Multi-Agent System

Defines specialized agent types with different capabilities and focuses:
- CodeAgent: Code reading, writing, refactoring
- TestAgent: Test creation and execution
- DebugAgent: Bug finding and fixing
- ReviewAgent: Code review and quality checks
- ResearchAgent: Documentation and research tasks
"""

from dataclasses import dataclass, field
from enum import Enum


class AgentRole(Enum):
    """Available agent roles in the system"""

    CODE = "code"  # Code implementation
    TEST = "test"  # Testing and validation
    DEBUG = "debug"  # Debugging and troubleshooting
    REVIEW = "review"  # Code review and quality
    RESEARCH = "research"  # Documentation and research
    COORDINATOR = "coordinator"  # Task coordination
    SECURITY = "security"  # Security analysis and hardening
    PERFORMANCE = "performance"  # Performance optimization
    ARCHITECTURE = "architecture"  # System design and architecture


@dataclass
class AgentCapability:
    """Represents a capability an agent can perform"""

    name: str
    description: str
    required_tools: list[str]
    confidence_level: float = 1.0  # 0.0 to 1.0


@dataclass
class AgentProfile:
    """Profile defining an agent's characteristics"""

    role: AgentRole
    name: str
    description: str
    capabilities: list[AgentCapability]
    available_tools: set[str]
    specializations: list[str] = field(default_factory=list)
    max_iterations: int = 10

    def can_handle_task(self, task_type: str, required_tools: list[str]) -> bool:
        """Check if agent can handle a specific task"""
        # Check if all required tools are available
        if not all(tool in self.available_tools for tool in required_tools):
            return False

        # Check if any capability matches the task type
        return any(task_type.lower() in cap.name.lower() for cap in self.capabilities)

    def get_capability_confidence(self, task_type: str) -> float:
        """Get confidence level for handling a task type"""
        for cap in self.capabilities:
            if task_type.lower() in cap.name.lower():
                return cap.confidence_level
        return 0.0


# ===== Predefined Agent Profiles =====

CODE_AGENT_PROFILE = AgentProfile(
    role=AgentRole.CODE,
    name="CodeAgent",
    description="Specialized in writing, editing, and refactoring code",
    capabilities=[
        AgentCapability(
            name="implement_feature",
            description="Implement new features and functionality",
            required_tools=["read_file", "write_file", "edit_file"],
            confidence_level=0.95,
        ),
        AgentCapability(
            name="refactor_code",
            description="Refactor and improve existing code",
            required_tools=["read_file", "edit_file", "grep_code"],
            confidence_level=0.90,
        ),
        AgentCapability(
            name="fix_syntax",
            description="Fix syntax errors and basic issues",
            required_tools=["read_file", "edit_file"],
            confidence_level=0.85,
        ),
    ],
    available_tools={
        "read_file",
        "write_file",
        "edit_file",
        "list_files",
        "grep_code",
        "run_command",
    },
    specializations=["Python", "JavaScript", "TypeScript", "Go"],
)

TEST_AGENT_PROFILE = AgentProfile(
    role=AgentRole.TEST,
    name="TestAgent",
    description="Specialized in writing and running tests",
    capabilities=[
        AgentCapability(
            name="write_tests",
            description="Write unit and integration tests",
            required_tools=["read_file", "write_file"],
            confidence_level=0.90,
        ),
        AgentCapability(
            name="run_tests",
            description="Execute test suites and analyze results",
            required_tools=["run_tests", "run_command"],
            confidence_level=0.95,
        ),
        AgentCapability(
            name="analyze_coverage",
            description="Analyze test coverage and identify gaps",
            required_tools=["run_command", "read_file"],
            confidence_level=0.80,
        ),
    ],
    available_tools={
        "read_file",
        "write_file",
        "edit_file",
        "run_tests",
        "run_command",
        "grep_code",
    },
    specializations=["pytest", "jest", "mocha", "go test"],
)

DEBUG_AGENT_PROFILE = AgentProfile(
    role=AgentRole.DEBUG,
    name="DebugAgent",
    description="Specialized in finding and fixing bugs",
    capabilities=[
        AgentCapability(
            name="analyze_errors",
            description="Analyze error messages and stack traces",
            required_tools=["read_file", "grep_code"],
            confidence_level=0.90,
        ),
        AgentCapability(
            name="fix_bugs",
            description="Fix identified bugs and issues",
            required_tools=["read_file", "edit_file", "run_tests"],
            confidence_level=0.85,
        ),
        AgentCapability(
            name="trace_execution",
            description="Trace code execution to find issues",
            required_tools=["read_file", "grep_code", "run_command"],
            confidence_level=0.80,
        ),
    ],
    available_tools={
        "read_file",
        "edit_file",
        "grep_code",
        "run_command",
        "run_tests",
        "list_files",
    },
    specializations=["debugging", "error_analysis", "root_cause"],
)

REVIEW_AGENT_PROFILE = AgentProfile(
    role=AgentRole.REVIEW,
    name="ReviewAgent",
    description="Specialized in code review and quality assurance",
    capabilities=[
        AgentCapability(
            name="review_code",
            description="Review code for quality and best practices",
            required_tools=["read_file", "grep_code"],
            confidence_level=0.90,
        ),
        AgentCapability(
            name="check_style",
            description="Check code style and formatting",
            required_tools=["read_file", "run_command"],
            confidence_level=0.85,
        ),
        AgentCapability(
            name="security_audit",
            description="Identify security vulnerabilities",
            required_tools=["read_file", "grep_code"],
            confidence_level=0.80,
        ),
    ],
    available_tools={"read_file", "grep_code", "run_command", "list_files"},
    specializations=["code_quality", "security", "best_practices"],
)

RESEARCH_AGENT_PROFILE = AgentProfile(
    role=AgentRole.RESEARCH,
    name="ResearchAgent",
    description="Specialized in research and documentation",
    capabilities=[
        AgentCapability(
            name="analyze_codebase",
            description="Analyze and understand codebase structure",
            required_tools=["read_file", "list_files", "grep_code"],
            confidence_level=0.90,
        ),
        AgentCapability(
            name="write_documentation",
            description="Write documentation and guides",
            required_tools=["read_file", "write_file"],
            confidence_level=0.85,
        ),
        AgentCapability(
            name="find_examples",
            description="Find code examples and patterns",
            required_tools=["grep_code", "read_file"],
            confidence_level=0.80,
        ),
    ],
    available_tools={"read_file", "write_file", "list_files", "grep_code"},
    specializations=["documentation", "analysis", "research"],
)

SECURITY_AGENT_PROFILE = AgentProfile(
    role=AgentRole.SECURITY,
    name="SecurityAgent",
    description="Specialized in security analysis, vulnerability detection, and hardening",
    capabilities=[
        AgentCapability(
            name="vulnerability_scan",
            description="Scan code for security vulnerabilities (OWASP Top 10, CWE)",
            required_tools=["read_file", "grep_code", "list_files"],
            confidence_level=0.95,
        ),
        AgentCapability(
            name="security_audit",
            description="Comprehensive security audit of codebase",
            required_tools=["read_file", "grep_code", "run_command"],
            confidence_level=0.90,
        ),
        AgentCapability(
            name="fix_security_issues",
            description="Fix identified security vulnerabilities",
            required_tools=["read_file", "edit_file", "run_tests"],
            confidence_level=0.85,
        ),
        AgentCapability(
            name="authentication_review",
            description="Review authentication and authorization implementations",
            required_tools=["read_file", "grep_code"],
            confidence_level=0.90,
        ),
        AgentCapability(
            name="secrets_detection",
            description="Detect hardcoded secrets and credentials",
            required_tools=["grep_code", "read_file"],
            confidence_level=0.95,
        ),
    ],
    available_tools={
        "read_file",
        "edit_file",
        "grep_code",
        "run_command",
        "list_files",
        "run_tests",
    },
    specializations=[
        "vulnerability_detection",
        "security_hardening",
        "authentication",
        "injection_prevention",
        "cryptography",
    ],
    max_iterations=15,  # Security scans may need more iterations
)

PERFORMANCE_AGENT_PROFILE = AgentProfile(
    role=AgentRole.PERFORMANCE,
    name="PerformanceAgent",
    description="Specialized in performance optimization and profiling",
    capabilities=[
        AgentCapability(
            name="profile_code",
            description="Profile code to identify performance bottlenecks",
            required_tools=["read_file", "run_command"],
            confidence_level=0.90,
        ),
        AgentCapability(
            name="optimize_performance",
            description="Optimize slow code paths and algorithms",
            required_tools=["read_file", "edit_file", "run_tests"],
            confidence_level=0.85,
        ),
        AgentCapability(
            name="identify_bottlenecks",
            description="Identify CPU, memory, and I/O bottlenecks",
            required_tools=["read_file", "run_command", "grep_code"],
            confidence_level=0.90,
        ),
        AgentCapability(
            name="memory_analysis",
            description="Analyze memory usage and detect leaks",
            required_tools=["run_command", "read_file"],
            confidence_level=0.85,
        ),
        AgentCapability(
            name="query_optimization",
            description="Optimize database queries and N+1 issues",
            required_tools=["read_file", "grep_code", "edit_file"],
            confidence_level=0.80,
        ),
    ],
    available_tools={
        "read_file",
        "edit_file",
        "grep_code",
        "run_command",
        "list_files",
        "run_tests",
    },
    specializations=[
        "profiling",
        "algorithm_optimization",
        "caching",
        "database_optimization",
        "async_patterns",
    ],
)

ARCHITECTURE_AGENT_PROFILE = AgentProfile(
    role=AgentRole.ARCHITECTURE,
    name="ArchitectureAgent",
    description="Specialized in system design, architecture patterns, and structural analysis",
    capabilities=[
        AgentCapability(
            name="design_system",
            description="Design system architecture and component structure",
            required_tools=["read_file", "list_files", "grep_code"],
            confidence_level=0.90,
        ),
        AgentCapability(
            name="review_architecture",
            description="Review and critique architectural decisions",
            required_tools=["read_file", "grep_code", "list_files"],
            confidence_level=0.95,
        ),
        AgentCapability(
            name="suggest_patterns",
            description="Suggest appropriate design patterns for problems",
            required_tools=["read_file", "grep_code"],
            confidence_level=0.85,
        ),
        AgentCapability(
            name="dependency_analysis",
            description="Analyze dependencies and coupling between modules",
            required_tools=["read_file", "grep_code", "list_files"],
            confidence_level=0.90,
        ),
        AgentCapability(
            name="refactor_structure",
            description="Refactor code structure to improve architecture",
            required_tools=["read_file", "edit_file", "write_file", "run_tests"],
            confidence_level=0.80,
        ),
    ],
    available_tools={
        "read_file",
        "write_file",
        "edit_file",
        "list_files",
        "grep_code",
        "run_tests",
    },
    specializations=[
        "microservices",
        "monolith",
        "layered_architecture",
        "domain_driven_design",
        "event_sourcing",
        "cqrs",
    ],
    max_iterations=12,  # Architecture tasks may need exploration
)


# Agent registry
AGENT_PROFILES: dict[AgentRole, AgentProfile] = {
    AgentRole.CODE: CODE_AGENT_PROFILE,
    AgentRole.TEST: TEST_AGENT_PROFILE,
    AgentRole.DEBUG: DEBUG_AGENT_PROFILE,
    AgentRole.REVIEW: REVIEW_AGENT_PROFILE,
    AgentRole.RESEARCH: RESEARCH_AGENT_PROFILE,
    AgentRole.SECURITY: SECURITY_AGENT_PROFILE,
    AgentRole.PERFORMANCE: PERFORMANCE_AGENT_PROFILE,
    AgentRole.ARCHITECTURE: ARCHITECTURE_AGENT_PROFILE,
}


def get_agent_profile(role: AgentRole) -> AgentProfile:
    """Get agent profile by role"""
    return AGENT_PROFILES.get(role)


def select_best_agent(task_type: str, required_tools: list[str]) -> AgentProfile | None:
    """
    Select the best agent for a given task

    Args:
        task_type: Type of task to perform
        required_tools: Tools required for the task

    Returns:
        Best matching agent profile or None
    """
    best_agent = None
    best_confidence = 0.0

    for profile in AGENT_PROFILES.values():
        if profile.can_handle_task(task_type, required_tools):
            confidence = profile.get_capability_confidence(task_type)
            if confidence > best_confidence:
                best_confidence = confidence
                best_agent = profile

    return best_agent


def get_collaborative_agents(task_description: str) -> list[AgentProfile]:
    """
    Get agents that should collaborate on a task

    Args:
        task_description: Description of the task

    Returns:
        List of agent profiles that should work together
    """
    agents = []
    task_lower = task_description.lower()

    # Security tasks - highest priority, always include SecurityAgent
    if any(
        word in task_lower
        for word in [
            "security",
            "vulnerability",
            "secure",
            "auth",
            "injection",
            "xss",
            "csrf",
            "owasp",
            "cve",
            "secrets",
            "credentials",
            "encryption",
            "sanitize",
        ]
    ):
        agents.append(SECURITY_AGENT_PROFILE)
        if any(word in task_lower for word in ["fix", "patch", "remediate"]):
            agents.append(CODE_AGENT_PROFILE)
        agents.append(TEST_AGENT_PROFILE)  # Always verify security changes

    # Performance tasks
    elif any(
        word in task_lower
        for word in [
            "performance",
            "slow",
            "optimize",
            "speed",
            "profil",
            "bottleneck",
            "memory",
            "cache",
            "latency",
            "throughput",
            "n+1",
            "query optimization",
        ]
    ):
        agents.append(PERFORMANCE_AGENT_PROFILE)
        if any(word in task_lower for word in ["fix", "improve", "optimize"]):
            agents.append(CODE_AGENT_PROFILE)
        agents.append(TEST_AGENT_PROFILE)  # Verify optimizations don't break things

    # Architecture tasks
    elif any(
        word in task_lower
        for word in [
            "architecture",
            "design",
            "structure",
            "pattern",
            "refactor",
            "modular",
            "decouple",
            "dependency",
            "microservice",
            "monolith",
            "layer",
            "separation of concerns",
        ]
    ):
        agents.append(ARCHITECTURE_AGENT_PROFILE)
        if any(word in task_lower for word in ["implement", "refactor", "migrate"]):
            agents.append(CODE_AGENT_PROFILE)
        agents.append(REVIEW_AGENT_PROFILE)  # Review architectural changes

    # Code implementation tasks
    elif any(word in task_lower for word in ["implement", "add", "create", "build"]):
        agents.append(CODE_AGENT_PROFILE)
        agents.append(TEST_AGENT_PROFILE)  # Always add tests

    # Bug fixing tasks
    elif any(word in task_lower for word in ["fix", "bug", "error", "broken"]):
        agents.append(DEBUG_AGENT_PROFILE)
        agents.append(TEST_AGENT_PROFILE)  # Verify fixes

    # Refactoring tasks (without architecture keywords)
    elif any(word in task_lower for word in ["refactor", "improve", "clean"]):
        agents.append(CODE_AGENT_PROFILE)
        agents.append(REVIEW_AGENT_PROFILE)  # Review quality

    # Documentation tasks
    elif any(word in task_lower for word in ["document", "explain", "analyze"]):
        agents.append(RESEARCH_AGENT_PROFILE)

    # Testing tasks
    elif any(word in task_lower for word in ["test", "coverage", "validation"]):
        agents.append(TEST_AGENT_PROFILE)

    # Code review tasks
    elif any(word in task_lower for word in ["review", "audit", "check", "quality"]):
        agents.append(REVIEW_AGENT_PROFILE)
        # Add specialized agents based on review focus
        if "security" in task_lower:
            agents.append(SECURITY_AGENT_PROFILE)
        if "performance" in task_lower or "optimization" in task_lower:
            agents.append(PERFORMANCE_AGENT_PROFILE)

    # Default: code + test
    else:
        agents.append(CODE_AGENT_PROFILE)

    return agents


def get_agent_for_capability(capability_name: str) -> AgentProfile | None:
    """
    Find the best agent for a specific capability.

    Args:
        capability_name: Name of the capability needed

    Returns:
        Best matching agent profile or None
    """
    best_agent = None
    best_confidence = 0.0

    for profile in AGENT_PROFILES.values():
        for cap in profile.capabilities:
            if capability_name.lower() in cap.name.lower():
                if cap.confidence_level > best_confidence:
                    best_confidence = cap.confidence_level
                    best_agent = profile

    return best_agent
