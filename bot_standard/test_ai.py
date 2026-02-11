
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY is missing in .env!")
else:
    print(f"✅ GEMINI_API_KEY found: {GEMINI_API_KEY[:4]}...{GEMINI_API_KEY[-4:]}")

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Hello, workd!")
        print(f"✅ AI Response: {response.text}")
    except Exception as e:
        print(f"❌ AI Error: {e}")
