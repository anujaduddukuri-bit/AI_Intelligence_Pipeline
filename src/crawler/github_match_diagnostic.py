import json
import re
import requests
from pathlib import Path


PAPERS_FILE = Path(
    "data/raw/research_papers_arxiv.json"
)

PWC_API = (
    "https://datasets-server.huggingface.co/rows"
)

DATASET = (
    "pwc-archive/links-between-paper-and-code"
)

CONFIG = "default"
SPLIT = "train"

PAGE_SIZE = 100


def load_papers():
    with open(
        PAPERS_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def extract_arxiv_id(paper):
    url = str(
        paper.get("paper_url", "")
    )

    match = re.search(
        r"arxiv\.org/"
        r"(?:abs|pdf)/"
        r"([0-9]{4}\.[0-9]{4,5})"
        r"(?:v\d+)?",
        url,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None


def download_pwc_ids(max_rows=5000):
    """
    Download only enough Papers With Code rows
    for diagnostic comparison.
    """

    ids = set()

    offset = 0

    while offset < max_rows:

        params = {
            "dataset": DATASET,
            "config": CONFIG,
            "split": SPLIT,
            "offset": offset,
            "length": PAGE_SIZE,
        }

        print(
            f"Downloading rows "
            f"{offset + 1}-{offset + PAGE_SIZE}..."
        )

        try:

            response = requests.get(
                PWC_API,
                params=params,
                timeout=30
            )

            if response.status_code == 429:

                print()
                print(
                    "Hugging Face rate limit reached."
                )

                print(
                    "Stopping diagnostic download."
                )

                break

            response.raise_for_status()

            data = response.json()

        except Exception as error:

            print(
                f"Request failed: {error}"
            )

            break

        rows = data.get(
            "rows",
            []
        )

        if not rows:
            break

        for item in rows:

            row = item.get(
                "row",
                {}
            )

            arxiv_id = row.get(
                "paper_arxiv_id"
            )

            if arxiv_id:

                # Normalize version suffix.
                match = re.search(
                    r"([0-9]{4}\.[0-9]{4,5})",
                    str(arxiv_id)
                )

                if match:

                    ids.add(
                        match.group(1)
                    )

        offset += len(rows)

        if len(rows) < PAGE_SIZE:
            break

    return ids


def main():

    print("=" * 70)
    print("ARXIV ↔ PAPERS WITH CODE MATCH DIAGNOSTIC")
    print("=" * 70)

    papers = load_papers()

    print(
        f"Your research papers: "
        f"{len(papers)}"
    )

    # --------------------------------------------------
    # Extract user's arXiv IDs
    # --------------------------------------------------

    user_ids = set()

    missing_ids = []

    for paper in papers:

        arxiv_id = extract_arxiv_id(
            paper
        )

        if arxiv_id:

            user_ids.add(
                arxiv_id
            )

        else:

            missing_ids.append(
                paper.get(
                    "title",
                    "Unknown"
                )
            )

    print(
        f"Valid arXiv IDs extracted: "
        f"{len(user_ids)}"
    )

    print(
        f"Papers without arXiv ID: "
        f"{len(missing_ids)}"
    )

    print()
    print(
        "Downloading Papers With Code IDs..."
    )

    pwc_ids = download_pwc_ids(
        max_rows=5000
    )

    print()
    print(
        f"Papers With Code arXiv IDs downloaded: "
        f"{len(pwc_ids)}"
    )

    # --------------------------------------------------
    # Compare
    # --------------------------------------------------

    matches = user_ids.intersection(
        pwc_ids
    )

    only_user = user_ids - pwc_ids

    only_pwc = pwc_ids - user_ids

    print()
    print("=" * 70)
    print("MATCH RESULTS")
    print("=" * 70)

    print(
        f"Your arXiv IDs:              "
        f"{len(user_ids):,}"
    )

    print(
        f"Papers With Code IDs:        "
        f"{len(pwc_ids):,}"
    )

    print(
        f"Exact matching IDs:          "
        f"{len(matches):,}"
    )

    print(
        f"Your IDs without PWC match:  "
        f"{len(only_user):,}"
    )

    print(
        f"PWC IDs not in your dataset: "
        f"{len(only_pwc):,}"
    )

    # --------------------------------------------------
    # Percentage
    # --------------------------------------------------

    if user_ids:

        percentage = (
            len(matches)
            / len(user_ids)
            * 100
        )

        print()
        print(
            f"Match percentage: "
            f"{percentage:.2f}%"
        )

    # --------------------------------------------------
    # Show sample matches
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("SAMPLE MATCHES")
    print("=" * 70)

    for arxiv_id in list(matches)[:20]:

        print(
            arxiv_id
        )

    # --------------------------------------------------
    # Show sample non-matches
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("SAMPLE NON-MATCHES")
    print("=" * 70)

    for arxiv_id in list(only_user)[:20]:

        print(
            arxiv_id
        )

    print()
    print("=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()