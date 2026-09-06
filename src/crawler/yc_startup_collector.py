import asyncio
import json
from pathlib import Path

import aiohttp


# ============================================================
# CONFIGURATION
# ============================================================

SOURCE_URL = "https://yc-oss.github.io/api/companies/all.json"

OUTPUT_FILE = "data/raw/startup_urls.json"

MINIMUM_STARTUPS = 1000


# ============================================================
# FETCH YC COMPANY DATA
# ============================================================

async def fetch_company_data(session):

    print("\nFetching YC company dataset...")

    try:

        async with session.get(
            SOURCE_URL,
            timeout=aiohttp.ClientTimeout(total=60),
            headers={
                "User-Agent": (
                    "AI-Intelligence-Pipeline/1.0 "
                    "(educational research project)"
                )
            }
        ) as response:

            print(f"Status: {response.status}")

            if response.status != 200:

                print(
                    f"Failed to fetch dataset. "
                    f"HTTP status: {response.status}"
                )

                return None

            data = await response.json()

            return data

    except Exception as error:

        print(
            f"Error fetching YC dataset: {error}"
        )

        return None


# ============================================================
# EXTRACT COMPANY URLS
# ============================================================

def extract_startup_urls(companies):

    startup_urls = set()

    for company in companies:

        if not isinstance(company, dict):
            continue

        # Prefer the official YC company page
        url = company.get("url")

        if not url:
            continue

        if not isinstance(url, str):
            continue

        if not url.startswith(
            "https://www.ycombinator.com/companies/"
        ):
            continue

        # Ignore non-company directory pages
        if "/industry/" in url:
            continue

        if "/location/" in url:
            continue

        if "/jobs/" in url:
            continue

        startup_urls.add(url.rstrip("/"))

    return sorted(startup_urls)


# ============================================================
# SAVE URLS
# ============================================================

def save_urls(startup_urls):

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
            indent=4,
            ensure_ascii=False
        )

    print(
        f"\nSaved {len(startup_urls)} startup URLs."
    )

    print(
        f"Output file: {OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    async with aiohttp.ClientSession() as session:

        companies = await fetch_company_data(
            session
        )

        if not companies:

            print(
                "\nNo company data received."
            )

            return

        print(
            f"\nCompany records received: "
            f"{len(companies)}"
        )

        startup_urls = extract_startup_urls(
            companies
        )

        print(
            f"Valid YC startup URLs found: "
            f"{len(startup_urls)}"
        )

        if len(startup_urls) < MINIMUM_STARTUPS:

            print(
                "\nWARNING:"
            )

            print(
                f"Only {len(startup_urls)} "
                f"startup URLs were found."
            )

            print(
                f"The assignment requires at least "
                f"{MINIMUM_STARTUPS}."
            )

        else:

            print(
                f"\nSUCCESS:"
            )

            print(
                f"{len(startup_urls)} startup URLs "
                f"are available."
            )

        print(
            "\nFirst 10 URLs:"
        )

        for url in startup_urls[:10]:

            print(url)

        save_urls(startup_urls)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
