# /// script
# dependencies = [
#   "feedparser-rs==0.5.3",
#   "jinja2==3.1.6",
#   "aiohttp==3.13.5",
# ]
# ///

"""Configurable RSS Feed Fetcher - Uses feedparser-rs."""

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import aiohttp
import feedparser_rs as feedparser
from jinja2 import Environment, FileSystemLoader


@dataclass
class Article:
    title: str
    link: str
    published: datetime
    feed_title: str


async def fetch_feed(
    url: str, session: aiohttp.ClientSession
) -> feedparser.FeedParserDict:
    """Fetch feed and parse with feedparser."""
    async with session.get(url) as resp:
        feed = feedparser.parse(await resp.text())

    if feed.bozo:
        pass

    return feed


async def get_recent_articles(feed_urls: list[str], days_back: int) -> list[Article]:
    """Get articles published within the specified timeframe."""
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
    recent_articles: list[Article] = []

    async with aiohttp.ClientSession() as session:
        coros = [fetch_feed(url, session) for url in feed_urls]
        results = await asyncio.gather(*coros, return_exceptions=True)

    for feed in results:
        if not feed or isinstance(feed, aiohttp.ClientError):
            continue

        for entry in feed.entries:
            published_date_time_tuple = entry.get(
                "published_parsed",
                (2025, 10, 4, 0, 0, 0, 5, 277, 0),
            )
            # convert from a time.struct_time object into a datetime object
            article_date = datetime(
                *published_date_time_tuple[0:6], tzinfo=timezone.utc
            )

            link = entry.get("link", "")
            title = entry.get("title", "No title")
            feed_title = feed.feed.get("title", "Unknown feed")

            if link and article_date >= cutoff_date:
                recent_articles.append(Article(title, link, article_date, feed_title))

    return recent_articles


def generate_html_output(
    articles: list[Article], output_file: str, days_back: int
) -> None:
    """Generate HTML output with proper list tags."""
    environment = Environment(loader=FileSystemLoader("feeds/templates/"))
    template = environment.get_template("feeds.html")

    html_content = template.render(
        articles=articles,
        date_now=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d at %H:%M:%S"),
        days_back=days_back,
    )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)


def main() -> None:
    """Parse command-line arguments and generate HTML."""
    parser = argparse.ArgumentParser(
        description="Fetch recent articles from RSS/Atom feeds and generate HTML output",
    )
    parser.add_argument("--input", help="File containing feed URLs (one per line)")
    parser.add_argument("--days", type=int, help="Number of days back to check")
    parser.add_argument("--output", help="Output HTML file")

    args = parser.parse_args()

    def read_input():
        with open(args.input, encoding="utf-8") as f:
            return list(f)

    feed_urls = read_input()
    articles = asyncio.run(get_recent_articles(feed_urls, days_back=args.days))
    articles.sort(key=lambda a: a.published, reverse=True)

    generate_html_output(articles, args.output, args.days)


if __name__ == "__main__":
    main()
