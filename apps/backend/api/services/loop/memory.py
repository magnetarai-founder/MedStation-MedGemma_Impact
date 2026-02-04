"""
Working Memory

Short-term memory for the agentic loop.
Manages context, learned patterns, and extracted facts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .models import Decision, Observation, Reflection


@dataclass
class MemoryEntry:
    """A single entry in working memory"""

    key: str
    value: Any
    entry_type: str  # "fact", "pattern", "observation", "reflection"
    importance: float = 0.5  # 0.0 - 1.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    access_count: int = 0
    last_accessed: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def touch(self) -> None:
        """Mark entry as accessed"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow().isoformat()


class WorkingMemory:
    """
    Short-term memory for agentic loop context.

    Manages:
    - Observation history (with summarization)
    - Extracted facts (file paths, symbols, patterns found)
    - Learned patterns (what works, what doesn't)
    - Relevant context for LLM prompts
    """

    # Maximum entries before pruning
    MAX_OBSERVATIONS = 20
    MAX_REFLECTIONS = 10
    MAX_FACTS = 50
    MAX_PATTERNS = 20

    # Token budget for context
    MAX_CONTEXT_TOKENS = 4000

    def __init__(self):
        # History
        self.observations: list[Observation] = []
        self.reflections: list[Reflection] = []
        self.decisions: list[Decision] = []

        # Extracted knowledge
        self.facts: dict[str, MemoryEntry] = {}
        self.patterns: list[MemoryEntry] = []

        # Summarized history (when observations are pruned)
        self.summarized_history: str = ""

    def add_observation(self, observation: Observation) -> None:
        """Add an observation to memory"""
        self.observations.append(observation)

        # Extract facts from observation
        self._extract_facts(observation)

        # Prune if needed
        if len(self.observations) > self.MAX_OBSERVATIONS:
            self._summarize_old_observations()

    def add_reflection(self, reflection: Reflection) -> None:
        """Add a reflection to memory"""
        self.reflections.append(reflection)

        # Extract patterns from reflection
        self._extract_patterns(reflection)

        # Prune if needed
        if len(self.reflections) > self.MAX_REFLECTIONS:
            self.reflections = self.reflections[-self.MAX_REFLECTIONS:]

    def add_decision(self, decision: Decision) -> None:
        """Add a decision to memory"""
        self.decisions.append(decision)

    def add_fact(self, key: str, value: Any, importance: float = 0.5) -> None:
        """
        Add or update a fact.

        Args:
            key: Fact identifier (e.g., "main_file", "error_type")
            value: The fact value
            importance: How important this fact is (0.0 - 1.0)
        """
        if key in self.facts:
            self.facts[key].value = value
            self.facts[key].touch()
        else:
            self.facts[key] = MemoryEntry(
                key=key,
                value=value,
                entry_type="fact",
                importance=importance,
            )

        # Prune low-importance facts if over limit
        if len(self.facts) > self.MAX_FACTS:
            self._prune_facts()

    def add_pattern(self, pattern: str, importance: float = 0.5) -> None:
        """
        Add a learned pattern.

        Args:
            pattern: Description of the pattern
            importance: How important this pattern is
        """
        # Check for duplicate
        for existing in self.patterns:
            if existing.value == pattern:
                existing.touch()
                return

        self.patterns.append(
            MemoryEntry(
                key=f"pattern_{len(self.patterns)}",
                value=pattern,
                entry_type="pattern",
                importance=importance,
            )
        )

        # Prune if over limit
        if len(self.patterns) > self.MAX_PATTERNS:
            self._prune_patterns()

    def get_fact(self, key: str) -> Any:
        """Get a fact value by key"""
        if key in self.facts:
            self.facts[key].touch()
            return self.facts[key].value
        return None

    def get_recent_observations(self, n: int = 5) -> list[Observation]:
        """Get the N most recent observations"""
        return self.observations[-n:]

    def get_recent_reflections(self, n: int = 3) -> list[Reflection]:
        """Get the N most recent reflections"""
        return self.reflections[-n:]

    def get_recent_decisions(self, n: int = 3) -> list[Decision]:
        """Get the N most recent decisions"""
        return self.decisions[-n:]

    def get_important_facts(self, min_importance: float = 0.5) -> dict[str, Any]:
        """Get facts above importance threshold"""
        return {
            key: entry.value
            for key, entry in self.facts.items()
            if entry.importance >= min_importance
        }

    def get_relevant_patterns(self, query: str = "") -> list[str]:
        """Get patterns, optionally filtered by relevance to query"""
        # For now, return most accessed patterns
        sorted_patterns = sorted(
            self.patterns, key=lambda p: p.access_count, reverse=True
        )
        return [p.value for p in sorted_patterns[:5]]

    def to_context_string(self, max_length: int = 2000) -> str:
        """
        Format memory as context string for LLM.

        Args:
            max_length: Maximum characters to return

        Returns:
            Formatted context string
        """
        sections = []

        # Add summarized history if any
        if self.summarized_history:
            sections.append(f"Previous History:\n{self.summarized_history}")

        # Add recent observations
        recent_obs = self.get_recent_observations(5)
        if recent_obs:
            obs_lines = ["Recent Actions:"]
            for obs in recent_obs:
                status = "✓" if obs.success else "✗"
                obs_lines.append(f"  {status} {obs.action_description[:60]}")
            sections.append("\n".join(obs_lines))

        # Add important facts
        facts = self.get_important_facts(0.6)
        if facts:
            fact_lines = ["Known Facts:"]
            for key, value in list(facts.items())[:10]:
                fact_lines.append(f"  - {key}: {str(value)[:50]}")
            sections.append("\n".join(fact_lines))

        # Add learned patterns
        patterns = self.get_relevant_patterns()
        if patterns:
            pattern_lines = ["Learned Patterns:"]
            for pattern in patterns[:5]:
                pattern_lines.append(f"  - {pattern}")
            sections.append("\n".join(pattern_lines))

        # Combine and truncate
        result = "\n\n".join(sections)
        if len(result) > max_length:
            result = result[:max_length - 3] + "..."

        return result

    def _extract_facts(self, observation: Observation) -> None:
        """Extract facts from observation"""
        # Files involved
        for file_path in observation.files_modified:
            self.add_fact(f"modified_file:{file_path}", True, 0.7)

        for file_path in observation.files_created:
            self.add_fact(f"created_file:{file_path}", True, 0.8)

        # Error types
        if observation.error:
            error_type = self._extract_error_type(observation.error)
            if error_type:
                self.add_fact("last_error_type", error_type, 0.9)
                self.add_fact("last_error_message", observation.error, 0.8)

        # Commands run
        for cmd in observation.commands_run:
            self.add_fact(f"command_run:{cmd[:20]}", cmd, 0.5)

    def _extract_error_type(self, error: str) -> str | None:
        """Extract error type from error message"""
        import re

        # Common Python errors
        match = re.search(
            r"(TypeError|ValueError|KeyError|AttributeError|ImportError|"
            r"SyntaxError|RuntimeError|FileNotFoundError|PermissionError)",
            error,
        )
        if match:
            return match.group(1)

        # HTTP errors
        match = re.search(r"\b(4\d{2}|5\d{2})\b", error)
        if match:
            return f"HTTP {match.group(1)}"

        return None

    def _extract_patterns(self, reflection: Reflection) -> None:
        """Extract patterns from reflection"""
        # Add lessons learned as patterns
        for lesson in reflection.lessons_learned:
            self.add_pattern(lesson, importance=0.7)

        # Track what works and what doesn't
        if reflection.what_went_well:
            for item in reflection.what_went_well:
                self.add_pattern(f"SUCCESS: {item}", importance=0.6)

        if reflection.what_went_wrong:
            for item in reflection.what_went_wrong:
                self.add_pattern(f"ISSUE: {item}", importance=0.8)

    def _summarize_old_observations(self) -> None:
        """Summarize and prune old observations"""
        if len(self.observations) <= self.MAX_OBSERVATIONS // 2:
            return

        # Keep recent half
        keep_count = self.MAX_OBSERVATIONS // 2
        old_observations = self.observations[:-keep_count]
        self.observations = self.observations[-keep_count:]

        # Summarize old observations
        summary_parts = []

        # Count successes and failures
        successes = sum(1 for o in old_observations if o.success)
        failures = len(old_observations) - successes

        summary_parts.append(
            f"Previous {len(old_observations)} actions: "
            f"{successes} succeeded, {failures} failed"
        )

        # Note any files that were modified
        all_files = set()
        for obs in old_observations:
            all_files.update(obs.files_modified)
            all_files.update(obs.files_created)

        if all_files:
            summary_parts.append(f"Files touched: {', '.join(list(all_files)[:5])}")

        self.summarized_history = "; ".join(summary_parts)

    def _prune_facts(self) -> None:
        """Remove low-importance, rarely accessed facts"""
        # Sort by importance and access count
        sorted_facts = sorted(
            self.facts.items(),
            key=lambda x: (x[1].importance, x[1].access_count),
            reverse=True,
        )

        # Keep top N
        self.facts = dict(sorted_facts[:self.MAX_FACTS])

    def _prune_patterns(self) -> None:
        """Remove least useful patterns"""
        # Sort by access count and importance
        self.patterns.sort(
            key=lambda p: (p.access_count, p.importance), reverse=True
        )
        self.patterns = self.patterns[:self.MAX_PATTERNS]

    def clear(self) -> None:
        """Clear all memory"""
        self.observations = []
        self.reflections = []
        self.decisions = []
        self.facts = {}
        self.patterns = []
        self.summarized_history = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize memory state"""
        return {
            "observations_count": len(self.observations),
            "reflections_count": len(self.reflections),
            "decisions_count": len(self.decisions),
            "facts_count": len(self.facts),
            "patterns_count": len(self.patterns),
            "has_summarized_history": bool(self.summarized_history),
            "facts": {k: v.value for k, v in list(self.facts.items())[:10]},
            "patterns": [p.value for p in self.patterns[:5]],
        }
