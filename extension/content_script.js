/**
 * Content script — runs on every page, watches text inputs/textareas/
 * contenteditable elements for typing or pasting, and shows an inline
 * warning banner if Redactive flags the content as risky.
 *
 * Deliberately conservative about when it actually calls the API:
 * - Debounces 1200ms after the user stops typing (not every keystroke —
 *   both to respect the backend's rate limit and to avoid flooding Groq
 *   with a request per character).
 * - Skips text under MIN_LENGTH chars (not worth analyzing "hi").
 * - Skips re-analyzing text that hasn't changed since the last check.
 */

const MIN_LENGTH = 15;
const DEBOUNCE_MS = 1200;

const debounceTimers = new WeakMap();
const lastAnalyzedText = new WeakMap();
const activeWarnings = new WeakMap();

function getFieldText(el) {
  if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") return el.value;
  if (el.isContentEditable) return el.innerText;
  return "";
}

function isTextField(el) {
  if (!el) return false;
  if (el.tagName === "TEXTAREA") return true;
  if (el.tagName === "INPUT") {
    const type = (el.getAttribute("type") || "text").toLowerCase();
    return ["text", "search", "email", "url"].includes(type);
  }
  return el.isContentEditable === true;
}

function removeWarning(el) {
  const existing = activeWarnings.get(el);
  if (existing) {
    existing.remove();
    activeWarnings.delete(el);
  }
}

function showWarning(el, result) {
  removeWarning(el);

  if (!result || result.risk_score < 40) return;

  const banner = document.createElement("div");
  banner.textContent = `⚠️ Redactive: risk ${result.risk_score}/100 — ${result.llm_review?.explanation || "sensitive content detected"}`;
  banner.style.cssText = `
    position: absolute;
    z-index: 2147483647;
    background: #fff3cd;
    color: #664d03;
    border: 1px solid #ffe69c;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    font-family: -apple-system, sans-serif;
    max-width: 340px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    pointer-events: none;
  `;

  const rect = el.getBoundingClientRect();
  banner.style.left = `${window.scrollX + rect.left}px`;
  banner.style.top = `${window.scrollY + rect.bottom + 4}px`;

  document.body.appendChild(banner);
  activeWarnings.set(el, banner);
}

function analyzeField(el) {
  const text = getFieldText(el);

  if (text.length < MIN_LENGTH) {
    removeWarning(el);
    return;
  }
  if (lastAnalyzedText.get(el) === text) return;
  lastAnalyzedText.set(el, text);

  chrome.runtime.sendMessage({ type: "ANALYZE_TEXT", text }, (response) => {
    if (chrome.runtime.lastError) return; // extension context invalidated, page navigated, etc.
    if (!response) return;
    if (response.error) {
      console.warn("[Redactive]", response.error);
      return;
    }
    showWarning(el, response.result);
  });
}

function scheduleAnalysis(el) {
  const existing = debounceTimers.get(el);
  if (existing) clearTimeout(existing);
  debounceTimers.set(el, setTimeout(() => analyzeField(el), DEBOUNCE_MS));
}

function handleEvent(e) {
  const el = e.target;
  if (!isTextField(el)) return;
  scheduleAnalysis(el);
}

document.addEventListener("input", handleEvent, true);
document.addEventListener("paste", (e) => {
  const el = e.target;
  if (!isTextField(el)) return;
  // Paste fires before the field's value updates, so wait a tick.
  setTimeout(() => scheduleAnalysis(el), 50);
}, true);

// Clean up warnings when the field loses focus or the user clears it.
document.addEventListener("blur", (e) => {
  const el = e.target;
  if (isTextField(el) && getFieldText(el).length === 0) removeWarning(el);
}, true);