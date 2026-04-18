import json
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUEST_FILE = PROJECT_ROOT / "examples" / "linkedin_request_sample.json"
WORKFLOW_URL = "http://127.0.0.1:8000/workflow/linkedin"


def main():
    if not REQUEST_FILE.exists():
        raise FileNotFoundError(f"Request file not found: {REQUEST_FILE}")

    with open(REQUEST_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)

    print("=== Sending Request to Workflow Endpoint ===")
    print(json.dumps(payload, indent=2))
    print()

    response = requests.post(WORKFLOW_URL, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()

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

    print("=== Full JSON ===")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()