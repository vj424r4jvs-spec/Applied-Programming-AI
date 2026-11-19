// TV Series Episode Finder: uses the public TVmaze API (no API key needed).
//
// The flow from the lecture:
//   1. Name -> ID:       GET /search/shows?q=<name>   (list of matching shows, each with an id)
//   2. ID   -> episodes: GET /shows/<id>/episodes     (all episodes of that show)
//
// All text from the API is inserted with textContent (never innerHTML),
// so HTML inside API data can't run as code on this page.

const API = "https://api.tvmaze.com";
const RECENT_KEY = "tvmaze-recent-searches";
const MAX_RECENT = 6;

const $ = (id) => document.getElementById(id);
let currentShow = null;
let currentEpisodes = [];

// ---------------------------------------------------------------- API
async function getJson(path) {
  const url = API + path;
  logRequest(url);
  const response = await fetch(url);
  if (response.status === 429) throw new Error("Too many requests to TVmaze. Wait a few seconds and try again.");
  if (!response.ok) throw new Error(`TVmaze answered with status ${response.status}.`);
  return response.json();
}

// Step 1: name -> list of shows (with their IDs)
const searchShows = (name) => getJson(`/search/shows?q=${encodeURIComponent(name)}`);
// Step 2: ID -> show details and all episodes
const getShow = (id) => getJson(`/shows/${id}`);
const getEpisodes = (id) => getJson(`/shows/${id}/episodes`);

function logRequest(url) {
  const li = document.createElement("li");
  li.textContent = `GET ${url}`;
  $("api-log").prepend(li);
}

// ---------------------------------------------------------------- helpers
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  }
  node.append(...children.filter((c) => c !== null && c !== undefined));
  return node;
}

// TVmaze summaries contain HTML like "<p><b>Leonard</b> is ...</p>". Keep only the text.
function stripHtml(html) {
  if (!html) return "";
  return new DOMParser().parseFromString(html, "text/html").body.textContent.trim();
}

const pad = (n) => String(n).padStart(2, "0");
const episodeCode = (ep) => (ep.number == null ? `S${pad(ep.season)} Special` : `S${pad(ep.season)}E${pad(ep.number)}`);
const year = (date) => (date ? date.slice(0, 4) : "?");

function setStatus(text, isError = false) {
  $("status").textContent = text;
  $("status").classList.toggle("error", isError);
}

// ---------------------------------------------------------------- recent searches (localStorage)
function loadRecent() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY)) ?? [];
  } catch {
    return [];
  }
}

function rememberSearch(term) {
  const list = [term, ...loadRecent().filter((t) => t.toLowerCase() !== term.toLowerCase())].slice(0, MAX_RECENT);
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(list)); } catch { /* private mode: ignore */ }
  renderRecent();
}

function renderRecent() {
  const list = loadRecent();
  const box = $("recent");
  box.replaceChildren();
  if (list.length === 0) return;
  box.append("Recent: ");
  for (const term of list) {
    const button = el("button", { type: "button", text: term });
    button.addEventListener("click", () => { $("search-input").value = term; runSearch(term); });
    box.append(button);
  }
}

// ---------------------------------------------------------------- step 1: search
async function runSearch(term) {
  term = term.trim();
  if (!term) return;
  $("show-section").hidden = true;
  $("results-section").hidden = true;
  setStatus(`Searching for “${term}”…`);
  try {
    const results = await searchShows(term);
    rememberSearch(term);
    if (results.length === 0) {
      setStatus(`No series found for “${term}”. Check the spelling.`);
      return;
    }
    setStatus(`${results.length} series found. Click one to see its episodes.`);
    renderResults(results.map((r) => r.show));
    location.hash = ""; // we are on the results view again
  } catch (err) {
    setStatus(`Search failed: ${err.message}`, true);
  }
}

function renderResults(shows) {
  $("results").replaceChildren(
    ...shows.map((show) => {
      const image = show.image?.medium
        ? el("img", { src: show.image.medium, alt: `Poster of ${show.name}`, loading: "lazy" })
        : el("div", { class: "noimg", text: "📺" });
      const li = el(
        "li", { tabindex: "0", title: "Show all episodes" },
        image,
        el("div", { class: "info" },
          el("strong", { text: show.name }),
          el("span", { text: `${year(show.premiered)} · ${show.network?.name ?? show.webChannel?.name ?? "—"}` }),
          el("br"),
          el("span", { class: "id", text: `ID ${show.id}` }),
          show.rating?.average ? el("span", { text: ` · ★ ${show.rating.average}` }) : null
        )
      );
      li.addEventListener("click", () => openShow(show.id));
      li.addEventListener("keydown", (e) => { if (e.key === "Enter") openShow(show.id); });
      return li;
    })
  );
  $("results-section").hidden = false;
}

// ---------------------------------------------------------------- step 2: episodes
async function openShow(id) {
  setStatus("Loading episodes…");
  try {
    const [show, episodes] = await Promise.all([getShow(id), getEpisodes(id)]);
    currentShow = show;
    currentEpisodes = episodes;
    location.hash = `show=${id}`; // makes the view linkable and survives a reload
    renderShow(show, episodes);
    $("results-section").hidden = true;
    $("show-section").hidden = false;
    setStatus("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    setStatus(`Could not load the episodes: ${err.message}`, true);
  }
}

function renderShow(show, episodes) {
  const seasons = [...new Set(episodes.map((e) => e.season))];
  const ended = show.ended ? `–${year(show.ended)}` : show.status === "Running" ? "–today" : "";

  const poster = show.image?.medium
    ? el("img", { src: show.image.medium, alt: `Poster of ${show.name}` })
    : el("div", { class: "noimg", text: "📺" });
  $("show").replaceChildren(
    poster,
    el("div", {},
      el("h2", { text: show.name }),
      el("div", { class: "meta", text: [
        `${year(show.premiered)}${ended}`,
        show.network?.name ?? show.webChannel?.name,
        show.genres?.join(", "),
        show.rating?.average ? `★ ${show.rating.average}` : null,
        `TVmaze ID ${show.id}`,
      ].filter(Boolean).join(" · ") }),
      el("div", { class: "meta", text: `${seasons.length} seasons · ${episodes.length} episodes · status: ${show.status}` }),
      el("p", { text: stripHtml(show.summary) })
    )
  );

  const filter = $("season-filter");
  filter.replaceChildren(
    el("option", { value: "all", text: "All seasons" }),
    ...seasons.map((s) => el("option", { value: String(s), text: `Season ${s}` }))
  );
  $("episode-filter").value = "";
  renderEpisodes();
}

function renderEpisodes() {
  const season = $("season-filter").value;
  const text = $("episode-filter").value.trim().toLowerCase();
  const visible = currentEpisodes.filter((ep) =>
    (season === "all" || String(ep.season) === season) &&
    (!text || (ep.name ?? "").toLowerCase().includes(text))
  );

  $("episode-count").textContent = `Showing ${visible.length} of ${currentEpisodes.length} episodes.`;

  // group by season, one table per season
  const bySeason = new Map();
  for (const ep of visible) {
    if (!bySeason.has(ep.season)) bySeason.set(ep.season, []);
    bySeason.get(ep.season).push(ep);
  }

  $("episodes").replaceChildren(
    ...[...bySeason].map(([seasonNumber, eps]) =>
      el("div", { class: "season" },
        el("h3", { text: `Season ${seasonNumber} (${eps.length} episodes)` }),
        el("table", {},
          el("thead", {}, el("tr", {},
            el("th", { text: "Episode" }), el("th", { text: "Title" }),
            el("th", { class: "hide-small", text: "Aired" }), el("th", { class: "hide-small", text: "Runtime" }),
            el("th", { text: "Rating" })
          )),
          el("tbody", {}, ...eps.map((ep) => el("tr", {},
            el("td", { class: "code", text: episodeCode(ep) }),
            el("td", {},
              el("a", { href: ep.url, target: "_blank", rel: "noopener", text: ep.name ?? "(untitled)" }),
              ep.summary ? el("div", { class: "summary", text: stripHtml(ep.summary) }) : null
            ),
            el("td", { class: "nowrap hide-small", text: ep.airdate || "—" }),
            el("td", { class: "nowrap hide-small", text: ep.runtime ? `${ep.runtime} min` : "—" }),
            el("td", { class: "nowrap", text: ep.rating?.average ? `★ ${ep.rating.average}` : "—" })
          )))
        )
      )
    )
  );
}

// ---------------------------------------------------------------- CSV export
function downloadCsv() {
  if (!currentShow) return;
  const quote = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const header = ["season", "number", "code", "title", "airdate", "runtime_min", "rating", "url"];
  const rows = currentEpisodes.map((ep) =>
    [ep.season, ep.number, episodeCode(ep), ep.name, ep.airdate, ep.runtime, ep.rating?.average, ep.url].map(quote).join(",")
  );
  const blob = new Blob([[header.join(","), ...rows].join("\n")], { type: "text/csv;charset=utf-8" });
  const link = el("a", {
    href: URL.createObjectURL(blob),
    download: `${currentShow.name.replace(/[^\w]+/g, "_")}_episodes.csv`,
  });
  link.click();
  URL.revokeObjectURL(link.href);
}

// ---------------------------------------------------------------- wiring
$("search-form").addEventListener("submit", (e) => {
  e.preventDefault();
  runSearch($("search-input").value);
});
$("back").addEventListener("click", () => {
  $("show-section").hidden = true;
  if ($("results").children.length) $("results-section").hidden = false;
  location.hash = "";
});
$("season-filter").addEventListener("change", renderEpisodes);
$("episode-filter").addEventListener("input", renderEpisodes);
$("download").addEventListener("click", downloadCsv);

renderRecent();
// Opening index.html#show=66 goes straight to that show's episodes
const match = location.hash.match(/show=(\d+)/);
if (match) openShow(Number(match[1]));
