import json
import os
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse


# ============================================================
# AI INTELLIGENCE PIPELINE
# FINAL DATA VALIDATION
# ============================================================


# ============================================================
# FILE PATHS
# ============================================================

STARTUPS_FILE = "data/processed/startups_enriched.json"
PRODUCTS_FILE = "data/processed/products_resolved.json"
PAPERS_FILE = "data/raw/research_papers_github.json"
NEWS_FILE = "data/raw/news.json"
JOBS_FILE = "data/raw/jobs.json"
MAPPING_FILE = "data/processed/entity_mapping_log.json"


# ============================================================
# MINIMUM ASSIGNMENT TARGETS
# ============================================================

STARTUP_TARGET = 1000
PRODUCT_TARGET = 1000
PAPER_TARGET = 1000

LOOKBACK_HOURS = 24


# ============================================================
# VALID VALUES
# ============================================================

VALID_PRICING_MODELS = {
    "FREE",
    "FREEMIUM",
    "PAID",
    "ENTERPRISE"
}

VALID_MAPPING_STATUSES = {
    "MATCHED",
    "UNRESOLVED"
}


# ============================================================
# GLOBAL VALIDATION RESULTS
# ============================================================

validation_results = {}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def load_json(filename):
    """
    Load JSON file safely.

    Returns:
        list/dict: Parsed JSON data
        []       : If file is missing or invalid
    """

    if not os.path.exists(filename):
        print(f"[WARNING] File not found: {filename}")
        return []

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as error:
        print(f"[ERROR] Could not read {filename}: {error}")
        return []


def is_valid_url(url):
    """
    Check whether a value is a valid HTTP/HTTPS URL.
    """

    if not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)

        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
        )

    except Exception:
        return False


def normalize_name(name):
    """
    Normalize names for duplicate detection.
    """

    if not isinstance(name, str):
        return ""

    name = name.lower().strip()

    name = re.sub(
        r"[^a-z0-9]+",
        "",
        name
    )

    return name


def normalize_url(url):
    """
    Normalize URL for duplicate detection.
    """

    if not isinstance(url, str):
        return ""

    return url.strip().lower().rstrip("/")


def normalize_domain(url):
    """
    Extract normalized domain from URL.
    """

    if not is_valid_url(url):
        return ""

    try:
        domain = urlparse(url).netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:
        return ""


def parse_datetime(value):
    """
    Parse ISO-8601 datetime safely.
    """

    if not value:
        return None

    if not isinstance(value, str):
        return None

    try:

        value = value.strip()

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def print_status(status):
    """
    Print a consistent validation status.
    """

    print(f"STATUS: {status}")


# ============================================================
# STARTUP VALIDATION
# ============================================================

def validate_startups():

    print("\n" + "=" * 70)
    print("STARTUP VALIDATION")
    print("=" * 70)

    data = load_json(STARTUPS_FILE)

    total = len(data)

    names = []
    urls = []

    missing_names = 0
    invalid_urls = 0
    schema_errors = 0

    websites_found = 0
    missing_websites = 0

    for record in data:

        content = record.get(
            "content",
            {}
        )

        source = record.get(
            "source",
            {}
        )

        # ----------------------------------------------------
        # Record type
        # ----------------------------------------------------

        if record.get("recordType") != "STARTUP":
            schema_errors += 1

        # ----------------------------------------------------
        # Startup name
        # ----------------------------------------------------

        name = content.get(
            "entityName"
        )

        if not name:
            missing_names += 1
        else:
            names.append(
                normalize_name(name)
            )

        # ----------------------------------------------------
        # Source URL
        # ----------------------------------------------------

        source_url = source.get(
            "url"
        )

        if not source_url:

            invalid_urls += 1

        elif not is_valid_url(source_url):

            invalid_urls += 1

        else:

            urls.append(
                normalize_url(source_url)
            )

        # ----------------------------------------------------
        # Official website
        #
        # The enrichment process may store the website in
        # different locations, so check several legitimate
        # locations without inventing a value.
        # ----------------------------------------------------

        official_website = None

        data_section = content.get(
            "data",
            {}
        )

        if isinstance(data_section, dict):

            official_website = (
                data_section.get(
                    "officialWebsite"
                )
                or data_section.get(
                    "website"
                )
            )

        if not official_website:

            official_website = content.get(
                "officialWebsite"
            )

        if not official_website:

            official_website = content.get(
                "website"
            )

        if official_website:

            if is_valid_url(
                official_website
            ):
                websites_found += 1

        else:

            missing_websites += 1

    # --------------------------------------------------------
    # Duplicate calculations
    # --------------------------------------------------------

    duplicate_names = (
        total - len(set(names))
    )

    duplicate_urls = (
        len(urls) - len(set(urls))
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print(
        f"Total startups:             {total}"
    )

    print(
        f"Unique startup names:       {len(set(names))}"
    )

    print(
        f"Duplicate names:            {duplicate_names}"
    )

    print(
        f"Duplicate URLs:             {duplicate_urls}"
    )

    print(
        f"Missing names:              {missing_names}"
    )

    print(
        f"Invalid URLs:               {invalid_urls}"
    )

    print(
        f"Official websites found:    {websites_found}"
    )

    print(
        f"Missing official websites:  {missing_websites}"
    )

    print(
        f"Schema errors:              {schema_errors}"
    )

    # --------------------------------------------------------
    # PASS CONDITIONS
    # --------------------------------------------------------

    passed = (
        total >= STARTUP_TARGET
        and missing_names == 0
        and invalid_urls == 0
        and duplicate_names == 0
        and duplicate_urls == 0
        and schema_errors == 0
    )

    if passed:

        print_status("PASS")

    else:

        print_status("REVIEW")

    validation_results["startups"] = passed

    return passed


# ============================================================
# PRODUCT VALIDATION
# ============================================================

def validate_products():

    print("\n" + "=" * 70)
    print("PRODUCT VALIDATION")
    print("=" * 70)

    data = load_json(PRODUCTS_FILE)

    total = len(data)

    names = []
    urls = []

    missing_names = 0
    invalid_urls = 0

    invalid_pricing = 0

    matched = 0
    unresolved = 0

    missing_resolution = 0

    for record in data:

        content = record.get(
            "content",
            {}
        )

        # ----------------------------------------------------
        # Product name
        # ----------------------------------------------------

        product_name = content.get(
            "productName"
        )

        if not product_name:

            missing_names += 1

        else:

            names.append(
                normalize_name(
                    product_name
                )
            )

        # ----------------------------------------------------
        # Product website
        # ----------------------------------------------------

        website = content.get(
            "website"
        )

        if not website:

            invalid_urls += 1

        elif not is_valid_url(website):

            invalid_urls += 1

        else:

            urls.append(
                normalize_url(website)
            )

        # ----------------------------------------------------
        # Pricing model
        # ----------------------------------------------------

        pricing = content.get(
            "pricingModel"
        )

        if pricing not in VALID_PRICING_MODELS:

            invalid_pricing += 1

        # ----------------------------------------------------
        # Entity resolution
        # ----------------------------------------------------

        resolution = record.get(
            "entityResolution",
            {}
        )

        resolution_status = resolution.get(
            "status"
        )

        if resolution_status == "MATCHED":

            matched += 1

        elif resolution_status == "UNRESOLVED":

            unresolved += 1

        else:

            # Some records may represent resolution using
            # startupName rather than entityResolution.status.
            startup_name = content.get(
                "startupName"
            )

            if startup_name:

                matched += 1

            else:

                unresolved += 1
                missing_resolution += 1

    # --------------------------------------------------------
    # Duplicate calculations
    # --------------------------------------------------------

    duplicate_names = (
        total - len(set(names))
    )

    duplicate_urls = (
        len(urls) - len(set(urls))
    )

    resolution_rate = (
        matched / total * 100
        if total > 0
        else 0
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print(
        f"Total products:              {total}"
    )

    print(
        f"Unique product names:        {len(set(names))}"
    )

    print(
        f"Duplicate names:             {duplicate_names}"
    )

    print(
        f"Duplicate URLs:              {duplicate_urls}"
    )

    print(
        f"Missing product names:       {missing_names}"
    )

    print(
        f"Invalid URLs:                {invalid_urls}"
    )

    print(
        f"Invalid pricing models:      {invalid_pricing}"
    )

    print(
        f"Mapped to startups:          {matched}"
    )

    print(
        f"Unresolved products:         {unresolved}"
    )

    print(
        f"Resolution rate:             "
        f"{resolution_rate:.2f}%"
    )

    # --------------------------------------------------------
    # PASS CONDITIONS
    #
    # Duplicate product names are reported but do not
    # automatically fail the dataset because they can be
    # legitimate products with the same name.
    # --------------------------------------------------------

    passed = (
        total >= PRODUCT_TARGET
        and missing_names == 0
        and invalid_urls == 0
        and invalid_pricing == 0
    )

    if passed:

        print_status(
            "PASS COUNT / QUALITY"
        )

    else:

        print_status("REVIEW")

    validation_results["products"] = passed

    return passed


# ============================================================
# RESEARCH PAPER VALIDATION
# ============================================================

def validate_papers():

    print("\n" + "=" * 70)
    print("RESEARCH PAPER VALIDATION")
    print("=" * 70)

    data = load_json(PAPERS_FILE)

    total = len(data)

    titles = []

    missing_titles = 0
    missing_paper_urls = 0
    invalid_paper_urls = 0

    missing_github_urls = 0
    invalid_github_urls = 0

    missing_stars = 0

    for record in data:

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        title = record.get(
            "title"
        )

        if not title:

            missing_titles += 1

        else:

            titles.append(
                normalize_name(title)
            )

        # ----------------------------------------------------
        # Paper URL
        # ----------------------------------------------------

        paper_url = record.get(
            "paper_url"
        )

        if not paper_url:

            missing_paper_urls += 1

        elif not is_valid_url(
            paper_url
        ):

            invalid_paper_urls += 1

        # ----------------------------------------------------
        # GitHub URL
        # ----------------------------------------------------

        github_url = record.get(
            "github_url"
        )

        if not github_url:

            missing_github_urls += 1

        elif not is_valid_url(
            github_url
        ):

            invalid_github_urls += 1

        # ----------------------------------------------------
        # GitHub stars
        # ----------------------------------------------------

        stars = record.get(
            "github_stars"
        )

        if stars is None:

            missing_stars += 1

        elif not isinstance(
            stars,
            (int, float)
        ):

            missing_stars += 1

    duplicate_titles = (
        total - len(set(titles))
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print(
        f"Total papers:                {total}"
    )

    print(
        f"Unique titles:               {len(set(titles))}"
    )

    print(
        f"Duplicate titles:            {duplicate_titles}"
    )

    print(
        f"Missing titles:              {missing_titles}"
    )

    print(
        f"Missing paper URLs:          {missing_paper_urls}"
    )

    print(
        f"Invalid paper URLs:          {invalid_paper_urls}"
    )

    print(
        f"Missing GitHub URLs:         {missing_github_urls}"
    )

    print(
        f"Invalid GitHub URLs:         {invalid_github_urls}"
    )

    print(
        f"Missing GitHub stars:        {missing_stars}"
    )

    # --------------------------------------------------------
    # PASS
    # --------------------------------------------------------

    passed = (
        total >= PAPER_TARGET
        and missing_titles == 0
        and duplicate_titles == 0
        and missing_paper_urls == 0
        and invalid_paper_urls == 0
        and missing_github_urls == 0
        and invalid_github_urls == 0
        and missing_stars == 0
    )

    if passed:

        print_status("PASS")

    else:

        print_status("REVIEW")

    validation_results["papers"] = passed

    return passed


# ============================================================
# NEWS VALIDATION
# ============================================================

def validate_news():

    print("\n" + "=" * 70)
    print("NEWS VALIDATION")
    print("=" * 70)

    data = load_json(NEWS_FILE)

    total = len(data)

    fresh = 0
    stale = 0

    missing_dates = 0
    missing_titles = 0
    invalid_urls = 0
    duplicate_urls = 0

    urls = []

    now = datetime.now(
        timezone.utc
    )

    cutoff = (
        now
        - timedelta(
            hours=LOOKBACK_HOURS
        )
    )

    for record in data:

        content = record.get(
            "content",
            {}
        )

        title = content.get(
            "title"
        )

        url = content.get(
            "url"
        )

        published_at = content.get(
            "publishedAt"
        )

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        if not title:

            missing_titles += 1

        # ----------------------------------------------------
        # URL
        # ----------------------------------------------------

        if not url:

            invalid_urls += 1

        elif not is_valid_url(url):

            invalid_urls += 1

        else:

            urls.append(
                normalize_url(url)
            )

        # ----------------------------------------------------
        # Date
        # ----------------------------------------------------

        dt = parse_datetime(
            published_at
        )

        if not dt:

            missing_dates += 1

        elif dt >= cutoff:

            fresh += 1

        else:

            stale += 1

    duplicate_urls = (
        len(urls)
        - len(set(urls))
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print(
        f"Total news:                  {total}"
    )

    print(
        f"Fresh news (<24h):           {fresh}"
    )

    print(
        f"Stale news:                  {stale}"
    )

    print(
        f"Missing dates:               {missing_dates}"
    )

    print(
        f"Missing titles:              {missing_titles}"
    )

    print(
        f"Invalid URLs:                {invalid_urls}"
    )

    print(
        f"Duplicate URLs:              {duplicate_urls}"
    )

    # --------------------------------------------------------
    # News validation
    #
    # The validator checks quality of whatever was collected.
    # It does not fabricate a minimum news count.
    # --------------------------------------------------------

    passed = (
        total > 0
        and fresh == total
        and missing_dates == 0
        and missing_titles == 0
        and invalid_urls == 0
        and duplicate_urls == 0
    )

    if passed:

        print_status("PASS")

    else:

        print_status("REVIEW")

    validation_results["news"] = passed

    return passed


# ============================================================
# JOB VALIDATION
# ============================================================

def validate_jobs():

    print("\n" + "=" * 70)
    print("JOB VALIDATION")
    print("=" * 70)

    data = load_json(JOBS_FILE)

    total = len(data)

    fresh = 0
    stale = 0

    missing_dates = 0
    missing_companies = 0
    missing_roles = 0
    missing_remote = 0

    invalid_urls = 0
    duplicate_urls = 0

    urls = []

    now = datetime.now(
        timezone.utc
    )

    cutoff = (
        now
        - timedelta(
            hours=LOOKBACK_HOURS
        )
    )

    for record in data:

        content = record.get(
            "content",
            {}
        )

        date = content.get(
            "date"
        )

        company = content.get(
            "company"
        )

        role_family = content.get(
            "role_family"
        )

        is_remote = content.get(
            "is_remote"
        )

        url = content.get(
            "url"
        )

        # ----------------------------------------------------
        # Company
        # ----------------------------------------------------

        if not company:

            missing_companies += 1

        # ----------------------------------------------------
        # Role family
        # ----------------------------------------------------

        if not role_family:

            missing_roles += 1

        # ----------------------------------------------------
        # Remote
        # ----------------------------------------------------

        if is_remote is None:

            missing_remote += 1

        elif not isinstance(
            is_remote,
            bool
        ):

            missing_remote += 1

        # ----------------------------------------------------
        # URL
        # ----------------------------------------------------

        if not url:

            invalid_urls += 1

        elif not is_valid_url(url):

            invalid_urls += 1

        else:

            urls.append(
                normalize_url(url)
            )

        # ----------------------------------------------------
        # Date
        # ----------------------------------------------------

        dt = parse_datetime(
            date
        )

        if not dt:

            missing_dates += 1

        elif dt >= cutoff:

            fresh += 1

        else:

            stale += 1

    duplicate_urls = (
        len(urls)
        - len(set(urls))
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print(
        f"Total jobs:                  {total}"
    )

    print(
        f"Fresh jobs (<24h):           {fresh}"
    )

    print(
        f"Stale jobs:                  {stale}"
    )

    print(
        f"Missing dates:               {missing_dates}"
    )

    print(
        f"Missing companies:           {missing_companies}"
    )

    print(
        f"Missing role families:       {missing_roles}"
    )

    print(
        f"Missing remote flags:        {missing_remote}"
    )

    print(
        f"Invalid URLs:                {invalid_urls}"
    )

    print(
        f"Duplicate URLs:              {duplicate_urls}"
    )

    passed = (
        total > 0
        and fresh == total
        and missing_dates == 0
        and missing_companies == 0
        and missing_roles == 0
        and missing_remote == 0
        and invalid_urls == 0
        and duplicate_urls == 0
    )

    if passed:

        print_status("PASS")

    else:

        print_status("REVIEW")

    validation_results["jobs"] = passed

    return passed


# ============================================================
# ENTITY RESOLUTION VALIDATION
# ============================================================

def validate_entity_resolution():

    print("\n" + "=" * 70)
    print("ENTITY RESOLUTION VALIDATION")
    print("=" * 70)

    data = load_json(PRODUCTS_FILE)

    total = len(data)

    matched = 0
    unresolved = 0

    confidence_scores = []

    match_methods = {}

    for record in data:

        resolution = record.get(
            "entityResolution",
            {}
        )

        status = resolution.get(
            "status"
        )

        # ----------------------------------------------------
        # Matched
        # ----------------------------------------------------

        if status == "MATCHED":

            matched += 1

            score = resolution.get(
                "confidenceScore"
            )

            if isinstance(
                score,
                (int, float)
            ):

                confidence_scores.append(
                    score
                )

            method = resolution.get(
                "matchMethod",
                "unknown"
            )

            match_methods[method] = (
                match_methods.get(
                    method,
                    0
                ) + 1
            )

        # ----------------------------------------------------
        # Unresolved
        # ----------------------------------------------------

        else:

            unresolved += 1

    resolution_rate = (
        matched / total * 100
        if total > 0
        else 0
    )

    average_confidence = (
        sum(confidence_scores)
        / len(confidence_scores)
        if confidence_scores
        else 0
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print(
        f"Total products:              {total}"
    )

    print(
        f"Matched:                     {matched}"
    )

    print(
        f"Unresolved:                  {unresolved}"
    )

    print(
        f"Resolution rate:             "
        f"{resolution_rate:.2f}%"
    )

    print(
        f"Average confidence:          "
        f"{average_confidence:.2f}"
    )

    if match_methods:

        print(
            "\nMatch methods:"
        )

        for method, count in sorted(
            match_methods.items(),
            key=lambda x: x[1],
            reverse=True
        ):

            print(
                f"  {method}: {count}"
            )

    # --------------------------------------------------------
    # Entity resolution is considered valid if the resolver
    # has produced explicit matched/unresolved outcomes.
    #
    # We do NOT require 100% resolution because unresolved
    # records are intentionally safer than guessed matches.
    # --------------------------------------------------------

    passed = (
        total > 0
        and matched + unresolved == total
        and matched > 0
    )

    if passed:

        print_status("PASS")

    else:

        print_status("REVIEW")

    validation_results[
        "entity_resolution"
    ] = passed

    return passed


# ============================================================
# ENTITY MAPPING LOG VALIDATION
# ============================================================

def validate_mapping_log():

    print("\n" + "=" * 70)
    print("ENTITY MAPPING LOG")
    print("=" * 70)

    data = load_json(
        MAPPING_FILE
    )

    total = len(data)

    matched = 0
    unresolved = 0

    invalid_status = 0
    missing_product_names = 0

    confidence_scores = []

    for record in data:

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Actual mapping log uses:
        #
        # "matchStatus"
        #
        # NOT:
        #
        # "status"
        # ----------------------------------------------------

        status = record.get(
            "matchStatus"
        )

        if status == "MATCHED":

            matched += 1

        elif status == "UNRESOLVED":

            unresolved += 1

        else:

            invalid_status += 1

        # ----------------------------------------------------
        # Product name
        # ----------------------------------------------------

        if not record.get(
            "productName"
        ):

            missing_product_names += 1

        # ----------------------------------------------------
        # Confidence
        # ----------------------------------------------------

        score = record.get(
            "confidenceScore"
        )

        if isinstance(
            score,
            (int, float)
        ):

            confidence_scores.append(
                score
            )

    expected_total = (
        matched + unresolved
    )

    average_confidence = (
        sum(confidence_scores)
        / len(confidence_scores)
        if confidence_scores
        else 0
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print(
        f"Total mapping records:       {total}"
    )

    print(
        f"Matched mappings:            {matched}"
    )

    print(
        f"Unresolved mappings:         {unresolved}"
    )

    print(
        f"Invalid statuses:            {invalid_status}"
    )

    print(
        f"Missing product names:       "
        f"{missing_product_names}"
    )

    print(
        f"Matched + unresolved:        "
        f"{expected_total}"
    )

    print(
        f"Average confidence:          "
        f"{average_confidence:.2f}"
    )

    # --------------------------------------------------------
    # PASS
    # --------------------------------------------------------

    passed = (
        total > 0
        and expected_total == total
        and invalid_status == 0
        and missing_product_names == 0
    )

    if passed:

        print_status("PASS")

    else:

        print_status("REVIEW")

    validation_results[
        "mapping_log"
    ] = passed

    return passed


# ============================================================
# FINAL SUMMARY
# ============================================================

def print_final_summary():

    print("\n" + "=" * 70)
    print("FINAL VALIDATION SUMMARY")
    print("=" * 70)

    labels = {
        "startups": "Startups",
        "products": "Products",
        "papers": "Research Papers",
        "news": "News",
        "jobs": "Jobs",
        "entity_resolution": "Entity Resolution",
        "mapping_log": "Entity Mapping Log"
    }

    passed_count = 0

    total_checks = len(
        labels
    )

    for key, label in labels.items():

        status = validation_results.get(
            key,
            False
        )

        if status:

            print(
                f"  [PASS]   {label}"
            )

            passed_count += 1

        else:

            print(
                f"  [REVIEW] {label}"
            )

    print("\n" + "-" * 70)

    print(
        f"Checks passed: "
        f"{passed_count}/{total_checks}"
    )

    if passed_count == total_checks:

        print(
            "OVERALL STATUS: PASS"
        )

    else:

        print(
            "OVERALL STATUS: REVIEW"
        )

    print("-" * 70)

    print("\nAssignment minimum targets:")

    print(
        f"  Startups       >= {STARTUP_TARGET}"
    )

    print(
        f"  Products       >= {PRODUCT_TARGET}"
    )

    print(
        f"  Research       >= {PAPER_TARGET}"
    )

    print(
        "  News           = fresh within 24h"
    )

    print(
        "  Jobs           = fresh within 24h"
    )

    print(
        "  Entity Mapping = documented"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")

    print("=" * 70)

    print(
        "AI INTELLIGENCE PIPELINE"
    )

    print(
        "FINAL DATA VALIDATION"
    )

    print("=" * 70)

    print(
        f"\nValidation time: "
        f"{datetime.now(timezone.utc).isoformat()}"
    )

    # --------------------------------------------------------
    # Run all validation stages
    # --------------------------------------------------------

    validate_startups()

    validate_products()

    validate_papers()

    validate_news()

    validate_jobs()

    validate_entity_resolution()

    validate_mapping_log()

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print_final_summary()

    print(
        "\n" + "=" * 70
    )

    print(
        "VALIDATION COMPLETE"
    )

    print(
        "=" * 70
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
