const KEY = "airbnb_last";                         // where we store the single latest URL
const AIRBNB_GUEST_MSG_RE = /^https?:\/\/www\.airbnb\.com\/guest\/messages\/(\d+)/i;
const API_BASE = "http://127.0.0.1:5000/api";       // your Flask backend

// Fires whenever Chrome adds a page to history
chrome.history.onVisited.addListener(async (item) => {
  const m = item.url.match(AIRBNB_GUEST_MSG_RE);
  if (m) {
    const threadId = m[1];

    // 1) Keep the chrome.storage.local entry (optional)
    await chrome.storage.local.set({ [KEY]: threadId });

    // 2) Push it to your backend so App.jsx can fetch it
    fetch(`${API_BASE}/current-thread`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ threadId })
    }).catch(console.error);

    console.log("Updated threadId:", threadId);
  }
});