"""
Scrape books.toscrape.com and store the books in a local SQLite database.

books.toscrape.com is a practice website made for learning web scraping.
For every book, the script opens the book's own page to collect all details.

Usage (in the VS Code terminal, inside this folder):
    python scrape_books.py              # first 2 catalogue pages = 40 books (~30 s)
    python scrape_books.py --pages 5    # first 5 pages = 100 books
    python scrape_books.py --all        # all 50 pages = 1000 books (~10 min)
    python scrape_books.py --max-books 10   # stop after 10 books (quick test)

Output:
    books.db (SQLite file in this folder, table "books").
    Running the script again updates existing books instead of duplicating them.
"""

import argparse
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as err:
    sys.exit(
        f"Missing library: {err.name}\n"
        f"Install the libraries into the Python that runs this script with:\n"
        f"    {sys.executable} -m pip install -r requirements.txt"
    )

# ---------------------------------------------------------------- settings
BASE_URL = "https://books.toscrape.com/"
LISTING_URL = BASE_URL + "catalogue/page-{}.html"
TOTAL_PAGES = 50          # the site has 50 catalogue pages of 20 books
DB_PATH = Path(__file__).with_name("books.db")  # always next to this script
DELAY_SECONDS = 0.3       # pause between requests, to be polite to the server
TIMEOUT_SECONDS = 15

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

session = requests.Session()
session.headers["User-Agent"] = "books-scraper (student project; educational use)"


# ---------------------------------------------------------------- helpers
def get_soup(url):
    """Download a page and return it parsed by BeautifulSoup."""
    response = session.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    response.encoding = "utf-8"  # otherwise '£' comes out as 'Â£'
    time.sleep(DELAY_SECONDS)
    return BeautifulSoup(response.text, "html.parser")


def to_float(text):
    """'£51.77' -> 51.77"""
    match = re.search(r"\d+(?:\.\d+)?", text or "")
    return float(match.group()) if match else None


def to_int(text):
    """'In stock (22 available)' -> 22"""
    match = re.search(r"\d+", text or "")
    return int(match.group()) if match else None


# ---------------------------------------------------------------- scraping
def get_book_links(page_number):
    """Return the full URLs of the 20 books on one catalogue page."""
    url = LISTING_URL.format(page_number)
    soup = get_soup(url)
    return [urljoin(url, a["href"]) for a in soup.select("article.product_pod h3 a")]


def parse_book(url):
    """Open one book's page and return its details as a dictionary."""
    soup = get_soup(url)

    # The "Product Information" table: UPC, prices, tax, availability, reviews
    info = {
        row.th.get_text(strip=True): row.td.get_text(strip=True)
        for row in soup.select("table.table-striped tr")
    }

    # The rating is only stored as a CSS class: <p class="star-rating Three">
    rating = None
    rating_tag = soup.select_one("p.star-rating")
    if rating_tag:
        rating = next((RATING_WORDS[c] for c in rating_tag["class"] if c in RATING_WORDS), None)

    description_tag = soup.select_one("#product_description + p")
    breadcrumbs = soup.select("ul.breadcrumb li a")  # Home > Books > Category
    image_tag = soup.select_one("div.item.active img")

    return {
        "upc": info.get("UPC"),
        "title": soup.select_one("div.product_main h1").get_text(strip=True),
        "category": breadcrumbs[2].get_text(strip=True) if len(breadcrumbs) > 2 else None,
        "price_excl_tax": to_float(info.get("Price (excl. tax)")),
        "price_incl_tax": to_float(info.get("Price (incl. tax)")),
        "tax": to_float(info.get("Tax")),
        "availability": to_int(info.get("Availability")),
        "rating": rating,
        "num_reviews": to_int(info.get("Number of reviews")),
        "description": description_tag.get_text(strip=True) if description_tag else None,
        "image_url": urljoin(url, image_tag["src"]) if image_tag else None,
        "product_url": url,
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------- database
def init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            upc            TEXT PRIMARY KEY,   -- unique product code from the site
            title          TEXT NOT NULL,
            category       TEXT,
            price_excl_tax REAL,
            price_incl_tax REAL,
            tax            REAL,
            availability   INTEGER,            -- number of copies in stock
            rating         INTEGER,            -- 1 to 5 stars
            num_reviews    INTEGER,
            description    TEXT,
            image_url      TEXT,
            product_url    TEXT,
            scraped_at     TEXT                -- ISO timestamp (UTC)
        )
        """
    )
    conn.commit()


def save_book(conn, book):
    """Insert a book, or update it if its UPC is already stored (safe to re-run)."""
    columns = list(book.keys())
    placeholders = ", ".join(f":{c}" for c in columns)
    updates = ", ".join(f"{c} = excluded.{c}" for c in columns if c != "upc")
    conn.execute(
        f"""
        INSERT INTO books ({", ".join(columns)})
        VALUES ({placeholders})
        ON CONFLICT(upc) DO UPDATE SET {updates}
        """,
        book,
    )
    conn.commit()


# ---------------------------------------------------------------- main
def parse_args():
    parser = argparse.ArgumentParser(description="Scrape books.toscrape.com into books.db")
    parser.add_argument("--pages", type=int, default=2,
                        help="number of catalogue pages to scrape, 20 books each (default: 2)")
    parser.add_argument("--all", action="store_true", help="scrape all 50 pages (1000 books)")
    parser.add_argument("--max-books", type=int, default=None,
                        help="stop after this many books (for a quick test)")
    args = parser.parse_args()
    if args.all:
        args.pages = TOTAL_PAGES
    args.pages = max(1, min(args.pages, TOTAL_PAGES))
    return args


def main():
    args = parse_args()
    print(f"Scraping {args.pages} catalogue page(s) into {DB_PATH.name} ...")

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    saved = failed = 0

    try:
        for page in range(1, args.pages + 1):
            print(f"\nCatalogue page {page}/{args.pages}")
            try:
                links = get_book_links(page)
            except requests.RequestException as err:
                print(f"  Could not load page {page}: {err}")
                print("  Check your internet connection and try again.")
                break

            for link in links:
                if args.max_books is not None and saved + failed >= args.max_books:
                    break
                try:
                    book = parse_book(link)
                    save_book(conn, book)
                    saved += 1
                    stars = "★" * (book["rating"] or 0)
                    print(f"  [{saved:>4}] {book['title'][:55]:<55} £{book['price_incl_tax']:>6.2f}  {stars}")
                except (requests.RequestException, AttributeError, KeyError, TypeError) as err:
                    failed += 1
                    print(f"  Failed: {link} -> {err}")
            else:
                continue  # inner loop finished normally: go to the next page
            break         # inner loop hit --max-books: stop completely
    except KeyboardInterrupt:
        print("\nStopped by user. Books saved so far are kept.")

    total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    conn.close()
    print(f"\nDone. Saved {saved} books this run ({failed} failed). "
          f"{total} books now in {DB_PATH.name}.")
    print("Open the interface with:  streamlit run app.py")


if __name__ == "__main__":
    main()
