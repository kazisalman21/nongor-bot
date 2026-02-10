
import os
import google.generativeai as genai
from dotenv import load_dotenv
import traceback

try:
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env")
        exit(1)
    
    print(f"Using API Key: {api_key[:10]}...")
    genai.configure(api_key=api_key)

    print("Fetching models...")
    models = genai.list_models()
    count = 0
    for m in models:
        count += 1
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name} ({m.display_name})")
    
    print(f"Total models found: {count}")
except Exception as e:
    print(f"FAILED with error: {e}")
    traceback.print_exc()
