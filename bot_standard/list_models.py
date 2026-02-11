
import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print(f"Python Executable: {sys.executable}")
print(f"Google Generative AI Version: {genai.__version__}")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY is missing in .env!")
else:
    print(f"✅ GEMINI_API_KEY found. Listing available models...")

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"❌ Error: {e}")
