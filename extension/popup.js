const input = document.getElementById("apiKey");
const status = document.getElementById("status");
const saveBtn = document.getElementById("save");

// Pre-fill with the currently saved key (if any) on popup open.
chrome.storage.local.get("redactiveApiKey", ({ redactiveApiKey }) => {
  if (redactiveApiKey) input.value = redactiveApiKey;
});

saveBtn.addEventListener("click", () => {
  const key = input.value.trim();

  if (!key) {
    status.textContent = "Enter a key first.";
    status.className = "err";
    return;
  }

  chrome.storage.local.set({ redactiveApiKey: key }, () => {
    status.textContent = "Saved.";
    status.className = "ok";
    setTimeout(() => (status.textContent = ""), 2000);
  });
});