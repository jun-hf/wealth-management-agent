import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found in environment variables!")
    print("Please check your .env file")
    exit(1)

genai.configure(api_key=api_key)

print("=" * 60)
print("Available Gemini Models for generateContent:")
print("=" * 60)

try:
    models = genai.list_models()
    found_models = []
    
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            found_models.append(model.name)
            print(f"\n✓ {model.name}")
            print(f"  Display Name: {model.display_name}")
            print(f"  Description: {model.description}")
            print(f"  Supported Methods: {', '.join(model.supported_generation_methods)}")
    
    print("\n" + "=" * 60)
    print(f"Total models found: {len(found_models)}")
    print("=" * 60)
    
    if found_models:
        print("\n📋 Copy one of these model names to use in your code:")
        for model_name in found_models:
            print(f"  '{model_name}'")
    else:
        print("\n❌ No models found! Check your API key permissions.")
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    print("\nTroubleshooting:")
    print("1. Check if your GEMINI_API_KEY is valid")
    print("2. Visit https://makersuite.google.com/app/apikey to verify your key")
    print("3. Ensure your API key has access to Gemini models")