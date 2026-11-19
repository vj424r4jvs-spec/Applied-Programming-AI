"""
Scrape books.toscrape.com and store the results in a Supabase (Postgres) database.

TEST MODE: only the first 10 books are scraped. Each book's own page is
opened to collect the full details. Raise MAX_BOOKS / MAX_LISTING_PAGES
below to scrape more (the full site is 50 pages x 20 books = 1000 books).

Setup (once, in the VS Code terminal):
    pip install -r requirements.txt
    Copy .env.example to .env and paste your Supabase connection string
    into DATABASE_URL (see README.md for where to find it).

Run:
    python scrape_books.py

Output:
    Table "books" in your Supabase project (created automatically).
"""

import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

try:
    import psycopg
    import requests
    from bs4 import BeautifulSoup
    from dotenv import load_dotenv
    from psycopg.rows import dict_row
except ImportError as err:
    sys.exit(
        f"Missing library: {err.name}\n"
        f"Install the libraries into the Python that runs this script with:\n"
        f"    {sys.executable} -m pip install -r requirements.txt"
    )

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")

# ---------------------------------------------------------------- settings
LISTING_URL = "https://books.toscrape.com/catalogue/page-{}.html"
MAX_LISTING_PAGES = 1    # catalogue pages to walk (each holds 20 books)
MAX_BOOKS = 10           # stop after this many books; None = no limit
DELAY_SECONDS = 0.5      # pause between requests, to be polite
TIMEOUT_SECONDS = 15

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

# Generic headers, the same as a very common desktop browser sends. Without
# these, requests announces itself as "python-requests/<version>".
GENERIC_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

load_dotenv(ENV_PATH)  # always the .env next to this script, wherever it's run from

session = requests.Session()
session.headers.update(GENERIC_HEADERS)
session.trust_env = False  # ignore system proxy settings; only PROXY_URL is used

# Optional: send all scraping traffic through a proxy so the site sees the
# proxy's IP address instead of yours. Set PROXY_URL in .env (see README.md).
PROXY_URL = os.getenv("PROXY_URL", "").strip()
if PROXY_URL:
    session.proxies = {"http": PROXY_URL, "https": PROXY_URL}


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
        "scraped_at": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------- database
def connect():
    """Open a connection to Supabase using DATABASE_URL from the .env file."""
    if not os.path.exists(ENV_PATH):
        sys.exit(f"No .env file found at {ENV_PATH}\n"
                 "Copy .env.example to a file named exactly '.env' in this folder "
                 "and put your Supabase connection string in it (see README.md).")
    url = os.getenv("DATABASE_URL", "").strip()
    if not url or "[" in url:
        sys.exit("DATABASE_URL in .env is empty or still has a placeholder like "
                 "[YOUR-PASSWORD] or [PROJECT-REF]. Paste your real Supabase "
                 "connection string (see README.md).")
    try:
        # prepare_threshold=None keeps it working with Supabase's connection pooler
        return psycopg.connect(url, prepare_threshold=None, connect_timeout=15)
    except psycopg.OperationalError as err:
        message = str(err).strip()
        hint = "Check the connection string in .env (copy it again from Supabase → Connect)."
        if "password authentication failed" in message:
            hint = ("Wrong database password. Reset it in Supabase under Project Settings → "
                    "Database, then update .env.")
        elif any(s in message for s in ("resolve host", "translate host name", "nodename nor servname")):
            hint = ("The host name in DATABASE_URL is wrong. Copy the Shared pooler URI "
                    "from Supabase → Connect again.")
        elif "Tenant or user not found" in message:
            hint = ("The user name or region in DATABASE_URL is wrong. It must look like "
                    "postgres.<project-ref> and match the host from Supabase → Connect.")
        sys.exit(f"Could not connect to Supabase:\n  {message}\n{hint}")


def init_db(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.books (
                upc            TEXT PRIMARY KEY,
                title          TEXT NOT NULL,
                category       TEXT,
                price_excl_tax NUMERIC(10, 2),
                price_incl_tax NUMERIC(10, 2),
                tax            NUMERIC(10, 2),
                availability   INTEGER,
                rating         INTEGER,
                num_reviews    INTEGER,
                product_type   TEXT,
                description    TEXT,
                image_url      TEXT,
                product_url    TEXT,
                scraped_at     TIMESTAMPTZ
            )
            """
        )
        # Keeps the table private: Supabase's public API can't read or change it,
        # while this script (connecting as the database owner) still can.
        cur.execute("ALTER TABLE public.books ENABLE ROW LEVEL SECURITY")
    conn.commit()


def save_book(conn, book):
    """Insert a book, or update it if its UPC is already stored (safe to re-run)."""
    columns = list(book.keys())
    placeholders = ", ".join(f"%({c})s" for c in columns)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != "upc")
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO public.books ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT (upc) DO UPDATE SET {updates}
            """,
            book,
        )
    conn.commit()


def show_first_row(conn, max_width=70):
    """Print the first row of the books table as a table, to check the data."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM public.books ORDER BY scraped_at, upc LIMIT 1")
        row = cur.fetchone()
    if row is None:
        print("\nThe books table is empty.")
        return

    # One line per column; long values (like the description) are shortened
    rows = []
    for column, value in row.items():
        text = "" if value is None else str(value)
        if len(text) > max_width:
            text = text[: max_width - 3] + "..."
        rows.append((column, text))

    col_w = max(len("Column"), *(len(c) for c, _ in rows))
    val_w = max(len("Value"), *(len(v) for _, v in rows))
    line = f"+-{'-' * col_w}-+-{'-' * val_w}-+"

    print("\nFirst row in the database:")
    print(line)
    print(f"| {'Column':<{col_w}} | {'Value':<{val_w}} |")
    print(line)
    for column, text in rows:
        print(f"| {column:<{col_w}} | {text:<{val_w}} |")
    print(line)


# ---------------------------------------------------------------- main
def show_public_ip():
    """Print the IP address websites see for this script's requests."""
    try:
        ip = session.get("https://api.ipify.org", timeout=TIMEOUT_SECONDS).text.strip()
    except requests.RequestException as err:
        sys.exit(f"Could not connect through the proxy: {err}\n"
                 "Stopping, so nothing is sent from your real IP address.")
    print(f"Proxy: ON. Websites see this IP address: {ip}")


def main():
    if PROXY_URL:
        show_public_ip()
    else:
        print("Proxy: OFF. Websites see your own IP address "
              "(set PROXY_URL in .env to change that).")

    with connect() as conn:
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
                except (requests.RequestException, AttributeError, KeyError, psycopg.Error) as err:
                    conn.rollback()
                    failed += 1
                    print(f"  Failed: {link} -> {err}")

            if done:
                break

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.books")
            total = cur.fetchone()[0]
        print(f"\nDone. Saved {saved} books this run ({failed} failed). "
              f"{total} books now in Supabase table 'books'.")

        show_first_row(conn)


if __name__ == "__main__":
    main()
