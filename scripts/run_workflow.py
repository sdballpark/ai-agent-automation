import json
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUEST_FILE = PROJECT_ROOT / "examples" / "linkedin_request_sample.json"
WORKFLOW_URL = "http://127.0.0.1:8000/workflow/linkedin"


def load_payload():
    if not REQUEST_FILE.exists():
        raise FileNotFoundError(f"Request file not found: {REQUEST_FILE}")

    with open(REQUEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def call_workflow(payload: dict) -> dict:
    response = requests.post(WORKFLOW_URL, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def display_response(data: dict) -> None:
    print("=== Workflow Response ===")
    print(f"Status: {data.get('status')}")
    print(f"Stage: {data.get('stage')}")
    print(f"Next Action: {data.get('next_action')}")
    print(f"Approved For Publish: {data.get('approved_for_publish')}")
    print(f"Confidence: {data.get('confidence')}")
    print()

    print("=== Ideas ===")
    for idx, idea in enumerate(data.get("ideas", []), start=1):
        print(f"{idx}. {idea}")
    print()

    print("=== Draft ===")
    print(data.get("draft", ""))
    print()

    print("=== Hashtags ===")
    print(", ".join(data.get("hashtags", [])))
    print()


def prompt_human_review() -> str:
    print("=== Human Review Gate ===")
    print("Enter one of: approve, revise, reject")
    decision = input("Decision: ").strip().lower()

    valid = {"approve", "revise", "reject"}
    while decision not in valid:
        print("Invalid choice. Please enter: approve, revise, or reject")
        decision = input("Decision: ").strip().lower()

    return decision


def main():
    payload = load_payload()

    print("=== Sending Request to Workflow Endpoint ===")
    print(json.dumps(payload, indent=2))
    print()

    data = call_workflow(payload)
    display_response(data)

    decision = prompt_human_review()
    print()

    print("=== Human Review Result ===")
    if decision == "approve":
        print("Content approved for next workflow stage.")
    elif decision == "revise":
        print("Content sent back for revision.")
    else:
        print("Content rejected.")

    print()
    print("=== Final Review Record ===")
    review_record = {
        "request_topic": payload.get("topic"),
        "decision": decision,
        "workflow_stage": data.get("stage"),
        "next_action": data.get("next_action"),
        "confidence": data.get("confidence"),
        "timestamp": data.get("timestamp"),
    }
    print(json.dumps(review_record, indent=2))


if __name__ == "__main__":
    main()