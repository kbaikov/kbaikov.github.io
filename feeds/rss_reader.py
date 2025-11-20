# /// script
# dependencies = [
#   "feedparser",
# ]
# ///

"""
Configurable RSS Feed Fetcher - Uses feedparser but not requests
"""

import argparse
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta

import feedparser


@dataclass
class Article:
    title: str
    link: str
    published: datetime
    feed: str
    feed_title: str


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


def get_recent_articles(feed_urls: list[str], days_back: int) -> list[Article]:
    """
    Get articles published within the specified timeframe
    """
    cutoff_date = datetime.now() - timedelta(days=days_back)
    recent_articles: list[Article] = []

    for url in feed_urls:
        feed = fetch_feed_urllib(url)

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
                recent_articles.append(
                    Article(title, link, article_date, url, feed_title)
                )

        time.sleep(0.5)  # Be polite to servers

    return recent_articles


def generate_html_output(
    articles: list[Article], output_file: str, days_back: int
) -> None:
    """
    Generate HTML output with proper list tags
    """
    html_content = f"""<!doctype html>
<html lang="en">
<head>
    <!-- Required meta tags -->
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

    <link rel="stylesheet" href="https://cdn.simplecss.org/simple.min.css">
    <title>Recent RSS Articles</title>
</head>
<body>
    <header>
        <nav>
            <a href="/index.html">Home</a>
            <a href="/feeds/index.html" aria-current="page">Feeds</a>
            <a href="/weight/index.html">Weight</a>
            <a href="/about.html">About</a>
        </nav>
        <h1>Recent RSS Articles</h1>
        <p>Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")}</p>
        <p>Showing articles from the last {days_back} days</p>
        <p>Total articles: {len(articles)}</p>
    </header>
    
    <ul class="article-list">
"""

    if not articles:
        html_content += """
        <div class="empty-state">
            <h2>No articles found</h2>
            <p>No recent articles were found in the specified timeframe.</p>
        </div>
"""
    else:
        for article in articles:
            html_content += f"""
        <li class="article-item">
            <div class="article-title">
                <a href="{article.link}" target="_blank" rel="noopener">{article.title}</a>
            </div>
            <div class="article-meta">
                <span class="publish-date">{article.published}</span>
                <span class="feed-source"> {article.feed_title}</span>
            </div>
        </li>
"""

    html_content += """
    </ul>
    
</body>
</html>
"""

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

    # print(f"Found {len(articles)} recent articles")
    # for article in articles:
    #     print(f"- {article.published}: {article.title}")


if __name__ == "__main__":
    main()
