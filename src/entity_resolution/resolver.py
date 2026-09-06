import json
import os
import re
from urllib.parse import urlparse
from datetime import datetime, timezone


# ============================================================
# FILE PATHS
# ============================================================

STARTUPS_FILE = "data/processed/startups_enriched.json"
PRODUCTS_FILE = "data/raw/products_merged.json"

OUTPUT_FILE = "data/processed/products_resolved.json"
LOG_FILE = "data/processed/entity_mapping_log.json"


# ============================================================
# MATCHING CONFIGURATION
# ============================================================

# Minimum score required for an automatic match.
# Weak matches remain unresolved.
MATCH_THRESHOLD = 70

# Score components
EXACT_DOMAIN_SCORE = 100
REGISTERED_DOMAIN_SCORE = 90
COMPANY_NAME_SCORE = 85
DESCRIPTION_COMPANY_SCORE = 80
PRODUCT_NAME_SCORE = 75

# Domains that should never be treated as startup ownership.
IGNORED_DOMAINS = {
    "google.com",
    "youtube.com",
    "github.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "medium.com",
    "substack.com",
    "producthunt.com",
    "bestaihub.cc",
    "aifoxx.com",
}


# ============================================================
# FILE HELPERS
# ============================================================

def load_json(filename):
    """Load a JSON file."""

    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(filename, data):
    """
    Save JSON safely.

    Uses a temporary file and os.replace().
    Includes retries for Windows file-locking issues.
    """

    directory = os.path.dirname(filename)

    if directory:
        os.makedirs(directory, exist_ok=True)

    temporary_file = filename + ".tmp"

    try:

        with open(
            temporary_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        for attempt in range(5):

            try:

                os.replace(
                    temporary_file,
                    filename
                )

                return True

            except PermissionError:

                if attempt < 4:

                    import time
                    time.sleep(1)

        print(
            f"[WARNING] Could not replace {filename}"
        )

        return False

    except Exception as error:

        print(
            f"[WARNING] Save failed for {filename}: "
            f"{error}"
        )

        return False


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value):
    """
    Normalize text for comparison.

    Example:

        "Akon Labs, Inc."
        ->
        "akon labs"
    """

    if not value:
        return ""

    value = str(value).lower().strip()

    # Replace punctuation with spaces.
    value = re.sub(
        r"[^a-z0-9\s]",
        " ",
        value
    )

    # Common company suffixes.
    suffixes = [
        "incorporated",
        "corporation",
        "company",
        "limited",
        "private limited",
        "pvt ltd",
        "pvt",
        "llc",
        "ltd",
        "inc",
        "corp",
        "co",
        "technologies",
        "technology"
    ]

    for suffix in suffixes:

        value = re.sub(
            r"\b" + re.escape(suffix) + r"\b",
            " ",
            value
        )

    # Normalize whitespace.
    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_name_for_matching(value):
    """
    Stronger name normalization.

    Removes spaces so that:

        "Open AI"
        "OpenAI"

    can be compared as:

        "openai"
    """

    normalized = normalize_text(value)

    return normalized.replace(" ", "")


# ============================================================
# URL / DOMAIN HELPERS
# ============================================================

def normalize_domain(url):
    """Extract normalized domain from URL."""

    if not url:
        return ""

    try:

        url = str(url).strip()

        if not url.startswith(
            ("http://", "https://")
        ):
            url = "https://" + url

        parsed = urlparse(url)

        domain = parsed.netloc.lower()

        # Remove port.
        domain = domain.split(":")[0]

        # Remove www.
        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:
        return ""


def get_registered_domain(domain):
    """
    Approximate registered domain.

    Example:

        app.example.com
        ->
        example.com
    """

    if not domain:
        return ""

    parts = domain.split(".")

    if len(parts) >= 2:

        return ".".join(parts[-2:])

    return domain


def is_ignored_domain(domain):
    """Return True for generic platform domains."""

    if not domain:
        return True

    registered = get_registered_domain(domain)

    return (
        domain in IGNORED_DOMAINS
        or registered in IGNORED_DOMAINS
    )


def domains_match(
    product_domain,
    startup_domain
):
    """Check whether two domains represent the same organization."""

    if not product_domain or not startup_domain:
        return False

    if is_ignored_domain(product_domain):
        return False

    if is_ignored_domain(startup_domain):
        return False

    # Exact match.
    if product_domain == startup_domain:
        return True

    # Subdomain match.
    if (
        product_domain.endswith(
            "." + startup_domain
        )
        or startup_domain.endswith(
            "." + product_domain
        )
    ):
        return True

    # Registered domain match.
    product_registered = get_registered_domain(
        product_domain
    )

    startup_registered = get_registered_domain(
        startup_domain
    )

    if (
        product_registered
        and startup_registered
        and product_registered == startup_registered
    ):
        return True

    return False


# ============================================================
# PRODUCT FIELD EXTRACTION
# ============================================================

def extract_product_name(product):
    """Extract product name."""

    content = product.get(
        "content",
        {}
    )

    return (
        content.get("productName")
        or content.get("name")
        or product.get("productName")
        or product.get("name")
        or ""
    )


def extract_product_website(product):
    """Extract product website."""

    content = product.get(
        "content",
        {}
    )

    return (
        content.get("website")
        or content.get("url")
        or product.get("website")
        or product.get("url")
        or ""
    )


def extract_product_description(product):
    """Extract product description."""

    content = product.get(
        "content",
        {}
    )

    return (
        content.get("description")
        or product.get("description")
        or ""
    )


def extract_product_category(product):
    """Extract product category."""

    content = product.get(
        "content",
        {}
    )

    return (
        content.get("category")
        or product.get("category")
        or ""
    )


def extract_existing_company(product):
    """
    Extract company/vendor if the source already contains it.
    """

    content = product.get(
        "content",
        {}
    )

    return (
        content.get("startupName")
        or content.get("companyName")
        or content.get("vendor")
        or content.get("company")
        or product.get("startupName")
        or product.get("companyName")
        or product.get("vendor")
        or ""
    )


# ============================================================
# STARTUP FIELD EXTRACTION
# ============================================================

def extract_startup_name(startup):
    """Extract canonical startup name."""

    content = startup.get(
        "content",
        {}
    )

    return (
        content.get("entityName")
        or startup.get("entityName")
        or ""
    )


def extract_startup_website(startup):
    """Extract enriched official startup website."""

    content = startup.get(
        "content",
        {}
    )

    data = content.get(
        "data",
        {}
    )

    return (
        data.get("website")
        or content.get("website")
        or startup.get("website")
        or ""
    )


# ============================================================
# DESCRIPTION COMPANY EXTRACTION
# ============================================================

def clean_description(description):
    """Clean description text."""

    if not description:
        return ""

    description = str(description)

    # Remove URLs.
    description = re.sub(
        r"https?://\S+",
        " ",
        description
    )

    # Normalize whitespace.
    description = re.sub(
        r"\s+",
        " ",
        description
    )

    return description.strip()


def company_mentions_in_description(
    description,
    startup_name
):
    """
    Determine whether a startup name is explicitly
    mentioned in a product description.

    This is intentionally conservative.

    Examples of useful evidence:

        "Built by Acme AI"

        "Acme AI's platform..."

        "Acme AI provides..."

        "Developed by Acme AI..."

    """

    if not description or not startup_name:
        return False

    description = clean_description(
        description
    ).lower()

    startup_normalized = normalize_text(
        startup_name
    ).lower()

    startup_compact = (
        normalize_name_for_matching(
            startup_name
        )
    )

    if not startup_normalized:
        return False

    # Exact phrase.
    if startup_normalized in description:
        return True

    # Compact comparison for names such as:
    # OpenAI vs Open AI.
    words = re.findall(
        r"[a-z0-9]+",
        description
    )

    compact_description = "".join(
        words
    )

    if (
        startup_compact
        and len(startup_compact) >= 5
        and startup_compact in compact_description
    ):
        return True

    return False


# ============================================================
# NAME MATCHING
# ============================================================

def exact_name_match(
    product_name,
    startup_name
):
    """
    Strong exact name matching.

    This avoids weak substring matches.
    """

    if not product_name or not startup_name:
        return False

    product_normalized = normalize_name_for_matching(
        product_name
    )

    startup_normalized = normalize_name_for_matching(
        startup_name
    )

    if not product_normalized or not startup_normalized:
        return False

    return product_normalized == startup_normalized


def existing_company_match(
    company_name,
    startup_name
):
    """Check source-provided company name."""

    if not company_name or not startup_name:
        return False

    return exact_name_match(
        company_name,
        startup_name
    )


# ============================================================
# STARTUP INDEXES
# ============================================================

def build_indexes(startups):
    """
    Build efficient indexes.

    Returns:

        name_index
        domain_index
        registered_domain_index
    """

    name_index = {}
    domain_index = {}
    registered_domain_index = {}

    for startup in startups:

        startup_name = extract_startup_name(
            startup
        )

        startup_website = extract_startup_website(
            startup
        )

        normalized_name = normalize_name_for_matching(
            startup_name
        )

        domain = normalize_domain(
            startup_website
        )

        registered_domain = get_registered_domain(
            domain
        )

        # ---------------------------------------------
        # Name index
        # ---------------------------------------------

        if normalized_name:

            name_index.setdefault(
                normalized_name,
                []
            ).append(startup)

        # ---------------------------------------------
        # Domain index
        # ---------------------------------------------

        if domain and not is_ignored_domain(domain):

            domain_index.setdefault(
                domain,
                []
            ).append(startup)

        # ---------------------------------------------
        # Registered domain index
        # ---------------------------------------------

        if (
            registered_domain
            and not is_ignored_domain(
                registered_domain
            )
        ):

            registered_domain_index.setdefault(
                registered_domain,
                []
            ).append(startup)

    return (
        name_index,
        domain_index,
        registered_domain_index
    )


# ============================================================
# CANDIDATE SCORING
# ============================================================

def score_candidate(
    product,
    startup
):
    """
    Calculate evidence score for a product/startup pair.

    Maximum possible score is 100.

    Evidence:

        Exact domain             100
        Registered domain         90
        Existing company name     85
        Description mention       80
        Exact product/startup     75

    Additional evidence can increase confidence.

    Returns:

        score
        evidence
    """

    score = 0
    evidence = []

    product_name = extract_product_name(
        product
    )

    product_website = extract_product_website(
        product
    )

    product_description = extract_product_description(
        product
    )

    existing_company = extract_existing_company(
        product
    )

    startup_name = extract_startup_name(
        startup
    )

    startup_website = extract_startup_website(
        startup
    )

    product_domain = normalize_domain(
        product_website
    )

    startup_domain = normalize_domain(
        startup_website
    )

    # --------------------------------------------------------
    # Domain evidence
    # --------------------------------------------------------

    if (
        product_domain
        and startup_domain
        and not is_ignored_domain(
            product_domain
        )
        and not is_ignored_domain(
            startup_domain
        )
    ):

        if product_domain == startup_domain:

            score = max(
                score,
                EXACT_DOMAIN_SCORE
            )

            evidence.append(
                "Exact product/startup domain match"
            )

        elif domains_match(
            product_domain,
            startup_domain
        ):

            score = max(
                score,
                REGISTERED_DOMAIN_SCORE
            )

            evidence.append(
                "Product domain matches startup registered domain/subdomain"
            )

    # --------------------------------------------------------
    # Existing company name
    # --------------------------------------------------------

    if existing_company:

        if existing_company_match(
            existing_company,
            startup_name
        ):

            score = max(
                score,
                COMPANY_NAME_SCORE
            )

            evidence.append(
                "Source-provided company name matches startup"
            )

    # --------------------------------------------------------
    # Product name == startup name
    # --------------------------------------------------------

    if exact_name_match(
        product_name,
        startup_name
    ):

        score = max(
            score,
            PRODUCT_NAME_SCORE
        )

        evidence.append(
            "Product name exactly matches startup name"
        )

    # --------------------------------------------------------
    # Description evidence
    # --------------------------------------------------------

    if company_mentions_in_description(
        product_description,
        startup_name
    ):

        score = max(
            score,
            DESCRIPTION_COMPANY_SCORE
        )

        evidence.append(
            "Startup name explicitly mentioned in product description"
        )

    return score, evidence


# ============================================================
# RESOLUTION
# ============================================================

def resolve_product(
    product,
    startups,
    name_index,
    domain_index,
    registered_domain_index
):
    """
    Resolve one product.

    Resolution is based on multiple independent evidence
    sources.

    Returns:

        startup
        score
        method
        reason
    """

    product_name = extract_product_name(
        product
    )

    product_website = extract_product_website(
        product
    )

    product_description = extract_product_description(
        product
    )

    existing_company = extract_existing_company(
        product
    )

    product_domain = normalize_domain(
        product_website
    )

    product_registered_domain = (
        get_registered_domain(
            product_domain
        )
    )

    candidates = {}

    # ========================================================
    # Candidate generation — DOMAIN
    # ========================================================

    if (
        product_domain
        and not is_ignored_domain(
            product_domain
        )
    ):

        for startup in domain_index.get(
            product_domain,
            []
        ):

            key = id(startup)

            candidates[key] = startup

    # Registered domain candidates.
    if (
        product_registered_domain
        and not is_ignored_domain(
            product_registered_domain
        )
    ):

        for startup in registered_domain_index.get(
            product_registered_domain,
            []
        ):

            key = id(startup)

            candidates[key] = startup

    # ========================================================
    # Candidate generation — EXISTING COMPANY NAME
    # ========================================================

    if existing_company:

        normalized_company = (
            normalize_name_for_matching(
                existing_company
            )
        )

        for startup in name_index.get(
            normalized_company,
            []
        ):

            key = id(startup)

            candidates[key] = startup

    # ========================================================
    # Candidate generation — PRODUCT NAME
    # ========================================================

    if product_name:

        normalized_product = (
            normalize_name_for_matching(
                product_name
            )
        )

        for startup in name_index.get(
            normalized_product,
            []
        ):

            key = id(startup)

            candidates[key] = startup

    # ========================================================
    # Candidate generation — DESCRIPTION
    # ========================================================

    if product_description:

        for startup in startups:

            startup_name = extract_startup_name(
                startup
            )

            if company_mentions_in_description(
                product_description,
                startup_name
            ):

                key = id(startup)

                candidates[key] = startup

    # ========================================================
    # No candidates
    # ========================================================

    if not candidates:

        return (
            None,
            0,
            "unresolved",
            "No candidate startup found from available evidence"
        )

    # ========================================================
    # Score candidates
    # ========================================================

    scored_candidates = []

    for startup in candidates.values():

        score, evidence = score_candidate(
            product,
            startup
        )

        scored_candidates.append(
            (
                score,
                startup,
                evidence
            )
        )

    # Highest score first.
    scored_candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    best_score = scored_candidates[0][0]
    best_startup = scored_candidates[0][1]
    best_evidence = scored_candidates[0][2]

    # ========================================================
    # Check ambiguity
    # ========================================================

    if len(scored_candidates) > 1:

        second_score = scored_candidates[1][0]

        # If two startups have almost identical evidence,
        # don't guess.
        if (
            best_score < EXACT_DOMAIN_SCORE
            and second_score >= best_score - 5
        ):

            return (
                None,
                best_score,
                "ambiguous",
                (
                    "Multiple startups have similar evidence; "
                    "mapping intentionally left unresolved"
                )
            )

    # ========================================================
    # Threshold
    # ========================================================

    if best_score < MATCH_THRESHOLD:

        return (
            None,
            best_score,
            "low_confidence",
            (
                "Best candidate did not meet the "
                f"{MATCH_THRESHOLD}% confidence threshold"
            )
        )

    # ========================================================
    # Determine method
    # ========================================================

    product_domain = normalize_domain(
        product_website
    )

    startup_domain = normalize_domain(
        extract_startup_website(
            best_startup
        )
    )

    if (
        product_domain
        and startup_domain
        and product_domain == startup_domain
    ):

        method = "exact_domain"

    elif domains_match(
        product_domain,
        startup_domain
    ):

        method = "registered_domain"

    elif existing_company and existing_company_match(
        existing_company,
        extract_startup_name(
            best_startup
        )
    ):

        method = "company_name"

    elif company_mentions_in_description(
        product_description,
        extract_startup_name(
            best_startup
        )
    ):

        method = "description_company"

    elif exact_name_match(
        product_name,
        extract_startup_name(
            best_startup
        )
    ):

        method = "product_name"

    else:

        method = "multi_evidence"

    reason = "; ".join(
        best_evidence
    )

    return (
        best_startup,
        best_score,
        method,
        reason
    )


# ============================================================
# PRODUCT UPDATE
# ============================================================

def update_product(
    product,
    startup,
    score,
    method,
    reason
):
    """Add entity-resolution information to product."""

    if "content" not in product:

        product["content"] = {}

    if startup:

        startup_name = extract_startup_name(
            startup
        )

        startup_website = extract_startup_website(
            startup
        )

        product["content"][
            "startupName"
        ] = startup_name

        product["entityResolution"] = {

            "status": "MATCHED",

            "confidenceScore": score,

            "matchMethod": method,

            "matchReason": reason,

            "startupName": startup_name,

            "startupWebsite": startup_website,

            "startupSourceUrl": (
                startup.get(
                    "source",
                    {}
                ).get(
                    "url"
                )
            ),

            "resolvedAt": datetime.now(
                timezone.utc
            ).isoformat()
        }

    else:

        product["content"][
            "startupName"
        ] = None

        product["entityResolution"] = {

            "status": "UNRESOLVED",

            "confidenceScore": score,

            "matchMethod": method,

            "matchReason": reason,

            "startupName": None,

            "startupWebsite": None,

            "startupSourceUrl": None,

            "resolvedAt": datetime.now(
                timezone.utc
            ).isoformat()
        }

    return product


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("ENTITY RESOLUTION V2")
    print("=" * 70)

    # ========================================================
    # Check files
    # ========================================================

    if not os.path.exists(
        STARTUPS_FILE
    ):

        print()
        print(
            "[ERROR] Startup file not found:"
        )
        print(
            STARTUPS_FILE
        )
        return

    if not os.path.exists(
        PRODUCTS_FILE
    ):

        print()
        print(
            "[ERROR] Product file not found:"
        )
        print(
            PRODUCTS_FILE
        )
        return

    # ========================================================
    # Load datasets
    # ========================================================

    startups = load_json(
        STARTUPS_FILE
    )

    products = load_json(
        PRODUCTS_FILE
    )

    print()
    print(
        f"Startups loaded: {len(startups)}"
    )

    print(
        f"Products loaded: {len(products)}"
    )

    # ========================================================
    # Build indexes
    # ========================================================

    (
        name_index,
        domain_index,
        registered_domain_index
    ) = build_indexes(
        startups
    )

    print()
    print("STARTUP INDEX")
    print("-" * 70)

    print(
        f"Startup names indexed: "
        f"{len(name_index)}"
    )

    print(
        f"Official domains indexed: "
        f"{len(domain_index)}"
    )

    print(
        f"Registered domains indexed: "
        f"{len(registered_domain_index)}"
    )

    # ========================================================
    # Statistics
    # ========================================================

    matched = 0
    unresolved = 0

    exact_domain_matches = 0
    registered_domain_matches = 0
    company_name_matches = 0
    description_matches = 0
    product_name_matches = 0
    multi_evidence_matches = 0

    confidence_scores = []

    mapping_log = []
    resolved_products = []

    # ========================================================
    # Process products
    # ========================================================

    for index, product in enumerate(
        products,
        start=1
    ):

        (
            startup,
            score,
            method,
            reason
        ) = resolve_product(
            product,
            startups,
            name_index,
            domain_index,
            registered_domain_index
        )

        product = update_product(
            product,
            startup,
            score,
            method,
            reason
        )

        resolved_products.append(
            product
        )

        product_name = extract_product_name(
            product
        )

        product_website = extract_product_website(
            product
        )

        # ====================================================
        # Matched
        # ====================================================

        if startup:

            matched += 1

            confidence_scores.append(
                score
            )

            startup_name = extract_startup_name(
                startup
            )

            startup_website = extract_startup_website(
                startup
            )

            if method == "exact_domain":

                exact_domain_matches += 1

            elif method == "registered_domain":

                registered_domain_matches += 1

            elif method == "company_name":

                company_name_matches += 1

            elif method == "description_company":

                description_matches += 1

            elif method == "product_name":

                product_name_matches += 1

            elif method == "multi_evidence":

                multi_evidence_matches += 1

            mapping_log.append(
                {
                    "schemaVersion": "1.0",

                    "recordType": "ENTITY_MAPPING",

                    "productName": product_name,

                    "productWebsite": product_website,

                    "startupName": startup_name,

                    "startupWebsite": startup_website,

                    "matchStatus": "MATCHED",

                    "confidenceScore": score,

                    "matchMethod": method,

                    "matchReason": reason,

                    "startupSourceUrl": (
                        startup.get(
                            "source",
                            {}
                        ).get(
                            "url"
                        )
                    ),

                    "mappedAt": datetime.now(
                        timezone.utc
                    ).isoformat()
                }
            )

        # ====================================================
        # Unresolved
        # ====================================================

        else:

            unresolved += 1

            mapping_log.append(
                {
                    "schemaVersion": "1.0",

                    "recordType": "ENTITY_MAPPING",

                    "productName": product_name,

                    "productWebsite": product_website,

                    "startupName": None,

                    "startupWebsite": None,

                    "matchStatus": "UNRESOLVED",

                    "confidenceScore": score,

                    "matchMethod": method,

                    "matchReason": reason,

                    "startupSourceUrl": None,

                    "mappedAt": datetime.now(
                        timezone.utc
                    ).isoformat()
                }
            )

        # ====================================================
        # Progress
        # ====================================================

        if index % 100 == 0:

            print(
                f"Processed {index}/{len(products)} | "
                f"Matched: {matched} | "
                f"Unresolved: {unresolved}"
            )

    # ========================================================
    # Save results
    # ========================================================

    save_json(
        OUTPUT_FILE,
        resolved_products
    )

    save_json(
        LOG_FILE,
        mapping_log
    )

    # ========================================================
    # Final statistics
    # ========================================================

    total = len(products)

    if total:

        resolution_rate = (
            matched / total
        ) * 100

    else:

        resolution_rate = 0

    if confidence_scores:

        average_confidence = (
            sum(confidence_scores)
            / len(confidence_scores)
        )

    else:

        average_confidence = 0

    print()
    print("=" * 70)
    print("ENTITY RESOLUTION V2 COMPLETE")
    print("=" * 70)

    print()
    print(
        f"Startups:                 {len(startups)}"
    )

    print(
        f"Products:                 {total}"
    )

    print(
        f"Matched:                  {matched}"
    )

    print(
        f"Unresolved:               {unresolved}"
    )

    print(
        f"Resolution rate:          "
        f"{resolution_rate:.2f}%"
    )

    print(
        f"Average confidence:       "
        f"{average_confidence:.2f}"
    )

    print()
    print("MATCH BREAKDOWN")
    print("-" * 70)

    print(
        f"Exact domain:             "
        f"{exact_domain_matches}"
    )

    print(
        f"Registered domain:        "
        f"{registered_domain_matches}"
    )

    print(
        f"Company name:             "
        f"{company_name_matches}"
    )

    print(
        f"Description/company:      "
        f"{description_matches}"
    )

    print(
        f"Product name:             "
        f"{product_name_matches}"
    )

    print(
        f"Multi-evidence:            "
        f"{multi_evidence_matches}"
    )

    print()
    print("OUTPUT FILES")
    print("-" * 70)

    print(
        f"Resolved products:        "
        f"{OUTPUT_FILE}"
    )

    print(
        f"Entity mapping log:       "
        f"{LOG_FILE}"
    )

    print()
    print("=" * 70)

    if resolution_rate >= 20:

        print(
            "STATUS: GOOD"
        )

    elif resolution_rate >= 10:

        print(
            "STATUS: REVIEW"
        )

    else:

        print(
            "STATUS: LOW MATCH RATE"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()
