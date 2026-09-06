import asyncio
import json
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup


SOURCE_URL = "https://www.ycombinator.com/companies/industry/ai"
OUTPUT_FILE = "data/raw/startup_urls.json"


async def fetch_page(session, url):
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/139.0 Safari/537.36"
                )
            },
        ) as response:

            print(f"Status: {response.status}")

            if response.status != 200:
                print(f"Failed to fetch: {url}")
                return None

            return await response.text()

    except Exception as error:
        print(f"Error fetching {url}: {error}")
        return None


async def collect_startup_urls():

    async with aiohttp.ClientSession() as session:

        html = await fetch_page(session, SOURCE_URL)

        if not html:
            print("Could not retrieve YC directory.")
            return

        soup = BeautifulSoup(html, "html.parser")

        startup_urls = set()

        for link in soup.find_all("a", href=True):

            href = link["href"]

            # Only accept actual YC company profile URLs.
            #
            # Valid:
            # /companies/company-name
            #
            # Ignore:
            # /companies/industry/...
            # /companies/location/...
            # /companies/jobs/...
            if (
                href.startswith("/companies/")
                and not href.startswith("/companies/industry/")
                and not href.startswith("/companies/location/")
                and not href.startswith("/companies/jobs/")
            ):

                full_url = "https://www.ycombinator.com" + href

                startup_urls.add(full_url)

        startup_urls = sorted(startup_urls)

        print(f"\nFound {len(startup_urls)} startup URLs.")

        for url in startup_urls[:10]:
            print(url)

        output_path = Path(OUTPUT_FILE)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                startup_urls,
                file,
                indent=4
            )

        print(
            f"\nSaved {len(startup_urls)} URLs to "
            f"{OUTPUT_FILE}"
        )


if __name__ == "__main__":
    asyncio.run(collect_startup_urls())