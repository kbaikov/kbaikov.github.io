# /// script
# dependencies = [
#   "feedparser-rs==0.7.0",
#   "aiohttp==3.14.3",
#   "loguru",
# ]
# ///

"""Configurable RSS Feed Fetcher - Uses feedparser-rs.

Example:
    uv run scripts/rss_reader.py --input scripts/programming.txt --days 14 --output src/rss.md
"""

import argparse
import asyncio
import sys
import textwrap
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

import aiohttp
import feedparser_rs as feedparser
from loguru import logger


@dataclass
class Article:
    title: str
    link: str
    published: date
    feed_title: str


async def fetch_feed(
    url: str, session: aiohttp.ClientSession
) -> feedparser.FeedParserDict:

    logger.debug(f"Fetching url: {url}")
    timeout = aiohttp.ClientTimeout(total=30)
    headers = {"User-Agent": "RSS-Reader/1.0 (https://kbaikov.github.io/rss.html)"}

    async with session.get(url, timeout=timeout, headers=headers) as resp:
        if resp.status == 429:
            await asyncio.sleep(int(resp.headers.get("Retry-After", 5)))
            return await fetch_feed(url, session)
        resp.raise_for_status()
        feed = feedparser.parse(await resp.text())

    if feed.bozo:
        logger.warning("Bad feed: {} at url: {}.", feed, url)

    return feed


async def fetch_all_feeds(feed_urls: list[str], concurrency: int) -> list:
    logger.info(f"Fetching {len(feed_urls)} feeds...")
    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:

        async def fetch_one(url):
            async with sem:
                return await fetch_feed(url, session)

        coros = [fetch_one(url) for url in feed_urls]
        return await asyncio.gather(*coros, return_exceptions=True)


def parse_articles(article_feeds: list, days_back: int) -> list[Article]:
    cutoff_date = datetime.now(tz=timezone.utc).date() - timedelta(days=days_back)
    recent_articles: list[Article] = []

    for feed in article_feeds:
        if not feed or isinstance(feed, (aiohttp.ClientError, TimeoutError)):
            logger.warning("Bad feed: {}. Ignoring.", feed)
            continue

        feed_title = feed.feed.get("title", "Unknown feed")
        for entry in feed.entries:
            article_date_tuple = (
                entry.get("published_parsed")
                or entry.get("updated_parsed")
                or entry.get("created_parsed")
            )
            if not article_date_tuple:
                continue
            if article_date_tuple <= cutoff_date.timetuple():
                continue

            link = entry.get("link", "")
            if not link:
                continue
            title = entry.get("title", "No title")

            recent_articles.append(
                Article(title, link, date(*article_date_tuple[:3]), feed_title)
            )

    return recent_articles


def generate_md_output(
    articles: list[Article], output_file: Path, days_back: int
) -> None:
    md_content = textwrap.dedent(f"""
        # Recent RSS Articles

        Generated on {datetime.now(tz=timezone.utc).date().strftime("%Y-%m-%d")}

        Showing articles from the last {days_back} days

        Total articles: {len(articles)}

        ## Articles
        """)

    for article in articles:
        md_article = textwrap.dedent(f"""
            - [{article.title}]({article.link})

                {article.feed_title} {article.published}
            """)

        md_content += md_article

    output_file.write_text(md_content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch recent articles from RSS/Atom feeds and generate output",
    )
    parser.add_argument(
        "--input", type=Path, help="File containing feed URLs (one per line)"
    )
    parser.add_argument(
        "--days", type=int, default=14, help="Number of days back to check"
    )
    parser.add_argument(
        "--concurrency", type=int, default=10, help="semaphore concurrency"
    )
    parser.add_argument(
        "--output", type=Path, help="Output file. Should be an *.md file."
    )
    parser.add_argument(
        "--verbose",
        default=False,
        action="store_true",
        help="Enable debug output.",
    )

    args = parser.parse_args()

    if not args.verbose:
        logger.remove()  # Remove the default handler.
        logger.add(sys.stderr, level="INFO")

    try:
        feed_urls = args.input.read_text().splitlines()
    except FileNotFoundError:
        raise FileNotFoundError("The input file should exist")

    if args.days <= 0:
        raise ValueError("Days should be a positive integer")

    start_time = perf_counter()
    articles_raw = asyncio.run(fetch_all_feeds(feed_urls, args.concurrency))
    fetch_end_time = perf_counter()
    logger.debug(f"Fetched in: {fetch_end_time - start_time:.2f} sec")
    articles = parse_articles(articles_raw, args.days)
    logger.info(f"Found {len(articles)} recent articles")
    articles.sort(key=lambda a: a.published, reverse=True)

    if args.output.suffix == ".md":
        generate_md_output(articles, args.output, args.days)
    else:
        raise ValueError(
            f"Unsupported output file extension: {args.output.suffix}. Use .md"
        )


if __name__ == "__main__":
    main()
