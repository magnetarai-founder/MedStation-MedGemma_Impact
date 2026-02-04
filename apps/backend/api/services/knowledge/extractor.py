"""
Knowledge Extractor

Extracts structured knowledge from conversations using NLP.
Identifies topics, code patterns, and problem-solution pairs.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TopicCategory(str, Enum):
    """Categories of discussion topics."""

    DEBUGGING = "debugging"
    IMPLEMENTATION = "implementation"
    REFACTORING = "refactoring"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    GENERAL = "general"


class PatternType(str, Enum):
    """Types of code patterns."""

    ERROR_HANDLING = "error_handling"
    DATA_VALIDATION = "data_validation"
    API_DESIGN = "api_design"
    DATABASE = "database"
    ASYNC_AWAIT = "async_await"
    TESTING = "testing"
    LOGGING = "logging"
    CACHING = "caching"
    AUTHENTICATION = "authentication"
    OTHER = "other"


@dataclass
class Topic:
    """An extracted discussion topic."""

    name: str
    category: TopicCategory
    confidence: float
    keywords: list[str]
    frequency: int = 1
    last_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "confidence": self.confidence,
            "keywords": self.keywords,
            "frequency": self.frequency,
            "last_seen": self.last_seen,
        }


@dataclass
class CodePattern:
    """An extracted code pattern."""

    name: str
    pattern_type: PatternType
    description: str
    example_code: str
    language: str
    files_seen_in: list[str] = field(default_factory=list)
    frequency: int = 1

    @property
    def pattern_id(self) -> str:
        """Generate unique ID for pattern."""
        content = f"{self.name}:{self.pattern_type}:{self.example_code[:100]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.pattern_id,
            "name": self.name,
            "pattern_type": self.pattern_type.value,
            "description": self.description,
            "example_code": self.example_code,
            "language": self.language,
            "files_seen_in": self.files_seen_in,
            "frequency": self.frequency,
        }


@dataclass
class ProblemSolution:
    """A problem-solution pair."""

    problem: str
    solution: str
    context: str
    files_involved: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    effectiveness_score: float = 0.0  # Updated based on user feedback
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def pair_id(self) -> str:
        """Generate unique ID for pair."""
        content = f"{self.problem[:100]}:{self.solution[:100]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.pair_id,
            "problem": self.problem,
            "solution": self.solution,
            "context": self.context,
            "files_involved": self.files_involved,
            "tags": self.tags,
            "effectiveness_score": self.effectiveness_score,
            "created_at": self.created_at,
        }


@dataclass
class ExtractionResult:
    """Result of knowledge extraction."""

    topics: list[Topic] = field(default_factory=list)
    patterns: list[CodePattern] = field(default_factory=list)
    solutions: list[ProblemSolution] = field(default_factory=list)
    raw_insights: list[str] = field(default_factory=list)
    extraction_time_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "topics": [t.to_dict() for t in self.topics],
            "patterns": [p.to_dict() for p in self.patterns],
            "solutions": [s.to_dict() for s in self.solutions],
            "raw_insights": self.raw_insights,
            "extraction_time_ms": self.extraction_time_ms,
        }


class KnowledgeExtractor:
    """
    Extracts knowledge from conversations.

    Uses a combination of:
    - Rule-based extraction (fast, high precision)
    - LLM-based extraction (slower, higher recall)
    - Pattern matching for code structures
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5-coder:7b",
        use_llm: bool = True,
    ):
        self._ollama_url = ollama_url
        self._model = model
        self._use_llm = use_llm

        # Topic keyword mappings
        self._topic_keywords = {
            TopicCategory.DEBUGGING: [
                "error", "bug", "fix", "issue", "crash", "exception",
                "traceback", "debug", "problem", "broken", "failing",
            ],
            TopicCategory.IMPLEMENTATION: [
                "implement", "create", "build", "add", "new feature",
                "develop", "code", "write", "function", "class",
            ],
            TopicCategory.REFACTORING: [
                "refactor", "clean", "improve", "restructure", "optimize",
                "simplify", "reorganize", "modernize", "upgrade",
            ],
            TopicCategory.TESTING: [
                "test", "unit test", "integration", "coverage", "assert",
                "mock", "fixture", "pytest", "jest", "spec",
            ],
            TopicCategory.ARCHITECTURE: [
                "architecture", "design", "pattern", "structure", "layer",
                "module", "service", "component", "interface", "api",
            ],
            TopicCategory.PERFORMANCE: [
                "performance", "slow", "fast", "optimize", "memory",
                "cpu", "latency", "throughput", "cache", "profile",
            ],
            TopicCategory.SECURITY: [
                "security", "auth", "permission", "vulnerability", "inject",
                "xss", "csrf", "token", "encrypt", "password",
            ],
            TopicCategory.DOCUMENTATION: [
                "document", "doc", "readme", "comment", "explain",
                "docstring", "api doc", "specification",
            ],
            TopicCategory.CONFIGURATION: [
                "config", "setting", "environment", "env", "setup",
                "install", "deploy", "docker", "kubernetes",
            ],
        }

        # Code pattern regexes
        self._pattern_regexes = {
            PatternType.ERROR_HANDLING: [
                r"try\s*{[\s\S]*?}\s*catch",  # JS/TS try-catch
                r"try:\s*[\s\S]*?except",  # Python try-except
                r"\.catch\s*\(",  # Promise catch
                r"Result<.*,\s*Error>",  # Rust Result
            ],
            PatternType.ASYNC_AWAIT: [
                r"async\s+def\s+\w+",  # Python async def
                r"async\s+function\s+\w+",  # JS async function
                r"await\s+\w+",  # await keyword
                r"\.then\s*\(",  # Promise then
            ],
            PatternType.DATA_VALIDATION: [
                r"@validator|@field_validator",  # Pydantic validators
                r"z\.object|z\.string|z\.number",  # Zod
                r"Joi\.\w+",  # Joi validation
                r"class\s+\w+\(BaseModel\)",  # Pydantic model
            ],
            PatternType.API_DESIGN: [
                r"@router\.\w+|@app\.\w+",  # FastAPI/Flask routes
                r"@Get|@Post|@Put|@Delete",  # NestJS decorators
                r"def\s+get_|def\s+create_|def\s+update_|def\s+delete_",
            ],
            PatternType.DATABASE: [
                r"SELECT\s+[\s\S]*?FROM",  # SQL queries
                r"INSERT\s+INTO",
                r"\.query\s*\(|\.execute\s*\(",  # DB operations
                r"session\.add|session\.commit",  # SQLAlchemy
            ],
            PatternType.TESTING: [
                r"def\s+test_\w+|it\s*\(['\"]",  # Test functions
                r"@pytest\.fixture|beforeEach",  # Fixtures
                r"assert\s+|expect\s*\(",  # Assertions
                r"mock\.|Mock\(|patch\(",  # Mocking
            ],
            PatternType.LOGGING: [
                r"logger\.\w+|logging\.\w+",  # Python logging
                r"console\.\w+",  # JS console
                r"log\.\w+|Log\.\w+",  # Generic logging
            ],
            PatternType.CACHING: [
                r"@cache|@lru_cache|@cached",  # Python caching
                r"redis\.|Redis\(",  # Redis
                r"\.setex\(|\.get\(|\.set\(",  # Cache operations
            ],
            PatternType.AUTHENTICATION: [
                r"jwt\.|JWT|token",  # JWT
                r"@auth|authenticate|authorize",  # Auth decorators
                r"password|hash|bcrypt|argon",  # Password handling
            ],
        }

    async def extract(
        self,
        messages: list[dict[str, str]],
        context: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        """
        Extract knowledge from conversation messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            context: Optional context (workspace, files, etc.)

        Returns:
            ExtractionResult with topics, patterns, and solutions
        """
        import time
        start = time.time()

        result = ExtractionResult()

        # Combine all message content
        full_text = "\n".join(m.get("content", "") for m in messages)

        # Extract code blocks
        code_blocks = self._extract_code_blocks(full_text)

        # Rule-based extraction (fast)
        result.topics = self._extract_topics_rule_based(full_text)
        result.patterns = self._extract_patterns_rule_based(code_blocks)
        result.solutions = self._extract_solutions_rule_based(messages)

        # LLM-based extraction (optional, more thorough)
        if self._use_llm and len(full_text) > 100:
            llm_result = await self._extract_with_llm(messages, context)

            # Merge LLM results
            result.topics.extend(llm_result.topics)
            result.patterns.extend(llm_result.patterns)
            result.solutions.extend(llm_result.solutions)
            result.raw_insights = llm_result.raw_insights

        # Deduplicate
        result.topics = self._dedupe_topics(result.topics)
        result.patterns = self._dedupe_patterns(result.patterns)
        result.solutions = self._dedupe_solutions(result.solutions)

        result.extraction_time_ms = int((time.time() - start) * 1000)

        return result

    def _extract_code_blocks(self, text: str) -> list[dict[str, str]]:
        """Extract code blocks with language info."""
        blocks = []

        # Match ```language\ncode\n```
        pattern = r"```(\w*)\n([\s\S]*?)```"
        matches = re.findall(pattern, text)

        for lang, code in matches:
            blocks.append({
                "language": lang or "unknown",
                "code": code.strip(),
            })

        return blocks

    def _extract_topics_rule_based(self, text: str) -> list[Topic]:
        """Extract topics using keyword matching."""
        topics = []
        text_lower = text.lower()

        for category, keywords in self._topic_keywords.items():
            matched_keywords = [kw for kw in keywords if kw in text_lower]

            if matched_keywords:
                # Calculate confidence based on keyword frequency
                frequency = sum(text_lower.count(kw) for kw in matched_keywords)
                confidence = min(0.9, 0.3 + (len(matched_keywords) * 0.1))

                # Generate topic name from most frequent keyword
                main_keyword = max(matched_keywords, key=lambda k: text_lower.count(k))

                topics.append(Topic(
                    name=f"{main_keyword.title()} Discussion",
                    category=category,
                    confidence=confidence,
                    keywords=matched_keywords,
                    frequency=frequency,
                ))

        return topics

    def _extract_patterns_rule_based(
        self, code_blocks: list[dict[str, str]]
    ) -> list[CodePattern]:
        """Extract code patterns using regex matching."""
        patterns = []

        for block in code_blocks:
            code = block["code"]
            lang = block["language"]

            for pattern_type, regexes in self._pattern_regexes.items():
                for regex in regexes:
                    if re.search(regex, code, re.IGNORECASE):
                        # Extract a snippet around the match
                        match = re.search(regex, code, re.IGNORECASE)
                        if match:
                            start = max(0, match.start() - 50)
                            end = min(len(code), match.end() + 100)
                            snippet = code[start:end]

                            patterns.append(CodePattern(
                                name=f"{pattern_type.value.replace('_', ' ').title()}",
                                pattern_type=pattern_type,
                                description=f"Found {pattern_type.value} pattern",
                                example_code=snippet,
                                language=lang,
                            ))
                        break  # One pattern per type per block

        return patterns

    def _extract_solutions_rule_based(
        self, messages: list[dict[str, str]]
    ) -> list[ProblemSolution]:
        """Extract problem-solution pairs from conversation flow."""
        solutions = []

        # Look for problem indicators in user messages
        problem_indicators = [
            "error", "bug", "issue", "problem", "not working",
            "fails", "broken", "help", "how do i", "can't",
        ]

        # Look for solution indicators in assistant messages
        solution_indicators = [
            "try", "you can", "here's", "solution", "fix",
            "change", "update", "modify", "add", "remove",
        ]

        for i, msg in enumerate(messages):
            if msg.get("role") != "user":
                continue

            content_lower = msg.get("content", "").lower()

            # Check if this is a problem message
            has_problem = any(ind in content_lower for ind in problem_indicators)

            if has_problem and i + 1 < len(messages):
                # Look at next message for solution
                next_msg = messages[i + 1]
                if next_msg.get("role") == "assistant":
                    next_content = next_msg.get("content", "")
                    next_lower = next_content.lower()

                    has_solution = any(ind in next_lower for ind in solution_indicators)

                    if has_solution:
                        # Extract tags from content
                        tags = []
                        for category, keywords in self._topic_keywords.items():
                            if any(kw in content_lower or kw in next_lower for kw in keywords):
                                tags.append(category.value)

                        solutions.append(ProblemSolution(
                            problem=msg.get("content", "")[:500],
                            solution=next_content[:1000],
                            context="Extracted from conversation",
                            tags=tags[:5],
                        ))

        return solutions

    async def _extract_with_llm(
        self,
        messages: list[dict[str, str]],
        context: dict[str, Any] | None,
    ) -> ExtractionResult:
        """Extract knowledge using LLM for deeper understanding."""
        import httpx

        result = ExtractionResult()

        # Build prompt for LLM
        conversation = "\n".join(
            f"{m.get('role', 'unknown').upper()}: {m.get('content', '')[:500]}"
            for m in messages[-10:]  # Last 10 messages
        )

        prompt = f"""Analyze this coding conversation and extract insights.

CONVERSATION:
{conversation}

Extract:
1. TOPICS: What subjects were discussed? (list 2-3 main topics)
2. PATTERNS: What code patterns or practices were shown? (list any notable ones)
3. SOLUTIONS: What problems were solved and how? (list problem->solution pairs)
4. INSIGHTS: Any other useful learnings? (list 1-2 key insights)

Respond in this format:
TOPICS: topic1, topic2, topic3
PATTERNS: pattern1 - description; pattern2 - description
SOLUTIONS: problem1 -> solution1; problem2 -> solution2
INSIGHTS: insight1; insight2"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._ollama_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 500,
                        },
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    llm_response = data.get("response", "")

                    # Parse LLM response
                    result = self._parse_llm_response(llm_response)

        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")

        return result

    def _parse_llm_response(self, response: str) -> ExtractionResult:
        """Parse structured response from LLM."""
        result = ExtractionResult()

        lines = response.strip().split("\n")

        for line in lines:
            line = line.strip()

            if line.startswith("TOPICS:"):
                topics_str = line.replace("TOPICS:", "").strip()
                for topic_name in topics_str.split(","):
                    topic_name = topic_name.strip()
                    if topic_name:
                        result.topics.append(Topic(
                            name=topic_name,
                            category=self._categorize_topic(topic_name),
                            confidence=0.7,
                            keywords=[topic_name.lower()],
                        ))

            elif line.startswith("PATTERNS:"):
                patterns_str = line.replace("PATTERNS:", "").strip()
                for pattern in patterns_str.split(";"):
                    if " - " in pattern:
                        name, desc = pattern.split(" - ", 1)
                        result.patterns.append(CodePattern(
                            name=name.strip(),
                            pattern_type=PatternType.OTHER,
                            description=desc.strip(),
                            example_code="",
                            language="unknown",
                        ))

            elif line.startswith("SOLUTIONS:"):
                solutions_str = line.replace("SOLUTIONS:", "").strip()
                for solution in solutions_str.split(";"):
                    if " -> " in solution:
                        problem, sol = solution.split(" -> ", 1)
                        result.solutions.append(ProblemSolution(
                            problem=problem.strip(),
                            solution=sol.strip(),
                            context="LLM extracted",
                        ))

            elif line.startswith("INSIGHTS:"):
                insights_str = line.replace("INSIGHTS:", "").strip()
                result.raw_insights = [
                    i.strip() for i in insights_str.split(";") if i.strip()
                ]

        return result

    def _categorize_topic(self, topic_name: str) -> TopicCategory:
        """Categorize a topic name."""
        topic_lower = topic_name.lower()

        for category, keywords in self._topic_keywords.items():
            if any(kw in topic_lower for kw in keywords):
                return category

        return TopicCategory.GENERAL

    def _dedupe_topics(self, topics: list[Topic]) -> list[Topic]:
        """Deduplicate topics by name."""
        seen = {}
        for topic in topics:
            key = topic.name.lower()
            if key in seen:
                seen[key].frequency += topic.frequency
            else:
                seen[key] = topic
        return list(seen.values())

    def _dedupe_patterns(self, patterns: list[CodePattern]) -> list[CodePattern]:
        """Deduplicate patterns by ID."""
        seen = {}
        for pattern in patterns:
            if pattern.pattern_id in seen:
                seen[pattern.pattern_id].frequency += 1
            else:
                seen[pattern.pattern_id] = pattern
        return list(seen.values())

    def _dedupe_solutions(self, solutions: list[ProblemSolution]) -> list[ProblemSolution]:
        """Deduplicate solutions by ID."""
        seen = {}
        for solution in solutions:
            if solution.pair_id not in seen:
                seen[solution.pair_id] = solution
        return list(seen.values())


def create_knowledge_extractor(
    use_llm: bool = True,
    model: str = "qwen2.5-coder:7b",
) -> KnowledgeExtractor:
    """Create a knowledge extractor instance."""
    import os

    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    return KnowledgeExtractor(
        ollama_url=ollama_url,
        model=model,
        use_llm=use_llm,
    )
