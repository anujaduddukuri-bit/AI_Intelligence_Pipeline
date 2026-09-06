import os
import json
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import pandas as pd
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

OUTPUT_FILE = Path(
    "data/raw/research_papers_github.json"
)

MAPPING_FILE = Path(
    "data/raw/pwc_links_between_papers_and_code.parquet"
)

PWC_URL = (
    "https://huggingface.co/datasets/"
    "pwc-archive/links-between-paper-and-code/"
    "resolve/main/data/train-00000-of-00001.parquet"
)

TARGET_PAPERS = 1000

GITHUB_API = "https://api.github.com"

TIMEOUT = 30

# GitHub REST API is much more generous for normal
# authenticated requests than the Search API.
REQUEST_DELAY = 0.15


# ============================================================
# GITHUB HEADERS
# ============================================================

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = (
        f"Bearer {GITHUB_TOKEN}"
    )


# ============================================================
# DOWNLOAD PAPERS WITH CODE DATASET
# ============================================================

def download_mapping_dataset():

    if MAPPING_FILE.exists():

        print(
            "Papers With Code mapping dataset already exists."
        )

        return True

    print()
    print("=" * 60)
    print("DOWNLOADING PAPERS WITH CODE MAPPING DATASET")
    print("=" * 60)

    print()
    print(
        "Source:"
    )

    print(PWC_URL)

    try:

        response = requests.get(
            PWC_URL,
            timeout=120,
        )

        response.raise_for_status()

        MAPPING_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            MAPPING_FILE,
            "wb"
        ) as f:

            f.write(
                response.content
            )

        size_mb = (
            len(response.content)
            / 1024
            / 1024
        )

        print()
        print(
            f"Downloaded: {size_mb:.1f} MB"
        )

        print(
            f"Saved to: {MAPPING_FILE}"
        )

        return True

    except Exception as e:

        print()
        print(
            f"Dataset download failed: {e}"
        )

        return False


# ============================================================
# LOAD MAPPING DATASET
# ============================================================

def load_mapping_dataset():

    print()
    print(
        "Loading Papers With Code mappings..."
    )

    try:

        df = pd.read_parquet(
            MAPPING_FILE
        )

    except Exception as e:

        print(
            f"Could not read parquet file: {e}"
        )

        return None

    print(
        f"Total mapping rows: {len(df):,}"
    )

    return df


# ============================================================
# CLEAN GITHUB URL
# ============================================================

def clean_github_url(url):

    if not url:
        return None

    url = str(url).strip()

    if not url.startswith(
        "https://github.com/"
    ):
        return None

    parsed = urlparse(url)

    parts = [
        p
        for p in parsed.path.split("/")
        if p
    ]

    if len(parts) < 2:
        return None

    owner = parts[0]
    repo = parts[1]

    # Remove .git
    repo = repo.removesuffix(
        ".git"
    )

    return (
        f"https://github.com/"
        f"{owner}/{repo}"
    )


# ============================================================
# EXTRACT REPOSITORY NAME
# ============================================================

def get_repo_api_url(github_url):

    cleaned = clean_github_url(
        github_url
    )

    if not cleaned:
        return None

    parsed = urlparse(
        cleaned
    )

    parts = [
        p
        for p in parsed.path.split("/")
        if p
    ]

    if len(parts) < 2:
        return None

    owner = parts[0]
    repo = parts[1]

    return (
        f"{GITHUB_API}/repos/"
        f"{owner}/{repo}"
    )


# ============================================================
# GET GITHUB REPOSITORY
# ============================================================

def get_github_repository(
    github_url
):

    api_url = get_repo_api_url(
        github_url
    )

    if not api_url:
        return None, "invalid_url"

    try:

        response = requests.get(
            api_url,
            headers=HEADERS,
            timeout=TIMEOUT,
        )

    except requests.RequestException as e:

        print(
            f"Request error: {e}"
        )

        return None, "request_error"

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    if response.status_code == 200:

        return response.json(), "success"

    # --------------------------------------------------------
    # RATE LIMIT
    # --------------------------------------------------------

    if response.status_code in (
        403,
        429,
    ):

        remaining = response.headers.get(
            "X-RateLimit-Remaining",
            "unknown"
        )

        reset = response.headers.get(
            "X-RateLimit-Reset",
            "unknown"
        )

        print()
        print(
            "GitHub API rate limit reached."
        )

        print(
            f"Remaining: {remaining}"
        )

        print(
            f"Reset: {reset}"
        )

        return None, "rate_limit"

    # --------------------------------------------------------
    # REPOSITORY NOT FOUND
    # --------------------------------------------------------

    if response.status_code == 404:

        return None, "not_found"

    # --------------------------------------------------------
    # OTHER ERROR
    # --------------------------------------------------------

    print(
        f"GitHub API error: "
        f"{response.status_code}"
    )

    return None, "api_error"


# ============================================================
# CHECK GITHUB CORE RATE LIMIT
# ============================================================

def check_rate_limit():

    try:

        response = requests.get(
            f"{GITHUB_API}/rate_limit",
            headers=HEADERS,
            timeout=TIMEOUT,
        )

        if response.status_code != 200:
            return None

        data = response.json()

        return data.get(
            "resources",
            {}
        ).get(
            "core"
        )

    except Exception:
        return None


# ============================================================
# BUILD CANDIDATE PAPER DATASET
# ============================================================

def build_candidates(df):

    print()
    print("=" * 60)
    print("BUILDING PAPER → GITHUB CANDIDATES")
    print("=" * 60)

    required_columns = {
        "paper_title",
        "paper_arxiv_id",
        "repo_url",
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    if missing:

        print(
            f"Missing columns: {missing}"
        )

        return pd.DataFrame()

    # --------------------------------------------------------
    # Keep only rows with arXiv IDs
    # --------------------------------------------------------

    df = df[
        df["paper_arxiv_id"]
        .notna()
    ].copy()

    print(
        f"Rows with arXiv ID: {len(df):,}"
    )

    # --------------------------------------------------------
    # Keep GitHub repositories
    # --------------------------------------------------------

    df["github_url_clean"] = (
        df["repo_url"]
        .apply(clean_github_url)
    )

    df = df[
        df["github_url_clean"]
        .notna()
    ].copy()

    print(
        f"Rows with GitHub URL: {len(df):,}"
    )

    # --------------------------------------------------------
    # Prefer official implementations
    # --------------------------------------------------------

    if "is_official" in df.columns:

        df["official_score"] = (
            df["is_official"]
            .fillna(False)
            .astype(bool)
            .astype(int)
        )

    else:

        df["official_score"] = 0

    # --------------------------------------------------------
    # Prefer papers where code is explicitly connected
    # --------------------------------------------------------

    if "mentioned_in_paper" in df.columns:

        df["paper_mention_score"] = (
            df["mentioned_in_paper"]
            .fillna(False)
            .astype(bool)
            .astype(int)
        )

    else:

        df["paper_mention_score"] = 0

    if "mentioned_in_github" in df.columns:

        df["github_mention_score"] = (
            df["mentioned_in_github"]
            .fillna(False)
            .astype(bool)
            .astype(int)
        )

    else:

        df["github_mention_score"] = 0

    # --------------------------------------------------------
    # Ranking
    # --------------------------------------------------------

    df["verification_score"] = (
        df["official_score"] * 3
        + df["paper_mention_score"] * 2
        + df["github_mention_score"]
    )

    df = df.sort_values(
        [
            "verification_score",
            "official_score",
        ],
        ascending=False
    )

    # --------------------------------------------------------
    # One repository per paper
    # --------------------------------------------------------

    df = df.drop_duplicates(
        subset=[
            "paper_arxiv_id"
        ],
        keep="first"
    )

    print(
        f"Unique papers with GitHub code: "
        f"{len(df):,}"
    )

    # --------------------------------------------------------
    # One paper per repository where possible
    # --------------------------------------------------------

    df = df.drop_duplicates(
        subset=[
            "github_url_clean"
        ],
        keep="first"
    )

    print(
        f"Unique paper/repository pairs: "
        f"{len(df):,}"
    )

    return df


# ============================================================
# CREATE FINAL RECORD
# ============================================================

def create_record(
    row,
    github_data
):

    arxiv_id = str(
        row["paper_arxiv_id"]
    ).strip()

    title = str(
        row["paper_title"]
    ).strip()

    github_url = clean_github_url(
        row["repo_url"]
    )

    # PWC provides paper URL fields.
    paper_url = row.get(
        "paper_url_abs"
    )

    if not paper_url:
        paper_url = (
            f"https://arxiv.org/abs/"
            f"{arxiv_id}"
        )

    # --------------------------------------------------------
    # GitHub information
    # --------------------------------------------------------

    stars = github_data.get(
        "stargazers_count",
        0
    )

    forks = github_data.get(
        "forks_count",
        0
    )

    watchers = github_data.get(
        "watchers_count",
        0
    )

    default_branch = github_data.get(
        "default_branch"
    )

    created_at = github_data.get(
        "created_at"
    )

    updated_at = github_data.get(
        "updated_at"
    )

    # --------------------------------------------------------
    # Final assignment schema
    # --------------------------------------------------------

    return {
        "schemaVersion": "1.0",
        "recordType": "RESEARCH_PAPER",

        "title": title,

        "authors": [],

        "paper_url": paper_url,

        "github_url": github_url,

        "github_stars": int(stars),

        "published_date": None,

        # Additional useful engineering fields
        "arxiv_id": arxiv_id,

        "github_forks": int(forks),

        "github_watchers": int(
            watchers
        ),

        "github_default_branch":
            default_branch,

        "github_created_at":
            created_at,

        "github_updated_at":
            updated_at,

        "github_match_verified": True,

        "source": {
            "name":
                "Papers With Code Archive",
            "url":
                PWC_URL,
        },
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print(
        "RESEARCH PAPER + GITHUB METRICS PIPELINE"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # TOKEN CHECK
    # --------------------------------------------------------

    if not GITHUB_TOKEN:

        print()
        print(
            "ERROR: GITHUB_TOKEN not found."
        )

        print(
            "Check your .env file."
        )

        return

    print()
    print(
        "GitHub token: FOUND"
    )

    # --------------------------------------------------------
    # RATE LIMIT
    # --------------------------------------------------------

    rate = check_rate_limit()

    if rate:

        print()
        print(
            "GitHub Core API:"
        )

        print(
            f"Limit:     {rate.get('limit')}"
        )

        print(
            f"Used:      {rate.get('used')}"
        )

        print(
            f"Remaining: {rate.get('remaining')}"
        )

        if rate.get(
            "remaining",
            0
        ) < 100:

            print()
            print(
                "WARNING: Less than 100 "
                "GitHub API requests remain."
            )

            print(
                "Stopping for safety."
            )

            return

    # --------------------------------------------------------
    # DOWNLOAD DATASET
    # --------------------------------------------------------

    if not download_mapping_dataset():
        return

    # --------------------------------------------------------
    # LOAD DATASET
    # --------------------------------------------------------

    df = load_mapping_dataset()

    if df is None:
        return

    # --------------------------------------------------------
    # BUILD CANDIDATES
    # --------------------------------------------------------

    candidates = build_candidates(
        df
    )

    if candidates.empty:

        print(
            "No suitable candidates found."
        )

        return

    # --------------------------------------------------------
    # LIMIT
    # --------------------------------------------------------

    candidates = candidates.head(
        TARGET_PAPERS
    ).copy()

    print()
    print(
        f"Target papers: {TARGET_PAPERS}"
    )

    print(
        f"Candidates selected: "
        f"{len(candidates)}"
    )

    # --------------------------------------------------------
    # PROCESS
    # --------------------------------------------------------

    results = []

    failed = []

    print()
    print("=" * 60)
    print("VERIFYING GITHUB REPOSITORIES")
    print("=" * 60)

    for index, (
        row_index,
        row
    ) in enumerate(
        candidates.iterrows(),
        start=1
    ):

        title = str(
            row["paper_title"]
        ).strip()

        arxiv_id = str(
            row["paper_arxiv_id"]
        ).strip()

        github_url = clean_github_url(
            row["repo_url"]
        )

        print()
        print(
            f"[{index}/{len(candidates)}]"
        )

        print(
            f"Paper: {title}"
        )

        print(
            f"arXiv: {arxiv_id}"
        )

        print(
            f"GitHub: {github_url}"
        )

        github_data, status = (
            get_github_repository(
                github_url
            )
        )

        # ----------------------------------------------------
        # RATE LIMIT
        # ----------------------------------------------------

        if status == "rate_limit":

            print()
            print(
                "Stopping immediately because "
                "GitHub API rate limit was reached."
            )

            break

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        if status == "success":

            record = create_record(
                row,
                github_data
            )

            results.append(
                record
            )

            print(
                f"Verified ✓"
            )

            print(
                f"Stars: "
                f"{record['github_stars']}"
            )

        else:

            print(
                f"Could not verify "
                f"repository: {status}"
            )

            failed.append(
                {
                    "arxiv_id":
                        arxiv_id,

                    "title":
                        title,

                    "paper_url":
                        row.get(
                            "paper_url_abs"
                        ),

                    "github_url":
                        github_url,

                    "reason":
                        status,
                }
            )

        # ----------------------------------------------------
        # SAVE PROGRESS
        # ----------------------------------------------------

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                results,
                f,
                indent=2,
                ensure_ascii=False
            )

        # ----------------------------------------------------
        # DELAY
        # ----------------------------------------------------

        time.sleep(
            REQUEST_DELAY
        )

    # --------------------------------------------------------
    # SAVE FAILED RECORDS
    # --------------------------------------------------------

    failed_file = Path(
        "data/raw/"
        "research_papers_github_failed.json"
    )

    with open(
        failed_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            failed,
            f,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # FINAL RATE
    # --------------------------------------------------------

    final_rate = check_rate_limit()

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print(
        "RESEARCH PAPER PIPELINE COMPLETE"
    )
    print("=" * 60)

    print()
    print(
        f"Verified papers: {len(results)}"
    )

    print(
        f"Failed/unavailable: {len(failed)}"
    )

    print(
        f"Target: {TARGET_PAPERS}"
    )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )

    print(
        f"Failed: {failed_file}"
    )

    if final_rate:

        print()
        print(
            "GitHub Core API remaining:"
        )

        print(
            final_rate.get(
                "remaining"
            )
        )


if __name__ == "__main__":
    main()