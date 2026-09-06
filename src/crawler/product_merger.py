import json
import re
from pathlib import Path
from urllib.parse import urlparse


SOURCE1_FILE = Path("data/raw/product_sources.json")
SOURCE2_FILE = Path("data/raw/product_sources_2.json")

EXISTING_PRODUCTS_FILE = Path("data/raw/products.json")

OUTPUT_FILE = Path("data/raw/products_merged.json")
URL_FILE = Path("data/raw/product_urls_merged.json")

TARGET_COUNT = 1000


def load_json(path):

    if not path.exists():
        print(f"WARNING: File not found: {path}")
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print(f"ERROR reading {path}: {e}")
        return []


def normalize_url(url):

    if not url:
        return None

    try:
        parsed = urlparse(url.strip().lower())

        if not parsed.netloc:
            return None

        host = parsed.netloc

        if host.startswith("www."):
            host = host[4:]

        return host

    except Exception:
        return None


def normalize_name(name):

    if not name:
        return ""

    name = str(name).lower().strip()

    name = re.sub(
        r"[^a-z0-9]+",
        " ",
        name
    )

    return " ".join(name.split())


def normalize_pricing(value):

    if not value:
        return None

    value = str(value).strip().upper()

    allowed = {
        "FREE",
        "FREEMIUM",
        "PAID",
        "ENTERPRISE",
    }

    return value if value in allowed else None


def create_product_record(product, source_name):

    name = product.get("name")

    website = (
        product.get("website")
        or product.get("url")
    )

    pricing = normalize_pricing(
        product.get("pricing")
    )

    description = product.get("description")

    category = product.get("category")

    return {
        "schemaVersion": "1.0",
        "recordType": "PRODUCT",

        "source": {
            "name": source_name,
            "url": (
                product.get("source_url")
                or website
            ),
        },

        "content": {
            "productName": name,
            "startupName": None,
            "pricingModel": pricing,
            "website": website,
            "description": description,
            "category": category,
        },

        "collectedAt": (
            product.get("last_verified")
            or product.get("collectedAt")
        ),
    }


def merge_products():

    print("=" * 60)
    print("PRODUCT SOURCE MERGER")
    print("=" * 60)

    source1 = load_json(SOURCE1_FILE)
    source2 = load_json(SOURCE2_FILE)

    existing = load_json(EXISTING_PRODUCTS_FILE)

    print(f"Source 1 candidates: {len(source1)}")
    print(f"Source 2 candidates: {len(source2)}")
    print(f"Existing validated products: {len(existing)}")

    merged = []

    seen_domains = set()
    seen_names = set()

    duplicate_count = 0

    def add_product(product, source_name):

        nonlocal duplicate_count

        if not isinstance(product, dict):
            return

        name = (
            product.get("name")
            or product.get("productName")
        )

        website = (
            product.get("website")
            or product.get("url")
        )

        if not name or not website:
            return

        domain = normalize_url(website)
        normalized_name = normalize_name(name)

        if not domain:
            return

        # Strong duplicate check: same official domain
        if domain in seen_domains:
            duplicate_count += 1
            return

        # Secondary duplicate check
        if normalized_name and normalized_name in seen_names:
            duplicate_count += 1
            return

        seen_domains.add(domain)

        if normalized_name:
            seen_names.add(normalized_name)

        record = create_product_record(
            product,
            source_name
        )

        merged.append(record)

    # --------------------------------------------------
    # Existing validated products first
    # --------------------------------------------------

    for product in existing:

        if not isinstance(product, dict):
            continue

        content = product.get("content", {})

        if content:

            product_data = {
                "name": content.get("productName"),
                "website": content.get("website"),
                "pricing": content.get("pricingModel"),
                "description": content.get("description"),
                "category": content.get("category"),
                "source_url": (
                    product
                    .get("source", {})
                    .get("url")
                ),
                "collectedAt": product.get(
                    "collectedAt"
                ),
            }

            add_product(
                product_data,
                product
                .get("source", {})
                .get("name", "Existing")
            )

        else:

            add_product(
                product,
                product
                .get("source", "Existing")
            )

    existing_after_merge = len(merged)

    print(
        f"Products retained from existing dataset: "
        f"{existing_after_merge}"
    )

    # --------------------------------------------------
    # Add Source 1
    # --------------------------------------------------

    before = len(merged)

    for product in source1:
        add_product(
            product,
            "Best of AI"
        )

    source1_added = len(merged) - before

    print(
        f"New products added from Source 1: "
        f"{source1_added}"
    )

    # --------------------------------------------------
    # Add Source 2
    # --------------------------------------------------

    before = len(merged)

    for product in source2:
        add_product(
            product,
            "AIFOXX"
        )

    source2_added = len(merged) - before

    print(
        f"New products added from Source 2: "
        f"{source2_added}"
    )

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

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
            merged,
            f,
            indent=2,
            ensure_ascii=False
        )

    urls = []

    for record in merged:

        website = (
            record
            .get("content", {})
            .get("website")
        )

        if website:
            urls.append(website)

    with open(
        URL_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            urls,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 60)
    print("PRODUCT MERGE COMPLETE")
    print("=" * 60)

    print(f"Final unique products: {len(merged)}")
    print(f"Duplicates removed: {duplicate_count}")
    print(f"Target: {TARGET_COUNT}")

    if len(merged) >= TARGET_COUNT:

        print()
        print("SUCCESS!")
        print(
            f"Target achieved: "
            f"{len(merged)} >= {TARGET_COUNT}"
        )

    else:

        remaining = TARGET_COUNT - len(merged)

        print()
        print("TARGET NOT YET ACHIEVED")
        print(
            f"Need {remaining} more unique products."
        )

    print()
    print(f"Merged records: {OUTPUT_FILE}")
    print(f"Merged URLs: {URL_FILE}")


if __name__ == "__main__":
    merge_products()