import aiohttp
import asyncio
from bs4 import BeautifulSoup


async def scrape_page(url):
    async with aiohttp.ClientSession() as session:

        try:
            async with session.get(url) as response:

                print("Status:", response.status)

                html = await response.text()

                soup = BeautifulSoup(html, "html.parser")

                title = soup.title.string if soup.title else "No title"

                print("Title:", title)

        except Exception as e:
            print("Error:", e)


asyncio.run(scrape_page("https://example.com"))