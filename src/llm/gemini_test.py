import os
from dotenv import load_dotenv
from google import genai

# Load API key from .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Gemini API key not found!")
    exit()

# Create Gemini client
client = genai.Client(api_key=api_key)

# Send request using the current Interactions API
interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input="What is a startup? Explain in one sentence."
)

print("Gemini response:")
print(interaction.output_text)