"""
Scrape books.toscrape.com and store the results in a SQLite database.

TEST MODE: only the first 10 books are scraped. Each book's own page is
opened to collect the full details. Raise MAX_BOOKS / MAX_LISTING_PAGES
below to scrape more (the full site is 50 pages x 20 books = 1000 books).

Setup (once, in the VS Code terminal):
    pip install requests beautifulsoup4

Run:
    python scrape_books.py

Output:
    books.db  (SQLite file next to this script, table "books")
"""

import re
import sqlite3
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------- settings
LISTING_URL = "https://books.toscrape.com/catalogue/page-{}.html"
MAX_LISTING_PAGES = 1    # catalogue pages to walk (each holds 20 books)
MAX_BOOKS = 10           # stop after this many books; None = no limit
DB_PATH = "books.db"
DELAY_SECONDS = 0.5      # pause between requests, to be polite
TIMEOUT_SECONDS = 15

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

session = requests.Session()
session.headers["User-Agent"] = "Mozilla/5.0 (books-scraper-practice)"


# ---------------------------------------------------------------- helpers
def get_soup(url):
    """Download a page and return it parsed."""
    resp = session.get(url, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    resp.encoding = "utf-8"  # otherwise '£' can come out as 'Â£'
    time.sleep(DELAY_SECONDS)
    return BeautifulSoup(resp.text, "html.parser")


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
    """Return the absolute URLs of every book on one catalogue page."""
    url = LISTING_URL.format(page_number)
    soup = get_soup(url)
    return [urljoin(url, a["href"]) for a in soup.select("article.product_pod h3 a")]


def parse_book(url):
    """Open one book's page and pull out all its fields."""
    soup = get_soup(url)

    # The "Product Information" table: UPC, prices, tax, availability, reviews
    info = {
        row.th.get_text(strip=True): row.td.get_text(strip=True)
        for row in soup.select("table.table-striped tr")
    }

    rating_tag = soup.select_one("p.star-rating")
    rating = None
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
        "product_type": info.get("Product Type"),
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
            upc            TEXT PRIMARY KEY,
            title          TEXT NOT NULL,
            category       TEXT,
            price_excl_tax REAL,
            price_incl_tax REAL,
            tax            REAL,
            availability   INTEGER,
            rating         INTEGER,
            num_reviews    INTEGER,
            product_type   TEXT,
            description    TEXT,
            image_url      TEXT,
            product_url    TEXT,
            scraped_at     TEXT
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
def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    saved, failed = 0, 0
    done = False

    for page in range(1, MAX_LISTING_PAGES + 1):
        print(f"\nCatalogue page {page}")
        try:
            links = get_book_links(page)
        except requests.RequestException as err:
            print(f"  Could not load page {page}: {err}")
            break

        for link in links:
            if MAX_BOOKS is not None and saved + failed >= MAX_BOOKS:
                done = True
                break
            try:
                book = parse_book(link)
                save_book(conn, book)
                saved += 1
                print(f"  [{saved:>3}] {book['title'][:60]}  £{book['price_incl_tax']}  ({book['rating']}★)")
            except (requests.RequestException, AttributeError, KeyError) as err:
                failed += 1
                print(f"  Failed: {link} -> {err}")

        if done:
            break

    total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    conn.close()
    print(f"\nDone. Saved {saved} books this run ({failed} failed). "
          f"{total} books now in {DB_PATH}.")


if __name__ == "__main__":
    main()
