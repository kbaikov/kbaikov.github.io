# /// script
# dependencies = [
#   "feedparser-rs==0.6.0",
#   "aiohttp==3.14.3",
# ]
# ///

"""Configurable RSS Feed Fetcher - Uses feedparser-rs."""

import argparse
import asyncio
import textwrap
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import aiohttp
import feedparser_rs as feedparser


@dataclass
class Article:
    title: str
    link: str
    published: date
    feed_title: str


async def fetch_feed(
    url: str, session: aiohttp.ClientSession
) -> feedparser.FeedParserDict:
    """Fetch feed and parse with feedparser."""
    timeout = aiohttp.ClientTimeout(total=30)
    async with session.get(url, timeout=timeout) as resp:
        feed = feedparser.parse(await resp.text())

    if feed.bozo:
        pass

    return feed


def parse_feed_date(entry) -> date:
    """Extract and parse date from feed entry."""
    for date_field in ["published_parsed", "updated_parsed", "created_parsed"]:
        date_tuple = entry.get(date_field)
        if date_tuple and len(date_tuple) >= 6:
            # convert from a time.struct_time object into a datetime object
            return date(*date_tuple[0:3])
    return date(year=2025, month=1, day=1)


async def get_recent_articles(feed_urls: list[str], days_back: int) -> list[Article]:
    """Get articles published within the specified timeframe."""
    cutoff_date = date.today() - timedelta(days=days_back)
    recent_articles: list[Article] = []

    semaphore = asyncio.Semaphore(10)
    async with semaphore, aiohttp.ClientSession() as session:
        coros = [fetch_feed(url, session) for url in feed_urls]
        results = await asyncio.gather(*coros, return_exceptions=True)

    for feed in results:
        if not feed or isinstance(feed, (aiohttp.ClientError, TimeoutError)):
            continue

        for entry in feed.entries:
            article_date = parse_feed_date(entry)

            link = entry.get("link", "")
            title = entry.get("title", "No title")
            feed_title = feed.feed.get("title", "Unknown feed")

            if link and article_date >= cutoff_date:
                recent_articles.append(Article(title, link, article_date, feed_title))

    return recent_articles


def generate_md_output(
    articles: list[Article], output_file: Path, days_back: int
) -> None:
    """Generate HTML output with proper list tags."""

    md_content = textwrap.dedent(f"""
        # Recent RSS Articles

        Generated on {date.today().strftime("%Y-%m-%d")}

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
    """Parse command-line arguments and generate HTML."""
    parser = argparse.ArgumentParser(
        description="Fetch recent articles from RSS/Atom feeds and generate HTML output",
    )
    parser.add_argument(
        "--input", type=Path, help="File containing feed URLs (one per line)"
    )
    parser.add_argument("--days", type=int, help="Number of days back to check")
    parser.add_argument(
        "--output", type=Path, help="Output file. Should be *.html or *.md file."
    )

    args = parser.parse_args()

    feed_urls = args.input.read_text().splitlines()

    articles = asyncio.run(get_recent_articles(feed_urls, days_back=args.days))
    articles.sort(key=lambda a: a.published, reverse=True)

    if args.output.suffix == ".md":
        generate_md_output(articles, args.output, args.days)
    else:
        raise ValueError(
            f"Unsupported output file extension: {args.output.suffix}. Use .html or .md"
        )


if __name__ == "__main__":
    main()
