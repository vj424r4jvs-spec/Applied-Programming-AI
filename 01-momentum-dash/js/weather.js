// Weather from Open-Meteo (https://open-meteo.com): free, no API key needed.
//
// Location: either the browser's current position (geolocation) or a city
// the user picked in Settings. If neither works, Lisbon is used.
// The forecast is cached for 30 minutes, so opening many tabs does not
// send many requests.

import { load, save } from "./storage.js";

const FORECAST_API = "https://api.open-meteo.com/v1/forecast";
const GEOCODING_API = "https://geocoding-api.open-meteo.com/v1/search";
const REVERSE_GEOCODING_API = "https://api.bigdatacloud.net/data/reverse-geocode-client";
const CACHE_MINUTES = 30;
const LISBON = { name: "Lisbon", latitude: 38.7167, longitude: -9.1333 };

// WMO weather codes used by Open-Meteo -> [emoji, description]
const WEATHER_CODES = {
  0: ["☀️", "Clear sky"], 1: ["🌤️", "Mainly clear"], 2: ["⛅", "Partly cloudy"], 3: ["☁️", "Overcast"],
  45: ["🌫️", "Fog"], 48: ["🌫️", "Rime fog"],
  51: ["🌦️", "Light drizzle"], 53: ["🌦️", "Drizzle"], 55: ["🌧️", "Dense drizzle"],
  56: ["🌧️", "Freezing drizzle"], 57: ["🌧️", "Freezing drizzle"],
  61: ["🌦️", "Light rain"], 63: ["🌧️", "Rain"], 65: ["🌧️", "Heavy rain"],
  66: ["🌧️", "Freezing rain"], 67: ["🌧️", "Freezing rain"],
  71: ["🌨️", "Light snow"], 73: ["🌨️", "Snow"], 75: ["❄️", "Heavy snow"], 77: ["❄️", "Snow grains"],
  80: ["🌦️", "Rain showers"], 81: ["🌧️", "Rain showers"], 82: ["⛈️", "Violent rain showers"],
  85: ["🌨️", "Snow showers"], 86: ["❄️", "Snow showers"],
  95: ["⛈️", "Thunderstorm"], 96: ["⛈️", "Thunderstorm with hail"], 99: ["⛈️", "Thunderstorm with hail"],
};
const describe = (code) => WEATHER_CODES[code] ?? ["🌡️", "Unknown"];

export async function showWeather(settings) {
  const place = document.getElementById("weather-place");
  try {
    const location = await resolveLocation(settings);
    const forecast = await getForecast(location, settings.unit);
    render(location, forecast);
  } catch (err) {
    console.warn("Weather failed:", err);
    place.textContent = "Weather unavailable (offline?)";
  }
}

// ---------------------------------------------------------------- location
async function resolveLocation(settings) {
  if (settings.locationMode === "city" && settings.city) return settings.city;

  try {
    const pos = await currentPosition();
    const latitude = round(pos.coords.latitude);
    const longitude = round(pos.coords.longitude);
    return { name: await placeName(latitude, longitude), latitude, longitude };
  } catch (err) {
    console.info("No geolocation, using Lisbon:", err.message);
    return { ...LISBON, name: "Lisbon (default)" };
  }
}

function currentPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error("geolocation not supported"));
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      timeout: 10_000,
      maximumAge: 60 * 60 * 1000, // a position from the last hour is fine
    });
  });
}

// 2 decimals ≈ 1 km: precise enough for weather, and keeps the exact position private
const round = (x) => Math.round(x * 100) / 100;

// Turns coordinates into a town name. Cached, because it never changes.
async function placeName(latitude, longitude) {
  const key = `${latitude},${longitude}`;
  const names = await load("placeNames", {});
  if (names[key]) return names[key];
  try {
    const params = new URLSearchParams({ latitude, longitude, localityLanguage: "en" });
    const data = await (await fetch(`${REVERSE_GEOCODING_API}?${params}`)).json();
    const name = data.city || data.locality || data.principalSubdivision || "Your location";
    await save("placeNames", { ...names, [key]: name });
    return name;
  } catch {
    return "Your location";
  }
}

// Used by the settings panel: "Porto" -> list of matching places
export async function searchCity(query) {
  const params = new URLSearchParams({ name: query, count: "5", language: "en", format: "json" });
  const data = await (await fetch(`${GEOCODING_API}?${params}`)).json();
  return (data.results ?? []).map((r) => ({
    name: r.name,
    label: [r.name, r.admin1, r.country].filter(Boolean).join(", "),
    latitude: r.latitude,
    longitude: r.longitude,
  }));
}

// ---------------------------------------------------------------- forecast
async function getForecast(location, unit = "celsius") {
  const key = `${location.latitude},${location.longitude},${unit}`;
  const cached = await load("weatherCache");
  if (cached && cached.key === key && Date.now() - cached.fetchedAt < CACHE_MINUTES * 60_000) {
    return cached.data;
  }

  const params = new URLSearchParams({
    latitude: location.latitude,
    longitude: location.longitude,
    current: "temperature_2m,weather_code",
    daily: "weather_code,temperature_2m_max,temperature_2m_min",
    timezone: "auto",
    forecast_days: "5",
    temperature_unit: unit,
  });
  const response = await fetch(`${FORECAST_API}?${params}`);
  if (!response.ok) throw new Error(`Open-Meteo answered ${response.status}`);
  const data = await response.json();

  await save("weatherCache", { key, fetchedAt: Date.now(), data });
  return data;
}

function render(location, data) {
  const unit = data.current_units?.temperature_2m ?? "°C";
  const [icon, text] = describe(data.current.weather_code);

  document.getElementById("weather-icon").textContent = icon;
  document.getElementById("weather-temp").textContent = `${Math.round(data.current.temperature_2m)}${unit}`;
  document.getElementById("weather-place").textContent = `${location.name} · ${text}`;

  const list = document.getElementById("forecast");
  list.replaceChildren(
    ...data.daily.time.map((date, i) => {
      const [dayIcon, dayText] = describe(data.daily.weather_code[i]);
      const weekday = i === 0 ? "Today"
        : new Date(`${date}T12:00`).toLocaleDateString("en-GB", { weekday: "short" });
      const li = document.createElement("li");
      li.title = dayText;
      li.innerHTML = `<span class="day"></span><span class="ico"></span>
        <span class="max"></span> <span class="min"></span>`;
      li.querySelector(".day").textContent = weekday;
      li.querySelector(".ico").textContent = dayIcon;
      li.querySelector(".max").textContent = `${Math.round(data.daily.temperature_2m_max[i])}°`;
      li.querySelector(".min").textContent = `${Math.round(data.daily.temperature_2m_min[i])}°`;
      return li;
    })
  );
}
