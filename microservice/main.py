import os
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

Revision feedback to apply:
{request.feedback}

Revise the draft to address that feedback directly.
"""

    api_key_present = bool(os.getenv("OPENAI_API_KEY"))

    if api_key_present:
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert LinkedIn content strategist.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
            return normalize_text(response.choices[0].message.content or "")
        except Exception as e:
            return f"LLM call failed: {str(e)}"

    return "Fallback draft: no API key configured."


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
        f"Three lessons about {request.topic} for {request.audience}",
        f"What leaders should know about {request.topic} right now",
    ]

    draft = generate_draft(request)

    hashtags = ["#AI", "#Automation", "#LinkedInStrategy", "#AgenticAI"]

    confidence = 0.82
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
        hashtags=hashtags,
        confidence=confidence,
        approved_for_publish=approved_for_publish,
        next_action=next_action,
        timestamp=datetime.now(UTC).isoformat(),
    )