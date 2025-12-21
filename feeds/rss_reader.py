# /// script
# dependencies = [
#   "feedparser",
#   "jinja2",
# ]
# ///

"""
Configurable RSS Feed Fetcher - Uses feedparser but not requests
"""

import argparse
import concurrent.futures
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import ParamSpec, TypeVar

import feedparser
from jinja2 import Environment, FileSystemLoader

T = TypeVar("T")
P = ParamSpec("P")


@dataclass
class Article:
    title: str
    link: str
    published: datetime
    feed_title: str


def log_step(func: Callable[P, T]) -> Callable[P, T]:
    """Prints the time it took for a function to run."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        """wrapper"""
        tic = datetime.now()
        result = func(*args, **kwargs)
        time_taken = str(datetime.now() - tic)
        print(f"Ran step: {func.__name__} took: {time_taken}")  # ty:ignore[unresolved-attribute]
        return result

    return wrapper


def fetch_feed_urllib(url: str, timeout: int = 10) -> feedparser.FeedParserDict | None:
    """
    Fetch feed using urllib and parse with feedparser
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; RSSReader/1.0)"}

        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content = response.read()
            feed = feedparser.parse(content)

            if feed.bozo:
                print(
                    f"Warning: Parse issues with {url}: {feed.bozo_exception}",
                    file=sys.stderr,
                )

            return feed

    except urllib.error.URLError as e:
        print(f"Error fetching feed {url}: {e}", file=sys.stderr)
        return None

    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


@log_step
def get_recent_articles(feed_urls: list[str], days_back: int) -> list[Article]:
    """
    Get articles published within the specified timeframe
    """
    cutoff_date = datetime.now() - timedelta(days=days_back)
    recent_articles: list[Article] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {
            executor.submit(fetch_feed_urllib, url): url for url in feed_urls
        }
        feeds = [f.result() for f in concurrent.futures.as_completed(future_to_url)]

    for feed in feeds:
        if not feed or not hasattr(feed, "entries"):
            continue

        for entry in feed.entries:
            # convert from a time.struct_time object into a datetime object
            published_date = entry.get(
                "published_parsed", (2025, 10, 4, 0, 0, 0, 5, 277, 0)
            )
            article_date = datetime.fromtimestamp(time.mktime(published_date))

            link = entry.get("link", "")
            title = entry.get("title", "No title")
            feed_title = feed.feed.get("title", "Unknown feed")

            if link and article_date >= cutoff_date:
                recent_articles.append(Article(title, link, article_date, feed_title))

    return recent_articles


def generate_html_output(
    articles: list[Article], output_file: str, days_back: int
) -> None:
    """
    Generate HTML output with proper list tags
    """
    environment = Environment(loader=FileSystemLoader("feeds/templates/"))
    template = environment.get_template("feeds.html")

    html_content = template.render(
        articles=articles,
        date_now=datetime.now().strftime("%Y-%m-%d at %H:%M:%S"),
        days_back=days_back,
    )

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"HTML output written to {output_file}")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}", file=sys.stderr)


def main() -> None:
    """
    Main function with command-line argument parsing
    """
    parser = argparse.ArgumentParser(
        description="Fetch recent articles from RSS/Atom feeds and generate HTML output"
    )
    parser.add_argument("--input", help="File containing feed URLs (one per line)")
    parser.add_argument("--days", type=int, help="Number of days back to check")
    parser.add_argument("--output", help="Output HTML file")

    args = parser.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            feed_urls = [line for line in f.readlines()]
    except FileNotFoundError:
        print(f"Error: File {args.input} not found", file=sys.stderr)
        return

    print(
        f"Checking {len(feed_urls)} feeds for articles from the last {args.days} days..."
    )

    articles = get_recent_articles(feed_urls, days_back=args.days)
    articles.sort(key=lambda a: a.published, reverse=True)

    generate_html_output(articles, args.output, args.days)


if __name__ == "__main__":
    main()
