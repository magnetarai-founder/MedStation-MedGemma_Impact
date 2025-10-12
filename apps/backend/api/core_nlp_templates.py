#!/usr/bin/env python3
"""
Core NLP Template Library for Jarvis
Similar to BigQuery's 256 SQL templates, provides natural language patterns
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import re
import json


class IntentCategory(Enum):
    """Categories of user intent"""
    CODE_GENERATION = "code_generation"
    CODE_MODIFICATION = "code_modification"
    DEBUGGING = "debugging"
    RESEARCH = "research"
    SYSTEM_OPERATION = "system_operation"
    DATA_ANALYSIS = "data_analysis"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    LEARNING = "learning"


@dataclass
class NLPTemplate:
    """Natural Language Processing Template"""
    id: str
    name: str
    category: IntentCategory
    patterns: List[str]  # Regex patterns to match
    keywords: List[str]  # Key words that signal this intent
    entities: List[str]  # Entities to extract (file, function, variable, etc.)
    response_template: str
    tool_suggestions: List[str]
    confidence_threshold: float = 0.7
    examples: List[str] = None
    
    def match(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if text matches this template"""
        text_lower = text.lower()
        
        # Check patterns
        for pattern in self.patterns:
            match = re.search(pattern, text_lower)
            if match:
                return True, {"pattern": pattern, "groups": match.groups()}
        
        # Check keywords (weighted)
        keyword_matches = sum(1 for kw in self.keywords if kw in text_lower)
        if keyword_matches >= len(self.keywords) * 0.5:
            return True, {"keywords": keyword_matches}
        
        return False, {}


class CoreNLPLibrary:
    """Core library of NLP templates - Jarvis's language understanding"""
    
    def __init__(self):
        self.templates = self._initialize_templates()
        self.intent_cache = {}
        
    def _initialize_templates(self) -> List[NLPTemplate]:
        """Initialize 256 NLP templates like BigQuery SQL templates"""
        templates = []
        
        # CODE GENERATION TEMPLATES (001-030)
        templates.extend([
            NLPTemplate(
                id="CG_001",
                name="Create Function",
                category=IntentCategory.CODE_GENERATION,
                patterns=[
                    r"(create|write|implement|build)\s+(?:a\s+)?function\s+(?:to\s+|that\s+|for\s+)?(.+)",
                    r"function\s+(?:to\s+|that\s+)(.+)",
                    r"(?:can you\s+)?(?:please\s+)?write\s+(?:me\s+)?(?:a\s+)?function"
                ],
                keywords=["function", "create", "write", "implement"],
                entities=["function_name", "purpose", "parameters", "return_type"],
                response_template="Creating function",
                tool_suggestions=["aider", "ollama:qwen2.5-coder"],
                examples=[
                    "create a function to sort a list",
                    "write function that validates email",
                    "implement a function for calculating fibonacci"
                ]
            ),
            
            NLPTemplate(
                id="CG_002", 
                name="Create Class",
                category=IntentCategory.CODE_GENERATION,
                patterns=[
                    r"(create|write|implement|build)\s+(?:a\s+)?class\s+(?:for\s+|that\s+)?(.+)",
                    r"class\s+(?:to\s+|that\s+|for\s+)(.+)",
                    r"(?:i need\s+)?(?:a\s+)?class\s+(?:that\s+)?(.+)"
                ],
                keywords=["class", "create", "object", "implement"],
                entities=["class_name", "purpose", "methods", "attributes"],
                response_template="Creating class for {purpose}",
                tool_suggestions=["aider", "ollama:qwen2.5-coder"],
                examples=[
                    "create a class for user management",
                    "write class that handles database connections",
                    "I need a class to represent a car"
                ]
            ),
            
            NLPTemplate(
                id="CG_003",
                name="Create API Endpoint",
                category=IntentCategory.CODE_GENERATION,
                patterns=[
                    r"(create|add|implement)\s+(?:an?\s+)?(?:api\s+)?endpoint\s+(?:for\s+|to\s+)?(.+)",
                    r"(?:rest\s+)?api\s+(?:endpoint\s+)?(?:for\s+|to\s+)(.+)",
                    r"add\s+(?:a\s+)?route\s+(?:for\s+|to\s+)?(.+)"
                ],
                keywords=["api", "endpoint", "route", "rest", "http"],
                entities=["endpoint_path", "method", "purpose", "parameters"],
                response_template="Creating API endpoint for {purpose}",
                tool_suggestions=["aider", "workflow:code_gen"],
                examples=[
                    "create an API endpoint for user authentication",
                    "add endpoint to get user profile",
                    "implement REST API for products"
                ]
            ),
            
            NLPTemplate(
                id="CG_004",
                name="Generate Test",
                category=IntentCategory.TESTING,
                patterns=[
                    r"(write|create|add|generate)\s+(?:a\s+)?test(?:s)?\s+(?:for\s+)?(.+)",
                    r"test\s+(?:for\s+|that\s+)?(.+)",
                    r"(?:unit\s+)?test\s+(.+)"
                ],
                keywords=["test", "testing", "unit", "coverage"],
                entities=["test_target", "test_type", "assertions"],
                response_template="Generating tests for {test_target}",
                tool_suggestions=["aider", "pytest", "workflow:test_gen"],
                examples=[
                    "write tests for the auth module",
                    "create unit tests for user class",
                    "add test coverage for API endpoints"
                ]
            ),
            
            NLPTemplate(
                id="CG_005",
                name="Create Script",
                category=IntentCategory.CODE_GENERATION,
                patterns=[
                    r"(create|write|make)\s+(?:a\s+)?script\s+(?:to\s+|that\s+|for\s+)?(.+)",
                    r"(?:python\s+)?script\s+(?:to\s+|for\s+)?(.+)",
                    r"automation\s+(?:script\s+)?(?:for\s+)?(.+)"
                ],
                keywords=["script", "automation", "automate"],
                entities=["script_purpose", "script_type", "inputs", "outputs"],
                response_template="Creating script to {script_purpose}",
                tool_suggestions=["aider", "bash", "python"],
                examples=[
                    "create a script to backup database",
                    "write automation script for deployment",
                    "make a script that processes CSV files"
                ]
            ),
        ])
        
        # CODE MODIFICATION TEMPLATES (031-060)
        templates.extend([
            NLPTemplate(
                id="CM_001",
                name="Refactor Code",
                category=IntentCategory.CODE_MODIFICATION,
                patterns=[
                    r"refactor\s+(?:the\s+)?(.+)",
                    r"(clean up|cleanup|improve)\s+(?:the\s+)?(?:code\s+)?(?:in\s+)?(.+)",
                    r"make\s+(.+)\s+(?:more\s+)?(?:clean|readable|efficient)"
                ],
                keywords=["refactor", "clean", "improve", "optimize"],
                entities=["target_code", "improvement_type"],
                response_template="Refactoring {target_code}",
                tool_suggestions=["aider", "ollama:qwen2.5-coder"],
                examples=[
                    "refactor the authentication module",
                    "clean up code in main.py",
                    "improve the database queries"
                ]
            ),
            
            NLPTemplate(
                id="CM_002",
                name="Add Feature",
                category=IntentCategory.CODE_MODIFICATION,
                patterns=[
                    r"add\s+(?:a\s+)?(?:feature\s+)?(?:to\s+|for\s+)?(.+)",
                    r"implement\s+(.+)\s+feature",
                    r"(?:can you\s+)?add\s+(.+)\s+(?:functionality|capability)"
                ],
                keywords=["add", "feature", "implement", "functionality"],
                entities=["feature_name", "target_location", "requirements"],
                response_template="Adding {feature_name} feature",
                tool_suggestions=["aider", "workflow:feature_add"],
                examples=[
                    "add dark mode to the app",
                    "implement search feature",
                    "add export functionality to reports"
                ]
            ),
            
            NLPTemplate(
                id="CM_003",
                name="Update Dependencies",
                category=IntentCategory.CODE_MODIFICATION,
                patterns=[
                    r"update\s+(?:the\s+)?(?:dependencies|packages|libs|libraries)",
                    r"upgrade\s+(.+)\s+(?:package|dependency|library)",
                    r"(?:npm|pip|cargo)\s+update"
                ],
                keywords=["update", "upgrade", "dependencies", "packages"],
                entities=["package_manager", "packages"],
                response_template="Updating dependencies",
                tool_suggestions=["bash", "npm", "pip"],
                examples=[
                    "update all dependencies",
                    "upgrade React to latest version",
                    "npm update packages"
                ]
            ),
        ])
        
        # DEBUGGING TEMPLATES (061-090)
        templates.extend([
            NLPTemplate(
                id="DB_001",
                name="Fix Bug",
                category=IntentCategory.DEBUGGING,
                patterns=[
                    r"fix\s+(?:the\s+)?(?:bug|issue|problem|error)(?:\s+in\s+|with\s+)?(.+)?",
                    r"(?:there\'s\s+)?(?:a\s+)?bug(?:\s+in\s+)?(.+)?",
                    r"(.+)\s+(?:is\s+)?(?:not\s+working|broken|failing)",
                    r"fix\s+(?:the\s+)?bug"
                ],
                keywords=["fix", "bug", "error", "issue", "broken"],
                entities=["bug_location", "error_message", "symptoms"],
                response_template="Fixing bug",
                tool_suggestions=["aider", "workflow:bug_fix", "debugger"],
                examples=[
                    "fix the bug in authentication",
                    "fix the bug",
                    "there's a bug in the payment module",
                    "the login form is not working"
                ]
            ),
            
            NLPTemplate(
                id="DB_002",
                name="Debug Code",
                category=IntentCategory.DEBUGGING,
                patterns=[
                    r"debug\s+(?:the\s+)?(.+)",
                    r"(?:help me\s+)?(?:find|locate)\s+(?:the\s+)?(?:issue|problem)\s+(?:in\s+)?(.+)",
                    r"why\s+(?:is\s+)?(.+)\s+(?:not\s+working|failing)"
                ],
                keywords=["debug", "find", "issue", "why", "failing"],
                entities=["debug_target", "symptoms", "error_output"],
                response_template="Debugging {debug_target}",
                tool_suggestions=["debugger", "print", "logging"],
                examples=[
                    "debug the API endpoint",
                    "help me find the issue in the loop",
                    "why is the function returning null"
                ]
            ),
            
            NLPTemplate(
                id="DB_003",
                name="Analyze Error",
                category=IntentCategory.DEBUGGING,
                patterns=[
                    r"(?:analyze|explain)\s+(?:this\s+)?error:?\s*(.+)",
                    r"what\s+does\s+(?:this\s+)?error\s+mean:?\s*(.+)",
                    r"(?:i\'m getting|got)\s+(?:an?\s+)?error:?\s*(.+)"
                ],
                keywords=["error", "analyze", "explain", "mean"],
                entities=["error_message", "stack_trace", "context"],
                response_template="Analyzing error: {error_message}",
                tool_suggestions=["ollama", "error_lookup", "documentation"],
                examples=[
                    "analyze this error: TypeError: cannot read property",
                    "what does this error mean: ECONNREFUSED",
                    "I'm getting error 404"
                ]
            ),
        ])
        
        # RESEARCH TEMPLATES (091-120)
        templates.extend([
            NLPTemplate(
                id="RS_001",
                name="Search Codebase",
                category=IntentCategory.RESEARCH,
                patterns=[
                    r"(?:search|find|look)\s+(?:for\s+)?(.+?)(?:\s+in\s+)?(?:the\s+)?(?:code|codebase|project)?",
                    r"where\s+(?:is|are)\s+(.+)\s+(?:defined|implemented|used)",
                    r"(?:show me|find)\s+(?:all\s+)?(?:uses|usages|references)\s+(?:of\s+)?(.+)",
                    r"search\s+for\s+all\s+(.+)"
                ],
                keywords=["search", "find", "where", "locate", "references", "all"],
                entities=["search_term", "search_scope", "file_pattern"],
                response_template="Searching for {search_term}",
                tool_suggestions=["grep", "ripgrep", "workflow:research"],
                examples=[
                    "search for database connections in the code",
                    "search for all database connections",
                    "where is the User class defined",
                    "find all uses of the authenticate function"
                ]
            ),
            
            NLPTemplate(
                id="RS_002",
                name="Explain Code",
                category=IntentCategory.RESEARCH,
                patterns=[
                    r"explain\s+(?:this\s+)?(?:code|function|class|method):?\s*(.+)?",
                    r"what\s+does\s+(?:this\s+)?(.+)\s+do",
                    r"how\s+does\s+(.+)\s+work"
                ],
                keywords=["explain", "what", "how", "understand"],
                entities=["code_target", "context"],
                response_template="Explaining {code_target}",
                tool_suggestions=["ollama", "code_analysis"],
                examples=[
                    "explain this function",
                    "what does the auth middleware do",
                    "how does the caching system work"
                ]
            ),
            
            NLPTemplate(
                id="RS_003",
                name="Analyze Architecture",
                category=IntentCategory.RESEARCH,
                patterns=[
                    r"(?:analyze|show|explain)\s+(?:the\s+)?(?:architecture|structure)\s+(?:of\s+)?(.+)?",
                    r"how\s+is\s+(?:the\s+)?(.+)\s+(?:structured|organized|architected)",
                    r"(?:what\'s|what is)\s+the\s+(?:project\s+)?structure"
                ],
                keywords=["architecture", "structure", "organization", "design"],
                entities=["target_scope", "detail_level"],
                response_template="Analyzing architecture",
                tool_suggestions=["tree", "workflow:architecture_analysis"],
                examples=[
                    "analyze the project architecture",
                    "how is the backend structured",
                    "show me the folder structure"
                ]
            ),
        ])
        
        # SYSTEM OPERATION TEMPLATES (121-150)
        templates.extend([
            NLPTemplate(
                id="SO_001",
                name="Run Command",
                category=IntentCategory.SYSTEM_OPERATION,
                patterns=[
                    r"run\s+(.+)",
                    r"execute\s+(.+)",
                    r"(?:can you\s+)?(?:please\s+)?run\s+(?:the\s+)?command:?\s*(.+)"
                ],
                keywords=["run", "execute", "command"],
                entities=["command", "arguments", "working_directory"],
                response_template="Running: {command}",
                tool_suggestions=["bash", "system"],
                examples=[
                    "run npm install",
                    "execute the build script",
                    "run python main.py"
                ]
            ),
            
            NLPTemplate(
                id="SO_002",
                name="Git Operations",
                category=IntentCategory.SYSTEM_OPERATION,
                patterns=[
                    r"(?:git\s+)?commit\s+(.+)",
                    r"(?:git\s+)?(?:push|pull|merge|branch)",
                    r"(?:create|make)\s+(?:a\s+)?(?:git\s+)?commit"
                ],
                keywords=["git", "commit", "push", "pull", "branch"],
                entities=["git_command", "message", "branch"],
                response_template="Executing git {git_command}",
                tool_suggestions=["git", "workflow:git_ops"],
                examples=[
                    "commit the changes",
                    "git push to main",
                    "create a new branch"
                ]
            ),
            
            NLPTemplate(
                id="SO_003",
                name="File Operations",
                category=IntentCategory.SYSTEM_OPERATION,
                patterns=[
                    r"(?:create|make|touch)\s+(?:a\s+)?(?:new\s+)?file\s+(.+)",
                    r"(?:delete|remove|rm)\s+(?:the\s+)?file\s+(.+)",
                    r"(?:move|rename|mv)\s+(.+)\s+to\s+(.+)"
                ],
                keywords=["file", "create", "delete", "move", "rename"],
                entities=["file_path", "operation", "destination"],
                response_template="Performing file operation: {operation}",
                tool_suggestions=["bash", "file_system"],
                examples=[
                    "create a new file config.json",
                    "delete the temp file",
                    "rename old.txt to new.txt"
                ]
            ),
        ])
        
        # DATA ANALYSIS TEMPLATES (151-180)
        templates.extend([
            NLPTemplate(
                id="DA_001",
                name="Analyze Data",
                category=IntentCategory.DATA_ANALYSIS,
                patterns=[
                    r"analyze\s+(?:the\s+)?(?:data\s+)?(?:in\s+)?(.+)",
                    r"(?:show|get)\s+(?:me\s+)?statistics\s+(?:for|on|about)\s+(.+)",
                    r"(?:what are|what\'s)\s+the\s+(?:metrics|stats|statistics)\s+(?:for\s+)?(.+)"
                ],
                keywords=["analyze", "data", "statistics", "metrics"],
                entities=["data_source", "metrics_requested"],
                response_template="Analyzing data from {data_source}",
                tool_suggestions=["pandas", "workflow:data_analysis"],
                examples=[
                    "analyze the user data",
                    "show me statistics for the last month",
                    "what are the performance metrics"
                ]
            ),
            
            NLPTemplate(
                id="DA_002",
                name="Generate Report",
                category=IntentCategory.DATA_ANALYSIS,
                patterns=[
                    r"(?:generate|create|make)\s+(?:a\s+)?report\s+(?:for|on|about)\s+(.+)",
                    r"(?:summarize|summary)\s+(?:the\s+)?(.+)",
                    r"(?:create|make)\s+(?:a\s+)?summary\s+of\s+(.+)"
                ],
                keywords=["report", "summary", "summarize", "generate"],
                entities=["report_subject", "format", "time_range"],
                response_template="Generating report on {report_subject}",
                tool_suggestions=["workflow:report_gen", "markdown"],
                examples=[
                    "generate a report on user activity",
                    "summarize the test results",
                    "create a performance report"
                ]
            ),
        ])
        
        # DOCUMENTATION TEMPLATES (181-210)
        templates.extend([
            NLPTemplate(
                id="DC_001",
                name="Write Documentation",
                category=IntentCategory.DOCUMENTATION,
                patterns=[
                    r"(?:write|create|add)\s+(?:documentation|docs)\s+(?:for\s+)?(.+)",
                    r"document\s+(?:the\s+)?(.+)",
                    r"add\s+(?:code\s+)?comments\s+(?:to\s+)?(.+)"
                ],
                keywords=["documentation", "document", "docs", "comments"],
                entities=["doc_target", "doc_type", "detail_level"],
                response_template="Writing documentation for {doc_target}",
                tool_suggestions=["aider", "markdown", "workflow:doc_gen"],
                examples=[
                    "write documentation for the API",
                    "document the User class",
                    "add comments to main.py"
                ]
            ),
            
            NLPTemplate(
                id="DC_002",
                name="Generate README",
                category=IntentCategory.DOCUMENTATION,
                patterns=[
                    r"(?:create|write|generate)\s+(?:a\s+)?readme",
                    r"(?:update|improve)\s+(?:the\s+)?readme",
                    r"add\s+(.+)\s+to\s+(?:the\s+)?readme"
                ],
                keywords=["readme", "create", "generate"],
                entities=["readme_sections", "project_info"],
                response_template="Generating README",
                tool_suggestions=["workflow:readme_gen", "markdown"],
                examples=[
                    "create a README file",
                    "update the README with installation steps",
                    "add usage examples to README"
                ]
            ),
        ])
        
        # DEPLOYMENT TEMPLATES (211-240)
        templates.extend([
            NLPTemplate(
                id="DP_001",
                name="Deploy Application",
                category=IntentCategory.DEPLOYMENT,
                patterns=[
                    r"deploy\s+(?:the\s+)?(?:app|application|project)\s+(?:to\s+)?(.+)?",
                    r"(?:push|ship)\s+to\s+(?:production|staging|dev)",
                    r"release\s+(?:version\s+)?(.+)?"
                ],
                keywords=["deploy", "deployment", "release", "production"],
                entities=["environment", "version", "config"],
                response_template="Deploying to {environment}",
                tool_suggestions=["workflow:deploy", "docker", "kubernetes"],
                examples=[
                    "deploy the app to production",
                    "push to staging environment",
                    "release version 2.0"
                ]
            ),
            
            NLPTemplate(
                id="DP_002",
                name="Build Project",
                category=IntentCategory.DEPLOYMENT,
                patterns=[
                    r"build\s+(?:the\s+)?(?:project|app|application)",
                    r"(?:compile|bundle)\s+(?:the\s+)?(?:code|project)",
                    r"(?:create|make)\s+(?:a\s+)?(?:production\s+)?build"
                ],
                keywords=["build", "compile", "bundle"],
                entities=["build_type", "target", "options"],
                response_template="Building project",
                tool_suggestions=["npm", "webpack", "make"],
                examples=[
                    "build the project",
                    "create a production build",
                    "compile the TypeScript code"
                ]
            ),
        ])
        
        # LEARNING TEMPLATES (241-256)
        templates.extend([
            NLPTemplate(
                id="LN_001",
                name="Learn Pattern",
                category=IntentCategory.LEARNING,
                patterns=[
                    r"(?:learn|remember)\s+(?:that\s+)?(.+)",
                    r"(?:next time|always)\s+(.+)",
                    r"(?:my\s+)?preference\s+(?:is\s+)?(.+)"
                ],
                keywords=["learn", "remember", "preference", "always"],
                entities=["pattern", "context", "preference_type"],
                response_template="Learning: {pattern}",
                tool_suggestions=["learning_system"],
                examples=[
                    "remember that I prefer tabs over spaces",
                    "always use pytest for testing",
                    "my preference is qwen for code generation"
                ]
            ),
            
            NLPTemplate(
                id="LN_002",
                name="Recall Information",
                category=IntentCategory.LEARNING,
                patterns=[
                    r"(?:what\s+)?(?:do you\s+)?remember\s+(?:about\s+)?(.+)",
                    r"(?:what\s+)?(?:did I\s+)?(?:say|tell you)\s+about\s+(.+)",
                    r"(?:recall|show)\s+(?:my\s+)?(?:previous|past)\s+(.+)"
                ],
                keywords=["remember", "recall", "previous", "history"],
                entities=["memory_query", "time_range"],
                response_template="Recalling information about {memory_query}",
                tool_suggestions=["memory", "history"],
                examples=[
                    "what do you remember about the auth system",
                    "what did I say about testing",
                    "recall previous commands"
                ]
            ),
            
            NLPTemplate(
                id="LN_003",
                name="Improve Performance",
                category=IntentCategory.LEARNING,
                patterns=[
                    r"(?:how can you|can you)\s+(?:improve|get better)\s+(?:at\s+)?(.+)",
                    r"(?:learn to|learn how to)\s+(.+)\s+better",
                    r"(?:optimize|improve)\s+(?:your\s+)?performance\s+(?:on\s+)?(.+)"
                ],
                keywords=["improve", "better", "optimize", "performance"],
                entities=["improvement_area", "metrics"],
                response_template="Analyzing how to improve {improvement_area}",
                tool_suggestions=["learning_system", "analytics"],
                examples=[
                    "how can you improve at debugging",
                    "learn to write tests better",
                    "optimize your code generation performance"
                ]
            ),
        ])
        
        # Add more comprehensive templates to reach 256
        
        # EXTENDED CODE GENERATION TEMPLATES (031-050)
        templates.extend([
            NLPTemplate(
                id="CG_006",
                name="Create Database Model",
                category=IntentCategory.CODE_GENERATION,
                patterns=[
                    r"(create|write|implement)\s+(?:a\s+)?(?:database\s+)?model\s+(?:for\s+)?(.+)",
                    r"(?:define|create)\s+(?:a\s+)?schema\s+(?:for\s+)?(.+)"
                ],
                keywords=["model", "database", "schema", "table"],
                entities=["model_name", "fields", "relationships"],
                response_template="Creating database model for {model_name}",
                tool_suggestions=["aider", "ollama:qwen2.5-coder"],
                examples=["create a model for users", "define schema for products"]
            ),
            
            NLPTemplate(
                id="CG_007",
                name="Create CLI Tool",
                category=IntentCategory.CODE_GENERATION,
                patterns=[
                    r"(create|build|make)\s+(?:a\s+)?(?:cli|command.line)\s+(?:tool|app|application)\s+(?:for\s+)?(.+)",
                    r"(?:cli|command)\s+(?:for\s+)?(.+)"
                ],
                keywords=["cli", "command", "tool", "terminal"],
                entities=["tool_name", "commands", "options"],
                response_template="Creating CLI tool for {tool_name}",
                tool_suggestions=["aider", "python"],
                examples=["create a CLI tool for file processing", "build command line app"]
            ),
            
            NLPTemplate(
                id="CG_008",
                name="Create Configuration",
                category=IntentCategory.CODE_GENERATION,
                patterns=[
                    r"(create|generate|write)\s+(?:a\s+)?config(?:uration)?\s+(?:file\s+)?(?:for\s+)?(.+)",
                    r"(?:setup|configure)\s+(.+)"
                ],
                keywords=["config", "configuration", "setup", "settings"],
                entities=["config_type", "settings"],
                response_template="Creating configuration for {config_type}",
                tool_suggestions=["aider", "write_file"],
                examples=["create config for docker", "generate configuration file"]
            ),
            
            NLPTemplate(
                id="CG_009",
                name="Create Interface",
                category=IntentCategory.CODE_GENERATION,
                patterns=[
                    r"(create|define|write)\s+(?:an?\s+)?interface\s+(?:for\s+)?(.+)",
                    r"interface\s+(.+)"
                ],
                keywords=["interface", "contract", "protocol"],
                entities=["interface_name", "methods"],
                response_template="Creating interface for {interface_name}",
                tool_suggestions=["aider", "ollama:qwen2.5-coder"],
                examples=["create an interface for payment processor", "define interface for storage"]
            ),
            
            NLPTemplate(
                id="CG_010",
                name="Create Middleware",
                category=IntentCategory.CODE_GENERATION,
                patterns=[
                    r"(create|implement|add)\s+(?:a\s+)?middleware\s+(?:for\s+)?(.+)",
                    r"middleware\s+(?:for\s+)?(.+)"
                ],
                keywords=["middleware", "interceptor", "handler"],
                entities=["middleware_type", "purpose"],
                response_template="Creating middleware for {middleware_type}",
                tool_suggestions=["aider", "workflow:code_gen"],
                examples=["create authentication middleware", "add middleware for logging"]
            ),
        ])
        
        # EXTENDED DEBUGGING TEMPLATES (091-110)
        templates.extend([
            NLPTemplate(
                id="DB_004",
                name="Trace Execution",
                category=IntentCategory.DEBUGGING,
                patterns=[
                    r"trace\s+(?:the\s+)?(?:execution\s+)?(?:of\s+)?(.+)",
                    r"(?:show|display)\s+(?:the\s+)?(?:execution\s+)?(?:flow|path)\s+(?:of\s+)?(.+)"
                ],
                keywords=["trace", "execution", "flow", "path"],
                entities=["trace_target"],
                response_template="Tracing execution of {trace_target}",
                tool_suggestions=["debugger", "print", "logging"],
                examples=["trace the execution of main function", "show execution flow"]
            ),
            
            NLPTemplate(
                id="DB_005",
                name="Memory Leak Detection",
                category=IntentCategory.DEBUGGING,
                patterns=[
                    r"(?:find|detect|check)\s+(?:for\s+)?memory\s+leak",
                    r"memory\s+(?:usage|consumption)\s+(?:issue|problem)"
                ],
                keywords=["memory", "leak", "usage"],
                entities=["memory_target"],
                response_template="Checking for memory leaks",
                tool_suggestions=["profiler", "valgrind", "memory_profiler"],
                examples=["find memory leak", "check memory usage"]
            ),
            
            NLPTemplate(
                id="DB_006",
                name="Performance Bottleneck",
                category=IntentCategory.DEBUGGING,
                patterns=[
                    r"(?:find|identify|locate)\s+(?:performance\s+)?bottleneck",
                    r"(?:what\'s|what is)\s+(?:making|causing)\s+(?:it|this)\s+slow"
                ],
                keywords=["bottleneck", "performance", "slow"],
                entities=["performance_target"],
                response_template="Identifying performance bottlenecks",
                tool_suggestions=["profiler", "workflow:optimize"],
                examples=["find performance bottleneck", "what's making it slow"]
            ),
        ])
        
        # EXTENDED SYSTEM OPERATION TEMPLATES (151-170)
        templates.extend([
            NLPTemplate(
                id="SO_004",
                name="Install Package",
                category=IntentCategory.SYSTEM_OPERATION,
                patterns=[
                    r"install\s+(.+)",
                    r"(?:pip|npm|cargo|gem)\s+install\s+(.+)",
                    r"add\s+(?:package|dependency)\s+(.+)"
                ],
                keywords=["install", "package", "dependency"],
                entities=["package_name", "package_manager"],
                response_template="Installing {package_name}",
                tool_suggestions=["pip", "npm", "bash"],
                examples=["install numpy", "pip install requests", "add package flask"]
            ),
            
            NLPTemplate(
                id="SO_005",
                name="Environment Setup",
                category=IntentCategory.SYSTEM_OPERATION,
                patterns=[
                    r"(?:setup|create|init)\s+(?:virtual\s+)?env(?:ironment)?",
                    r"(?:activate|deactivate)\s+(?:virtual\s+)?env(?:ironment)?"
                ],
                keywords=["environment", "venv", "virtualenv", "setup"],
                entities=["env_name", "python_version"],
                response_template="Setting up environment",
                tool_suggestions=["venv", "virtualenv", "conda"],
                examples=["setup virtual environment", "create venv", "activate environment"]
            ),
            
            NLPTemplate(
                id="SO_006",
                name="Process Management",
                category=IntentCategory.SYSTEM_OPERATION,
                patterns=[
                    r"(?:kill|stop|terminate)\s+(?:process|pid)\s+(.+)",
                    r"(?:list|show)\s+(?:running\s+)?processes",
                    r"(?:restart|start)\s+(?:service\s+)?(.+)"
                ],
                keywords=["process", "kill", "stop", "restart", "service"],
                entities=["process_name", "pid"],
                response_template="Managing process {process_name}",
                tool_suggestions=["ps", "kill", "systemctl"],
                examples=["kill process 1234", "restart nginx", "list processes"]
            ),
        ])
        
        # EXTENDED DATA ANALYSIS TEMPLATES (181-200)
        templates.extend([
            NLPTemplate(
                id="DA_003",
                name="Visualize Data",
                category=IntentCategory.DATA_ANALYSIS,
                patterns=[
                    r"(?:visualize|plot|graph)\s+(?:the\s+)?(.+)",
                    r"(?:create|make|generate)\s+(?:a\s+)?(?:chart|graph|plot)\s+(?:of|for)\s+(.+)"
                ],
                keywords=["visualize", "plot", "graph", "chart"],
                entities=["data_source", "chart_type"],
                response_template="Visualizing {data_source}",
                tool_suggestions=["matplotlib", "plotly", "seaborn"],
                examples=["visualize the sales data", "create a chart of user growth", "plot the results"]
            ),
            
            NLPTemplate(
                id="DA_004",
                name="Data Transformation",
                category=IntentCategory.DATA_ANALYSIS,
                patterns=[
                    r"(?:transform|convert|process)\s+(?:the\s+)?data\s+(?:from\s+)?(.+)",
                    r"(?:clean|normalize|aggregate)\s+(?:the\s+)?(.+)\s+data"
                ],
                keywords=["transform", "convert", "clean", "normalize", "aggregate"],
                entities=["data_source", "transformation_type"],
                response_template="Transforming {data_source} data",
                tool_suggestions=["pandas", "workflow:data_pipeline"],
                examples=["transform the CSV data", "clean the dataset", "normalize user data"]
            ),
            
            NLPTemplate(
                id="DA_005",
                name="Query Database",
                category=IntentCategory.DATA_ANALYSIS,
                patterns=[
                    r"(?:query|select|get)\s+(?:from\s+)?(?:the\s+)?database\s+(.+)",
                    r"(?:sql|database)\s+(?:query\s+)?(?:for\s+)?(.+)"
                ],
                keywords=["query", "database", "sql", "select"],
                entities=["query_target", "table", "conditions"],
                response_template="Querying database for {query_target}",
                tool_suggestions=["sql", "sqlalchemy", "database"],
                examples=["query database for users", "select from orders table", "get all products"]
            ),
        ])
        
        # EXTENDED DOCUMENTATION TEMPLATES (211-230)
        templates.extend([
            NLPTemplate(
                id="DC_003",
                name="API Documentation",
                category=IntentCategory.DOCUMENTATION,
                patterns=[
                    r"(?:document|write docs for)\s+(?:the\s+)?api",
                    r"(?:create|generate)\s+api\s+(?:docs|documentation)"
                ],
                keywords=["api", "documentation", "swagger", "openapi"],
                entities=["api_endpoints", "format"],
                response_template="Generating API documentation",
                tool_suggestions=["swagger", "openapi", "workflow:doc_gen"],
                examples=["document the API", "create API docs", "generate swagger documentation"]
            ),
            
            NLPTemplate(
                id="DC_004",
                name="Code Comments",
                category=IntentCategory.DOCUMENTATION,
                patterns=[
                    r"(?:add|write)\s+comments\s+(?:to|in)\s+(.+)",
                    r"comment\s+(?:the\s+)?(?:code\s+)?(?:in\s+)?(.+)"
                ],
                keywords=["comment", "comments", "annotate"],
                entities=["file_path", "comment_style"],
                response_template="Adding comments to {file_path}",
                tool_suggestions=["aider", "editor"],
                examples=["add comments to main.py", "comment the code", "write comments in functions"]
            ),
        ])
        
        # EXTENDED DEPLOYMENT TEMPLATES (241-256)
        templates.extend([
            NLPTemplate(
                id="DP_003",
                name="Docker Operations",
                category=IntentCategory.DEPLOYMENT,
                patterns=[
                    r"(?:build|create)\s+(?:a\s+)?docker\s+(?:image|container)",
                    r"(?:run|start|stop)\s+(?:docker\s+)?container\s+(.+)",
                    r"docker\s+(.+)"
                ],
                keywords=["docker", "container", "image"],
                entities=["docker_command", "container_name", "image_name"],
                response_template="Executing Docker operation",
                tool_suggestions=["docker", "docker-compose"],
                examples=["build docker image", "run container myapp", "docker ps"]
            ),
            
            NLPTemplate(
                id="DP_004",
                name="CI/CD Pipeline",
                category=IntentCategory.DEPLOYMENT,
                patterns=[
                    r"(?:setup|create|configure)\s+(?:ci.?cd|pipeline)",
                    r"(?:github|gitlab)\s+actions",
                    r"(?:jenkins|circleci)\s+(?:pipeline|job)"
                ],
                keywords=["ci", "cd", "pipeline", "actions", "jenkins"],
                entities=["pipeline_type", "stages"],
                response_template="Setting up CI/CD pipeline",
                tool_suggestions=["github", "jenkins", "workflow:deploy"],
                examples=["setup CI/CD pipeline", "create github actions", "configure jenkins"]
            ),
            
            NLPTemplate(
                id="DP_005",
                name="Environment Configuration",
                category=IntentCategory.DEPLOYMENT,
                patterns=[
                    r"(?:configure|setup)\s+(?:production|staging|dev)\s+(?:environment|env)",
                    r"(?:set|update)\s+env(?:ironment)?\s+(?:variables|vars)"
                ],
                keywords=["environment", "env", "variables", "production", "staging"],
                entities=["environment", "variables"],
                response_template="Configuring {environment} environment",
                tool_suggestions=["dotenv", "config", "bash"],
                examples=["configure production environment", "set env variables", "setup staging env"]
            ),
        ])
        
        # MACHINE LEARNING TEMPLATES (257-270)
        templates.extend([
            NLPTemplate(
                id="ML_001",
                name="Train Model",
                category=IntentCategory.LEARNING,
                patterns=[
                    r"train\s+(?:a\s+)?(?:model|classifier|network)\s+(?:on|for|with)\s+(.+)",
                    r"(?:machine\s+)?learning\s+(?:model\s+)?(?:for\s+)?(.+)"
                ],
                keywords=["train", "model", "machine learning", "ml"],
                entities=["model_type", "dataset"],
                response_template="Training model for {model_type}",
                tool_suggestions=["scikit-learn", "tensorflow", "pytorch"],
                examples=["train model on dataset", "train classifier for spam detection"]
            ),
            
            NLPTemplate(
                id="ML_002",
                name="Evaluate Model",
                category=IntentCategory.LEARNING,
                patterns=[
                    r"evaluate\s+(?:the\s+)?model",
                    r"(?:test|validate)\s+(?:model\s+)?performance",
                    r"(?:check|measure)\s+accuracy"
                ],
                keywords=["evaluate", "test", "accuracy", "performance"],
                entities=["model_name", "metrics"],
                response_template="Evaluating model performance",
                tool_suggestions=["scikit-learn", "metrics"],
                examples=["evaluate the model", "test model performance", "check accuracy"]
            ),
            
            # Direct system commands
            NLPTemplate(
                id="SYS_CMD_001",
                name="Direct System Command",
                category=IntentCategory.SYSTEM_OPERATION,
                patterns=[
                    r"^(echo|cat|ls|pwd|cd|mkdir|rm|cp|mv|touch|grep|find|ps|kill|df|du|chmod|chown)\b"
                ],
                keywords=["echo", "cat", "ls", "pwd", "system", "command"],
                entities=["command", "arguments"],
                response_template="Executing system command",
                tool_suggestions=["system", "bash"],
                examples=["echo hello", "ls -la", "pwd", "cat file.txt"]
            ),
            
            # File operations with redirection
            NLPTemplate(
                id="SYS_CMD_002",
                name="Command with Redirection",
                category=IntentCategory.SYSTEM_OPERATION,
                patterns=[
                    r".*(>|\|).*"
                ],
                keywords=["pipe", "redirect", "output"],
                entities=["command", "target"],
                response_template="Executing command with redirection",
                tool_suggestions=["system", "bash"],
                examples=["echo test > file.txt", "ls | grep py", "cat file | head"]
            ),
        ])
        
        return templates
    
    def classify_intent(self, text: str) -> Tuple[Optional[NLPTemplate], float]:
        """Classify user intent using template matching"""
        best_match = None
        best_confidence = 0.0
        
        for template in self.templates:
            matched, metadata = template.match(text)
            if matched:
                # Calculate confidence based on match quality
                confidence = template.confidence_threshold
                
                if "pattern" in metadata:
                    confidence += 0.1  # Pattern match is strong
                if "keywords" in metadata:
                    confidence += 0.05 * metadata["keywords"]
                
                confidence = min(1.0, confidence)
                
                if confidence > best_confidence:
                    best_match = template
                    best_confidence = confidence
        
        return best_match, best_confidence
    
    def extract_entities(self, text: str, template: NLPTemplate) -> Dict[str, Any]:
        """Extract entities from text based on template"""
        entities = {}
        
        # Extract based on patterns
        for pattern in template.patterns:
            match = re.search(pattern, text.lower())
            if match:
                groups = match.groups()
                for i, entity in enumerate(template.entities[:len(groups)]):
                    if i < len(groups) and groups[i]:
                        entities[entity] = groups[i]
                break
        
        # Provide defaults for missing entities to avoid KeyError
        for entity in template.entities:
            if entity not in entities:
                entities[entity] = ""
        
        # Additional extraction logic
        if "file_path" in template.entities:
            # Look for file paths
            file_pattern = r'[\w/\\]+\.\w+'
            files = re.findall(file_pattern, text)
            if files:
                entities["file_path"] = files[0]
        
        if "function_name" in template.entities:
            # Look for function names
            func_pattern = r'\b([a-zA-Z_]\w*)\s*\('
            funcs = re.findall(func_pattern, text)
            if funcs:
                entities["function_name"] = funcs[0]
        
        return entities
    
    def suggest_workflow(self, intent: NLPTemplate) -> Optional[str]:
        """Suggest a workflow based on intent"""
        workflow_map = {
            IntentCategory.CODE_GENERATION: "code_gen",
            IntentCategory.DEBUGGING: "bug_fix",
            IntentCategory.RESEARCH: "research",
            IntentCategory.TESTING: "test_gen",
            IntentCategory.DOCUMENTATION: "doc_gen",
            IntentCategory.DEPLOYMENT: "deploy"
        }
        
        return workflow_map.get(intent.category)
    
    def get_response(self, text: str) -> Dict[str, Any]:
        """Get complete response for user input"""
        # Classify intent
        template, confidence = self.classify_intent(text)
        
        if not template or confidence < 0.5:
            return {
                "understood": False,
                "confidence": confidence,
                "suggestions": ["Can you rephrase that?", "Try being more specific"]
            }
        
        # Extract entities
        entities = self.extract_entities(text, template)
        
        # Prepare response
        response = {
            "understood": True,
            "intent": template.name,
            "category": template.category.value,
            "confidence": confidence,
            "entities": entities,
            "response": template.response_template.format(**entities),
            "tools": template.tool_suggestions,
            "workflow": self.suggest_workflow(template),
            "examples": template.examples
        }
        
        return response
    
    def add_custom_template(self, template: NLPTemplate):
        """Add a custom template to the library"""
        self.templates.append(template)
    
    def export_templates(self, path: str):
        """Export templates to JSON for backup/sharing"""
        data = []
        for template in self.templates:
            data.append({
                "id": template.id,
                "name": template.name,
                "category": template.category.value,
                "patterns": template.patterns,
                "keywords": template.keywords,
                "entities": template.entities,
                "response_template": template.response_template,
                "tool_suggestions": template.tool_suggestions,
                "confidence_threshold": template.confidence_threshold,
                "examples": template.examples
            })
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_templates_by_category(self, category: IntentCategory) -> List[NLPTemplate]:
        """Get all templates for a category"""
        return [t for t in self.templates if t.category == category]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the template library"""
        stats = {
            "total_templates": len(self.templates),
            "categories": {}
        }
        
        for category in IntentCategory:
            templates = self.get_templates_by_category(category)
            stats["categories"][category.value] = {
                "count": len(templates),
                "templates": [t.name for t in templates]
            }
        
        return stats


if __name__ == "__main__":
    # Test the NLP library
    nlp = CoreNLPLibrary()
    
    # Test various inputs
    test_inputs = [
        "create a function to sort a list",
        "fix the bug in authentication",
        "search for database connections in the code",
        "deploy the app to production",
        "analyze the user data from last month",
        "refactor the payment module to be more efficient",
        "where is the User class defined?",
        "add dark mode feature to the application"
    ]
    
    print("NLP Template Library Test\n" + "="*50)
    print(f"Total templates: {len(nlp.templates)}\n")
    
    for text in test_inputs:
        print(f"Input: {text}")
        response = nlp.get_response(text)
        
        if response["understood"]:
            print(f"  Intent: {response['intent']}")
            print(f"  Category: {response['category']}")
            print(f"  Confidence: {response['confidence']:.2%}")
            print(f"  Response: {response['response']}")
            print(f"  Tools: {', '.join(response['tools'])}")
            if response.get('workflow'):
                print(f"  Workflow: {response['workflow']}")
        else:
            print(f"  Not understood (confidence: {response['confidence']:.2%})")
        print()
    
    # Show statistics
    stats = nlp.get_statistics()
    print("\nLibrary Statistics:")
    for category, info in stats["categories"].items():
        print(f"  {category}: {info['count']} templates")