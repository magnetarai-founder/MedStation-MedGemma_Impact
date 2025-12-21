#!/usr/bin/env python3
"""
Recursive NLP Prompt Library for ElohimOS
Breaks complex prompts into optimized sub-tasks with Metal 4 + ANE acceleration
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# ===== SAFETY LIMITS (For Missionary Field Use) =====
MAX_RECURSION_DEPTH = 5           # Prevent infinite loops
MAX_TOKENS_PER_STEP = 2000        # Limit token usage per step
TIMEOUT_PER_STEP_SECONDS = 15     # Kill slow steps
GLOBAL_TIMEOUT_SECONDS = 60       # Kill entire query if too slow
MAX_RETRIES = 2                   # Retry failed steps
BACKOFF_BASE_SECONDS = 1          # Exponential backoff base


class TaskComplexity(Enum):
    """Complexity levels for routing to ANE vs Metal GPU"""
    SIMPLE = "simple"      # ANE: 0.1-0.5s, <0.5W
    MODERATE = "moderate"  # Metal: 0.5-2s, 2-5W
    COMPLEX = "complex"    # Metal: 2-10s, 5-10W


class ExecutionBackend(Enum):
    """Where to run the inference"""
    ANE = "ane"           # Apple Neural Engine (low power, fast for small tasks)
    METAL_GPU = "metal"   # Metal GPU (high power, fast for big tasks)
    CPU = "cpu"           # CPU fallback


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
        self.decomposition_patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[str, Any]:
        """Load decomposition patterns for common query types"""
        return {
            'data_analysis': {
                'keywords': ['analyze', 'data', 'sales', 'trends', 'patterns'],
                'steps': [
                    {'description': 'Identify data requirements', 'complexity': TaskComplexity.SIMPLE},
                    {'description': 'Generate SQL queries', 'complexity': TaskComplexity.MODERATE},
                    {'description': 'Execute analysis', 'complexity': TaskComplexity.COMPLEX},
                    {'description': 'Interpret results', 'complexity': TaskComplexity.SIMPLE},
                ]
            },
            'missionary_report': {
                'keywords': ['field', 'report', 'missionary', 'health', 'security'],
                'steps': [
                    {'description': 'Extract key information', 'complexity': TaskComplexity.SIMPLE},
                    {'description': 'Categorize by type', 'complexity': TaskComplexity.SIMPLE},
                    {'description': 'Identify risks/concerns', 'complexity': TaskComplexity.MODERATE},
                    {'description': 'Generate recommendations', 'complexity': TaskComplexity.MODERATE},
                ]
            },
            'message_compose': {
                'keywords': ['send', 'message', 'email', 'update', 'notify'],
                'steps': [
                    {'description': 'Identify recipients', 'complexity': TaskComplexity.SIMPLE},
                    {'description': 'Detect language preferences', 'complexity': TaskComplexity.SIMPLE},
                    {'description': 'Compose message', 'complexity': TaskComplexity.MODERATE},
                    {'description': 'Translate if needed', 'complexity': TaskComplexity.MODERATE},
                ]
            },
            'prediction': {
                'keywords': ['predict', 'forecast', 'estimate', 'project'],
                'steps': [
                    {'description': 'Gather historical data', 'complexity': TaskComplexity.MODERATE},
                    {'description': 'Identify trends', 'complexity': TaskComplexity.COMPLEX},
                    {'description': 'Apply forecasting model', 'complexity': TaskComplexity.COMPLEX},
                    {'description': 'Generate prediction', 'complexity': TaskComplexity.SIMPLE},
                ]
            },
            'general': {
                'keywords': [],  # Fallback
                'steps': [
                    {'description': 'Understand question', 'complexity': TaskComplexity.SIMPLE},
                    {'description': 'Generate answer', 'complexity': TaskComplexity.MODERATE},
                ]
            }
        }

    def decompose(self, query: str) -> RecursiveExecutionPlan:
        """Break query into optimized execution steps"""

        # Detect query type
        query_lower = query.lower()
        detected_type = 'general'

        for pattern_type, pattern_data in self.decomposition_patterns.items():
            if pattern_type == 'general':
                continue
            keywords = pattern_data['keywords']
            if any(kw in query_lower for kw in keywords):
                detected_type = pattern_type
                break

        logger.info(f"📋 Detected query type: {detected_type}")

        # Build execution steps
        pattern = self.decomposition_patterns[detected_type]
        steps = []

        for i, step_template in enumerate(pattern['steps']):
            backend = self._select_backend(step_template['complexity'])

            step = PromptStep(
                step_number=i + 1,
                description=step_template['description'],
                prompt=self._generate_step_prompt(query, step_template['description'], i),
                complexity=step_template['complexity'],
                backend=backend,
                depends_on=[i] if i > 0 else []
            )
            steps.append(step)

        # Estimate total time and power
        total_time = sum(self._estimate_step_time(s.complexity) for s in steps)
        avg_power = sum(self._estimate_power(s.backend) for s in steps) / len(steps)

        plan = RecursiveExecutionPlan(
            original_query=query,
            steps=steps,
            total_estimated_time_ms=total_time,
            estimated_power_usage_w=avg_power
        )

        logger.info(f"📊 Execution plan: {len(steps)} steps, ~{total_time:.0f}ms, ~{avg_power:.1f}W avg")

        return plan

    def _select_backend(self, complexity: TaskComplexity) -> ExecutionBackend:
        """Choose optimal backend based on task complexity"""
        if complexity == TaskComplexity.SIMPLE:
            return ExecutionBackend.ANE
        elif complexity == TaskComplexity.MODERATE:
            return ExecutionBackend.METAL_GPU
        else:  # COMPLEX
            return ExecutionBackend.METAL_GPU

    def _generate_step_prompt(self, original_query: str, step_desc: str, step_num: int) -> str:
        """Generate specific prompt for this step"""
        if step_num == 0:
            # First step - analyze the original query
            return f"For the query '{original_query}', {step_desc.lower()}. Be specific and concise."
        else:
            # Subsequent steps - reference previous results
            return f"Based on the previous analysis, {step_desc.lower()} for: '{original_query}'"

    def _estimate_step_time(self, complexity: TaskComplexity) -> float:
        """Estimate execution time in milliseconds"""
        estimates = {
            TaskComplexity.SIMPLE: 300,      # 0.3s on ANE
            TaskComplexity.MODERATE: 1000,   # 1s on Metal
            TaskComplexity.COMPLEX: 3000,    # 3s on Metal
        }
        return estimates[complexity]

    def _estimate_power(self, backend: ExecutionBackend) -> float:
        """Estimate power usage in watts"""
        estimates = {
            ExecutionBackend.ANE: 0.2,        # Very low power
            ExecutionBackend.METAL_GPU: 4.0,  # Moderate power
            ExecutionBackend.CPU: 2.0,        # Low-moderate power
        }
        return estimates[backend]


class RecursiveExecutor:
    """Executes recursive prompt plans with Metal 4 + ANE optimization"""

    def __init__(self):
        self.cache = {}  # Metal 4 dynamic caching simulation
        self.execution_history = []
        self.active_executions = 0  # Track concurrent executions
        self.max_concurrent = 3     # Limit concurrent branches

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
        # In practice, this would use a smaller, ANE-optimized model
        # For now, use the fastest Ollama model available
        try:
            if ollama_client:
                response = await ollama_client.generate(
                    model="qwen2.5-coder:1.5b-instruct",  # Smallest/fastest
                    prompt=prompt,
                    options={"num_predict": 128}  # Limit tokens for speed
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
                    model="qwen2.5-coder:7b-instruct",  # Bigger model
                    prompt=prompt,
                    options={"num_predict": 512}
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
        estimated_single_prompt_time = 8000  # Assume 8s for complex single prompt
        time_saved = max(0, estimated_single_prompt_time - total_time)
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
