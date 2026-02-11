
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

gemini_versions = [
    'gemini-2.5-flash',
    'gemini-2.5-pro',
    'gemini-2.0-flash',
    'gemini-2.0-flash-001',
    'gemini-2.0-flash-exp-image-generation',
    'gemini-2.0-flash-lite-001',
    'gemini-2.0-flash-lite',
    'gemini-exp-1206',
    'gemini-2.5-flash-preview-tts',
    'gemini-2.5-pro-preview-tts',
    'gemma-3-1b-it',
    'gemma-3-4b-it',
    'gemma-3-12b-it',
    'gemma-3-27b-it',
    'gemma-3n-e4b-it',
    'gemma-3n-e2b-it',
    'gemini-flash-latest',
    'gemini-flash-lite-latest',
    'gemini-pro-latest',
    'gemini-2.5-flash-lite',
    'gemini-2.5-flash-image',
    'gemini-2.5-flash-preview-09-2025',
    'gemini-2.5-flash-lite-preview-09-2025',
    'gemini-3-pro-preview',
    'gemini-3-flash-preview',
    'gemini-3-pro-image-preview',
    'nano-banana-pro-preview',
    'gemini-robotics-er-1.5-preview',
    'gemini-2.5-computer-use-preview-10-2025',
    'deep-research-pro-preview-12-2025']

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
for i in gemini_versions:
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY is missing in .env!")
    else:
        print(f"✅ GEMINI_API_KEY found: {GEMINI_API_KEY[:4]}...{GEMINI_API_KEY[-4:]}")

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(i)
        print(f"✅ Model: {i}")
        response = model.generate_content("Hello, workd!")
        print(f"✅ AI Response: {response.text}")
    except Exception as e:
        print(f"❌ AI Error: {e}")
