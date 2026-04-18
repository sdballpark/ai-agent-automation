import os
import re
from datetime import UTC, datetime
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI

load_dotenv()

app = FastAPI(title="AI Agent Automation Microservice")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


class LinkedInRequest(BaseModel):
    brand_name: str
    audience: str
    topic: str
    tone: str
    dry_run: bool = True
    feedback: Optional[str] = None


class WorkflowResponse(BaseModel):
    status: str
    stage: str
    ideas: List[str]
    draft: str
    title: str
    summary: str
    slug: str
    content_type: str
    hashtags: List[str]
    confidence: float
    approved_for_publish: bool
    next_action: str
    timestamp: str


def normalize_text(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
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
    slug = re.sub(r"[^a-zA-Z0-9\\s-]", "", title)
    slug = slug.lower().strip().replace(" ", "-")
    slug = re.sub(r"-+", "-", slug)
    return slug


def generate_metadata(draft: str, topic: str) -> tuple[str, str, str, str]:
    title = f"{topic.title()}: What Marketing Leaders Need to Know"
    first_paragraph = draft.split("\n\n")[0].strip()
    summary = first_paragraph[:200]
    slug = generate_slug(title)
    content_type = "linkedin_post"
    return title, summary, slug, content_type


def generate_draft(request: LinkedInRequest) -> str:
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
                    "content": "You are an expert LinkedIn strategist.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
        return normalize_text(response.choices[0].message.content or "")
    except Exception as e:
        return f"LLM error: {str(e)}"


@app.get("/")
def root():
    return {"message": "AI Agent Automation Microservice is running"}


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        service="ai-agent-automation-microservice",
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.post("/workflow/linkedin", response_model=WorkflowResponse)
def linkedin_workflow(request: LinkedInRequest):
    ideas = [
        f"How {request.brand_name} is approaching {request.topic}",
        f"Three lessons about {request.topic}",
        f"What leaders should know about {request.topic}",
    ]

    draft = generate_draft(request)
    title, summary, slug, content_type = generate_metadata(draft, request.topic)

    hashtags = ["#AI", "#Automation", "#LinkedInStrategy", "#AgenticAI"]

    confidence = 0.85
    approved_for_publish = confidence >= 0.80 and not request.dry_run

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
        confidence=confidence,
        approved_for_publish=approved_for_publish,
        next_action=next_action,
        timestamp=datetime.now(UTC).isoformat(),
    )