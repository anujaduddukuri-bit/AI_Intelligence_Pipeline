import json
import time
import ssl
import certifi
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


OUTPUT_FILE = Path("data/raw/research_papers_arxiv.json")

ARXIV_API = "https://export.arxiv.org/api/query"

TARGET_PAPERS = 1500
BATCH_SIZE = 100

# AI-related arXiv categories
SEARCH_QUERY = (
    "cat:cs.AI OR "
    "cat:cs.LG OR "
    "cat:cs.CL OR "
    "cat:cs.CV OR "
    "cat:cs.NE OR "
    "cat:stat.ML"
)


def fetch_arxiv(start, max_results):

    params = {
        "search_query": SEARCH_QUERY,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    url = ARXIV_API + "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "AI-Intelligence-Pipeline/1.0 "
                "(research-paper-collector)"
            )
        },
    )

    # Use certifi's trusted CA certificate bundle.
    ssl_context = ssl.create_default_context(
        cafile=certifi.where()
    )

    with urllib.request.urlopen(
        request,
        timeout=60,
        context=ssl_context
    ) as response:

        return response.read()


def parse_arxiv(xml_data):

    root = ET.fromstring(xml_data)

    namespace = {
        "atom": "http://www.w3.org/2005/Atom"
    }

    papers = []

    for entry in root.findall(
        "atom:entry",
        namespace
    ):

        title = entry.findtext(
            "atom:title",
            default="",
            namespaces=namespace
        )

        title = " ".join(title.split())

        summary = entry.findtext(
            "atom:summary",
            default="",
            namespaces=namespace
        )

        summary = " ".join(summary.split())

        published = entry.findtext(
            "atom:published",
            default=None,
            namespaces=namespace
        )

        paper_id = entry.findtext(
            "atom:id",
            default=None,
            namespaces=namespace
        )

        authors = []

        for author in entry.findall(
            "atom:author",
            namespace
        ):

            name = author.findtext(
                "atom:name",
                default="",
                namespaces=namespace
            )

            if name:
                authors.append(name.strip())

        categories = []

        for category in entry.findall(
            "atom:category",
            namespace
        ):

            term = category.attrib.get("term")

            if term:
                categories.append(term)

        if not paper_id or not title:
            continue

        arxiv_id = paper_id.split("/")[-1]

        paper_url = (
            f"https://arxiv.org/abs/{arxiv_id}"
        )

        papers.append(
            {
                "title": title,
                "authors": authors,
                "paper_url": paper_url,
                "arxiv_id": arxiv_id,
                "abstract": summary,
                "published_date": published,
                "categories": categories,
                "github_url": None,
                "github_stars": None,
            }
        )

    return papers


def main():

    print("=" * 60)
    print("RESEARCH PAPER COLLECTOR")
    print("=" * 60)

    print(f"Target papers: {TARGET_PAPERS}")
    print(f"Batch size: {BATCH_SIZE}")

    papers = []
    seen_ids = set()

    start = 0

    while len(papers) < TARGET_PAPERS:

        remaining = TARGET_PAPERS - len(papers)

        batch_size = min(
            BATCH_SIZE,
            remaining
        )

        print()
        print(
            f"Fetching papers "
            f"{start + 1}-{start + batch_size}"
        )

        try:

            xml_data = fetch_arxiv(
                start,
                batch_size
            )

            batch = parse_arxiv(xml_data)

        except Exception as e:

            print("ERROR:", e)
            print("Waiting before retry...")

            time.sleep(10)
            continue

        if not batch:

            print("No more papers returned.")
            break

        added = 0

        for paper in batch:

            arxiv_id = paper["arxiv_id"]

            if arxiv_id in seen_ids:
                continue

            seen_ids.add(arxiv_id)

            papers.append(paper)

            added += 1

        print(
            f"Received: {len(batch)} | "
            f"Added: {added} | "
            f"Total: {len(papers)}"
        )

        start += batch_size

        # Respect arXiv API request spacing.
        time.sleep(3)

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
            papers,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 60)
    print("RESEARCH PAPER COLLECTION COMPLETE")
    print("=" * 60)

    print(f"Total papers: {len(papers)}")
    print(f"Output: {OUTPUT_FILE}")

    print()
    print("First 5 papers:")

    for paper in papers[:5]:

        print(
            f"- {paper['title']}"
        )

        print(
            f"  {paper['paper_url']}"
        )


if __name__ == "__main__":
    main()