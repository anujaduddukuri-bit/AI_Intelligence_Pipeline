import asyncio
import json
from pathlib import Path

import aiohttp


SOURCE_URL = "https://bestaihub.cc/index.json"
OUTPUT_FILE = Path("data/raw/product_urls.json")
METADATA_FILE = Path("data/raw/product_sources.json")


async def fetch_source(session):
    try:
        async with session.get(
            SOURCE_URL,
            timeout=aiohttp.ClientTimeout(total=60),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/139.0 Safari/537.36"
                )
            },
        ) as response:

            print(f"Status: {response.status}")

            if response.status != 200:
                return None

            return await response.json(content_type=None)

    except Exception as e:
        print(f"ERROR: {e}")
        return None


def clean_products(data):

    products = []
    seen_websites = set()

    if not isinstance(data, list):
        return products

    for item in data:

        if not isinstance(item, dict):
            continue

        # Only actual tool records
        if item.get("type") != "tool":
            continue

        # Ignore dead entries
        if item.get("dead") is True:
            continue

        name = item.get("name")
        website = item.get("website")
        price = item.get("price")

        if not name or not website:
            continue

        website = website.strip()

        if not website.startswith(("http://", "https://")):
            continue

        # Deduplicate by official website
        website_key = website.lower().rstrip("/")

        if website_key in seen_websites:
            continue

        seen_websites.add(website_key)

        products.append(
            {
                "name": name.strip(),
                "website": website,
                "pricing": price,
                "category": item.get("category"),
                "description": item.get("description"),
                "source": SOURCE_URL,
            }
        )

    return products


async def main():

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 60)
    print("AI PRODUCT COLLECTOR")
    print("=" * 60)

    print(f"Source: {SOURCE_URL}")

    connector = aiohttp.TCPConnector(limit=10)

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        data = await fetch_source(session)

    if data is None:
        print("Failed to download product dataset.")
        return

    print(f"Total records received: {len(data)}")

    products = clean_products(data)

    print(f"Valid AI products found: {len(products)}")

    # Product URLs only
    product_urls = [
        product["website"]
        for product in products
    ]

    # Save URLs
    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            product_urls,
            f,
            indent=4,
            ensure_ascii=False
        )

    # Save metadata separately
    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            products,
            f,
            indent=4,
            ensure_ascii=False
        )

    print()
    print("=" * 60)
    print("PRODUCT COLLECTION COMPLETE")
    print("=" * 60)

    print(f"Clean product URLs: {len(product_urls)}")
    print(f"URL file: {OUTPUT_FILE}")
    print(f"Metadata file: {METADATA_FILE}")

    print()
    print("First 20 products:")

    for product in products[:20]:

        print(
            f"{product['name']} | "
            f"{product['pricing']} | "
            f"{product['website']}"
        )


if __name__ == "__main__":
    asyncio.run(main())