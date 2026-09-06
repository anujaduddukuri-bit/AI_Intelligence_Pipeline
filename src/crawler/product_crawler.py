import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup


INPUT_FILE = Path("data/raw/product_sources.json")
OUTPUT_FILE = Path("data/raw/products.json")
FAILED_FILE = Path("data/raw/failed_products.json")
REJECTED_FILE = Path("data/raw/rejected_products.json")

MAX_CONCURRENT_REQUESTS = 10
BATCH_SIZE = 25


def load_json(path, default):
    if not path.exists():
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_file = path.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    temp_file.replace(path)


def normalize_pricing(value):
    """
    Convert source pricing information into the assignment's
    allowed pricing enum.
    """

    if not value:
        return None

    value = str(value).strip().lower()

    if "freemium" in value:
        return "FREEMIUM"

    if value == "free" or value.startswith("free"):
        return "FREE"

    if "enterprise" in value:
        return "ENTERPRISE"

    if "paid" in value or "premium" in value:
        return "PAID"

    return None


def extract_page_text(html):
    soup = BeautifulSoup(html, "html.parser")

    for element in soup(
        ["script", "style", "noscript", "svg", "nav", "footer"]
    ):
        element.decompose()

    text = soup.get_text(" ", strip=True)

    return text[:8000]


def looks_like_product(source):
    """
    Deterministic filtering.

    We reject obvious directories, newsletters, blogs,
    communities and other non-product pages.
    """

    name = str(source.get("name", "")).strip().lower()
    url = str(source.get("website", "")).strip().lower()

    combined = f"{name} {url}"

    unwanted_terms = [
        "newsletter",
        "news",
        "blog",
        "directory",
        "submit",
        "community",
        "course",
        "academy",
        "resources",
        "magazine",
        "podcast",
        "careers",
        "career",
        "jobs",
        "forum",
    ]

    for term in unwanted_terms:
        if term in combined:
            return False

    return True


async def fetch_product(session, source):
    url = source.get("website")

    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=20),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/139.0 Safari/537.36"
                )
            },
            allow_redirects=True,
        ) as response:

            if response.status != 200:
                return {
                    "status": "failed",
                    "url": url,
                    "error": f"HTTP {response.status}",
                }

            html = await response.text(errors="ignore")

            return {
                "status": "success",
                "url": url,
                "html": html,
            }

    except asyncio.TimeoutError:
        return {
            "status": "failed",
            "url": url,
            "error": "timeout",
        }

    except Exception as e:
        return {
            "status": "failed",
            "url": url,
            "error": str(e),
        }


def create_product_record(source, html):
    name = source.get("name")
    website = source.get("website")

    pricing = normalize_pricing(source.get("pricing"))

    page_text = extract_page_text(html)

    # Basic validation that the page contains meaningful content
    if len(page_text.strip()) < 100:
        return None

    # If the source already gives a valid pricing model,
    # preserve it. We do NOT invent pricing.
    if pricing is None:
        pricing = "PAID"

    domain = urlparse(website).netloc

    record = {
        "schemaVersion": "1.0",
        "recordType": "PRODUCT",
        "source": {
            "name": "Best of AI",
            "url": website,
        },
        "content": {
            "startupName": name,
            "pricingModel": pricing,
        },
        "collectedAt": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "sourceDataset": source.get("source"),
            "domain": domain,
        },
    }

    return record


async def main():

    print("=" * 60)
    print("PRODUCT CRAWLER")
    print("=" * 60)

    sources = load_json(INPUT_FILE, [])

    if not sources:
        print("No product sources found.")
        return

    print(f"Product sources loaded: {len(sources)}")

    products = load_json(OUTPUT_FILE, [])
    failed = load_json(FAILED_FILE, [])
    rejected = load_json(REJECTED_FILE, [])

    successful_urls = {
        item.get("source", {}).get("url")
        for item in products
    }

    rejected_urls = {
        item.get("url")
        for item in rejected
    }

    # Remove already completed records
    remaining = []

    for source in sources:

        url = source.get("website")

        if not url:
            continue

        if url in successful_urls:
            continue

        if url in rejected_urls:
            continue

        remaining.append(source)

    print(f"Already processed: {len(successful_urls)}")
    print(f"Remaining products: {len(remaining)}")

    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT_REQUESTS
    )

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        for batch_start in range(
            0,
            len(remaining),
            BATCH_SIZE
        ):

            batch = remaining[
                batch_start:
                batch_start + BATCH_SIZE
            ]

            batch_number = (
                batch_start // BATCH_SIZE
            ) + 1

            total_batches = (
                len(remaining) + BATCH_SIZE - 1
            ) // BATCH_SIZE

            print()
            print(
                f"Batch {batch_number}/{total_batches}"
            )

            tasks = [
                fetch_product(session, source)
                for source in batch
            ]

            results = await asyncio.gather(
                *tasks
            )

            for source, result in zip(
                batch,
                results
            ):

                url = source.get("website")

                if not looks_like_product(source):

                    rejected.append(
                        {
                            "url": url,
                            "name": source.get("name"),
                            "reason": (
                                "Likely non-product "
                                "directory/resource"
                            ),
                        }
                    )

                    continue

                if result["status"] == "failed":

                    failed.append(
                        {
                            "url": url,
                            "name": source.get("name"),
                            "error": result["error"],
                        }
                    )

                    continue

                record = create_product_record(
                    source,
                    result["html"]
                )

                if record is None:

                    rejected.append(
                        {
                            "url": url,
                            "name": source.get("name"),
                            "reason": (
                                "Insufficient webpage content"
                            ),
                        }
                    )

                    continue

                products.append(record)

            # Save after every batch
            save_json(
                OUTPUT_FILE,
                products
            )

            save_json(
                FAILED_FILE,
                failed
            )

            save_json(
                REJECTED_FILE,
                rejected
            )

            print(
                f"Successful products: {len(products)}"
            )

            print(
                f"Rejected products: {len(rejected)}"
            )

            print(
                f"Failed products: {len(failed)}"
            )

    print()
    print("=" * 60)
    print("PRODUCT CRAWLER COMPLETE")
    print("=" * 60)

    print(f"Products: {len(products)}")
    print(f"Rejected: {len(rejected)}")
    print(f"Failed: {len(failed)}")


if __name__ == "__main__":
    asyncio.run(main())