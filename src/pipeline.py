import aiohttp
import asyncio
import json
from bs4 import BeautifulSoup
from google import genai
from dotenv import load_dotenv
import os


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Gemini API key not found!")
    exit()

client = genai.Client(api_key=api_key)


async def scrape_and_extract(url):

    print("Fetching:", url)

    async with aiohttp.ClientSession() as session:

        try:

            async with session.get(url, timeout=10) as response:

                print("HTTP Status:", response.status)

                if response.status != 200:
                    print("Could not access webpage.")
                    return

                html = await response.text()

                # Convert HTML to text
                soup = BeautifulSoup(html, "html.parser")

                # Remove unnecessary elements
                for element in soup(["script", "style", "nav", "footer"]):
                    element.decompose()

                text = soup.get_text(separator=" ", strip=True)

                print("\nExtracted webpage text:")
                print(text[:1000])

                # Send text to Gemini
                prompt = f"""
You are a strict startup data extraction system.

Your task is to determine whether the webpage contains information
about an actual startup/company.

IMPORTANT RULES:

1. Only use information explicitly present in the webpage text.
2. Do not guess or invent information.
3. Do not treat a webpage title, website name, or domain name alone
   as evidence that the entity is a startup.
4. The webpage must contain meaningful information about an actual
   company or startup.
5. If the webpage is a documentation page, example page, blog,
   unrelated website, or does not clearly describe a company,
   set isStartup to false.
6. If employee count is not available, use null.
7. If the entity is not a startup/company, entityName must be null.
8. Return ONLY valid JSON.
9. Do not add explanations.

Webpage text:

{text[:8000]}

Return exactly this JSON structure:

{{
    "isStartup": false,
    "entityName": null,
    "employeeCount": null
}}
"""

                print("\nSending data to Gemini...")

                interaction = client.interactions.create(
                    model="gemini-3.6-flash",
                    input=prompt
                )

                result = interaction.output_text

                print("\nGemini response:")
                print(result)

                # Convert Gemini response to Python dictionary
                try:

                    data = json.loads(result)

                    print("\nFinal structured data:")
                    print(json.dumps(data, indent=4))

                except json.JSONDecodeError:

                    print("Gemini returned invalid JSON.")


        except Exception as e:

            print("Error:", e)


if __name__ == "__main__":

    asyncio.run(
        scrape_and_extract("https://example.com")
    )