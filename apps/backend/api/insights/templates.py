"""
Insights Lab Templates Module

Built-in template definitions and template constants.
"""

BUILTIN_TEMPLATES = [
    {
        "id": "tmpl_exec_summary",
        "name": "Executive Summary",
        "description": "Concise 2-3 paragraph summary with key takeaways",
        "system_prompt": """Provide a concise executive summary of this transcript in 2-3 paragraphs.
Focus on the main points, key decisions, and actionable items.
Use clear, professional language. Start with the most important information.""",
        "category": "GENERAL",
        "output_format": "MARKDOWN"
    },
    {
        "id": "tmpl_key_points",
        "name": "Key Points",
        "description": "Bulleted list of main points",
        "system_prompt": """Extract the key points from this transcript as a bulleted list.
- Focus on actionable items, decisions, and important topics discussed
- Include specific names, numbers, or dates mentioned
- Keep each point concise (1-2 sentences)
- Order by importance, not chronologically""",
        "category": "GENERAL",
        "output_format": "MARKDOWN"
    },
    {
        "id": "tmpl_verbatim",
        "name": "Full Transcript",
        "description": "Clean, formatted verbatim transcript",
        "system_prompt": """Format this as a clean, readable transcript.
- Add paragraph breaks at natural pauses
- Clean up filler words (um, uh, like) unless they're meaningful
- Preserve the speaker's exact words otherwise
- Add [inaudible] markers if the original has gaps""",
        "category": "GENERAL",
        "output_format": "TEXT"
    },
    {
        "id": "tmpl_sermon_outline",
        "name": "Sermon Outline",
        "description": "Structured sermon outline with scripture references",
        "system_prompt": """Create a sermon outline from this transcript:

# [Title/Theme]

## Scripture References
- List all Bible verses mentioned

## Main Points
1. First main point
   - Sub-points
   - Supporting scripture
2. Second main point
   - Sub-points
   - Supporting scripture

## Illustrations/Stories
- Key illustrations used

## Application Questions
1. Reflection questions for the congregation

## Action Items
- Practical takeaways""",
        "category": "SERMON",
        "output_format": "MARKDOWN"
    },
    {
        "id": "tmpl_medical_soap",
        "name": "Medical Note (SOAP)",
        "description": "SOAP format medical documentation",
        "system_prompt": """Format this as a medical note following SOAP structure:

## Subjective
Patient's reported symptoms, history, and concerns.

## Objective
Observable findings, vital signs, examination results.

## Assessment
Diagnosis or clinical impression.

## Plan
- Treatment plan
- Medications
- Follow-up instructions
- Patient education

Use professional medical terminology. Preserve all clinical details accurately.""",
        "category": "MEDICAL",
        "output_format": "MARKDOWN"
    },
    {
        "id": "tmpl_meeting_minutes",
        "name": "Meeting Minutes",
        "description": "Formal meeting minutes with action items",
        "system_prompt": """Create formal meeting minutes:

# Meeting Minutes

**Date:** [Extract from context]
**Attendees:** [List if mentioned]

## Agenda Items
1. Topic discussed
2. Topic discussed

## Discussion Summary
Brief summary of key discussions.

## Decisions Made
- Decision 1
- Decision 2

## Action Items
| Action | Owner | Due Date |
|--------|-------|----------|
| Task   | Name  | Date     |

## Next Steps
- Follow-up items
- Next meeting date if mentioned""",
        "category": "MEETING",
        "output_format": "MARKDOWN"
    },
    {
        "id": "tmpl_academic_notes",
        "name": "Academic Notes",
        "description": "Lecture notes with key concepts and definitions",
        "system_prompt": """Format as academic lecture notes:

# [Topic/Subject]

## Key Concepts
- **Concept 1**: Definition and explanation
- **Concept 2**: Definition and explanation

## Main Arguments/Theories
1. First major point
2. Second major point

## Important Terms
| Term | Definition |
|------|------------|
| Term | Meaning    |

## Questions for Further Study
- Research questions raised

## References Mentioned
- Any books, papers, or sources cited""",
        "category": "ACADEMIC",
        "output_format": "MARKDOWN"
    },
]

# Default templates to auto-apply on upload
DEFAULT_TEMPLATE_IDS = ["tmpl_exec_summary", "tmpl_key_points", "tmpl_verbatim"]

__all__ = ["BUILTIN_TEMPLATES", "DEFAULT_TEMPLATE_IDS"]
