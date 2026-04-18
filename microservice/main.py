from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="AI Agent Automation Microservice")


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


@app.get("/")
def root():
    return {
        "message": "AI Agent Automation Microservice is running"
    }


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        service="ai-agent-automation-microservice",
        timestamp=datetime.utcnow().isoformat()
    )