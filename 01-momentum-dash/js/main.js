// Entry point of the new-tab page: clock, greeting, focus, settings, and
// starts the three data features (background, weather, quote).

import { load, save, todayKey } from "./storage.js";
import { showBackground } from "./background.js";
import { showWeather, searchCity } from "./weather.js";
import { showDailyQuote } from "./quote.js";

const DEFAULT_SETTINGS = {
  name: "",
  locationMode: "auto", // "auto" = browser location, "city" = picked in settings
  city: null,           // { name, latitude, longitude } when locationMode is "city"
  unit: "celsius",
  bgMode: "tab",        // "tab" | "hour" | "day"
};

const $ = (id) => document.getElementById(id);
let settings;

async function start() {
  settings = { ...DEFAULT_SETTINGS, ...(await load("settings", {})) };

  updateClock();
  setInterval(updateClock, 1000);
  await setupFocus();
  setupSettings();

  // The three features are independent: one failing must not stop the others
  showBackground({ mode: settings.bgMode }).catch((e) => console.warn(e));
  showWeather(settings);
  showDailyQuote().catch((e) => console.warn(e));

  $("next-photo").addEventListener("click", () =>
    showBackground({ mode: settings.bgMode, advance: true })
  );
}

// ---------------------------------------------------------------- clock + greeting
function updateClock() {
  const now = new Date();
  $("clock").textContent = now.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" });

  const hour = now.getHours();
  const hello = hour >= 5 && hour < 12 ? "Bom dia" : hour >= 12 && hour < 20 ? "Boa tarde" : "Boa noite";
  $("greeting").textContent = settings.name ? `${hello}, ${settings.name}.` : `${hello}.`;
}

// ---------------------------------------------------------------- daily focus
// Stored with today's date, so it disappears automatically tomorrow.
async function setupFocus() {
  const focus = await load("focus");
  showFocus(focus && focus.date === todayKey() ? focus.text : "");

  $("focus-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = $("focus-input").value.trim();
    if (!text) return;
    await save("focus", { date: todayKey(), text });
    showFocus(text);
  });

  $("focus-clear").addEventListener("click", async () => {
    await save("focus", null);
    $("focus-input").value = "";
    showFocus("");
  });
}

function showFocus(text) {
  $("focus-form").hidden = Boolean(text);
  $("focus-done").hidden = !text;
  $("focus-text").textContent = text;
}

// ---------------------------------------------------------------- settings panel
function setupSettings() {
  const panel = $("settings");

  $("settings-toggle").addEventListener("click", () => {
    fillSettingsForm();
    panel.hidden = !panel.hidden;
  });

  $("settings-close").addEventListener("click", async () => {
    settings.name = $("set-name").value.trim();
    settings.unit = $("set-unit").value;
    settings.bgMode = $("set-bg-mode").value;
    settings.locationMode = document.querySelector("input[name=loc-mode]:checked").value;
    if (settings.locationMode === "city" && !settings.city) settings.locationMode = "auto";

    await save("settings", settings);
    panel.hidden = true;
    updateClock();
    showWeather(settings);
  });

  $("city-find").addEventListener("click", findCity);
  $("set-city").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); findCity(); }
  });
}

function fillSettingsForm() {
  $("set-name").value = settings.name;
  $("set-unit").value = settings.unit;
  $("set-bg-mode").value = settings.bgMode;
  document.querySelector(`input[name=loc-mode][value=${settings.locationMode}]`).checked = true;
  $("city-current").textContent = settings.city ? `Chosen city: ${settings.city.label ?? settings.city.name}` : "";
  $("city-results").replaceChildren();
}

async function findCity() {
  const query = $("set-city").value.trim();
  const list = $("city-results");
  if (!query) return;
  list.textContent = "Searching…";
  try {
    const results = await searchCity(query);
    if (results.length === 0) { list.textContent = "No place found."; return; }
    list.replaceChildren(...results.map((place) => {
      const li = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = place.label;
      button.addEventListener("click", () => {
        settings.city = place;
        document.querySelector("input[name=loc-mode][value=city]").checked = true;
        $("city-current").textContent = `Chosen city: ${place.label}`;
        list.replaceChildren();
      });
      li.append(button);
      return li;
    }));
  } catch {
    list.textContent = "Search failed (offline?).";
  }
}

start();
