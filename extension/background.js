/**
 * Background service worker.
 *
 * Why the API call happens here instead of in content_script.js: content
 * scripts run in the context of the page they're injected into, and are
 * subject to that page's CORS/CSP restrictions — a page like Gmail could
 * block outgoing fetches entirely. Background service workers, with
 * host_permissions declared in the manifest, aren't subject to that same
 * restriction. So the flow is: content script sends a message here,
 * background does the real network call, sends the result back.
 */

const API_URL = "https://redactive.onrender.com/analyze";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "ANALYZE_TEXT") return;

  (async () => {
    try {
      const { redactiveApiKey } = await chrome.storage.local.get("redactiveApiKey");

      if (!redactiveApiKey) {
        sendResponse({ error: "No API key set. Click the extension icon to add one." });
        return;
      }

      const res = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": redactiveApiKey,
        },
        body: JSON.stringify({ text: message.text }),
      });

      if (res.status === 401) {
        sendResponse({ error: "Invalid API key. Check the key in the extension popup." });
        return;
      }
      if (res.status === 429) {
        sendResponse({ error: "Rate limit hit — slow down a bit." });
        return;
      }
      if (!res.ok) {
        sendResponse({ error: `Unexpected error (status ${res.status}).` });
        return;
      }

      const data = await res.json();
      sendResponse({ result: data });
    } catch (err) {
      sendResponse({ error: `Network error: ${err.message}` });
    }
  })();

  // Required for async sendResponse in Manifest V3 service workers.
  return true;
});