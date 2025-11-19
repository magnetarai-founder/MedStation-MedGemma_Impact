"""
Core NLP Library - Intent classification and entity extraction.
Moved from core_nlp_templates.py for modular architecture.
"""

from typing import List, Dict, Any, Optional, Tuple
import re
import json

from .types import NLPTemplate, IntentCategory
from . import (
    code_generation,
    code_modification,
    debugging,
    research,
    system_operation,
    data_analysis,
    documentation,
    deployment,
    testing,
    learning,
)


class CoreNLPLibrary:
    """Core library of NLP templates - Jarvis's language understanding"""

    def __init__(self):
        self.templates = self._initialize_templates()
        self.intent_cache = {}

    def _initialize_templates(self) -> List[NLPTemplate]:
        """Load all NLP templates from category modules"""
        templates = []

        # Load templates from each category module
        templates.extend(code_generation.get_templates())
        templates.extend(code_modification.get_templates())
        templates.extend(debugging.get_templates())
        templates.extend(research.get_templates())
        templates.extend(system_operation.get_templates())
        templates.extend(data_analysis.get_templates())
        templates.extend(documentation.get_templates())
        templates.extend(deployment.get_templates())
        templates.extend(testing.get_templates())
        templates.extend(learning.get_templates())

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
