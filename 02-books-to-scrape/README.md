# Practice Scraper

Scrapes [books.toscrape.com](https://books.toscrape.com) and saves the books to a `books` table in your Supabase database.

Test mode: only the first 10 books are scraped. Change `MAX_LISTING_PAGES` and `MAX_BOOKS` at the top of `scrape_books.py` to scrape more.

## Setup (once)

1. Install the libraries (on a Mac, use `python3`, not `python`):
   ```bash
   python3 -m pip install -r requirements.txt
   ```
   On Windows, use `python` instead of `python3`.
2. Get your connection string: in the Supabase dashboard, open your project, click **Connect**, choose **Shared pooler**, and copy the URI.
3. Copy `.env.example` to a new file called `.env`, then replace the `DATABASE_URL` value with the shared pooler URI from Supabase. Replace `[YOUR-PASSWORD]` in that URI with your database password. If your password contains special characters, percent-encode them in the URI.
   `.env` is in `.gitignore`, so your password never ends up on GitHub.

## Run

```bash
python3 scrape_books.py
```

If something is set up wrong (a missing library, no `.env`, a wrong password or host), the script stops with a message that says what to fix.

The script creates the `books` table the first time it runs. Re-running it updates existing books instead of adding duplicates. At the end it prints the first row of the table so you can check the data.

You can also view the data in the Supabase dashboard under **Table Editor → books**.

## Privacy

- The script sends generic browser headers, so the site doesn't see "python-requests", your operating system or your real browser. It sends no cookies and runs no JavaScript, so there is no browser fingerprint.
- **Your IP address** can only be hidden by sending the traffic through someone else's server. Set `PROXY_URL` in `.env` (examples are in `.env.example`). At startup the script prints the IP address websites will see. If the proxy can't be reached, it stops instead of falling back to your real IP.
- Alternative without any setup in the code: turn on a VPN on your computer before running the script.
- The connection to Supabase does not go through the proxy. It's your own database, so it only sees your IP.
