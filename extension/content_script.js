/**
 * Content script — runs on every page, watches text inputs/textareas/
 * contenteditable elements for typing or pasting, and shows an inline
 * warning banner if Redactive flags the content as risky.
 *
 * IMPORTANT DESIGN NOTE (fixed after real-world testing on Gmail):
 * Sites like Gmail use a contenteditable compose box that gets rebuilt
 * internally as you type — Google's own JS frequently replaces the
 * underlying DOM node. An earlier version of this script tracked one
 * warning banner per field element (via WeakMap), which meant that once
 * Gmail swapped out the element, the old banner became orphaned — nothing
 * left pointing to it ever told it to disappear, so it stuck around even
 * after the risky text was deleted.
 *
 * Fix: use a single shared banner for the whole page instead of one per
 * field. It's cleared optimistically the instant new typing starts, and
 * only re-shown if the fresh analysis says the (possibly new) field is
 * still risky. This means at most one warning is ever on screen, and it
 * can never go stale by pointing at a element that no longer matters.
 */

const MIN_LENGTH = 15;
const DEBOUNCE_MS = 1200;

let debounceTimer = null;
let lastAnalyzedText = "";
let currentField = null;
let banner = null;

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

function ensureBanner() {
  if (banner && document.body.contains(banner)) return banner;
  banner = document.createElement("div");
  banner.style.cssText = `
    position: fixed;
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
    display: none;
  `;
  document.body.appendChild(banner);
  return banner;
}

function hideBanner() {
  if (banner) banner.style.display = "none";
}

function showBanner(el, result) {
  if (!result || result.risk_score < 40) {
    hideBanner();
    return;
  }

  const b = ensureBanner();
  b.textContent = `⚠️ Redactive: risk ${result.risk_score}/100 — ${result.llm_review?.explanation || "sensitive content detected"}`;

  const rect = el.getBoundingClientRect();
  b.style.left = `${rect.left}px`;
  b.style.top = `${rect.bottom + 4}px`;
  b.style.display = "block";
}

function analyzeField(el) {
  const text = getFieldText(el);

  if (text.length < MIN_LENGTH) {
    hideBanner();
    lastAnalyzedText = text;
    return;
  }
  if (text === lastAnalyzedText) return;
  lastAnalyzedText = text;

  chrome.runtime.sendMessage({ type: "ANALYZE_TEXT", text }, (response) => {
    if (chrome.runtime.lastError) return; // extension context invalidated, page navigated, etc.
    if (!response) return;
    if (response.error) {
      console.warn("[Redactive]", response.error);
      return;
    }
    // Only show if this field is still the one the user is actively in —
    // avoids a slow response showing up over a field the user already left.
    if (currentField === el) showBanner(el, response.result);
  });
}

function handleEvent(e) {
  const el = e.target;
  if (!isTextField(el)) return;

  currentField = el;
  // Optimistic clear: hide any stale warning the instant new typing starts,
  // rather than waiting for the debounced re-analysis to catch up.
  hideBanner();

  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => analyzeField(el), DEBOUNCE_MS);
}

document.addEventListener("input", handleEvent, true);
document.addEventListener("paste", (e) => {
  const el = e.target;
  if (!isTextField(el)) return;
  // Paste fires before the field's value updates, so wait a tick.
  setTimeout(() => handleEvent(e), 50);
}, true);

// Clear the banner whenever focus leaves a text field entirely.
document.addEventListener(
  "focusout",
  (e) => {
    if (isTextField(e.target)) {
      currentField = null;
      hideBanner();
    }
  },
  true
);

// Also hide on scroll/resize since the banner's position is calculated
// once at show-time and won't track the field if the page moves.
window.addEventListener("scroll", hideBanner, true);
window.addEventListener("resize", hideBanner);