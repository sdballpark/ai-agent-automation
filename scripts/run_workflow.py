"""
AI Agent Automation Workflow Runner
File: scripts/run_workflow.py

Purpose:
- Act as a local command-line orchestrator for the LinkedIn workflow endpoint.
- Load a sample request payload from disk.
- Send that payload to the FastAPI microservice.
- Display workflow output in a readable format.
- Pause for human review (approve / revise / reject).
- If revise is chosen, collect feedback and request a revised draft.
- Persist review outcomes to a local review log for traceability.

Change Log / Historical Notes:
1. Initial version:
   - Added a simple local runner that called the workflow endpoint and printed the response.
   - Goal: prove the API could be invoked from the command line.

2. Human review gate:
   - Added approve / revise / reject prompt.
   - Goal: simulate human-in-the-loop workflow behavior locally.

3. Revision loop:
   - Added feedback capture and second-pass workflow call when "revise" is selected.
   - Goal: support iterative content improvement.

4. Review log persistence:
   - Added review_log.json output so decisions are stored locally.
   - Goal: preserve an audit trail of workflow activity.

5. Metadata display and persistence:
   - Added title, summary, slug, and content_type to the runner output and review log.
   - Goal: make the runner reflect publish-ready workflow data.

6. Publish payload display and persistence:
   - Added publish_payload to console output and to the final review record.
   - Goal: show exactly what downstream systems would consume.

Notes for maintainers:
- This file is intentionally verbose and highly commented for clarity.
- It is designed for local development and debugging, not silent production execution.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Project Paths / Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUEST_FILE = PROJECT_ROOT / "examples" / "linkedin_request_sample.json"
REVIEW_LOG = PROJECT_ROOT / "examples" / "review_log.json"
WORKFLOW_URL = "http://127.0.0.1:8000/workflow/linkedin"


# ---------------------------------------------------------------------------
# File / API Helpers
# ---------------------------------------------------------------------------

def load_payload() -> dict:
    """
    Load the sample request payload from disk.

    Why this exists:
    - Keeps request data external to the script.
    - Makes it easy to test different payloads without editing Python code.
    """
    if not REQUEST_FILE.exists():
        raise FileNotFoundError(f"Request file not found: {REQUEST_FILE}")

    with open(REQUEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def call_workflow(payload: dict) -> dict:
    """
    Send the payload to the workflow endpoint and return parsed JSON.

    Why this exists:
    - Centralizes the API call logic.
    - Makes later extension easier if headers, auth, or retries are added.
    """
    response = requests.post(WORKFLOW_URL, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Display Helpers
# ---------------------------------------------------------------------------

def display_response(data: dict, title: str = "=== Workflow Response ===") -> None:
    """
    Print a readable workflow response to the terminal.

    Sections shown:
    - workflow state
    - metadata
    - ideas
    - draft
    - hashtags
    - publish payload
    """
    print(title)
    print(f"Status: {data.get('status')}")
    print(f"Stage: {data.get('stage')}")
    print(f"Next Action: {data.get('next_action')}")
    print(f"Approved For Publish: {data.get('approved_for_publish')}")
    print(f"Confidence: {data.get('confidence')}")
    print()

    print("=== Metadata ===")
    print(f"Title: {data.get('title')}")
    print(f"Summary: {data.get('summary')}")
    print(f"Slug: {data.get('slug')}")
    print(f"Content Type: {data.get('content_type')}")
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

    print("=== Publish Payload ===")
    print(json.dumps(data.get("publish_payload", {}), indent=2))
    print()


# ---------------------------------------------------------------------------
# Human Review Helpers
# ---------------------------------------------------------------------------

def prompt_human_review() -> str:
    """
    Ask the user to approve, revise, or reject the generated content.
    """
    print("=== Human Review Gate ===")
    print("Enter one of: approve, revise, reject")
    decision = input("Decision: ").strip().lower()

    valid = {"approve", "revise", "reject"}
    while decision not in valid:
        print("Invalid choice. Please enter: approve, revise, or reject")
        decision = input("Decision: ").strip().lower()

    return decision


def prompt_revision_feedback() -> str:
    """
    Ask the user for revision feedback if 'revise' was selected.
    """
    print("=== Revision Feedback ===")
    feedback = input("Enter revision feedback: ").strip()

    while not feedback:
        print("Feedback cannot be empty.")
        feedback = input("Enter revision feedback: ").strip()

    return feedback


def determine_final_action(decision: str) -> str:
    """
    Convert human decision into a final workflow outcome.
    """
    if decision == "approve":
        return "READY_FOR_PUBLISH"
    if decision == "revise":
        return "RETURN_FOR_REVISION"
    return "REJECTED"


# ---------------------------------------------------------------------------
# Review Log Helpers
# ---------------------------------------------------------------------------

def load_review_log() -> list:
    """
    Load the existing review log if present.
    """
    if REVIEW_LOG.exists():
        with open(REVIEW_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_review_log(entries: list) -> None:
    """
    Persist the updated review log to disk.
    """
    with open(REVIEW_LOG, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


# ---------------------------------------------------------------------------
# Main Orchestration Flow
# ---------------------------------------------------------------------------

def main():
    """
    Run the full local workflow.

    Flow:
    1. Load the request payload
    2. Send initial workflow request
    3. Display response
    4. Ask for human decision
    5. If revise, collect feedback and send revised request
    6. Build review record
    7. Persist review record to local log
    """
    payload = load_payload()

    print("=== Sending Request to Workflow Endpoint ===")
    print(json.dumps(payload, indent=2))
    print()

    data = call_workflow(payload)
    display_response(data)

    decision = prompt_human_review()
    revised_data = None
    feedback = None

    if decision == "revise":
        feedback = prompt_revision_feedback()
        revised_payload = dict(payload)
        revised_payload["feedback"] = feedback

        print()
        print("=== Sending Revision Request ===")
        print(json.dumps(revised_payload, indent=2))
        print()

        revised_data = call_workflow(revised_payload)
        display_response(revised_data, title="=== Revised Workflow Response ===")

    final_action = determine_final_action(decision)

    print()
    print("=== Human Review Result ===")
    print(f"Decision: {decision}")
    print(f"Final Action: {final_action}")
    print()

    # Use revised response if it exists; otherwise use the original response.
    final_data = revised_data if revised_data else data

    review_record = {
        "request_topic": payload.get("topic"),
        "brand_name": payload.get("brand_name"),
        "decision": decision,
        "feedback": feedback,
        "workflow_stage": final_data.get("stage"),
        "workflow_next_action": final_data.get("next_action"),
        "final_action": final_action,
        "confidence": final_data.get("confidence"),
        "approved_for_publish": decision == "approve",
        "title": final_data.get("title"),
        "summary": final_data.get("summary"),
        "slug": final_data.get("slug"),
        "content_type": final_data.get("content_type"),
        "publish_payload": final_data.get("publish_payload"),
        "timestamp": datetime.now(UTC).isoformat(),
    }

    log_entries = load_review_log()
    log_entries.append(review_record)
    save_review_log(log_entries)

    print("=== Final Review Record ===")
    print(json.dumps(review_record, indent=2))
    print()
    print(f"Review log updated: {REVIEW_LOG}")


if __name__ == "__main__":
    main()