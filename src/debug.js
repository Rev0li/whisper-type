const { listen } = window.__TAURI__.event;
const { invoke } = window.__TAURI__.core;

const container = document.getElementById('log-container');
const emptyState = document.getElementById('empty-state');
const btnClear = document.getElementById('btn-clear');
const btnScroll = document.getElementById('btn-scroll');

let autoScroll = true;

function classForLine(text) {
  if (/\[ERROR\]|\[PY ERR\]/.test(text)) return 'error';
  if (/\[WARNING\]|\[WARN\]/.test(text)) return 'warn';
  if (/\[INFO\]|\[PY\]/.test(text)) return 'info';
  return '';
}

function appendLine(text, cls) {
  if (emptyState && emptyState.parentNode) emptyState.remove();

  const div = document.createElement('div');
  div.className = 'log-line ' + (cls ?? classForLine(text));
  div.textContent = text;
  container.appendChild(div);

  if (autoScroll) container.scrollTop = container.scrollHeight;
}

// Rejouer l'historique bufferisé côté Rust au moment de l'ouverture de la fenêtre.
invoke('get_logs').then((lines) => {
  lines.forEach(line => appendLine(line));
}).catch(() => {});

// Sidecar stdout + stderr via l'event unifié.
listen('debug-line', (event) => {
  appendLine(event.payload);
});

// Logs Rust/Tauri (tauri-plugin-log Webview target).
listen('log://log', (event) => {
  const { level, message } = event.payload;
  // level: 1=Error 2=Warn 3=Info 4=Debug 5=Trace
  const cls = level === 1 ? 'error' : level === 2 ? 'warn' : 'info';
  appendLine(`[RUST] ${message}`, cls);
});

btnClear.addEventListener('click', () => {
  container.innerHTML = '';
});

btnScroll.addEventListener('click', () => {
  autoScroll = !autoScroll;
  btnScroll.textContent = `Auto-scroll: ${autoScroll ? 'ON' : 'OFF'}`;
  if (autoScroll) container.scrollTop = container.scrollHeight;
});
