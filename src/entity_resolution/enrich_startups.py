import json
import os
import time
import requests

from bs4 import BeautifulSoup
from urllib.parse import urlparse


INPUT_FILE = "data/processed/startups.json"
OUTPUT_FILE = "data/processed/startups_enriched.json"


# Domains that are NOT startup websites
IGNORED_DOMAINS = {
    "ycombinator.com",
    "startupschool.org",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "github.com",
    "tiktok.com",
    "medium.com",
    "substack.com",
}


def load_json(filename):

    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(filename, data):

    os.makedirs(
        os.path.dirname(filename),
        exist_ok=True
    )

    temporary_file = filename + ".tmp"

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

            return

        except PermissionError:

            time.sleep(1)

    raise PermissionError(
        f"Could not save {filename}. "
        "Close the file if it is open in VS Code."
    )


def get_domain(url):

    try:

        parsed = urlparse(url)

        domain = parsed.netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:

        return ""


def is_valid_external_domain(url):

    domain = get_domain(url)

    if not domain:
        return False

    for ignored in IGNORED_DOMAINS:

        if (
            domain == ignored
            or domain.endswith("." + ignored)
        ):
            return False

    return True


def extract_website(soup):

    """
    Extract the actual startup website.

    YC pages contain many external links, including:
        - Startup School
        - social media
        - YC resources
        - company website

    We therefore prioritize links whose text explicitly
    indicates that they are the company website.
    """

    candidates = []

    # --------------------------------------------------------
    # PASS 1
    # Look for links whose visible text indicates website
    # --------------------------------------------------------

    priority_words = [
        "website",
        "visit website",
        "company website",
        "visit site",
        "company site",
        "web site",
    ]

    for link in soup.find_all("a", href=True):

        href = link.get("href", "").strip()

        text = link.get_text(
            " ",
            strip=True
        ).lower()

        if not href:
            continue

        if not (
            href.startswith("https://")
            or href.startswith("http://")
        ):
            continue

        if not is_valid_external_domain(href):
            continue

        score = 0

        for word in priority_words:

            if word in text:
                score += 10

        if score > 0:

            candidates.append(
                (score, href)
            )

    if candidates:

        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )

        return candidates[0][1]


    # --------------------------------------------------------
    # PASS 2
    # Look for external links near company information
    # --------------------------------------------------------

    for link in soup.find_all("a", href=True):

        href = link.get("href", "").strip()

        if not href:
            continue

        if not (
            href.startswith("https://")
            or href.startswith("http://")
        ):
            continue

        if not is_valid_external_domain(href):
            continue

        text = link.get_text(
            " ",
            strip=True
        ).lower()

        # Avoid obvious unrelated links
        if any(
            word in text
            for word in [
                "apply",
                "jobs",
                "job",
                "founder",
                "yc",
                "y combinator",
                "startup school",
                "privacy",
                "terms",
            ]
        ):
            continue

        return href


    return None


def enrich_startup(startup):

    source = startup.get(
        "source",
        {}
    )

    yc_url = source.get("url")

    if not yc_url:

        return startup, False


    try:

        response = requests.get(
            yc_url,
            timeout=20,
            headers={
                "User-Agent":
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/139.0 Safari/537.36"
            }
        )

        if response.status_code != 200:

            print(
                f"[FAILED] "
                f"{yc_url} "
                f"HTTP {response.status_code}"
            )

            return startup, False


        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        website = extract_website(
            soup
        )


        company_name = (
            startup
            .get("content", {})
            .get("entityName", "Unknown")
        )


        if website:

            content = startup.setdefault(
                "content",
                {}
            )

            data = content.setdefault(
                "data",
                {}
            )

            data["website"] = website

            print(
                f"[FOUND] "
                f"{company_name} "
                f"-> {website}"
            )

            return startup, True


        else:

            print(
                f"[NO WEBSITE] "
                f"{company_name}"
            )

            return startup, False


    except requests.exceptions.Timeout:

        print(
            f"[TIMEOUT] {yc_url}"
        )

        return startup, False


    except requests.exceptions.ConnectionError:

        print(
            f"[CONNECTION ERROR] {yc_url}"
        )

        return startup, False


    except requests.exceptions.RequestException as error:

        print(
            f"[REQUEST ERROR] "
            f"{yc_url} -> {error}"
        )

        return startup, False


    except Exception as error:

        print(
            f"[ERROR] "
            f"{yc_url} -> {error}"
        )

        return startup, False


def main():

    print("=" * 70)
    print("STARTUP WEBSITE ENRICHMENT")
    print("=" * 70)

    startups = load_json(
        INPUT_FILE
    )

    print(
        f"Startups loaded: {len(startups)}"
    )

    print()

    enriched = []

    websites_found = 0

    failed_requests = 0

    # --------------------------------------------------------
    # Process startups
    # --------------------------------------------------------

    for index, startup in enumerate(
        startups,
        start=1
    ):

        result, found = enrich_startup(
            startup
        )

        enriched.append(result)

        if found:

            websites_found += 1

        # ----------------------------------------------------
        # Checkpoint every 50 records
        # ----------------------------------------------------

        if index % 50 == 0:

            save_json(
                OUTPUT_FILE,
                enriched
            )

            print()
            print(
                f"Progress: "
                f"{index}/{len(startups)}"
            )

            print(
                f"Websites found: "
                f"{websites_found}"
            )

            print(
                f"Websites missing: "
                f"{index - websites_found}"
            )

            print(
                "Checkpoint saved."
            )

            print()

        # Small delay to avoid hammering YC
        time.sleep(0.2)


    # --------------------------------------------------------
    # Final save
    # --------------------------------------------------------

    save_json(
        OUTPUT_FILE,
        enriched
    )


    # --------------------------------------------------------
    # Final statistics
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("STARTUP ENRICHMENT COMPLETE")
    print("=" * 70)

    print(
        f"Total startups:       {len(startups)}"
    )

    print(
        f"Official websites:    {websites_found}"
    )

    print(
        f"Without website:      "
        f"{len(startups) - websites_found}"
    )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()