# 03 · TVmaze API — TV Series Episode Finder

![Screenshot: all episodes of The Big Bang Theory](screenshots/episodes.png)

## Purpose

A web page that uses the public [TVmaze API](https://www.tvmaze.com/api) to search for a TV series
by name and list **all of its episodes**, grouped by season. Example from the lecture: search
"The Big Bang Theory" → choose the show → see all 279 episodes.

The page follows the two-step flow from the lecture and makes it visible:

1. **Name → ID:** the API is searched by name and returns matching shows, each with an `id` (shown on each result card).
2. **ID → episodes:** with that `id`, the page requests the show's details and its full episode list.

A panel at the bottom ("API requests made by this page") lists every request the page sends.

## Data collection

All data comes live from the TVmaze REST API (JSON, free, no API key, CORS enabled):

| Step | Request | Returns |
|------|---------|---------|
| 1 | `GET https://api.tvmaze.com/search/shows?q=big bang theory` | list of `{ score, show }`; each `show` has `id`, `name`, `premiered`, `network`, `image`, `rating` |
| 2a | `GET https://api.tvmaze.com/shows/66` | details of the show with ID 66 |
| 2b | `GET https://api.tvmaze.com/shows/66/episodes` | every episode: `season`, `number`, `name`, `airdate`, `runtime`, `rating`, `summary`, `url` |

The requests are made with `fetch()` in `app.js`. Steps 2a and 2b run in parallel (`Promise.all`).
TVmaze allows about 20 requests per 10 seconds; a "too many requests" (HTTP 429) answer is shown as a readable message.

## Data persistence

- **Recent searches:** the last 6 search terms are saved in the browser's `localStorage` (key `tvmaze-recent-searches`) and shown as buttons under the search box, so you can repeat a search with one click. Only the search words are stored, nothing personal.
- **Current show in the URL:** after choosing a show, the address becomes `index.html#show=66`. Reloading or sharing the page opens the same show again.
- **CSV export:** the **Download CSV** button saves the episode list as a file on your computer (`The_Big_Bang_Theory_episodes.csv`).
- Show and episode data is **not** stored permanently. It is always fetched fresh from TVmaze, because episode lists of running shows change and the API is fast and free.

## User interaction

1. Type a series name (e.g. `The Big Bang Theory`) and press **Enter** or **Search**.
2. Click the right show among the results (posters, year, network, **ID**, rating).
3. See the show's details and all episodes in one table per season: code (`S01E01`), title (links to TVmaze), short summary, air date, runtime, rating.
4. Use the **season** drop-down or the **title filter** to narrow the list; **Download CSV** exports all episodes.
5. **← back to results** returns to the search results.

## Setup

Requirements: a modern web browser and an internet connection. No installation, no packages, no API key.

- **Simplest:** open `03-tvmaze/index.html` by double-clicking it.
- **Or with a local server** (e.g. VS Code's *Live Server* extension, or in a terminal):
  ```bash
  cd 03-tvmaze
  python3 -m http.server 8000
  # then open http://localhost:8000
  ```

| File | Role |
|------|------|
| `index.html` | page structure |
| `style.css` | layout and design |
| `app.js` | API requests, rendering, filters, recent searches, CSV export |

## Learning

> ✏️ **To write in my own words.** Points to cover:
> - What an API is (Application Programming Interface), and how a REST API answers a URL with JSON.
> - Why the ID is needed: names are ambiguous ("Big Bang" vs "The Big Bang Theory"), IDs are unique. Hence the two steps, Name → ID → Episodes.
> - `fetch`, `async`/`await` and reading JSON in JavaScript; checking `response.ok`.
> - **Challenge:** e.g. the API returns summaries as HTML (`<p><b>…</b></p>`). Inserting it directly with `innerHTML` would be unsafe, so the page converts it to plain text first. Or: shows without a poster image or specials without an episode number.

## Limitations and assistance

- **Limitations:** English interface only; very long series (1000+ episodes) are shown on one page without paging; no information about cast or seasons beyond the episode list; there is no offline mode.
- **Data:** TVmaze data is licensed under [CC BY-SA](https://www.tvmaze.com/api#licensing); the page credits TVmaze in the footer.
- **AI assistance:** I used Claude (Anthropic) as a coding assistant to write the page and draft this README. I tested it myself in the browser with several series and reviewed the code.
- **External code:** none; plain HTML, CSS and JavaScript without libraries.
