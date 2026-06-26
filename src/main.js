// Settings UI — sera connecté au backend Tauri (invoke) dans TICKET-08.
// Pour l'instant : lecture/écriture locale en attendant l'IPC.

const modelEl = document.getElementById("model");
const languageEl = document.getElementById("language");
const hotkeyEl = document.getElementById("hotkey");
const saveBtn = document.getElementById("save");
const statusEl = document.getElementById("status");

// Capture du raccourci clavier
hotkeyEl.addEventListener("keydown", (e) => {
  e.preventDefault();
  const parts = [];
  if (e.metaKey || e.key === "Meta") parts.push("SUPER");
  if (e.ctrlKey) parts.push("CTRL");
  if (e.shiftKey) parts.push("SHIFT");
  if (e.altKey) parts.push("ALT");
  const key = e.key;
  if (!["Control", "Shift", "Alt", "Meta"].includes(key)) {
    parts.push(key === "`" ? "grave" : key.toUpperCase());
  }
  if (parts.length > 1) hotkeyEl.value = parts.join("+");
});

saveBtn.addEventListener("click", () => {
  // TODO TICKET-08 : invoke Tauri command "save_config"
  statusEl.textContent = "Sauvegardé ✓";
  setTimeout(() => { statusEl.textContent = ""; }, 2000);
});
