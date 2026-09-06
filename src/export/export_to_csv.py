import csv
import json
import os


# ============================================================
# FILE PATHS
# ============================================================

STARTUPS_FILE = "data/processed/startups_enriched.json"
PRODUCTS_FILE = "data/processed/products_resolved.json"
PAPERS_FILE = "data/raw/research_papers_github.json"
JOBS_FILE = "data/raw/jobs.json"
NEWS_FILE = "data/raw/news.json"
MAPPING_FILE = "data/processed/entity_mapping_log.json"

OUTPUT_DIR = "data/processed/export"


# ============================================================
# HELPERS
# ============================================================

def load_json(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)


def write_csv(filename, rows, fieldnames):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"[CREATED] {filepath}")
    print(f"          Rows: {len(rows)}")


def get_nested(data, *keys):
    current = data

    for key in keys:

        if not isinstance(current, dict):
            return None

        current = current.get(key)

    return current


# ============================================================
# STARTUPS
# ============================================================

def export_startups():

    data = load_json(STARTUPS_FILE)

    rows = []

    for item in data:

        content = item.get("content", {})
        source = item.get("source", {})
        inner_data = content.get("data", {})

        official_website = (
            inner_data.get("officialWebsite")
            or inner_data.get("website")
            or content.get("officialWebsite")
            or content.get("website")
        )

        rows.append({
            "schemaVersion": item.get("schemaVersion"),
            "recordType": item.get("recordType"),
            "startupName": content.get("entityName"),
            "employeeCount": inner_data.get("employeeCount"),
            "officialWebsite": official_website,
            "sourceName": source.get("name"),
            "sourceURL": source.get("url"),
            "collectedAt": item.get("collectedAt"),
        })

    write_csv(
        "Startups.csv",
        rows,
        [
            "schemaVersion",
            "recordType",
            "startupName",
            "employeeCount",
            "officialWebsite",
            "sourceName",
            "sourceURL",
            "collectedAt",
        ]
    )


# ============================================================
# PRODUCTS
# ============================================================

def export_products():

    data = load_json(PRODUCTS_FILE)

    rows = []

    for item in data:

        content = item.get("content", {})
        source = item.get("source", {})
        resolution = item.get("entityResolution", {})

        rows.append({
            "schemaVersion": item.get("schemaVersion"),
            "recordType": item.get("recordType"),
            "productName": content.get("productName"),
            "startupName": content.get("startupName"),
            "pricingModel": content.get("pricingModel"),
            "website": content.get("website"),
            "description": content.get("description"),
            "category": content.get("category"),
            "resolutionStatus": resolution.get("status"),
            "confidenceScore": resolution.get("confidenceScore"),
            "matchMethod": resolution.get("matchMethod"),
            "matchReason": resolution.get("matchReason"),
            "sourceName": source.get("name"),
            "sourceURL": source.get("url"),
            "collectedAt": item.get("collectedAt"),
        })

    write_csv(
        "Products.csv",
        rows,
        [
            "schemaVersion",
            "recordType",
            "productName",
            "startupName",
            "pricingModel",
            "website",
            "description",
            "category",
            "resolutionStatus",
            "confidenceScore",
            "matchMethod",
            "matchReason",
            "sourceName",
            "sourceURL",
            "collectedAt",
        ]
    )


# ============================================================
# RESEARCH PAPERS
# ============================================================

def export_papers():

    data = load_json(PAPERS_FILE)

    rows = []

    for item in data:

        rows.append({
            "schemaVersion": item.get("schemaVersion"),
            "recordType": item.get("recordType"),
            "title": item.get("title"),
            "authors": item.get("authors"),
            "paper_url": item.get("paper_url"),
            "github_url": item.get("github_url"),
            "github_stars": item.get("github_stars"),
            "published_date": item.get("published_date"),
        })

    write_csv(
        "Research_Papers.csv",
        rows,
        [
            "schemaVersion",
            "recordType",
            "title",
            "authors",
            "paper_url",
            "github_url",
            "github_stars",
            "published_date",
        ]
    )


# ============================================================
# JOBS
# ============================================================

def export_jobs():

    data = load_json(JOBS_FILE)

    rows = []

    for item in data:

        source = item.get("source", {})
        content = item.get("content", {})

        rows.append({
            "schemaVersion": item.get("schemaVersion"),
            "recordType": item.get("recordType"),
            "company": content.get("company"),
            "title": content.get("title"),
            "date": content.get("date"),
            "is_remote": content.get("is_remote"),
            "role_family": content.get("role_family"),
            "url": content.get("url"),
            "sourceName": source.get("name"),
            "sourceURL": source.get("url"),
            "collectedAt": item.get("collectedAt"),
        })

    write_csv(
        "Jobs.csv",
        rows,
        [
            "schemaVersion",
            "recordType",
            "company",
            "title",
            "date",
            "is_remote",
            "role_family",
            "url",
            "sourceName",
            "sourceURL",
            "collectedAt",
        ]
    )


# ============================================================
# NEWS
# ============================================================

def export_news():

    data = load_json(NEWS_FILE)

    rows = []

    for item in data:

        source = item.get("source", {})
        content = item.get("content", {})

        rows.append({
            "schemaVersion": item.get("schemaVersion"),
            "recordType": item.get("recordType"),
            "title": content.get("title"),
            "url": content.get("url"),
            "text": content.get("text"),
            "publishedAt": content.get("publishedAt"),
            "sourceName": source.get("name"),
            "sourceURL": source.get("url"),
            "collectionMethod": item.get("collectionMethod", "full_text"),
            "collectedAt": item.get("collectedAt"),
        })

    write_csv(
        "News.csv",
        rows,
        [
            "schemaVersion",
            "recordType",
            "title",
            "url",
            "text",
            "publishedAt",
            "sourceName",
            "sourceURL",
            "collectionMethod",
            "collectedAt",
        ]
    )


# ============================================================
# ENTITY MAPPING LOG
# ============================================================

def export_mapping_log():

    data = load_json(MAPPING_FILE)

    rows = []

    for item in data:

        rows.append({
            "schemaVersion": item.get("schemaVersion"),
            "recordType": item.get("recordType"),
            "productName": item.get("productName"),
            "productWebsite": item.get("productWebsite"),
            "startupName": item.get("startupName"),
            "startupWebsite": item.get("startupWebsite"),
            "matchStatus": item.get("matchStatus"),
            "confidenceScore": item.get("confidenceScore"),
            "matchMethod": item.get("matchMethod"),
            "matchReason": item.get("matchReason"),
            "startupSourceUrl": item.get("startupSourceUrl"),
            "mappedAt": item.get("mappedAt"),
        })

    write_csv(
        "Entity_Mapping_Log.csv",
        rows,
        [
            "schemaVersion",
            "recordType",
            "productName",
            "productWebsite",
            "startupName",
            "startupWebsite",
            "matchStatus",
            "confidenceScore",
            "matchMethod",
            "matchReason",
            "startupSourceUrl",
            "mappedAt",
        ]
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("AI INTELLIGENCE PIPELINE")
    print("FINAL CSV EXPORT")
    print("=" * 70)
    print()

    export_startups()
    export_products()
    export_papers()
    export_jobs()
    export_news()
    export_mapping_log()

    print()
    print("=" * 70)
    print("EXPORT COMPLETE")
    print("=" * 70)
    print()
    print(f"Output folder: {OUTPUT_DIR}")
    print()
    print("Files created:")
    print("  1. Startups.csv")
    print("  2. Products.csv")
    print("  3. Research_Papers.csv")
    print("  4. Jobs.csv")
    print("  5. News.csv")
    print("  6. Entity_Mapping_Log.csv")
    print()


if __name__ == "__main__":
    main()