// Small wrapper around chrome.storage.local.
// When the page is opened as a normal file (not as an extension, e.g. for
// testing), chrome.storage does not exist, so we fall back to localStorage.

const hasChromeStorage =
  typeof chrome !== "undefined" && chrome.storage && chrome.storage.local;

export async function load(key, fallback = null) {
  if (hasChromeStorage) {
    const result = await chrome.storage.local.get(key);
    return result[key] ?? fallback;
  }
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export async function save(key, value) {
  if (hasChromeStorage) {
    await chrome.storage.local.set({ [key]: value });
    return;
  }
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage full or blocked: the page still works, it just won't remember */
  }
}

// Today's date as "2026-11-19", in the user's local time zone.
export function todayKey(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
