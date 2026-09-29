// Elcaro IPI Guard — popup.
// Opens the pane, remembers the rail preference.

const $ = (id) => document.getElementById(id);

chrome.storage.local.get(["rail"], ({ rail }) => {
  $("rail").value = rail || "engine";
});

$("rail").addEventListener("change", (e) => {
  chrome.storage.local.set({ rail: e.target.value });
});
