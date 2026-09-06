import json


STARTUPS_FILE = "data/processed/startups.json"
PRODUCTS_FILE = "data/raw/products_merged.json"


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def main():

    startups = load_json(STARTUPS_FILE)
    products = load_json(PRODUCTS_FILE)

    print("=" * 70)
    print("ENTITY RESOLUTION DATA DIAGNOSTIC")
    print("=" * 70)

    # --------------------------------------------------------
    # STARTUP STRUCTURE
    # --------------------------------------------------------

    print("\nSTARTUP SAMPLE")
    print("-" * 70)

    for key, value in startups[0].items():
        print(f"{key}: {value}")

    print("\nSTARTUP CONTENT")
    print("-" * 70)

    content = startups[0].get("content", {})

    for key, value in content.items():
        print(f"{key}: {value}")

    # --------------------------------------------------------
    # PRODUCT STRUCTURE
    # --------------------------------------------------------

    print("\nPRODUCT SAMPLE")
    print("-" * 70)

    for key, value in products[0].items():
        print(f"{key}: {value}")

    print("\nPRODUCT CONTENT")
    print("-" * 70)

    product_content = products[0].get("content", {})

    for key, value in product_content.items():
        print(f"{key}: {value}")

    # --------------------------------------------------------
    # STARTUP URL ANALYSIS
    # --------------------------------------------------------

    print("\nSTARTUP URL ANALYSIS")
    print("-" * 70)

    possible_urls = []

    for startup in startups:

        source = startup.get("source", {})
        content = startup.get("content", {})

        urls = [
            source.get("url"),
            source.get("website"),
            content.get("website"),
            content.get("url"),
            startup.get("website"),
            startup.get("url"),
        ]

        for url in urls:
            if url:
                possible_urls.append(url)

    print(f"Total startups: {len(startups)}")
    print(f"Startup URLs found: {len(possible_urls)}")

    print("\nFirst 20 startup URLs:")

    for url in possible_urls[:20]:
        print(url)

    # --------------------------------------------------------
    # PRODUCT URL ANALYSIS
    # --------------------------------------------------------

    print("\nPRODUCT URL ANALYSIS")
    print("-" * 70)

    product_urls = []

    for product in products:

        source = product.get("source", {})
        content = product.get("content", {})

        urls = [
            source.get("url"),
            source.get("website"),
            content.get("website"),
            content.get("url"),
            product.get("website"),
            product.get("url"),
        ]

        for url in urls:
            if url:
                product_urls.append(url)

    print(f"Total products: {len(products)}")
    print(f"Product URLs found: {len(product_urls)}")

    print("\nFirst 20 product URLs:")

    for url in product_urls[:20]:
        print(url)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()