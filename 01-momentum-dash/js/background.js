// Background photos of Portuguese nature from Wikimedia Commons.
//
// data/backgrounds.json lists the Commons file names. The Commons API turns
// them into image URLs plus author and licence (needed for the credit line).
// That answer is cached for 7 days in storage, so a new tab normally makes
// no API request at all, only the image download (which the browser caches).

import { load, save, todayKey } from "./storage.js";

const API = "https://commons.wikimedia.org/w/api.php";
const CACHE_DAYS = 7;
const IMAGE_WIDTH = 2560; // Commons scales the photo to this width for us

export async function showBackground({ mode = "tab", advance = false } = {}) {
  const photos = await getPhotoList();
  if (photos.length === 0) return; // offline and nothing cached: the CSS gradient stays

  // Decide which photo to show. "period" is what has to change before we move on:
  // a new tab, a new hour or a new day, depending on the setting.
  const state = await load("bgState", { index: -1, period: null });
  const period = currentPeriod(mode);
  if (advance || state.period !== period) {
    state.index = (state.index + 1) % photos.length;
    state.period = period;
    await save("bgState", state);
  }
  const photo = photos[state.index % photos.length];

  await fadeIn(photo.url);
  showCredit(photo);
}

function currentPeriod(mode) {
  const now = new Date();
  if (mode === "day") return todayKey(now);
  if (mode === "hour") return `${todayKey(now)}T${now.getHours()}`;
  return String(now.getTime()); // "tab": different on every new tab
}

async function getPhotoList() {
  const cached = await load("photoCache");
  const fresh = cached && Date.now() - cached.fetchedAt < CACHE_DAYS * 86_400_000;
  if (fresh && cached.items.length) return cached.items;

  try {
    const { files } = await (await fetch("data/backgrounds.json")).json();
    const items = await fetchFromCommons(files);
    if (items.length) await save("photoCache", { fetchedAt: Date.now(), items });
    return items;
  } catch (err) {
    console.warn("Could not load photos from Wikimedia Commons:", err);
    return cached ? cached.items : []; // an old list is better than none
  }
}

async function fetchFromCommons(fileNames) {
  const params = new URLSearchParams({
    action: "query",
    format: "json",
    origin: "*", // allows the request from a browser page (CORS)
    prop: "imageinfo",
    iiprop: "url|extmetadata",
    iiurlwidth: String(IMAGE_WIDTH),
    titles: fileNames.join("|"),
  });
  const response = await fetch(`${API}?${params}`);
  if (!response.ok) throw new Error(`Commons API answered ${response.status}`);
  const data = await response.json();

  // Keep the order of backgrounds.json and skip files that no longer exist
  const byTitle = {};
  for (const page of Object.values(data.query?.pages ?? {})) {
    if (!page.missing && page.imageinfo) byTitle[page.title] = page;
  }
  const normalized = Object.fromEntries((data.query?.normalized ?? []).map((n) => [n.from, n.to]));

  return fileNames
    .map((name) => byTitle[normalized[name] ?? name])
    .filter(Boolean)
    .map((page) => {
      const info = page.imageinfo[0];
      const meta = info.extmetadata ?? {};
      return {
        url: info.thumburl || info.url,
        page: info.descriptionurl,
        title: plainText(meta.ObjectName?.value) || page.title.replace(/^File:|\.\w+$/g, ""),
        author: plainText(meta.Artist?.value) || "Unknown author",
        license: plainText(meta.LicenseShortName?.value) || "see Commons",
      };
    });
}

// Commons returns author names as HTML (often a link). Turn it into plain text.
function plainText(html) {
  if (!html) return "";
  const doc = new DOMParser().parseFromString(html, "text/html");
  return doc.body.textContent.replace(/\s+/g, " ").trim();
}

// Load the image first, then fade it in over the previous one.
function fadeIn(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const current = document.getElementById("bg");
      const next = document.getElementById("bg-next");
      next.style.backgroundImage = `url("${url}")`;
      next.classList.add("visible");
      current.classList.remove("visible");
      // swap roles so the next change fades over this one
      current.id = "bg-next";
      next.id = "bg";
      resolve();
    };
    img.onerror = () => resolve(); // keep whatever is showing
    img.src = url;
  });
}

function showCredit(photo) {
  document.getElementById("photo-title").textContent = photo.title;
  const link = document.getElementById("photo-link");
  link.textContent = `${photo.author} · ${photo.license} · Wikimedia Commons`;
  link.href = photo.page;
}
