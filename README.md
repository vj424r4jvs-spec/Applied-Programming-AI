# Practice Scraper

Scrapes [books.toscrape.com](https://books.toscrape.com) and saves the books to a SQLite database (`books.db`).

Test mode: only the first 10 books are scraped. Change `MAX_LISTING_PAGES` and `MAX_BOOKS` at the top of `scrape_books.py` to scrape more.

## Run

```bash
pip install -r requirements.txt
python scrape_books.py
```

To browse `books.db` in VS Code, install the "SQLite Viewer" extension and click the file.
