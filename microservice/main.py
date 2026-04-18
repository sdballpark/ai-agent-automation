"""
AI Agent Automation Microservice
File: microservice/main.py

Purpose:
- Provide a local FastAPI microservice for AI-driven LinkedIn content workflows.
- Support draft generation, revision loops, metadata generation, and a publish-ready payload.
- Serve as the backend API layer for later orchestration with n8n or other workflow tools.

Change Log / Historical Notes:
1. Initial version:
   - Added root and health endpoints to prove the microservice could run locally.
   - Goal: establish a clean FastAPI foundation.

2. LLM integration:
   - Added OpenAI client usage so the service could generate live content instead of mock content.
   - Goal: move from placeholder responses to real generated drafts.

3. Encoding / punctuation normalization:
   - Added normalize_text() to handle curly quotes, dashes, ellipses, and common mojibake artifacts.
   - Goal: reduce messy output when text is displayed in Windows terminals or passed between systems.

4. Workflow endpoint:
   - Added /workflow/linkedin to return structured workflow output.
   - Included stage and next_action so an orchestrator can decide what to do next.
   - Goal: make the API automation-friendly instead of just text-generation-friendly.

5. Revision loop:
   - Added optional feedback field to the request model.
   - Draft generation now incorporates revision feedback when present.
   - Goal: support human-in-the-loop review and second-pass draft creation.

6. Metadata generation:
   - Added title, summary, slug, and content_type.
   - Goal: make the output publish-ready for downstream systems.

7. Publish-ready payload:
   - Added publish_payload to package the final content in one structured object.
   - Goal: simplify downstream integrations such as n8n, CMS publishing, or API handoff.

Notes for maintainers:
- This file is intentionally verbose and commented for clarity.
- The workflow is designed to be easy to debug from the command line.
- OpenAI is the active mode in this version.
"""

import os
import re
from datetime import UTC, datetime
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI

# Load environment variables from .env at startup.
# This keeps secrets and runtime configuration out of source control.
load_dotenv()

# Create the FastAPI application.
app = FastAPI(title="AI Agent Automation Microservice")

# Initialize the OpenAI client.
# Current design assumption:
# - We are using OpenAI mode from OPENAI_API_KEY in .env.
# - If the key is missing or invalid, draft generation will return an error message string.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ---------------------------------------------------------------------------
# Response / Request Models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """
    Health check response model.

    Why this exists:
    - Gives a simple structured response for service monitoring.
    - Useful for curl, browser checks, PowerShell Invoke-RestMethod, or n8n health tests.
    """
    status: str
    service: str
    timestamp: str


class LinkedInRequest(BaseModel):
    """
    Input model for the LinkedIn workflow endpoint.

    Fields:
    - brand_name: organization or brand name
    - audience: target audience for the content
    - topic: content topic
    - tone: desired tone/style
    - dry_run: if True, content is generated but not considered publish-ready
    - feedback: optional revision feedback from human review
    """
    brand_name: str
    audience: str
    topic: str
    tone: str
    dry_run: bool = True
    feedback: Optional[str] = None


class WorkflowResponse(BaseModel):
    """
    Main workflow response model.

    This is intentionally structured for orchestration systems.

    Included sections:
    - workflow status and routing fields
    - generated ideas
    - draft body
    - metadata
    - hashtags
    - publish_payload: a packaged object for downstream publishing systems
    """
    status: str
    stage: str
    ideas: List[str]
    draft: str
    title: str
    summary: str
    slug: str
    content_type: str
    hashtags: List[str]
    publish_payload: Dict[str, Any]
    confidence: float
    approved_for_publish: bool
    next_action: str
    timestamp: str


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Normalize common punctuation and mojibake artifacts.

    Why this exists:
    - LLM output may include curly punctuation or characters that render poorly in
      certain Windows shells or toolchains.
    - We want safer, cleaner plain-text output for logs, CLI display, and downstream systems.
    """
    if not text:
        return ""

    replacements = {
        # Standard Unicode punctuation -> plain ASCII
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",

        # Common mojibake sequences seen in terminal output / encoding mismatch cases
        "â€™": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€“": "-",
        "â€”": "-",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def generate_slug(title: str) -> str:
    """
    Create a URL-safe slug from a title.

    Why this exists:
    - Downstream systems often need a slug for URLs, content IDs, or CMS routing.
    - We normalize to lowercase and collapse repeated dashes.
    """
    # Remove characters except letters, numbers, whitespace, and dash.
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", title)

    # Lowercase and convert spaces to dashes.
    slug = slug.lower().strip().replace(" ", "-")

    # Collapse multiple dashes into a single dash.
    slug = re.sub(r"-+", "-", slug)

    return slug


def generate_metadata(draft: str, topic: str) -> tuple[str, str, str, str]:
    """
    Generate simple publish-oriented metadata.

    Current approach:
    - title: deterministic title based on topic
    - summary: first paragraph trimmed to 200 chars
    - slug: derived from title
    - content_type: fixed as linkedin_post for now

    Why this exists:
    - Makes the workflow output more structured and publish-ready.
    - Later this could be replaced by a second LLM pass or rules engine if needed.
    """
    title = f"{topic.title()}: What Marketing Leaders Need to Know"

    # Use the first paragraph as summary seed.
    first_paragraph = draft.split("\n\n")[0].strip()
    summary = first_paragraph[:200]

    slug = generate_slug(title)
    content_type = "linkedin_post"

    return title, summary, slug, content_type


def generate_draft(request: LinkedInRequest) -> str:
    """
    Generate the LinkedIn draft via OpenAI.

    Behavior:
    - Builds a focused prompt from request fields.
    - If revision feedback is present, the prompt includes it.
    - Returns normalized text.
    - If the LLM call fails, returns an error string instead of crashing the API.

    Why this design:
    - Keeps the endpoint resilient for local experimentation.
    - Makes failure visible while preserving API availability.
    """
    prompt = f"""
Write a LinkedIn post.

Brand: {request.brand_name}
Audience: {request.audience}
Topic: {request.topic}
Tone: {request.tone}

Requirements:
- Clear and professional
- 2 to 3 short paragraphs
- End with a strong takeaway
- Use only plain ASCII punctuation
"""

    # Revision feedback is optional and only appended when present.
    if request.feedback:
        prompt += f"""

Revision feedback:
{request.feedback}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert LinkedIn strategist. "
                        "Write concise, executive-friendly LinkedIn content."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        # Normalize the returned content before exposing it downstream.
        return normalize_text(response.choices[0].message.content or "")

    except Exception as e:
        # We intentionally return a readable error string instead of throwing,
        # because that makes local debugging easier and keeps the API predictable.
        return f"LLM error: {str(e)}"


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """
    Root endpoint.

    Why this exists:
    - Simple smoke test in a browser or via Invoke-RestMethod.
    - Lets users confirm the service is alive without needing a JSON body.
    """
    return {"message": "AI Agent Automation Microservice is running"}


@app.get("/health", response_model=HealthResponse)
def health():
    """
    Health endpoint.

    Why this exists:
    - Standard service health check for local testing and future orchestration.
    - Returns a timezone-aware UTC timestamp.
    """
    return HealthResponse(
        status="ok",
        service="ai-agent-automation-microservice",
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.post("/workflow/linkedin", response_model=WorkflowResponse)
def linkedin_workflow(request: LinkedInRequest):
    """
    Main workflow endpoint for LinkedIn content generation.

    Flow:
    1. Build idea list
    2. Generate draft (or revised draft if feedback exists)
    3. Generate metadata
    4. Build hashtags
    5. Determine workflow stage and next action
    6. Build publish_payload for downstream systems
    7. Return a structured workflow response

    Why this exists:
    - This is the core automation contract for the system.
    - It gives enough structure for local scripts, n8n, or other tools to decide next steps.
    """

    # Lightweight ideation block.
    # This is deterministic for now, which is helpful for consistency and debugging.
    ideas = [
        f"How {request.brand_name} is approaching {request.topic}",
        f"Three lessons about {request.topic}",
        f"What leaders should know about {request.topic}",
    ]

    # Generate the draft content.
    draft = generate_draft(request)

    # Derive metadata from the generated draft.
    title, summary, slug, content_type = generate_metadata(draft, request.topic)

    # Static hashtag set for now.
    # Could later be generated dynamically or tuned by content type.
    hashtags = ["#AI", "#Automation", "#LinkedInStrategy", "#AgenticAI"]

    # Confidence is currently a simple fixed value.
    # This is a placeholder for a future scoring function or model-based confidence estimator.
    confidence = 0.85

    # Publishing approval logic:
    # - If dry_run is True, we do not consider the content publish-approved.
    approved_for_publish = confidence >= 0.80 and not request.dry_run

    # Determine the workflow state.
    # This is intentionally explicit for downstream automation.
    if request.feedback:
        stage = "REVISED_DRAFT_GENERATED"
        next_action = "HUMAN_REVIEW"
    elif request.dry_run:
        stage = "DRAFT_GENERATED"
        next_action = "HUMAN_REVIEW"
    elif approved_for_publish:
        stage = "APPROVED"
        next_action = "PUBLISH"
    else:
        stage = "NEEDS_REVISION"
        next_action = "REVISE"

    # Publish-ready package for downstream systems.
    # This is the handoff object an orchestrator or CMS could consume directly.
    publish_payload = {
        "title": title,
        "body": draft,
        "summary": summary,
        "slug": slug,
        "tags": hashtags,
        "content_type": content_type,
        "status": "ready" if approved_for_publish else "draft",
        "brand": request.brand_name,
        "audience": request.audience,
    }

    return WorkflowResponse(
        status="success",
        stage=stage,
        ideas=ideas,
        draft=draft,
        title=title,
        summary=summary,
        slug=slug,
        content_type=content_type,
        hashtags=hashtags,
        publish_payload=publish_payload,
        confidence=confidence,
        approved_for_publish=approved_for_publish,
        next_action=next_action,
        timestamp=datetime.now(UTC).isoformat(),
    )