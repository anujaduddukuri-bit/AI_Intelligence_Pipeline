import json
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_URL = (
    "https://raw.githubusercontent.com/"
    "withkarann/aifoxx/main/src/data/tools.json"
)

OUTPUT_FILE = Path("data/raw/product_sources_2.json")


def fetch_json(url):
    request = Request(
        url,
        headers={
            "User-Agent": "AI-Intelligence-Pipeline/1.0"
        }
    )

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_pricing(value):
    if not value:
        return None

    value = str(value).strip().upper()

    mapping = {
        "FREE": "FREE",
        "FREEMIUM": "FREEMIUM",
        "PAID": "PAID",
        "ENTERPRISE": "ENTERPRISE",
        "OPEN SOURCE": "FREE",
        "OPEN-SOURCE": "FREE",
    }

    return mapping.get(value)


def clean_url(url):
    if not url:
        return None

    url = str(url).strip()

    if not url.startswith(("http://", "https://")):
        return None

    return url.rstrip("/")


def collect_products():

    print("=" * 60)
    print("PRODUCT SOURCE 2 COLLECTOR")
    print("=" * 60)

    print(f"Source: {SOURCE_URL}")

    try:
        data = fetch_json(SOURCE_URL)
    except Exception as e:
        print(f"ERROR: Could not download source")
        print(e)
        return

    print(f"Records received: {len(data)}")

    products = []
    seen_urls = set()

    for item in data:

        if not isinstance(item, dict):
            continue

        name = item.get("name")
        website = clean_url(item.get("url"))
        description = item.get("description")
        category = item.get("category")
        pricing = normalize_pricing(item.get("pricing"))
        status = str(item.get("status", "")).lower()

        # Required fields
        if not name:
            continue

        if not website:
            continue

        # Do not include dead products
        if status and status != "active":
            continue

        # Deduplicate within Source 2
        normalized_url = website.lower()

        if normalized_url in seen_urls:
            continue

        seen_urls.add(normalized_url)

        products.append(
            {
                "name": str(name).strip(),
                "website": website,
                "description": (
                    str(description).strip()
                    if description
                    else None
                ),
                "category": (
                    str(category).strip()
                    if category
                    else None
                ),
                "pricing": pricing,
                "source": "AIFOXX",
                "source_url": SOURCE_URL,
                "last_verified": item.get("last_verified"),
            }
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            products,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 60)
    print("SOURCE 2 COLLECTION COMPLETE")
    print("=" * 60)

    print(f"Valid products: {len(products)}")
    print(f"Output: {OUTPUT_FILE}")

    print()
    print("First 10 products:")

    for product in products[:10]:
        print(
            f"{product['name']} | "
            f"{product['pricing']} | "
            f"{product['website']}"
        )


if __name__ == "__main__":
    collect_products()