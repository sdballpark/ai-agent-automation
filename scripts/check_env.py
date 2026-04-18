from dotenv import load_dotenv
import os

load_dotenv()

print("=== Environment Check ===")

print(f"USE_AZURE: {os.getenv('USE_AZURE')}")
print(f"AZURE_OPENAI_API_KEY set: {bool(os.getenv('AZURE_OPENAI_API_KEY'))}")
print(f"AZURE_OPENAI_ENDPOINT set: {bool(os.getenv('AZURE_OPENAI_ENDPOINT'))}")
print(f"AZURE_OPENAI_DEPLOYMENT: {os.getenv('AZURE_OPENAI_DEPLOYMENT')}")
print(f"OPENAI_API_KEY set: {bool(os.getenv('OPENAI_API_KEY'))}")