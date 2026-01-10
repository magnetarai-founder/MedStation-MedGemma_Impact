#!/usr/bin/env python3
"""
Recursive NLP Prompt Library for ElohimOS
Breaks complex prompts into optimized sub-tasks with Metal 4 + ANE acceleration

Extracted modules (P2 decomposition):
- recursive_prompt_constants.py: Safety limits, enums, patterns, and helper functions
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Import from extracted module (P2 decomposition)
from api.recursive_prompt_constants import (
    # Safety constants
    MAX_RECURSION_DEPTH,
    TIMEOUT_PER_STEP_SECONDS,
    GLOBAL_TIMEOUT_SECONDS,
    MAX_RETRIES,
    BACKOFF_BASE_SECONDS,
    MAX_CONCURRENT_EXECUTIONS,
    # Enums
    TaskComplexity,
    ExecutionBackend,
    # Patterns and data
    DECOMPOSITION_PATTERNS,
    ANE_MODEL,
    METAL_MODEL,
    ANE_MAX_TOKENS,
    METAL_MAX_TOKENS,
    ESTIMATED_SINGLE_PROMPT_TIME_MS,
    # Helper functions
    get_step_time_estimate,
    get_power_estimate,
    select_backend_for_complexity,
    detect_query_type,
)

logger = logging.getLogger(__name__)


@dataclass
class PromptStep:
    """Single step in recursive prompt execution"""
    step_number: int
    description: str
    prompt: str
    complexity: TaskComplexity
    backend: ExecutionBackend
    parent_step: Optional[int] = None
    depends_on: List[int] = None
    depth: int = 0              # Track recursion depth
    retry_count: int = 0        # Track retries for this step

    def __post_init__(self) -> None:
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class StepResult:
    """Result from executing a prompt step"""
    step_number: int
    output: str
    execution_time_ms: float
    backend_used: ExecutionBackend
    tokens_used: int = 0
    cached: bool = False
    retry_count: int = 0        # How many retries needed
    timed_out: bool = False     # Whether step timed out
    error: Optional[str] = None # Error message if failed


@dataclass
class RecursiveExecutionPlan:
    """Complete execution plan for a recursive prompt"""
    original_query: str
    steps: List[PromptStep]
    total_estimated_time_ms: float
    estimated_power_usage_w: float


class PromptDecomposer:
    """Breaks complex prompts into optimized sub-tasks"""

    def __init__(self):
        self.decomposition_patterns = DECOMPOSITION_PATTERNS

    def decompose(self, query: str) -> RecursiveExecutionPlan:
        """Break query into optimized execution steps"""

        # Detect query type using helper function
        detected_type = detect_query_type(query)

        logger.info(f"📋 Detected query type: {detected_type}")

        # Build execution steps
        pattern = self.decomposition_patterns[detected_type]
        steps = []

        for i, step_template in enumerate(pattern['steps']):
            backend = select_backend_for_complexity(step_template['complexity'])

            step = PromptStep(
                step_number=i + 1,
                description=step_template['description'],
                prompt=self._generate_step_prompt(query, step_template['description'], i),
                complexity=step_template['complexity'],
                backend=backend,
                depends_on=[i] if i > 0 else []
            )
            steps.append(step)

        # Estimate total time and power using helper functions
        total_time = sum(get_step_time_estimate(s.complexity) for s in steps)
        avg_power = sum(get_power_estimate(s.backend) for s in steps) / len(steps)

        plan = RecursiveExecutionPlan(
            original_query=query,
            steps=steps,
            total_estimated_time_ms=total_time,
            estimated_power_usage_w=avg_power
        )

        logger.info(f"📊 Execution plan: {len(steps)} steps, ~{total_time:.0f}ms, ~{avg_power:.1f}W avg")

        return plan

    def _generate_step_prompt(self, original_query: str, step_desc: str, step_num: int) -> str:
        """Generate specific prompt for this step"""
        if step_num == 0:
            # First step - analyze the original query
            return f"For the query '{original_query}', {step_desc.lower()}. Be specific and concise."
        else:
            # Subsequent steps - reference previous results
            return f"Based on the previous analysis, {step_desc.lower()} for: '{original_query}'"


class RecursiveExecutor:
    """Executes recursive prompt plans with Metal 4 + ANE optimization"""

    def __init__(self):
        self.cache = {}  # Metal 4 dynamic caching simulation
        self.execution_history = []
        self.active_executions = 0  # Track concurrent executions
        self.max_concurrent = MAX_CONCURRENT_EXECUTIONS

    async def execute_plan(self, plan: RecursiveExecutionPlan, ollama_client: Any = None) -> List[StepResult]:
        """Execute the recursive prompt plan with safety limits"""

        logger.info(f"🚀 Executing {len(plan.steps)} step plan...")

        # SAFETY: Global timeout
        global_start = time.time()

        results = []
        context = ""  # Accumulate context from previous steps

        for step in plan.steps:
            # SAFETY: Check global timeout
            elapsed = time.time() - global_start
            if elapsed > GLOBAL_TIMEOUT_SECONDS:
                logger.warning(f"⚠️ Global timeout ({GLOBAL_TIMEOUT_SECONDS}s) - stopping execution")
                break

            # SAFETY: Check recursion depth
            if step.depth > MAX_RECURSION_DEPTH:
                logger.warning(f"⚠️ Max recursion depth ({MAX_RECURSION_DEPTH}) reached - skipping step")
                continue

            # SAFETY: Limit concurrent executions
            while self.active_executions >= self.max_concurrent:
                await asyncio.sleep(0.1)

            # Check dependencies
            if step.depends_on:
                # Wait for dependencies (in real version, this would be async)
                pass

            # Execute step with retries
            result = await self._execute_step_with_retry(step, context, ollama_client)
            results.append(result)

            # Update context for next step (only if successful)
            if not result.error:
                context += f"\nStep {step.step_number} ({step.description}): {result.output}\n"
                logger.info(f"  ✓ Step {step.step_number}: {result.execution_time_ms:.0f}ms ({result.backend_used.value})")
            else:
                logger.error(f"  ✗ Step {step.step_number} failed: {result.error}")

        total_time = sum(r.execution_time_ms for r in results)
        logger.info(f"✅ Plan completed in {total_time:.0f}ms")

        # Store in history for learning
        self.execution_history.append({
            'query': plan.original_query,
            'steps': len(plan.steps),
            'total_time_ms': total_time,
            'timestamp': time.time()
        })

        return results

    async def _execute_step_with_retry(self, step: PromptStep, context: str, ollama_client: Any) -> StepResult:
        """Execute step with exponential backoff retry"""

        last_error = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                # SAFETY: Per-step timeout
                result = await asyncio.wait_for(
                    self._execute_step(step, context, ollama_client),
                    timeout=TIMEOUT_PER_STEP_SECONDS
                )
                result.retry_count = attempt
                return result

            except asyncio.TimeoutError:
                last_error = f"Step timed out after {TIMEOUT_PER_STEP_SECONDS}s"
                logger.warning(f"  ⚠️ Step {step.step_number} timed out (attempt {attempt + 1}/{MAX_RETRIES + 1})")

                if attempt < MAX_RETRIES:
                    # Exponential backoff
                    backoff = BACKOFF_BASE_SECONDS * (2 ** attempt)
                    logger.debug(f"  ⏳ Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)

            except Exception as e:
                last_error = str(e)
                logger.error(f"  ✗ Step {step.step_number} error: {e} (attempt {attempt + 1}/{MAX_RETRIES + 1})")

                if attempt < MAX_RETRIES:
                    backoff = BACKOFF_BASE_SECONDS * (2 ** attempt)
                    await asyncio.sleep(backoff)

        # All retries failed - return error result
        return StepResult(
            step_number=step.step_number,
            output="",
            execution_time_ms=0,
            backend_used=step.backend,
            retry_count=MAX_RETRIES,
            timed_out=isinstance(last_error, str) and "timed out" in last_error.lower(),
            error=last_error
        )

    async def _execute_step(self, step: PromptStep, context: str, ollama_client: Any) -> StepResult:
        """Execute a single prompt step"""

        start_time = time.time()

        # Build full prompt with context
        full_prompt = step.prompt
        if context:
            full_prompt = f"Context from previous steps:\n{context}\n\nCurrent task: {step.prompt}"

        # Check cache (Metal 4 dynamic caching)
        cache_key = f"{step.description}:{hash(full_prompt)}"
        if cache_key in self.cache:
            logger.debug(f"    💾 Cache hit for step {step.step_number}")
            cached_result = self.cache[cache_key]
            return StepResult(
                step_number=step.step_number,
                output=cached_result,
                execution_time_ms=10,  # Instant from cache
                backend_used=step.backend,
                cached=True
            )

        # Execute based on backend
        if step.backend == ExecutionBackend.ANE:
            output = await self._execute_on_ane(full_prompt, ollama_client)
        elif step.backend == ExecutionBackend.METAL_GPU:
            output = await self._execute_on_metal(full_prompt, ollama_client)
        else:  # CPU
            output = await self._execute_on_cpu(full_prompt, ollama_client)

        execution_time_ms = (time.time() - start_time) * 1000

        # Store in cache
        self.cache[cache_key] = output

        return StepResult(
            step_number=step.step_number,
            output=output,
            execution_time_ms=execution_time_ms,
            backend_used=step.backend,
            cached=False
        )

    async def _execute_on_ane(self, prompt: str, ollama_client: Any) -> str:
        """Execute on Apple Neural Engine (simulated - uses fast model)"""
        try:
            if ollama_client:
                response = await ollama_client.generate(
                    model=ANE_MODEL,
                    prompt=prompt,
                    options={"num_predict": ANE_MAX_TOKENS}
                )
                return response.get('response', '')
        except Exception as e:
            logger.error(f"ANE execution failed: {e}")

        # Fallback
        return f"[ANE simulated response for: {prompt[:50]}...]"

    async def _execute_on_metal(self, prompt: str, ollama_client: Any) -> str:
        """Execute on Metal GPU (full power model)"""
        try:
            if ollama_client:
                response = await ollama_client.generate(
                    model=METAL_MODEL,
                    prompt=prompt,
                    options={"num_predict": METAL_MAX_TOKENS}
                )
                return response.get('response', '')
        except Exception as e:
            logger.error(f"Metal execution failed: {e}")

        return f"[Metal GPU simulated response for: {prompt[:50]}...]"

    async def _execute_on_cpu(self, prompt: str, ollama_client: Any) -> str:
        """Execute on CPU (fallback)"""
        return await self._execute_on_metal(prompt, ollama_client)


class RecursivePromptLibrary:
    """Main interface for recursive prompt execution"""

    def __init__(self):
        self.decomposer = PromptDecomposer()
        self.executor = RecursiveExecutor()
        self.stats = {
            'total_queries': 0,
            'total_time_saved_ms': 0,
            'cache_hits': 0,
        }

    async def process_query(self, query: str, ollama_client: Any = None) -> Dict[str, Any]:
        """
        Process a query using recursive decomposition

        Returns:
            {
                'final_answer': str,
                'steps_executed': int,
                'total_time_ms': float,
                'plan': RecursiveExecutionPlan,
                'results': List[StepResult]
            }
        """

        logger.info(f"🔄 Processing recursive query: {query[:80]}...")

        # Decompose into execution plan
        plan = self.decomposer.decompose(query)

        # Execute plan
        results = await self.executor.execute_plan(plan, ollama_client)

        # Combine results into final answer
        final_answer = self._synthesize_final_answer(query, results)

        # Update stats
        total_time = sum(r.execution_time_ms for r in results)
        cache_hits = sum(1 for r in results if r.cached)

        self.stats['total_queries'] += 1
        self.stats['cache_hits'] += cache_hits

        # Estimate time saved vs single prompt
        time_saved = max(0, ESTIMATED_SINGLE_PROMPT_TIME_MS - total_time)
        self.stats['total_time_saved_ms'] += time_saved

        return {
            'final_answer': final_answer,
            'steps_executed': len(results),
            'total_time_ms': total_time,
            'time_saved_ms': time_saved,
            'cache_hits': cache_hits,
            'plan': plan,
            'results': results
        }

    def _synthesize_final_answer(self, query: str, results: List[StepResult]) -> str:
        """Combine step results into coherent final answer"""

        if not results:
            return "No results generated."

        # Use the last step as the primary answer
        final_step = results[-1]

        # If there are multiple steps, create a structured response
        if len(results) > 1:
            answer_parts = [f"Analysis of: {query}\n"]

            for result in results:
                if result.output and len(result.output) > 10:
                    answer_parts.append(f"• {result.output}")

            return "\n\n".join(answer_parts)

        return final_step.output

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            **self.stats,
            'avg_time_saved_per_query_ms': (
                self.stats['total_time_saved_ms'] / self.stats['total_queries']
                if self.stats['total_queries'] > 0 else 0
            ),
            'cache_hit_rate': (
                self.stats['cache_hits'] / (self.stats['total_queries'] * 3)  # Avg 3 steps
                if self.stats['total_queries'] > 0 else 0
            )
        }


# Singleton instance
_recursive_library = None


def get_recursive_library() -> RecursivePromptLibrary:
    """Get singleton instance"""
    global _recursive_library
    if _recursive_library is None:
        _recursive_library = RecursivePromptLibrary()
        logger.info("🧠 Recursive Prompt Library initialized")
    return _recursive_library
