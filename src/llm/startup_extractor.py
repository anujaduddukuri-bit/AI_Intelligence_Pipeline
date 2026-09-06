import os
import json
from dotenv import load_dotenv
from google import genai

# Load API key
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Gemini API key not found!")
    exit()

# Create Gemini client
client = genai.Client(api_key=api_key)


# Example webpage text
webpage_text = """
TechNova AI is an artificial intelligence startup based in Hyderabad.
The company develops AI-powered business automation software.
TechNova AI has approximately 75 employees.
"""


# Prompt Gemini
prompt = f"""
You are a data extraction system.

Extract startup information from the webpage text below.

IMPORTANT RULES:
1. Only use information explicitly present in the text.
2. Do not guess or invent information.
3. If employee count is not available, use null.
4. Return ONLY valid JSON.
5. Do not add explanations.

Webpage text:
{webpage_text}

Return this JSON structure:

{{
    "entityName": "",
    "employeeCount": null
}}
"""


# Call Gemini
interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input=prompt
)


# Get response
result = interaction.output_text

print("Raw Gemini response:")
print(result)


# Convert response to Python dictionary
try:

    data = json.loads(result)

    print("\nStructured JSON:")
    print(json.dumps(data, indent=4))

except json.JSONDecodeError:

    print("\nGemini did not return valid JSON.")