import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import aiohttp
from bs4 import BeautifulSoup

from src.crawler.job_sources import JOB_SOURCES


# ============================================================
# CONFIGURATION
# ============================================================

OUT = Path("data/raw/jobs.json")
FAILED = Path("data/raw/jobs_failed.json")

LOOKBACK_HOURS = 24
CONCURRENCY = 10
REQUEST_TIMEOUT = 30

# Minimum amount of text required when we successfully
# crawl the individual job page.
MIN_FULL_TEXT_LENGTH = 150

# Minimum RSS description length to allow a safe fallback
# when the individual job page returns HTTP 403.
MIN_FEED_TEXT_LENGTH = 300


# ============================================================
# AI JOB DETECTION
# ============================================================

AI_TERMS = re.compile(
    r"\b("
    r"ai engineer|"
    r"artificial intelligence|"
    r"machine learning|"
    r"ml engineer|"
    r"machine learning engineer|"
    r"mlops|"
    r"machine learning operations|"
    r"llm|"
    r"large language model|"
    r"generative ai|"
    r"genai|"
    r"deep learning|"
    r"nlp|"
    r"natural language processing|"
    r"computer vision|"
    r"robotics|"
    r"agentic ai|"
    r"ai agent|"
    r"data scientist|"
    r"research scientist|"
    r"research engineer|"
    r"ai researcher|"
    r"machine learning scientist|"
    r"machine learning researcher|"
    r"prompt engineer"
    r")\b",
    re.I,
)


# ============================================================
# DATE PARSING
# ============================================================

def parse_date(value):
    """
    Convert RSS/Atom date strings into UTC datetime.
    """

    if not value:
        return None

    value = value.strip()

    # RSS / RFC date
    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        pass

    # ISO formats
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d",
    ]

    for fmt in formats:

        try:

            dt = datetime.strptime(value, fmt)

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc)

        except ValueError:
            continue

    return None


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(html):
    """
    Convert HTML into readable plain text.
    """

    if not html:
        return ""

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Remove non-content elements.
    for tag in soup(
        [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "noscript",
            "form",
            "iframe",
        ]
    ):
        tag.decompose()

    text = soup.get_text(
        " ",
        strip=True
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# XML HELPERS
# ============================================================

def lname(tag):
    """
    Remove XML namespace from a tag.
    """

    return tag.rsplit(
        "}",
        1
    )[-1].lower()


def child_text(item, names):
    """
    Extract text from an RSS/Atom child element.
    """

    for child in item:

        if lname(child.tag) not in names:
            continue

        # Normal XML text
        if child.text:

            return child.text.strip()

        # Sometimes content is nested inside the element.
        nested_text = "".join(
            child.itertext()
        ).strip()

        if nested_text:
            return nested_text

    return None


def child_link(item):
    """
    Extract RSS or Atom link.
    """

    for child in item:

        if lname(child.tag) != "link":
            continue

        # Atom:
        # <link href="https://example.com"/>
        href = child.attrib.get(
            "href"
        )

        if href:
            return href.strip()

        # RSS:
        # <link>https://example.com</link>
        if child.text:
            return child.text.strip()

    return None


# ============================================================
# URL CLEANING
# ============================================================

def clean_url(url):
    """
    Convert Markdown-wrapped URLs into normal URLs.

    Example:

    [https://example.com/job](https://example.com/job)

    becomes:

    https://example.com/job
    """

    if not url:
        return None

    url = url.strip()

    # Markdown:
    # [label](URL)
    match = re.search(
        r"\]\((https?://[^)]+)\)",
        url
    )

    if match:
        return match.group(1).strip()

    # [URL]
    match = re.match(
        r"^\[(https?://[^\]]+)\]$",
        url
    )

    if match:
        return match.group(1).strip()

    return url


# ============================================================
# FEED PARSER
# ============================================================

def parse_feed(
    xml_bytes,
    source_name,
    cutoff
):
    """
    Parse RSS/Atom feed.

    Returns fresh AI-related jobs.

    The RSS description is preserved because it can be used
    as a safe fallback if the individual job page blocks us.
    """

    root = ET.fromstring(
        xml_bytes
    )

    records = []

    for item in root.iter():

        if lname(item.tag) not in {
            "item",
            "entry"
        }:
            continue

        title = child_text(
            item,
            {"title"}
        )

        link = child_link(
            item
        )

        description = child_text(
            item,
            {
                "description",
                "summary",
                "content",
                "encoded",
            }
        ) or ""

        date_raw = child_text(
            item,
            {
                "pubdate",
                "published",
                "updated",
                "date",
                "created",
            }
        )

        dt = parse_date(
            date_raw
        )

        # ----------------------------------------------------
        # Required feed information
        # ----------------------------------------------------

        if not title:
            continue

        link = clean_url(
            link
        )

        if not link:
            continue

        if not dt:
            continue

        # ----------------------------------------------------
        # Freshness
        # ----------------------------------------------------

        if dt < cutoff:
            continue

        # ----------------------------------------------------
        # AI relevance
        # ----------------------------------------------------

        search_text = (
            f"{title} {description}"
        )

        if not AI_TERMS.search(
            search_text
        ):
            continue

        # Clean RSS description.
        feed_text = clean_text(
            description
        )

        records.append(
            {
                "source": source_name,
                "title": re.sub(
                    r"\s+",
                    " ",
                    title
                ).strip(),
                "url": link,
                "publishedAt": dt.isoformat(),
                "feedText": feed_text,
            }
        )

    return records


# ============================================================
# HTTP FETCH
# ============================================================

async def fetch(
    session,
    url
):
    """
    Fetch URL asynchronously.

    Returns:
        body, error
    """

    try:

        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(
                total=REQUEST_TIMEOUT
            ),
            allow_redirects=True,
        ) as response:

            if response.status != 200:

                return None, (
                    f"HTTP {response.status}"
                )

            body = await response.read()

            return body, None

    except asyncio.TimeoutError:

        return None, "timeout"

    except aiohttp.ClientError as e:

        return None, (
            f"client_error: {e}"
        )

    except Exception as e:

        return None, (
            f"error: {e}"
        )


# ============================================================
# COMPANY EXTRACTION
# ============================================================

def clean_company_name(company):
    """
    Clean an extracted company name.
    """

    if not company:
        return None

    company = company.strip()

    company = re.sub(
        r"\s+",
        " ",
        company
    )

    # Remove common source suffixes.
    company = re.sub(
        r"\s*[-|]\s*(Jobicy|RemoteFirstJobs|"
        r"We Work Remotely)\s*$",
        "",
        company,
        flags=re.I,
    )

    company = company.strip(
        " -|,."
    )

    if not company:
        return None

    # Reject obviously invalid values.
    invalid = {
        "jobicy",
        "remote first jobs",
        "remote-first-jobs",
        "we work remotely",
        "company",
        "employer",
        "unknown",
    }

    if company.lower() in invalid:
        return None

    return company


def extract_company(
    title,
    text=""
):
    """
    Extract company from title or job text.

    Supported examples:

        AI Engineer at OpenAI
        AI Engineer - OpenAI
        AI Engineer | OpenAI
        AI Engineer — OpenAI

    Also supports page text such as:

        Remote AI Engineer at Keyfactor, Inc. - Jobicy
        Company: OpenAI
        Employer: Anthropic
    """

    title = title or ""
    text = text or ""

    # ========================================================
    # TITLE PATTERNS
    # ========================================================

    title_patterns = [

        # Job title at Company
        r"\bat\s+(.+?)\s*$",

        # Job title at Company - Jobicy
        r"\bat\s+(.+?)\s+-\s+Jobicy\b",

        # Job title — Company
        r"\s+—\s+(.+?)\s*$",

        # Job title | Company
        r"\s+\|\s+(.+?)\s*$",

        # Job title - Company
        r"\s+-\s+(.+?)\s*$",
    ]

    for pattern in title_patterns:

        match = re.search(
            pattern,
            title,
            re.I
        )

        if not match:
            continue

        company = clean_company_name(
            match.group(1)
        )

        if not company:
            continue

        # Prevent extremely long matches.
        if len(company.split()) <= 12:

            return company

    # ========================================================
    # PAGE / FEED TEXT PATTERNS
    # ========================================================

    text_patterns = [

        # "at Keyfactor, Inc. - Jobicy"
        r"\bat\s+(.+?)\s+-\s+Jobicy\b",

        # "at Keyfactor, Inc."
        r"\bat\s+([A-Z][A-Za-z0-9&.,'() \-]{1,100}?)(?:\s+-\s+Jobicy|\s+Meet Jobicy|$)",

        # Company: OpenAI
        r"\bcompany\s*:\s*([A-Z][A-Za-z0-9&.,'() \-]{1,100})",

        # Employer: OpenAI
        r"\bemployer\s*:\s*([A-Z][A-Za-z0-9&.,'() \-]{1,100})",

        # "About COMPANY"
        r"\babout\s+([A-Z][A-Za-z0-9&.,'() \-]{1,80})",
    ]

    for pattern in text_patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if not match:
            continue

        company = clean_company_name(
            match.group(1)
        )

        if company:
            return company

    return None


# ============================================================
# REMOTE DETECTION
# ============================================================

def detect_remote(
    title,
    text
):
    """
    Determine whether a job is remote.
    """

    blob = (
        f"{title} {text}"
    )

    remote_patterns = [
        r"\bremote\b",
        r"\bwork from home\b",
        r"\bwork-from-home\b",
        r"\bfully remote\b",
        r"\bremote first\b",
        r"\bremote-first\b",
        r"\banywhere\b",
        r"\bdistributed team\b",
    ]

    return any(
        re.search(
            pattern,
            blob,
            re.I
        )
        for pattern in remote_patterns
    )


# ============================================================
# ROLE CLASSIFICATION
# ============================================================

def classify_role(
    title
):
    """
    Classify the job into a deterministic role family.
    """

    t = title.lower()

    # Research
    if any(
        keyword in t
        for keyword in [
            "research scientist",
            "research engineer",
            "ai researcher",
            "ml researcher",
            "machine learning researcher",
            "machine learning scientist",
            "researcher",
        ]
    ):
        return "RESEARCH"

    # AI/ML Engineering
    if any(
        keyword in t
        for keyword in [
            "machine learning engineer",
            "machine learning",
            "ml engineer",
            "ai engineer",
            "artificial intelligence engineer",
            "deep learning engineer",
        ]
    ):
        return "AI/ML ENGINEERING"

    # Data Science
    if any(
        keyword in t
        for keyword in [
            "data scientist",
            "data science",
        ]
    ):
        return "DATA SCIENCE"

    # NLP / LLM
    if any(
        keyword in t
        for keyword in [
            "llm",
            "large language model",
            "nlp",
            "natural language processing",
            "language model",
            "prompt engineer",
        ]
    ):
        return "NLP/LLM"

    # Computer Vision
    if any(
        keyword in t
        for keyword in [
            "computer vision",
            "vision engineer",
            "vision scientist",
        ]
    ):
        return "COMPUTER VISION"

    # MLOps
    if any(
        keyword in t
        for keyword in [
            "mlops",
            "ml ops",
            "machine learning operations",
        ]
    ):
        return "MLOPS"

    # AI Product
    if any(
        keyword in t
        for keyword in [
            "ai product manager",
            "ai product",
            "machine learning product",
            "product manager, ai",
        ]
    ):
        return "AI PRODUCT"

    return "AI/TECH"


# ============================================================
# INDIVIDUAL JOB PAGE
# ============================================================

async def fetch_job(
    session,
    record,
    sem
):

    async with sem:

        url = clean_url(
            record["url"]
        )

        title = record["title"]

        feed_text = (
            record.get("feedText")
            or ""
        )

        # ----------------------------------------------------
        # Try individual job page.
        # ----------------------------------------------------

        body, err = await fetch(
            session,
            url
        )

        # ====================================================
        # SAFE 403 FALLBACK
        # ====================================================

        if err == "HTTP 403":

            # We do NOT bypass the protection.
            #
            # Instead, we can only retain the job if the RSS
            # feed already provides enough useful description.
            if len(feed_text) >= MIN_FEED_TEXT_LENGTH:

                # Verify AI relevance using available RSS text.
                blob = (
                    f"{title} {feed_text}"
                )

                if not AI_TERMS.search(
                    blob
                ):

                    return None, {
                        **record,
                        "url": url,
                        "reason": "not_ai_job",
                    }

                company = extract_company(
                    title,
                    feed_text
                )

                if not company:

                    return None, {
                        **record,
                        "url": url,
                        "reason": "company_not_found_after_403",
                    }

                fallback_text = (
                    f"RSS feed description "
                    f"(job page returned HTTP 403). "
                    f"{feed_text}"
                )

                return {
                    **record,
                    "url": url,
                    "text": fallback_text,
                    "company": company,
                    "isRemote": detect_remote(
                        title,
                        fallback_text
                    ),
                    "roleFamily": classify_role(
                        title
                    ),
                    "fullTextSource": "RSS_FALLBACK",
                    "pageAccess": "HTTP_403",
                }, None

            # No sufficiently detailed RSS text.
            return None, {
                **record,
                "url": url,
                "reason": "HTTP 403 - insufficient RSS description for safe fallback",
            }

        # ====================================================
        # OTHER HTTP / NETWORK ERRORS
        # ====================================================

        if err:

            return None, {
                **record,
                "url": url,
                "reason": err,
            }

        # ====================================================
        # FULL PAGE TEXT
        # ====================================================

        text = clean_text(
            body.decode(
                "utf-8",
                errors="ignore"
            )
        )

        if len(text) < MIN_FULL_TEXT_LENGTH:

            return None, {
                **record,
                "url": url,
                "reason": "job_text_too_short",
            }

        # ====================================================
        # AI RELEVANCE
        # ====================================================

        blob = (
            f"{title} {text}"
        )

        if not AI_TERMS.search(
            blob
        ):

            return None, {
                **record,
                "url": url,
                "reason": "not_ai_job",
            }

        # ====================================================
        # COMPANY
        # ====================================================

        company = extract_company(
            title,
            text
        )

        if not company:

            # Try RSS text as a secondary source.
            company = extract_company(
                title,
                feed_text
            )

        if not company:

            return None, {
                **record,
                "url": url,
                "reason": "company_not_found",
            }

        # ====================================================
        # SUCCESSFUL FULL-TEXT RECORD
        # ====================================================

        return {
            **record,
            "url": url,
            "text": text,
            "company": company,
            "isRemote": detect_remote(
                title,
                text
            ),
            "roleFamily": classify_role(
                title
            ),
            "fullTextSource": "JOB_PAGE",
            "pageAccess": "HTTP_200",
        }, None


# ============================================================
# MAIN
# ============================================================

async def main():

    # ========================================================
    # CURRENT TIME
    # ========================================================

    now = datetime.now(
        timezone.utc
    )

    cutoff = (
        now
        - timedelta(
            hours=LOOKBACK_HOURS
        )
    )

    # ========================================================
    # HTTP CONFIGURATION
    # ========================================================

    headers = {
        "User-Agent": (
            "AI-Intelligence-Pipeline/1.0 "
            "(research-data-collector)"
        )
    }

    connector = aiohttp.TCPConnector(
        limit=CONCURRENCY,
        ssl=False
    )

    async with aiohttp.ClientSession(
        headers=headers,
        connector=connector
    ) as session:

        # ====================================================
        # STEP 1 — FETCH ALL RSS FEEDS
        # ====================================================

        feed_results = await asyncio.gather(
            *(
                fetch(
                    session,
                    source["url"]
                )
                for source in JOB_SOURCES
            )
        )

        candidates = []
        failed = []

        # ====================================================
        # STEP 2 — PARSE RSS FEEDS
        # ====================================================

        for source, (
            xml,
            err
        ) in zip(
            JOB_SOURCES,
            feed_results
        ):

            if err:

                failed.append(
                    {
                        "source": source["name"],
                        "url": source["url"],
                        "reason": err,
                    }
                )

                continue

            try:

                records = parse_feed(
                    xml,
                    source["name"],
                    cutoff
                )

                candidates.extend(
                    records
                )

            except ET.ParseError as e:

                failed.append(
                    {
                        "source": source["name"],
                        "url": source["url"],
                        "reason": (
                            f"feed_parse_error: {e}"
                        ),
                    }
                )

            except Exception as e:

                failed.append(
                    {
                        "source": source["name"],
                        "url": source["url"],
                        "reason": (
                            f"feed_error: {e}"
                        ),
                    }
                )

        # ====================================================
        # STEP 3 — DEDUPLICATE
        # ====================================================

        unique = {}

        for record in candidates:

            url = clean_url(
                record["url"]
            )

            if not url:
                continue

            record["url"] = url

            unique[url] = record

        print(
            f"\nFeed AI-job candidates: "
            f"{len(candidates)}"
        )

        print(
            f"Unique job URLs: "
            f"{len(unique)}"
        )

        # ====================================================
        # STEP 4 — CRAWL JOB PAGES
        # ====================================================

        sem = asyncio.Semaphore(
            CONCURRENCY
        )

        results = await asyncio.gather(
            *(
                fetch_job(
                    session,
                    record,
                    sem
                )
                for record in unique.values()
            )
        )

    # ========================================================
    # STEP 5 — SEPARATE SUCCESS / FAILURE
    # ========================================================

    jobs = [
        record
        for record, error in results
        if record
    ]

    failed.extend(
        error
        for record, error in results
        if error
    )

    # ========================================================
    # STEP 6 — FINAL DEDUPLICATION
    # ========================================================

    final_jobs = {}

    for job in jobs:

        url = clean_url(
            job["url"]
        )

        if url:
            final_jobs[url] = job

    jobs = list(
        final_jobs.values()
    )

    # ========================================================
    # STEP 7 — SORT NEWEST FIRST
    # ========================================================

    jobs.sort(
        key=lambda x: x["publishedAt"],
        reverse=True
    )

    # ========================================================
    # STEP 8 — BUILD FINAL SCHEMA
    # ========================================================

    payload = []

    for record in jobs:

        company = record.get(
            "company"
        )

        # Final safety fallback.
        if not company:

            company = extract_company(
                record["title"],
                record.get(
                    "text",
                    ""
                )
            )

        payload.append(
            {
                "schemaVersion": "1.0",

                "recordType": "JOB",

                "source": {
                    "name": record["source"],
                    "url": clean_url(
                        record["url"]
                    ),
                },

                "content": {
                    "title": record["title"],

                    "company": company,

                    "url": clean_url(
                        record["url"]
                    ),

                    "date": record[
                        "publishedAt"
                    ],

                    "is_remote": bool(
                        record["isRemote"]
                    ),

                    "role_family": record[
                        "roleFamily"
                    ],

                    "text": record[
                        "text"
                    ],
                },

                "collectedAt": now.isoformat(),
            }
        )

    # ========================================================
    # STEP 9 — SAVE JOB DATA
    # ========================================================

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # ========================================================
    # STEP 10 — SAVE FAILURES
    # ========================================================

    FAILED.write_text(
        json.dumps(
            failed,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # ========================================================
    # STEP 11 — STATISTICS
    # ========================================================

    full_page_jobs = sum(
        1
        for job in jobs
        if job.get(
            "fullTextSource"
        ) == "JOB_PAGE"
    )

    rss_fallback_jobs = sum(
        1
        for job in jobs
        if job.get(
            "fullTextSource"
        ) == "RSS_FALLBACK"
    )

    companies_found = sum(
        1
        for job in payload
        if job["content"]["company"]
    )

    # ========================================================
    # FINAL OUTPUT
    # ========================================================

    print(
        "\n" + "=" * 60
    )

    print(
        "JOB CRAWLER COMPLETE"
    )

    print(
        "=" * 60
    )

    print(
        f"Fresh AI jobs "
        f"(last {LOOKBACK_HOURS}h): "
        f"{len(payload)}"
    )

    print(
        f"Full job pages crawled: "
        f"{full_page_jobs}"
    )

    print(
        f"Safe RSS fallbacks: "
        f"{rss_fallback_jobs}"
    )

    print(
        f"Failed / rejected: "
        f"{len(failed)}"
    )

    print(
        f"Companies extracted: "
        f"{companies_found}"
    )

    print(
        f"Companies missing: "
        f"{len(payload) - companies_found}"
    )

    print(
        f"Output: {OUT}"
    )

    print(
        f"Failed output: {FAILED}"
    )

    print(
        "=" * 60
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())

