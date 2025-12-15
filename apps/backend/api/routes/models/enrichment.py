"""
Model Enrichment Routes - AI-powered metadata generation for local models
Uses Apple Foundation Models via intelligent routing to generate rich descriptions

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter()


# MARK: - Request/Response Models

class ModelEnrichmentRequest(BaseModel):
    modelName: str
    family: Optional[str] = None
    parameterSize: Optional[str] = None
    quantizationLevel: Optional[str] = None
    sizeBytes: int
    format: Optional[str] = None


class ModelEnrichmentResponse(BaseModel):
    displayName: str
    description: str
    capability: str  # chat, code, vision, reasoning, general, data
    primaryUseCases: list[str]
    badges: list[str]
    isMultiPurpose: bool
    strengths: list[str]
    idealFor: str
    parameterSize: Optional[str] = None
    estimatedMemoryGB: Optional[float] = None


# MARK: - Enrichment Endpoint

@router.post(
    "/enrich",
    response_model=SuccessResponse[ModelEnrichmentResponse],
    status_code=status.HTTP_200_OK,
    name="models_enrich",
    summary="Enrich model metadata",
    description="Generate AI-powered metadata for local Ollama models using Apple Foundation Models"
)
async def enrich_model(request: ModelEnrichmentRequest) -> SuccessResponse[ModelEnrichmentResponse]:
    """
    Enrich a local Ollama model with AI-generated metadata

    Uses Apple FM (Phi-3) to analyze model name and generate rich descriptions including:
    - Display name and description
    - Capability classification (chat, code, vision, reasoning, data, general)
    - Primary use cases and badges
    - Strengths and ideal use cases
    - Memory usage estimation

    Args:
        request: Model enrichment request with model name and metadata

    Returns:
        Enriched model metadata with AI-generated descriptions

    Note: Falls back to rule-based enrichment if AI enrichment fails
    """
    try:
        logger.info(f"🔍 Enriching model: {request.modelName}")

        # Build enrichment prompt for Apple FM
        prompt = build_enrichment_prompt(request)

        # Call Apple FM via agent routing
        enriched_data = await call_apple_fm_enrichment(prompt, request)

        # Parse and validate response
        response = parse_enrichment_response(enriched_data, request)

        logger.info(f"✅ Successfully enriched {request.modelName}")

        return SuccessResponse(
            data=response,
            message=f"Model '{request.modelName}' enriched successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"❌ Failed to enrich {request.modelName}", exc_info=True)
        # Return fallback enrichment instead of error
        fallback_data = fallback_enrichment(request)
        logger.info(f"Using fallback enrichment for {request.modelName}")

        return SuccessResponse(
            data=fallback_data,
            message=f"Model '{request.modelName}' enriched with fallback (AI enrichment unavailable)"
        )


# MARK: - Enrichment Logic

def build_enrichment_prompt(request: ModelEnrichmentRequest) -> str:
    """Build a structured prompt for Apple FM to analyze the model"""

    size_gb = request.sizeBytes / (1024 ** 3)

    prompt = f"""Analyze this locally installed AI model and provide structured metadata.

Model Details:
- Name: {request.modelName}
- Family: {request.family or 'unknown'}
- Parameter Size: {request.parameterSize or 'unknown'}
- Quantization: {request.quantizationLevel or 'unknown'}
- File Size: {size_gb:.1f} GB
- Format: {request.format or 'unknown'}

Your task: Generate a JSON response with model metadata. Be concise, accurate, and helpful.

Response format (MUST be valid JSON):
{{
  "displayName": "User-friendly name (e.g., 'Llama 3.2 3B', 'Mistral 7B Instruct')",
  "description": "2-3 sentence description of capabilities and use cases",
  "capability": "chat|code|vision|reasoning|general|data",
  "primaryUseCases": ["use case 1", "use case 2", "use case 3"],
  "badges": ["badge1", "badge2", "badge3"],
  "isMultiPurpose": true|false,
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "idealFor": "Description of ideal use case (one sentence)"
}}

Guidelines:
- displayName: Extract version from model name (e.g., "llama3.2:3b" → "Llama 3.2 3B")
- description: Focus on what makes this model unique and its best use cases
- capability: Choose ONE primary capability based on model name/family
- primaryUseCases: Be specific (not generic like "text generation")
- badges: Use relevant tags (e.g., "instruct", "code", "vision", "experimental", "fast")
- isMultiPurpose: True if model can handle multiple tasks well
- strengths: Focus on technical strengths (speed, accuracy, efficiency, multilingual, etc.)
- idealFor: One sentence describing the perfect use case for this model

Base analysis on:
- Model family knowledge (llama, mistral, qwen, phi, gemma, deepseek, command, etc.)
- Parameter size (smaller = faster/efficient, larger = more capable)
- Known suffixes (instruct, chat, code, vision, coder, sql, etc.)
- Quantization level (Q4 = fast, Q8 = accurate, F16 = highest quality)

Return ONLY the JSON object, no additional text."""

    return prompt


async def call_apple_fm_enrichment(prompt: str, request: ModelEnrichmentRequest) -> dict:
    """Call Apple FM (Phi-3) via Ollama to get enriched metadata"""

    try:
        # Import Ollama client
        from api.services.chat.core import _get_ollama_client

        # Get Ollama client
        client = _get_ollama_client()

        # Use phi-3 (Apple FM) for fast, structured analysis
        # Fallback to any available small model if phi-3 not available
        models_to_try = ["phi3.5:latest", "phi3:latest", "phi:latest", "llama3.2:3b", "mistral:latest"]

        model_to_use = None
        available_models = await list_available_models()

        for model in models_to_try:
            if any(model in m for m in available_models):
                model_to_use = model
                break

        if not model_to_use and available_models:
            # Use first available model
            model_to_use = available_models[0]
            logger.info(f"Using fallback model: {model_to_use}")

        if not model_to_use:
            raise Exception("No Ollama models available")

        # Call Ollama with the enrichment prompt
        response = client.chat(
            model=model_to_use,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant that generates structured JSON metadata for AI models. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": 0.3,  # Low temperature for consistent structured output
                "num_predict": 500   # Limit response length
            }
        )

        # Extract response text
        json_text = response.get("message", {}).get("content", "")

        # Extract JSON from response (handle markdown code blocks)
        json_text = extract_json_from_response(json_text)

        # Parse JSON
        enriched = json.loads(json_text)
        return enriched

    except Exception as e:
        logger.warning(f"⚠️ Apple FM enrichment failed: {e}, using fallback")
        raise


async def list_available_models() -> list[str]:
    """List available Ollama models"""
    try:
        from api.services import chat
        models = await chat.list_ollama_models()
        return [m.get("name", "") for m in models]
    except Exception:
        return []


def extract_json_from_response(text: str) -> str:
    """Extract JSON object from text that might contain markdown code blocks"""

    # Remove markdown code blocks
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end].strip()

    # Find JSON object boundaries
    start = text.find("{")
    end = text.rfind("}") + 1

    if start >= 0 and end > start:
        return text[start:end]

    return text


def parse_enrichment_response(enriched: dict, request: ModelEnrichmentRequest) -> ModelEnrichmentResponse:
    """Parse and validate enrichment response from Apple FM"""

    # Calculate estimated memory usage
    size_gb = request.sizeBytes / (1024 ** 3)
    estimated_memory = size_gb * 1.3  # 30% overhead for runtime

    return ModelEnrichmentResponse(
        displayName=enriched.get("displayName", request.modelName),
        description=enriched.get("description", "Locally installed language model"),
        capability=enriched.get("capability", "general"),
        primaryUseCases=enriched.get("primaryUseCases", ["General tasks"]),
        badges=enriched.get("badges", ["installed"]),
        isMultiPurpose=enriched.get("isMultiPurpose", False),
        strengths=enriched.get("strengths", ["Locally installed", "Privacy-focused"]),
        idealFor=enriched.get("idealFor", "General-purpose tasks"),
        parameterSize=request.parameterSize,
        estimatedMemoryGB=round(estimated_memory, 1)
    )


def fallback_enrichment(request: ModelEnrichmentRequest) -> ModelEnrichmentResponse:
    """Fallback enrichment using rule-based detection (no AI)"""

    name = request.modelName.lower()
    size_gb = request.sizeBytes / (1024 ** 3)
    estimated_memory = size_gb * 1.3

    # Detect family
    family, display_name = detect_family(name, request.modelName)

    # Detect capability
    capability = detect_capability(name)

    # Generate description
    description = generate_description(family, capability, request.parameterSize)

    # Detect use cases
    use_cases = detect_use_cases(capability)

    # Generate badges
    badges = generate_badges(name, capability)

    # Detect if multi-purpose
    is_multi_purpose = detect_multi_purpose(name)

    # Generate strengths
    strengths = generate_strengths(family, capability)

    # Generate ideal use case
    ideal_for = generate_ideal_for(capability, family)

    return ModelEnrichmentResponse(
        displayName=display_name,
        description=description,
        capability=capability,
        primaryUseCases=use_cases,
        badges=badges,
        isMultiPurpose=is_multi_purpose,
        strengths=strengths,
        idealFor=ideal_for,
        parameterSize=request.parameterSize,
        estimatedMemoryGB=round(estimated_memory, 1)
    )


# MARK: - Fallback Detection Helpers

def detect_family(name: str, original_name: str) -> tuple[str, str]:
    """Detect model family and generate display name"""

    if "llama" in name:
        version = extract_version(original_name)
        return ("llama", f"Llama {version}")
    elif "mistral" in name or "ministral" in name:
        version = extract_version(original_name)
        return ("mistral", f"Mistral {version}")
    elif "mixtral" in name:
        version = extract_version(original_name)
        return ("mixtral", f"Mixtral {version}")
    elif "phi" in name:
        version = extract_version(original_name)
        return ("phi", f"Phi {version}")
    elif "qwen" in name:
        version = extract_version(original_name)
        return ("qwen", f"Qwen {version}")
    elif "gemma" in name:
        version = extract_version(original_name)
        return ("gemma", f"Gemma {version}")
    elif "deepseek" in name:
        version = extract_version(original_name)
        return ("deepseek", f"DeepSeek {version}")
    elif "command" in name:
        return ("command", "Command R+")
    elif "gpt" in name:
        version = extract_version(original_name)
        return ("gpt", f"GPT {version}")
    elif "sqlcoder" in name:
        version = extract_version(original_name)
        return ("sqlcoder", f"SQLCoder {version}")
    else:
        base = original_name.split(":")[0]
        return ("unknown", base.capitalize())


def extract_version(name: str) -> str:
    """Extract version from model name"""

    if ":" in name:
        return name.split(":")[1].upper()

    # Try common patterns
    patterns = ["3.2", "3.1", "3", "2.5", "2", "7b", "13b", "70b"]
    for pattern in patterns:
        if pattern in name:
            return pattern.upper()

    return ""


def detect_capability(name: str) -> str:
    """Detect primary capability from model name"""

    if "code" in name or "coder" in name:
        return "code"
    elif "vision" in name or "llava" in name:
        return "vision"
    elif "reason" in name or "think" in name:
        return "reasoning"
    elif "chat" in name or "instruct" in name:
        return "chat"
    elif "sql" in name:
        return "data"
    else:
        return "general"


def detect_use_cases(capability: str) -> list[str]:
    """Generate use cases based on capability"""

    use_cases_map = {
        "code": ["Code generation", "Code review", "Debugging"],
        "vision": ["Image analysis", "Visual Q&A", "OCR"],
        "reasoning": ["Complex problem solving", "Chain-of-thought", "Math & logic"],
        "chat": ["Conversations", "Q&A", "General assistance"],
        "data": ["SQL generation", "Data analysis", "Query optimization"],
        "general": ["General tasks", "Text generation", "Conversational AI"]
    }

    return use_cases_map.get(capability, ["General tasks"])


def generate_badges(name: str, capability: str) -> list[str]:
    """Generate badges for the model"""

    badges = ["installed"]

    if "instruct" in name:
        badges.append("instruct")
    if capability == "code":
        badges.append("code")
    elif capability == "vision":
        badges.append("vision")
    elif capability == "reasoning":
        badges.append("reasoning")
    if "experimental" in name:
        badges.append("experimental")

    return badges


def detect_multi_purpose(name: str) -> bool:
    """Detect if model is multi-purpose"""

    multi_purpose_indicators = ["command-r", "gpt", "llama-3", "qwen2.5", "mistral"]
    return any(indicator in name for indicator in multi_purpose_indicators)


def generate_strengths(family: str, capability: str) -> list[str]:
    """Generate strengths based on family and capability"""

    family_strengths = {
        "llama": ["Open source", "Well-optimized", "Strong general performance"],
        "mistral": ["Fast inference", "Excellent reasoning", "Multilingual support"],
        "mixtral": ["Mixture-of-experts architecture", "Superior performance", "Efficient"],
        "phi": ["Compact size", "Low memory footprint", "Fast responses"],
        "qwen": ["Multilingual", "Strong coding ability", "Versatile"],
        "deepseek": ["Advanced reasoning", "Code expertise", "Chain-of-thought"],
        "gemma": ["Lightweight", "Efficient", "Google-backed"],
        "command": ["Enterprise-grade", "Multilingual", "Tool use"],
        "gpt": ["Open-source GPT", "Versatile", "Well-documented"],
        "sqlcoder": ["SQL expertise", "Database optimization", "Query generation"]
    }

    return family_strengths.get(family, ["Locally installed", "Privacy-focused", "Offline capable"])


def generate_description(family: str, capability: str, param_size: Optional[str]) -> str:
    """Generate description based on family and capability"""

    family_desc = {
        "llama": "Meta's powerful open-source language model",
        "mistral": "High-performance model with excellent reasoning capabilities",
        "mixtral": "Mixture-of-experts model with superior performance",
        "phi": "Microsoft's efficient small language model",
        "qwen": "Multilingual model with strong capabilities across tasks",
        "gemma": "Google's lightweight and efficient open model",
        "deepseek": "Advanced model specializing in reasoning and code",
        "command": "Cohere's enterprise-grade language model",
        "gpt": "GPT-style open-source language model",
        "sqlcoder": "Specialized model for SQL generation and database tasks"
    }

    capability_desc = {
        "code": "Optimized for code generation, review, and debugging.",
        "vision": "Capable of analyzing images and answering visual questions.",
        "reasoning": "Excels at complex problem-solving with chain-of-thought reasoning.",
        "chat": "Fine-tuned for natural conversations and general assistance.",
        "data": "Specialized in SQL generation and data analysis tasks.",
        "general": "Versatile general-purpose model for various tasks."
    }

    base = family_desc.get(family, "Locally installed language model")
    cap = capability_desc.get(capability, "Runs locally on your Mac.")
    size = f" ({param_size})" if param_size else ""

    return f"{base}{size}. {cap} Runs locally on your Mac with full privacy."


def generate_ideal_for(capability: str, family: str) -> str:
    """Generate ideal use case description"""

    capability_ideal = {
        "code": "Developers needing code assistance, refactoring, or debugging help",
        "vision": "Tasks requiring image understanding, OCR, or visual analysis",
        "reasoning": "Complex problem-solving, mathematical reasoning, or logical analysis",
        "chat": "General conversations, Q&A, and day-to-day assistance",
        "data": "Database work, SQL query generation, and data analysis",
        "general": "General-purpose tasks requiring balanced performance"
    }

    return capability_ideal.get(capability, "General-purpose tasks requiring balanced performance")
