const { listen } = window.__TAURI__.event;

const container = document.getElementById('log-container');
const emptyState = document.getElementById('empty-state');
const btnClear = document.getElementById('btn-clear');
const btnScroll = document.getElementById('btn-scroll');

let autoScroll = true;

function classForLine(text) {
  if (/\[ERROR\]/.test(text)) return 'error';
  if (/\[WARNING\]|\[WARN\]/.test(text)) return 'warn';
  if (/\[INFO\]/.test(text)) return 'info';
  return '';
}

function appendLine(text) {
  if (emptyState) emptyState.remove();

  const div = document.createElement('div');
  div.className = 'log-line ' + classForLine(text);
  div.textContent = text;
  container.appendChild(div);

  if (autoScroll) container.scrollTop = container.scrollHeight;
}

listen('sidecar-log', (event) => {
  appendLine(event.payload);
});

btnClear.addEventListener('click', () => {
  container.innerHTML = '';
});

btnScroll.addEventListener('click', () => {
  autoScroll = !autoScroll;
  btnScroll.textContent = `Auto-scroll: ${autoScroll ? 'ON' : 'OFF'}`;
  if (autoScroll) container.scrollTop = container.scrollHeight;
});
