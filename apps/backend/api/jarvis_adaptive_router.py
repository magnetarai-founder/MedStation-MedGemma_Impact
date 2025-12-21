#!/usr/bin/env python3
"""
Adaptive Router with Learning Integration
Combines enhanced routing with learning system for intelligent, adaptive behavior
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# Import our components
from enhanced_router import EnhancedRouter, RouteResult
from learning_system import LearningSystem, Recommendation
from jarvis_bigquery_memory import JarvisBigQueryMemory
from agent_simple import TaskType, ToolType


@dataclass
class AdaptiveRouteResult(RouteResult):
    """Extended route result with learning insights"""
    recommendations: List[Recommendation] = None
    adjusted_confidence: float = 0.0
    learning_insights: Dict[str, Any] = None
    

class AdaptiveRouter:
    """
    Intelligent adaptive router that:
    - Uses enhanced pattern matching
    - Learns from execution history
    - Adapts to user preferences
    - Provides context-aware recommendations
    """
    
    def __init__(self, memory: JarvisBigQueryMemory = None, 
                 learning: LearningSystem = None):
        # Initialize base components
        self.base_router = EnhancedRouter()
        self.memory = memory or JarvisBigQueryMemory()
        self.learning = learning or LearningSystem(memory=self.memory)
        
        # Track routing decisions for learning
        self.routing_history = []
        
    def route_task(self, command: str, context: Dict = None) -> AdaptiveRouteResult:
        """
        Route task with adaptive learning
        
        Args:
            command: The command to route
            context: Optional context (project, files, etc.)
            
        Returns:
            AdaptiveRouteResult with routing decision and recommendations
        """
        
        # Get base routing result
        base_result = self.base_router.route_task(command)
        
        # Get project context if not provided
        if not context:
            context = {}
            try:
                project_context = self.learning.detect_project_context()
                context['project'] = project_context
            except (AttributeError, OSError):
                pass  # Context detection not available
                
        # Get learning recommendations
        recommendations = self.learning.get_recommendations(command, context)
        
        # Adjust confidence based on historical success
        adjusted_confidence = self._adjust_confidence(
            command, 
            base_result.task_type,
            base_result.tool_type,
            base_result.confidence
        )
        
        # Check for user preferences that might override
        override_result = self._check_preference_override(command, base_result)
        if override_result:
            base_result = override_result
            
        # Get similar successful commands
        similar_commands = self.memory.find_similar_commands(command, limit=3)
        
        # Build learning insights
        project_type = 'unknown'
        if 'project' in context and hasattr(context['project'], 'project_type'):
            project_type = context['project'].project_type
            
        insights = {
            'similar_commands': similar_commands,
            'success_rate': self.learning.get_success_rate(
                command, 
                base_result.tool_type.value
            ),
            'user_preferences': self.learning.get_preferences('tool'),
            'project_type': project_type
        }
        
        # Create adaptive result
        result = AdaptiveRouteResult(
            task_type=base_result.task_type,
            tool_type=base_result.tool_type,
            confidence=base_result.confidence,
            matched_patterns=base_result.matched_patterns,
            reasoning=base_result.reasoning,
            fallback_options=base_result.fallback_options,
            recommendations=recommendations,
            adjusted_confidence=adjusted_confidence,
            learning_insights=insights
        )
        
        # Store routing decision for learning
        self._store_routing_decision(command, result)
        
        return result
        
    def _adjust_confidence(self, command: str, task_type: TaskType, 
                          tool_type: ToolType, base_confidence: float) -> float:
        """Adjust confidence based on historical success"""
        
        # Get success rate for this combination
        success_rate = self.learning.get_success_rate(
            command,
            tool_type.value
        )
        
        # If we have significant history, weight it
        if success_rate > 0 and success_rate != 0.5:  # 0.5 is default/unknown
            # Blend base confidence with historical success
            adjusted = (base_confidence * 0.6) + (success_rate * 0.4)
            return min(1.0, adjusted)
            
        return base_confidence
        
    def _check_preference_override(self, command: str, 
                                   base_result: RouteResult) -> Optional[RouteResult]:
        """Check if user preferences should override routing"""
        
        # Get tool preferences
        tool_prefs = self.learning.get_preferences('tool')
        
        if tool_prefs:
            top_pref = tool_prefs[0]
            
            # If user strongly prefers a tool and confidence is not too high
            if top_pref.confidence > 0.8 and base_result.confidence < 0.7:
                # Map preference to tool type
                tool_map = {
                    'aider': ToolType.AIDER,
                    'ollama': ToolType.OLLAMA,
                    'assistant': ToolType.ASSISTANT,
                    'system': ToolType.SYSTEM
                }
                
                if top_pref.preference in tool_map:
                    preferred_tool = tool_map[top_pref.preference]
                    
                    # Only override for compatible task types
                    if self._is_compatible(base_result.task_type, preferred_tool):
                        # Create override result
                        return RouteResult(
                            task_type=base_result.task_type,
                            tool_type=preferred_tool,
                            confidence=top_pref.confidence,
                            matched_patterns=['user_preference'],
                            reasoning=f"User preference override: {top_pref.preference} (confidence: {top_pref.confidence:.0%})",
                            fallback_options=[(base_result.task_type, base_result.tool_type, base_result.confidence)]
                        )
                        
        return None
        
    def _is_compatible(self, task_type: TaskType, tool_type: ToolType) -> bool:
        """Check if task type is compatible with tool type"""
        
        compatibility = {
            TaskType.CODE_WRITE: [ToolType.AIDER],
            TaskType.CODE_EDIT: [ToolType.AIDER],
            TaskType.BUG_FIX: [ToolType.AIDER],
            TaskType.CODE_REVIEW: [ToolType.ASSISTANT],
            TaskType.TEST_GENERATION: [ToolType.ASSISTANT],
            TaskType.DOCUMENTATION: [ToolType.ASSISTANT],
            TaskType.RESEARCH: [ToolType.ASSISTANT, ToolType.OLLAMA],
            TaskType.EXPLANATION: [ToolType.OLLAMA],
            TaskType.SYSTEM_COMMAND: [ToolType.SYSTEM],
            TaskType.GIT_OPERATION: [ToolType.SYSTEM],
            TaskType.FILE_OPERATION: [ToolType.SYSTEM],
        }
        
        return tool_type in compatibility.get(task_type, [])
        
    def _store_routing_decision(self, command: str, result: AdaptiveRouteResult) -> None:
        """Store routing decision for future learning"""
        
        self.routing_history.append({
            'command': command,
            'task_type': result.task_type.value,
            'tool_type': result.tool_type.value,
            'confidence': result.confidence,
            'adjusted_confidence': result.adjusted_confidence,
            'timestamp': Path.cwd().stat().st_mtime  # Simple timestamp
        })
        
        # Keep history limited
        if len(self.routing_history) > 100:
            self.routing_history = self.routing_history[-100:]
            
    def record_execution_result(self, command: str, tool: str, 
                               success: bool, execution_time: float):
        """Record execution result for learning"""
        
        # Track in learning system
        self.learning.track_execution(command, tool, success, execution_time)
        
        # Store in memory
        task_type = None
        for entry in self.routing_history:
            if entry['command'] == command:
                task_type = entry['task_type']
                break
                
        self.memory.store_command(
            command, 
            task_type or 'unknown',
            tool,
            success,
            execution_time
        )
        
    def route(self, command: str) -> Dict[str, Any]:
        """Simple route interface for compatibility"""
        result = self.route_task(command)
        return {
            'task_type': result.task_type.value if result.task_type else 'unknown',
            'tool': result.tool_type.value if hasattr(result, 'tool_type') and result.tool_type else 'unknown',
            'confidence': result.confidence,
            'model': result.model_name if hasattr(result, 'model_name') else 'unknown',
            'context': result.context if hasattr(result, 'context') else {}
        }
    
    def record_feedback(self, command: str, task_type: str, tool: str, 
                        success: bool, execution_time: float):
        """Record feedback for adaptive learning"""
        # This is an alias for record_execution_result for compatibility
        self.record_execution_result(command, tool, success, execution_time)
    
    def get_routing_stats(self) -> Dict:
        """Get routing statistics"""
        
        stats = {
            'total_routes': len(self.routing_history),
            'learning_adjustments': 0,
            'preference_overrides': 0,
            'average_confidence': 0.0
        }
        
        if self.routing_history:
            # Count adjustments
            for entry in self.routing_history:
                if entry.get('adjusted_confidence', 0) != entry.get('confidence', 0):
                    stats['learning_adjustments'] += 1
                    
            # Calculate average confidence
            confidences = [e.get('confidence', 0) for e in self.routing_history]
            stats['average_confidence'] = sum(confidences) / len(confidences)
            
        return stats
        
    def explain_routing(self, command: str) -> str:
        """Explain why a command was routed a certain way"""
        
        result = self.route_task(command)
        
        explanation = []
        explanation.append(f"Command: '{command}'")
        explanation.append(f"Routed to: {result.tool_type.value}")
        explanation.append(f"Task type: {result.task_type.value}")
        explanation.append(f"Base confidence: {result.confidence:.0%}")
        
        if result.adjusted_confidence != result.confidence:
            explanation.append(f"Adjusted confidence: {result.adjusted_confidence:.0%}")
            
        if result.matched_patterns:
            explanation.append(f"Matched patterns: {', '.join(result.matched_patterns[:3])}")
            
        if result.recommendations:
            explanation.append("\nRecommendations:")
            for rec in result.recommendations:
                explanation.append(f"  - {rec.action}")
                
        if result.learning_insights:
            success_rate = result.learning_insights.get('success_rate', 0)
            if success_rate > 0:
                explanation.append(f"Historical success rate: {success_rate:.0%}")
                
        return "\n".join(explanation)


def test_adaptive_router():
    """Test the adaptive router"""
    print("Testing Adaptive Router...")
    
    # Create components
    memory = JarvisBigQueryMemory(Path("/tmp/test_adaptive_memory.db"))
    learning = LearningSystem(memory=memory, db_path=Path("/tmp/test_adaptive_learning.db"))
    router = AdaptiveRouter(memory=memory, learning=learning)
    
    # Simulate some history for learning
    print("\n1. Building Learning History")
    history = [
        ("create calculator.py", "aider", True, 2.5),
        ("create calculator.py", "aider", True, 2.3),
        ("fix bug in test.py", "aider", True, 3.0),
        ("explain recursion", "ollama", True, 1.5),
        ("git status", "system", True, 0.2),
    ]
    
    for cmd, tool, success, time in history:
        learning.track_execution(cmd, tool, success, time)
        
    # Test routing with learning
    print("\n2. Testing Adaptive Routing")
    test_commands = [
        "create another calculator file",
        "fix the bug in main.py",
        "explain how neural networks work",
        "git commit -m 'test'",
    ]
    
    for cmd in test_commands:
        result = router.route_task(cmd)
        print(f"\n   Command: '{cmd}'")
        print(f"   Route: {result.tool_type.value} ({result.confidence:.0%} → {result.adjusted_confidence:.0%})")
        if result.recommendations:
            print(f"   Recommendations: {len(result.recommendations)}")
            
    # Test preference override
    print("\n3. Testing Preference Override")
    # Simulate strong preference for aider
    for _ in range(10):
        learning.track_execution("write code", "aider", True, 2.0)
        
    result = router.route_task("write a simple function")
    print(f"   With strong aider preference:")
    print(f"   Route: {result.tool_type.value}")
    print(f"   Reasoning: {result.reasoning}")
    
    # Test explanation
    print("\n4. Testing Routing Explanation")
    explanation = router.explain_routing("create a test file with pytest")
    print(f"   Explanation:\n{explanation}")
    
    # Get statistics
    print("\n5. Routing Statistics")
    stats = router.get_routing_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")
            
    print("\n✅ Adaptive Router Test Complete!")


if __name__ == "__main__":
    test_adaptive_router()