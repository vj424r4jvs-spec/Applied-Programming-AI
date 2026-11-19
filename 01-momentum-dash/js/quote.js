// Daily quote: the same quote all day, a different one tomorrow.
// Quotes come from the bundled data/quotes.json, so this works offline and
// needs no API key.

import { todayKey } from "./storage.js";

export async function showDailyQuote() {
  const response = await fetch("data/quotes.json");
  const quotes = await response.json();

  const quote = quotes[dayNumber() % quotes.length];
  document.getElementById("quote-text").textContent = `“${quote.text}”`;
  document.getElementById("quote-author").textContent = quote.author;
}

// Days since 1 Jan 1970 in local time. Goes up by exactly one every midnight,
// so stepping through the list gives every quote before repeating one.
function dayNumber() {
  const [y, m, d] = todayKey().split("-").map(Number);
  return Math.floor(Date.UTC(y, m - 1, d) / 86_400_000);
}
