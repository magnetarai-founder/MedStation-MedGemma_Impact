"""
Intent Training Data

Example phrases for each intent type, used to build intent embeddings.
The transformer classifier compares user input against these examples
to determine intent via semantic similarity.

To add new examples:
1. Add phrases to the appropriate INTENT_EXAMPLES entry
2. Run the embedding rebuild (or it will auto-rebuild on first use)
"""

from .interface import IntentType

# Example phrases for each intent type
# These are used to build intent embeddings for semantic comparison
INTENT_EXAMPLES: dict[IntentType, list[str]] = {
    IntentType.CODE_EDIT: [
        # Creation
        "add a new function to handle authentication",
        "create a login component",
        "implement the user registration feature",
        "build a REST API endpoint for users",
        "write a utility function for date formatting",
        "make a new class for database connections",
        # Modification
        "change the button color to blue",
        "update the API response format",
        "modify the validation logic",
        "edit the configuration file",
        "insert a new field in the form",
        "replace the old authentication method",
        # Deletion
        "remove the deprecated function",
        "delete the unused imports",
        "clean up dead code",
        # Multi-file
        "refactor the authentication across all files",
        "add error handling to all API endpoints",
        "update imports in the entire codebase",
    ],
    IntentType.DEBUG: [
        # Error fixing
        "fix the null pointer exception",
        "debug the login failure",
        "resolve the import error",
        "fix the broken test",
        "repair the database connection issue",
        # Error investigation
        "why is this function returning undefined",
        "investigate the memory leak",
        "find out why the API is slow",
        "trace the source of the bug",
        "analyze the stack trace",
        # Specific errors
        "TypeError: cannot read property of undefined",
        "the application crashes on startup",
        "getting 500 error from the server",
        "authentication is failing for all users",
        "the form submission doesn't work",
        # Recovery
        "the build is broken",
        "tests are failing in CI",
        "production is down",
    ],
    IntentType.REFACTOR: [
        # Code quality
        "refactor this function to be more readable",
        "improve the code structure",
        "clean up the messy code",
        "simplify this complex logic",
        "optimize the database queries",
        # Architecture
        "reorganize the project structure",
        "extract common logic into a utility",
        "split this large file into modules",
        "consolidate duplicate code",
        "convert to async await pattern",
        # Performance
        "make this function faster",
        "reduce memory usage",
        "optimize the rendering performance",
        "improve the algorithm efficiency",
        # Standards
        "apply consistent naming conventions",
        "follow the project style guide",
        "modernize the legacy code",
    ],
    IntentType.TEST: [
        # Test creation
        "write unit tests for the user service",
        "add integration tests for the API",
        "create test cases for the login flow",
        "write tests for edge cases",
        "add mock tests for external services",
        # Test execution
        "run the test suite",
        "execute the unit tests",
        "run pytest on this file",
        "check if all tests pass",
        # Coverage
        "improve test coverage",
        "find untested code paths",
        "analyze test coverage report",
        "add tests for uncovered functions",
        # Specific frameworks
        "add jest tests for the component",
        "write pytest fixtures",
        "create mocha test specs",
    ],
    IntentType.CODE_REVIEW: [
        # Quality review
        "review this code for issues",
        "check the code quality",
        "audit this function for bugs",
        "analyze the code for improvements",
        "look for potential problems",
        # Security
        "check for security vulnerabilities",
        "audit for SQL injection",
        "review authentication security",
        "find security issues in this code",
        # Best practices
        "check if this follows best practices",
        "review for coding standards",
        "ensure the code is maintainable",
        "verify the error handling is proper",
        # Performance review
        "check for performance issues",
        "review for memory leaks",
        "analyze for N+1 query problems",
    ],
    IntentType.EXPLAIN: [
        # Understanding
        "explain how this function works",
        "what does this code do",
        "describe the authentication flow",
        "how does the caching work",
        "why is this implemented this way",
        # Documentation
        "document this API endpoint",
        "write documentation for the module",
        "add comments explaining the logic",
        "create a README for this project",
        # Analysis
        "summarize what this file does",
        "give me an overview of the architecture",
        "explain the design patterns used",
        "describe the data flow",
        # Learning
        "help me understand this error",
        "teach me about this pattern",
        "what is the purpose of this class",
    ],
    IntentType.SEARCH: [
        # File search
        "find the file that handles authentication",
        "where is the user model defined",
        "locate the API routes",
        "show me all Python files",
        "find files containing database queries",
        # Code search
        "search for usages of this function",
        "find all references to UserService",
        "grep for TODO comments",
        "look for deprecated API calls",
        "find where this error is thrown",
        # Pattern search
        "show me all async functions",
        "find classes that extend BaseModel",
        "list all API endpoints",
        "find all database migrations",
        # Navigation
        "go to the definition of this function",
        "show me the implementation",
        "where is this imported from",
    ],
    IntentType.CHAT: [
        # General conversation
        "hello",
        "hi there",
        "good morning",
        "thanks for the help",
        "that looks good",
        # Clarification
        "can you explain that again",
        "I don't understand",
        "what do you mean",
        "could you clarify",
        # Confirmation
        "yes that's correct",
        "no that's not what I meant",
        "exactly",
        "perfect",
        # Meta
        "what can you do",
        "help",
        "how do I use this",
        "what are your capabilities",
    ],
}

# Confidence thresholds for intent classification
CONFIDENCE_THRESHOLDS = {
    "high": 0.85,  # Very confident match
    "medium": 0.70,  # Reasonably confident
    "low": 0.50,  # Possible match, may need fallback
    "minimum": 0.30,  # Below this, use keyword fallback
}

# Intent compatibility matrix - which intents can co-occur
# Used for multi-intent classification
COMPATIBLE_INTENTS: dict[IntentType, set[IntentType]] = {
    IntentType.CODE_EDIT: {IntentType.TEST, IntentType.CODE_REVIEW},
    IntentType.DEBUG: {IntentType.TEST, IntentType.EXPLAIN},
    IntentType.REFACTOR: {IntentType.TEST, IntentType.CODE_REVIEW},
    IntentType.TEST: {IntentType.CODE_EDIT, IntentType.DEBUG, IntentType.REFACTOR},
    IntentType.CODE_REVIEW: {IntentType.CODE_EDIT, IntentType.REFACTOR},
    IntentType.EXPLAIN: {IntentType.SEARCH, IntentType.DEBUG},
    IntentType.SEARCH: {IntentType.EXPLAIN},
    IntentType.CHAT: set(),  # Chat is usually standalone
}

# Intent priority for tie-breaking
# Higher number = higher priority when scores are close
INTENT_PRIORITY: dict[IntentType, int] = {
    IntentType.DEBUG: 10,  # Errors are urgent
    IntentType.CODE_EDIT: 9,  # Most common action
    IntentType.REFACTOR: 8,
    IntentType.TEST: 7,
    IntentType.CODE_REVIEW: 6,
    IntentType.SEARCH: 5,
    IntentType.EXPLAIN: 4,
    IntentType.CHAT: 1,  # Lowest priority (fallback)
}


def get_all_examples() -> list[tuple[str, IntentType]]:
    """
    Get all training examples as (text, intent) pairs.

    Returns:
        List of (example_text, intent_type) tuples
    """
    examples = []
    for intent_type, texts in INTENT_EXAMPLES.items():
        for text in texts:
            examples.append((text, intent_type))
    return examples


def get_examples_for_intent(intent_type: IntentType) -> list[str]:
    """Get all example phrases for a specific intent"""
    return INTENT_EXAMPLES.get(intent_type, [])


def get_intent_count() -> dict[IntentType, int]:
    """Get count of examples per intent (for balancing)"""
    return {intent: len(examples) for intent, examples in INTENT_EXAMPLES.items()}
