"""
Deployment templates (DEPLOYMENT category).
Moved from core_nlp_templates.py for modular architecture.
"""

from typing import List
from .types import NLPTemplate, IntentCategory


def get_templates() -> List[NLPTemplate]:
    """Return all DEPLOYMENT templates."""
    return [
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
    ]
