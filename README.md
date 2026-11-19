# Applied Programming & AI — Individual Submission

This repository contains my three individual projects. Each one has its own folder with a
README (purpose, data collection, persistence, user interaction, setup, learning, limitations),
a screenshot and an `AUDIT.md` recording the publication audit.

| # | Project | What it does | Folder |
|---|---------|--------------|--------|
| 1 | Momentum Dash replica | Chrome extension that replaces the new-tab page with Portuguese nature photos, the local weather forecast and a daily quote | [`01-momentum-dash/`](01-momentum-dash/) |
| 2 | Books to Scrape | Scrapes books.toscrape.com, stores the books in a SQLite database and shows them in a Streamlit web app | [`02-books-to-scrape/`](02-books-to-scrape/) |
| 3 | TVmaze API | Web page that searches a TV series by name, looks up its ID and lists all its episodes | [`03-tvmaze/`](03-tvmaze/) |

## Repository layout

```
.
├── README.md              ← this file
├── .gitignore             ← shared exclusions (secrets, databases, caches, editor files)
├── 01-momentum-dash/      ← Chrome extension (HTML, CSS, JavaScript)
├── 02-books-to-scrape/    ← Python scraper + SQLite + Streamlit
└── 03-tvmaze/             ← HTML + JavaScript page using the TVmaze API
```

## Tools used

VS Code, Git/GitHub, Python 3, Google Chrome and Claude (AI assistant). How AI was used is
described in the "Limitations and assistance" section of each project README.

No project needs an API key or password, so there is nothing secret to configure.
