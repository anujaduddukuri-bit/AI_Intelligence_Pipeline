import asyncio
import aiohttp
import json
import os
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup


LOOKBACK_HOURS = 24
CONCURRENCY = 10
MIN_ARTICLE_TEXT = 200

OUTPUT_FILE = "data/raw/news.json"
FAILED_FILE = "data/raw/news_failed.json"


NEWS_SOURCES = [
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
    },
    {
        "name": "MIT Technology Review AI",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",
    },
]


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/139.0 Safari/537.36"
    )
}


def parse_date(value):
    """Convert RSS date formats into timezone-aware datetime."""

    if not value:
        return None

    value = value.strip()

    # RFC 2822 / RSS date
    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        pass

    # ISO 8601
    try:
        value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def clean_url(url):
    """Remove tracking parameters from article URLs."""

    if not url:
        return None

    url = url.strip()

    # Remove common tracking parameters.
    url = re.split(r"[?#]", url)[0]

    return url.rstrip("/")


def clean_text(html):
    """Extract readable article text."""

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup([
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "aside",
        "noscript",
        "form",
        "iframe",
        "svg",
    ]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_rss_items(xml_text):
    """Extract article information from RSS/Atom feed."""

    soup = BeautifulSoup(xml_text, "xml")

    items = []

    # RSS
    for item in soup.find_all("item"):

        title_tag = item.find("title")
        link_tag = item.find("link")

        title = title_tag.get_text(" ", strip=True) if title_tag else None

        link = None

        if link_tag:
            link = link_tag.get_text(strip=True)

            if not link:
                link = link_tag.get("href")

        date_value = None

        for tag_name in [
            "pubDate",
            "published",
            "updated",
            "date",
            "dc:date",
        ]:
            tag = item.find(tag_name)

            if tag:
                date_value = tag.get_text(strip=True)
                break

        description = ""

        for tag_name in [
            "description",
            "summary",
            "content",
            "content:encoded",
        ]:
            tag = item.find(tag_name)

            if tag:
                description = tag.get_text(" ", strip=True)
                break

        items.append({
            "title": title,
            "url": clean_url(link),
            "date": parse_date(date_value),
            "description": description,
        })

    # Atom fallback
    if not items:

        for entry in soup.find_all("entry"):

            title_tag = entry.find("title")

            title = (
                title_tag.get_text(" ", strip=True)
                if title_tag
                else None
            )

            link = None

            link_tag = entry.find("link")

            if link_tag:
                link = link_tag.get("href")

                if not link:
                    link = link_tag.get_text(strip=True)

            date_value = None

            for tag_name in [
                "published",
                "updated",
                "date",
            ]:
                tag = entry.find(tag_name)

                if tag:
                    date_value = tag.get_text(strip=True)
                    break

            summary_tag = entry.find("summary")

            description = (
                summary_tag.get_text(" ", strip=True)
                if summary_tag
                else ""
            )

            items.append({
                "title": title,
                "url": clean_url(link),
                "date": parse_date(date_value),
                "description": description,
            })

    return items


async def fetch_text(session, url):
    """Fetch URL safely."""

    try:

        async with session.get(
            url,
            headers=HEADERS,
            timeout=aiohttp.ClientTimeout(total=30),
            allow_redirects=True,
        ) as response:

            status = response.status

            if status != 200:
                return None, f"HTTP {status}"

            text = await response.text(errors="ignore")

            return text, None

    except asyncio.TimeoutError:

        return None, "timeout"

    except Exception as error:

        return None, str(error)


async def crawl_article(
    session,
    semaphore,
    source,
    item,
    cutoff,
):
    """Crawl a single news article."""

    url = item["url"]

    if not url:
        return None, "missing URL"

    async with semaphore:

        html, error = await fetch_text(session, url)

        if html:

            text = clean_text(html)

            if len(text) >= MIN_ARTICLE_TEXT:

                return {
                    "schemaVersion": "1.0",
                    "recordType": "NEWS",

                    "source": {
                        "name": source["name"],
                        "url": source["url"],
                    },

                    "content": {
                        "title": item["title"],
                        "url": url,
                        "text": text,
                        "publishedAt": item["date"].isoformat(),
                    },

                    "collectedAt": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }, None

        # Safe RSS fallback.
        # We do NOT bypass blocked pages.
        rss_description = clean_text(
            item.get("description", "")
        )

        if len(rss_description) >= MIN_ARTICLE_TEXT:

            return {
                "schemaVersion": "1.0",
                "recordType": "NEWS",

                "source": {
                    "name": source["name"],
                    "url": source["url"],
                },

                "content": {
                    "title": item["title"],
                    "url": url,
                    "text": rss_description,
                    "publishedAt": item["date"].isoformat(),
                },

                "collectedAt": datetime.now(
                    timezone.utc
                ).isoformat(),

                "collectionMethod": "rss_fallback",
            }, None

        return None, error or "article text unavailable"


async def crawl_source(session, source, cutoff):
    """Collect fresh articles from one RSS source."""

    print()
    print("=" * 60)
    print(f"SOURCE: {source['name']}")
    print("=" * 60)

    feed_text, error = await fetch_text(
        session,
        source["url"]
    )

    if not feed_text:

        print(f"[FAILED FEED] {error}")

        return [], [{
            "source": source["name"],
            "url": source["url"],
            "reason": error,
        }]

    items = extract_rss_items(feed_text)

    print(f"Feed items: {len(items)}")

    fresh_items = []

    for item in items:

        if not item["url"]:
            continue

        if not item["date"]:
            continue

        if item["date"] >= cutoff:

            fresh_items.append(item)

    print(f"Fresh feed items: {len(fresh_items)}")

    semaphore = asyncio.Semaphore(CONCURRENCY)

    tasks = [
        crawl_article(
            session,
            semaphore,
            source,
            item,
            cutoff,
        )
        for item in fresh_items
    ]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True
    )

    articles = []
    failures = []

    for item, result in zip(
        fresh_items,
        results
    ):

        if isinstance(result, Exception):

            failures.append({
                "source": source["name"],
                "url": item["url"],
                "reason": str(result),
            })

            continue

        article, error = result

        if article:

            articles.append(article)

        else:

            failures.append({
                "source": source["name"],
                "url": item["url"],
                "reason": error,
            })

    print(f"Articles collected: {len(articles)}")
    print(f"Failures: {len(failures)}")

    return articles, failures


async def main():

    print("=" * 70)
    print("AI NEWS CRAWLER")
    print("=" * 70)

    now = datetime.now(timezone.utc)

    cutoff = now - timedelta(
        hours=LOOKBACK_HOURS
    )

    print(
        f"Current UTC time: {now.isoformat()}"
    )

    print(
        f"Freshness cutoff: {cutoff.isoformat()}"
    )

    connector = aiohttp.TCPConnector(
        limit=CONCURRENCY,
        ssl=False,
    )

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        tasks = [
            crawl_source(
                session,
                source,
                cutoff,
            )
            for source in NEWS_SOURCES
        ]

        source_results = await asyncio.gather(
            *tasks
        )

    all_articles = []
    all_failures = []

    for articles, failures in source_results:

        all_articles.extend(articles)
        all_failures.extend(failures)

    # Deduplicate by article URL.
    unique_articles = {}

    for article in all_articles:

        url = article["content"]["url"]

        if url:
            unique_articles[url] = article

    all_articles = list(
        unique_articles.values()
    )

    # Final freshness verification.
    final_articles = []

    for article in all_articles:

        published = parse_date(
            article["content"]["publishedAt"]
        )

        if published and published >= cutoff:

            final_articles.append(article)

    # Sort newest first.
    final_articles.sort(
        key=lambda x: x["content"]["publishedAt"],
        reverse=True,
    )

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            final_articles,
            file,
            indent=4,
            ensure_ascii=False,
        )

    with open(
        FAILED_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            all_failures,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print()
    print("=" * 70)
    print("NEWS CRAWLER COMPLETE")
    print("=" * 70)

    print(
        f"Sources monitored:       {len(NEWS_SOURCES)}"
    )

    print(
        f"Fresh news articles:     {len(final_articles)}"
    )

    print(
        f"Failed / unavailable:    {len(all_failures)}"
    )

    print(
        f"Output:                  {OUTPUT_FILE}"
    )

    print(
        f"Failures:                {FAILED_FILE}"
    )

    print()

    for source in NEWS_SOURCES:

        count = sum(
            1
            for article in final_articles
            if article["source"]["name"]
            == source["name"]
        )

        print(
            f"{source['name']}: {count}"
        )


if __name__ == "__main__":
    asyncio.run(main())