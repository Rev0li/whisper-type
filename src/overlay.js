// Overlay TICKET-07 : écoute sidecar-msg, gère sa propre visibilité + animation.
// Nécessite withGlobalTauri: true dans tauri.conf.json.

const body = document.body;
const label = document.getElementById('label');

function getWin() {
  return window.__TAURI__.window.getCurrentWindow();
}

async function positionBottomRight() {
  try {
    const { PhysicalPosition } = window.__TAURI__.dpi;
    const win = getWin();
    // window.screen donne les dimensions de l'écran physique.
    // Le scale factor peut être > 1 sur les écrans HiDPI.
    const scale = window.devicePixelRatio || 1;
    const x = Math.round((window.screen.width - 208) * scale);
    const y = Math.round((window.screen.height - 90) * scale);
    await win.setPosition(new PhysicalPosition(x, y));
  } catch (e) {
    console.warn('[overlay] positionBottomRight:', e);
  }
}

async function showRecording() {
  body.className = 'recording';
  label.textContent = 'Recording...';
  await positionBottomRight();
  await getWin().show();
}

async function showTranscribing() {
  body.className = 'transcribing';
  label.textContent = 'Transcribing...';
  // La fenêtre est déjà visible depuis showRecording ; on change juste l'état.
}

async function hideOverlay() {
  await getWin().hide();
  // Reset visuel pour la prochaine ouverture.
  body.className = 'recording';
  label.textContent = 'Recording...';
}

// Écoute les events globaux émis par Rust (tous les états sidecar).
window.__TAURI__.event.listen('sidecar-msg', (event) => {
  try {
    const msg = JSON.parse(event.payload);
    switch (msg.status) {
      case 'recording':     showRecording();    break;
      case 'transcribing':  showTranscribing(); break;
      case 'done':          hideOverlay();      break;
    }
  } catch (_) { /* JSON invalide ou status inconnu : ignorer */ }
});
