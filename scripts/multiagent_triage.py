import os
from dotenv import load_dotenv

load_dotenv()

print("=== Multi-Agent Triage Bootstrap ===")

use_azure = os.getenv("USE_AZURE", "true").lower() == "true"
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")
openai_api_key = os.getenv("OPENAI_API_KEY", "")

print(f"USE_AZURE: {use_azure}")
print(f"AZURE endpoint configured: {bool(azure_endpoint)}")
print(f"AZURE API key configured: {bool(azure_api_key)}")
print(f"AZURE deployment: {azure_deployment}")
print(f"OPENAI API key configured: {bool(openai_api_key)}")

tickets = [
    {"id": 1, "title": "Payment failure at checkout"},
    {"id": 2, "title": "Login OTP delays"},
    {"id": 3, "title": "Offline video playback not working"},
]

print("\nTickets loaded for triage:")
for ticket in tickets:
    print(f"- Ticket {ticket['id']}: {ticket['title']}")

if use_azure and (not azure_endpoint or not azure_api_key):
    print("\nAzure is selected, but endpoint/key are not configured yet.")
    print("Next step will be to add your real values to .env before live agent calls.")
elif not use_azure and not openai_api_key:
    print("\nOpenAI mode is selected, but OPENAI_API_KEY is not configured yet.")
else:
    print("\nEnvironment appears ready for live LLM calls.")