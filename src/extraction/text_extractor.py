import aiohttp
import asyncio
from bs4 import BeautifulSoup


async def extract_text(url):

    async with aiohttp.ClientSession() as session:

        try:
            async with session.get(url, timeout=10) as response:

                print("Status:", response.status)

                if response.status != 200:
                    print("Could not access webpage")
                    return

                html = await response.text()

                soup = BeautifulSoup(html, "html.parser")

                # Remove unnecessary elements
                for element in soup(["script", "style", "nav", "footer"]):
                    element.decompose()

                # Extract visible text
                text = soup.get_text(separator=" ", strip=True)

                print("\nExtracted text:\n")
                print(text[:2000])

        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":

    asyncio.run(
        extract_text("https://example.com")
    )