import os
from datetime import datetime
from typing import List

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


class LinkedInResponse(BaseModel):
    ideas: List[str]
    draft: str
    hashtags: List[str]
    confidence: float
    approved_for_publish: bool
    timestamp: str


def normalize_text(text: str) -> str:
    """
    Normalize common Unicode punctuation to plain ASCII and clean up
    frequent mojibake artifacts seen in Windows terminal output.
    """
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
        "\u00a0": " ",   # non-breaking space

        # common mojibake sequences
        "â€™": "'",
        "â€˜": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€“": "-",
        "â€”": "-",
        "â€¦": "...",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


@app.get("/")
def root():
    return {"message": "AI Agent Automation Microservice is running"}


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        service="ai-agent-automation-microservice",
        timestamp=datetime.utcnow().isoformat(),
    )


@app.post("/linkedin", response_model=LinkedInResponse)
def linkedin_content(request: LinkedInRequest):
    ideas = [
        f"How {request.brand_name} is approaching {request.topic}",
        f"Three lessons about {request.topic} for {request.audience}",
        f"What leaders should know about {request.topic} right now",
    ]

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
- Do not use curly apostrophes, curly quotes, or em dashes
- No hashtags in the body
"""

    api_key_present = bool(os.getenv("OPENAI_API_KEY"))

    if api_key_present:
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert LinkedIn content strategist. "
                            "Use only plain ASCII punctuation."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
            draft = response.choices[0].message.content or ""
            draft = normalize_text(draft)
        except Exception as e:
            draft = f"LLM call failed; using fallback draft. Error: {str(e)}"
    else:
        draft = (
            f"{request.brand_name} perspective: {request.topic}\n\n"
            f"We help {request.audience} think more clearly about {request.topic}. "
            f"Our tone is {request.tone}, and this is a fallback draft because no OPENAI_API_KEY is configured.\n\n"
            f"Key takeaway: organizations that build repeatable workflows around {request.topic} "
            f"can improve consistency, speed, and operational confidence."
        )

    hashtags = ["#AI", "#Automation", "#LinkedInStrategy", "#AgenticAI", "#Workflow"]

    confidence = 0.82
    approved_for_publish = confidence >= 0.80 and not request.dry_run

    return LinkedInResponse(
        ideas=ideas,
        draft=draft,
        hashtags=hashtags,
        confidence=confidence,
        approved_for_publish=approved_for_publish,
        timestamp=datetime.utcnow().isoformat(),
    )