import aiohttp
import asyncio
from bs4 import BeautifulSoup


urls = [
    "https://example.com",
    "https://www.python.org",
    "https://www.wikipedia.org",
    "https://www.github.com"
]


async def scrape_page(session, url):

    for attempt in range(3):

        try:
            async with session.get(url, timeout=10) as response:

                print(f"URL: {url}")
                print(f"Status: {response.status}")

                if response.status == 200:

                    html = await response.text()

                    soup = BeautifulSoup(html, "html.parser")

                    title = (
                        soup.title.string.strip()
                        if soup.title and soup.title.string
                        else "No title"
                    )

                    print(f"Title: {title}")
                    print("Success")

                    return

                elif response.status == 403:

                    print("Access forbidden (403)")
                    return

                elif response.status == 429:

                    print("Rate limited (429)")

                    await asyncio.sleep(2 ** attempt)

                else:

                    print(f"HTTP error: {response.status}")
                    return

        except asyncio.TimeoutError:

            print(f"Timeout - Attempt {attempt + 1}/3")

        except Exception as e:

            print(f"Error - Attempt {attempt + 1}/3: {e}")

        await asyncio.sleep(1)


async def main():

    async with aiohttp.ClientSession() as session:

        tasks = []

        for url in urls:

            tasks.append(
                scrape_page(session, url)
            )

        await asyncio.gather(*tasks)


if __name__ == "__main__":

    asyncio.run(main())