#!/usr/bin/env python3
"""
Enhanced Planner that adds search before ambiguous edits and shows references.
Features:
- Detects ambiguous edit requests
- Automatically adds search step before propose
- Shows references in output
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Set
import os
import json
import shutil
import subprocess
import re
from pathlib import Path
import logging

try:
    from models import ModelSelector, TaskType
except Exception:
    ModelSelector = None
    TaskType = None  # type: ignore

from planner import Plan, Step, Planner as BasePlanner

logger = logging.getLogger(__name__)


class EnhancedPlanner(BasePlanner):
    """Enhanced planner with search capabilities for ambiguous edits"""
    
    def __init__(self):
        super().__init__()
        self._ambiguous_patterns = [
            r'\b(update|modify|change|fix|improve|refactor)\s+(?:the\s+)?(\w+)',
            r'\b(rename|move|extract)\s+(?:the\s+)?(\w+)',
            r'\b(?:make|ensure|add|remove)\s+.*\s+(?:to|from|in)\s+(\w+)',
            r'\bchange\s+all\s+(\w+)',
            r'\b(\w+)\s+(?:should|must|needs?\s+to)\s+',
        ]
        
        # File attachment settings
        self.attach_mode = os.environ.get('PLANNER_ATTACH_FILES', 'auto')
        self.attach_limit = int(os.environ.get('PLANNER_ATTACH_LIMIT', '5'))
        self.force_search = os.environ.get('PLANNER_FORCE_SEARCH', '0') == '1'
        
    def plan(self, description: str, files: List[str] = None) -> Plan:
        """Create a plan, adding search step for ambiguous edits"""
        files = files or []
        
        # Check if the edit request is ambiguous
        is_ambiguous, search_terms = self._detect_ambiguous_edit(description, files)
        
        # Decide whether to add search step
        should_search = False
        
        if self.force_search and search_terms:
            # Force search if flag is set and we have search terms
            should_search = True
        elif is_ambiguous and (not files or len(files) > 3):
            # Normal logic: search for ambiguous edits without specific files
            should_search = True
        
        if should_search:
            return self._create_search_first_plan(description, files, search_terms)
            
        # Otherwise use base planner logic
        return super().plan(description, files)
        
    def _detect_ambiguous_edit(self, description: str, files: List[str]) -> Tuple[bool, List[str]]:
        """Detect if an edit request is ambiguous and extract search terms"""
        # If specific files are provided and few, it's not ambiguous (unless force search)
        if files and len(files) <= 3 and not self.force_search:
            return False, []
            
        search_terms = set()
        desc_lower = description.lower()
        
        # Check for ambiguous patterns
        ambiguous = False
        
        # Common programming words to exclude
        common_words = {
            'the', 'a', 'an', 'to', 'from', 'in', 'for', 'and', 'or', 'not', 
            'if', 'then', 'else', 'all', 'any', 'some', 'update', 'modify', 
            'change', 'fix', 'improve', 'refactor', 'rename', 'move', 'extract',
            'add', 'remove', 'delete', 'create', 'make', 'ensure', 'should',
            'must', 'needs', 'need', 'use', 'into', 'with', 'without', 'instead',
            'new', 'old', 'current', 'existing', 'function', 'class', 'method',
            'module', 'file', 'code', 'logic', 'bug', 'issue', 'problem',
            'feature', 'test', 'tests', 'handle', 'process', 'validate',
            'check', 'verify', 'ensure', 'support', 'implement', 'values',
            'data', 'error', 'errors', 'exception', 'exceptions', 'import',
            'imports', 'across', 'codebase', 'instances', 'occurrences',
            'separate', 'different', 'same', 'similar', 'related'
        }
        
        # First check for rename patterns specifically
        rename_pattern = r'\b(?:rename|change)\s+(\w+)\s+(?:to|into|as)\s+(\w+)'
        rename_match = re.search(rename_pattern, description, re.IGNORECASE)
        if rename_match:
            old_name, new_name = rename_match.groups()
            if old_name.lower() not in common_words:
                search_terms.add(old_name)
            if new_name.lower() not in common_words:
                search_terms.add(new_name)
            ambiguous = True
        
        # Look for specific identifiers with stricter patterns
        # CamelCase (at least one uppercase after first letter)
        camelcase_pattern = r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b'
        for match in re.finditer(camelcase_pattern, description):
            term = match.group(1)
            search_terms.add(term)
            ambiguous = True
            
        # snake_case or CONSTANT_CASE (with underscores)
        snake_pattern = r'\b([a-zA-Z]+(?:_[a-zA-Z]+)+)\b'
        for match in re.finditer(snake_pattern, description):
            term = match.group(1)
            if term.lower() not in common_words:
                search_terms.add(term)
                ambiguous = True
                
        # Function/method calls (identifier followed by parentheses in description)
        function_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        for match in re.finditer(function_pattern, description):
            term = match.group(1)
            if term.lower() not in common_words and len(term) > 2:
                search_terms.add(term)
                ambiguous = True
                
        # Quoted identifiers
        quoted_pattern = r'["\']([a-zA-Z_][a-zA-Z0-9_]*)["\']'
        for match in re.finditer(quoted_pattern, description):
            term = match.group(1)
            if term.lower() not in common_words:
                search_terms.add(term)
                ambiguous = True
                
        # Module paths (e.g., utils.helpers, core.auth)
        module_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+)\b'
        for match in re.finditer(module_pattern, description):
            term = match.group(1)
            search_terms.add(term)
            ambiguous = True
            
        # If we found specific identifiers, we're ambiguous
        # Also check for general ambiguous language without specific targets
        if not search_terms:
            general_patterns = [
                r'\b(?:fix|update|modify|change)\s+(?:the\s+)?(?:bug|issue|problem|error)\b',
                r'\b(?:refactor|improve|optimize)\s+(?:the\s+)?(?:code|logic|implementation)\b',
                r'\badd\s+(?:more\s+)?(?:logging|validation|error\s+handling)\b',
            ]
            for pattern in general_patterns:
                if re.search(pattern, desc_lower):
                    ambiguous = True
                    # Try to extract any remaining identifiers
                    words = description.split()
                    for word in words:
                        # Clean word of punctuation
                        clean_word = re.sub(r'[^\w]', '', word)
                        if (len(clean_word) > 3 and 
                            clean_word.lower() not in common_words and
                            (clean_word[0].isupper() or '_' in clean_word)):
                            search_terms.add(clean_word)
                    break
                    
        return ambiguous, list(search_terms)
        
    def _create_search_first_plan(self, description: str, files: List[str], 
                                 search_terms: List[str]) -> Plan:
        """Create a plan that starts with search step"""
        heavy = self._is_heavy(description, files)
        
        # Build search description
        search_desc = "Search for: " + ", ".join(search_terms[:5])  # Limit terms
        if len(search_terms) > 5:
            search_desc += f" (and {len(search_terms)-5} more)"
            
        steps = [
            Step(
                name='search', 
                engine='search',  # Will be handled by codex
                description=search_desc, 
                files=[],  # Search doesn't need files
                timeout_s=30
            )
        ]
        
        # Add propose step
        if heavy or self._repo_wide(description):
            proposer = 'continue'
            model = self._pick_code_model(heavy=True)
        else:
            proposer = 'aider'
            model = self._pick_code_model(heavy=False)
            
        steps.append(
            Step(
                name='propose', 
                engine=proposer, 
                description=description, 
                files=files,  # Will be populated by search results
                model=model, 
                timeout_s=300
            )
        )
        
        # Add verify step
        steps.append(
            Step(
                name='verify', 
                engine='verify', 
                description='quick_checks+pytest', 
                files=files, 
                timeout_s=90
            )
        )
        
        return Plan(
            steps=steps, 
            heavy=heavy, 
            rationale=f"ambiguous_edit_search_first ({len(search_terms)} terms)",
            metadata={
                'search_terms': search_terms,
                'search_term_count': len(search_terms),
                'has_search_step': True
            }
        )
        
    def execute_search_step(self, step: Step, show_references: bool = True) -> Dict[str, any]:
        """Execute a search step and return results with references"""
        try:
            from engines.codex_engine import CodexEngine
            
            codex = CodexEngine()
            results = {
                'terms': [],
                'total_matches': 0,
                'files_found': set(),
                'references': []
            }
            
            # Extract search terms from description
            terms = []
            if step.description.startswith("Search for: "):
                terms_str = step.description[len("Search for: "):]
                # Handle "and X more" suffix
                if " (and " in terms_str:
                    terms_str = terms_str.split(" (and ")[0]
                terms = [t.strip() for t in terms_str.split(",")]
                
            for term in terms[:5]:  # Limit to 5 terms
                # Search for the term
                matches = codex.search_code(
                    pattern=rf'\b{re.escape(term)}\b',
                    globs=['**/*.py', '**/*.js', '**/*.ts'],
                    max_results=50
                )
                
                if matches:
                    results['terms'].append({
                        'term': term,
                        'count': len(matches),
                        'files': list(set(m[0] for m in matches))
                    })
                    results['total_matches'] += len(matches)
                    results['files_found'].update(m[0] for m in matches)
                    
                    # Add references if requested
                    if show_references:
                        for path, line_no, content in matches[:10]:  # First 10 refs
                            results['references'].append({
                                'term': term,
                                'file': path,
                                'line': line_no,
                                'content': content.strip()
                            })
                            
            results['files_found'] = sorted(list(results['files_found']))
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                'error': str(e),
                'terms': [],
                'total_matches': 0,
                'files_found': [],
                'references': []
            }
            
    def format_search_results(self, results: Dict[str, any]) -> str:
        """Format search results for display with references"""
        if results.get('error'):
            return f"Search failed: {results['error']}"
            
        lines = []
        lines.append(f"\n🔍 Search Results Summary")
        lines.append(f"{'='*60}")
        lines.append(f"Total matches: {results['total_matches']} across {len(results['files_found'])} files")
        
        # Summary by term with counts
        lines.append(f"\n📊 Match Distribution by Term:")
        for term_info in results['terms']:
            count = term_info['count']
            files = len(term_info['files'])
            bar = '█' * min(20, count // 2) + '░' * (20 - min(20, count // 2))
            lines.append(f"  '{term_info['term']}' [{bar}] {count} matches in {files} file{'s' if files != 1 else ''}")
            
        # Top files by match density
        if results['files_found']:
            lines.append(f"\n📁 Top Files (showing {min(10, len(results['files_found']))} of {len(results['files_found'])}):")
            # Count matches per file
            file_counts = {}
            for term_info in results['terms']:
                for ref in results.get('references', []):
                    if ref['term'] == term_info['term']:
                        file_counts[ref['file']] = file_counts.get(ref['file'], 0) + 1
            
            # Sort by match count
            sorted_files = sorted(results['files_found'][:10], 
                                key=lambda f: file_counts.get(f, 0), 
                                reverse=True)
            
            for f in sorted_files:
                match_count = file_counts.get(f, 1)
                lines.append(f"  • {f} ({match_count} match{'es' if match_count != 1 else ''})")
            
            if len(results['files_found']) > 10:
                lines.append(f"  ... and {len(results['files_found'])-10} more files")
                
        # Grouped references with context
        if results.get('references'):
            lines.append(f"\n🎯 Key References (grouped by term):")
            
            # Group references by term
            refs_by_term = {}
            for ref in results['references']:
                term = ref['term']
                if term not in refs_by_term:
                    refs_by_term[term] = []
                refs_by_term[term].append(ref)
            
            for term, refs in refs_by_term.items():
                lines.append(f"\n  '{term}' ({len(refs)} references shown):")
                for i, ref in enumerate(refs[:5]):  # Show up to 5 per term
                    lines.append(f"    {i+1}. {ref['file']}:{ref['line']}")
                    # Clean and format content
                    content = ref['content'].strip()
                    if len(content) > 70:
                        content = content[:67] + "..."
                    lines.append(f"       └─ {content}")
                
                if len(refs) > 5:
                    lines.append(f"       ... and {len(refs)-5} more references")
        
        # Next actions hint
        lines.append(f"\n💡 Next Actions:")
        if results['files_found']:
            primary_files = results['files_found'][:3]
            if len(primary_files) == 1:
                lines.append(f"  • Focus on {primary_files[0]} for targeted changes")
            else:
                lines.append(f"  • Primary files to review: {', '.join(primary_files)}")
            
            # Suggest based on term types
            has_class = any('class' in str(ref.get('content', '')).lower() or 
                          ref['term'][0].isupper() 
                          for ref in results.get('references', []))
            has_function = any('def ' in str(ref.get('content', '')) or 
                             '(' in str(ref.get('content', ''))
                             for ref in results.get('references', []))
            
            if has_class:
                lines.append(f"  • Class definitions found - consider inheritance/interface changes")
            if has_function:
                lines.append(f"  • Function definitions found - check parameter usage and return values")
            
            if results['total_matches'] > 20:
                lines.append(f"  • High match count - consider using more specific search terms")
        else:
            lines.append(f"  • No matches found - try alternate search terms or patterns")
                
        return "\n".join(lines)
    
    def get_attached_files(self, search_results: Dict[str, any]) -> List[str]:
        """Get files to attach to propose step based on search results and settings"""
        if self.attach_mode == 'none':
            return []
        
        files_found = search_results.get('files_found', [])
        if not files_found:
            return []
        
        # For 'auto' mode or specific topN mode
        if self.attach_mode == 'auto' or self.attach_mode.startswith('top'):
            # Get limit from mode or use default
            if self.attach_mode.startswith('top'):
                try:
                    limit = int(self.attach_mode[3:])  # Extract N from 'topN'
                except ValueError:
                    limit = self.attach_limit
            else:
                limit = self.attach_limit
            
            # Sort files by relevance (match count)
            file_counts = {}
            for term_info in search_results.get('terms', []):
                for ref in search_results.get('references', []):
                    if ref['term'] == term_info['term']:
                        file_counts[ref['file']] = file_counts.get(ref['file'], 0) + 1
            
            # Sort by match count descending
            sorted_files = sorted(files_found, 
                                key=lambda f: file_counts.get(f, 0), 
                                reverse=True)
            
            return sorted_files[:limit]
        
        # Unknown mode, return empty
        return []
    
    def update_plan_with_search_results(self, plan: Plan, search_results: Dict[str, any]) -> Plan:
        """Update plan metadata with search results"""
        if not plan.metadata:
            plan.metadata = {}
        
        # Add search results summary
        plan.metadata['search_results'] = {
            'total_matches': search_results.get('total_matches', 0),
            'files_found': len(search_results.get('files_found', [])),
            'terms_matched': [t['term'] for t in search_results.get('terms', [])],
            'top_files': search_results.get('files_found', [])[:5],
            'attached_files': self.get_attached_files(search_results)
        }
        
        # Update propose step files if auto-attach is enabled
        if self.attach_mode != 'none':
            attached_files = self.get_attached_files(search_results)
            for step in plan.steps:
                if step.name == 'propose' and step.engine in ['aider', 'continue']:
                    # Add attached files to existing files
                    existing = set(step.files)
                    existing.update(attached_files)
                    step.files = sorted(list(existing))
                    plan.metadata['files_attached_to_propose'] = len(attached_files)
        
        return plan