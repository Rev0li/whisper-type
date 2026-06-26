const modelEl    = document.getElementById('model');
const languageEl = document.getElementById('language');
const hotkeyEl   = document.getElementById('hotkey');
const saveBtn    = document.getElementById('save');
const statusEl   = document.getElementById('status');

// ─── Chargement de la config au démarrage ─────────────────────────────────

async function loadSettings() {
    try {
        const cfg = await window.__TAURI__.core.invoke('get_settings');
        modelEl.value    = cfg.model    || 'small';
        languageEl.value = cfg.language || 'fr';
        hotkeyEl.value   = cfg.hotkey   || 'SUPER+grave';
    } catch (e) {
        console.warn('[settings] load failed:', e);
    }
}

loadSettings();

// ─── Capture du raccourci clavier ─────────────────────────────────────────

hotkeyEl.addEventListener('keydown', (e) => {
    e.preventDefault();
    const parts = [];
    if (e.metaKey || e.key === 'Meta') parts.push('SUPER');
    if (e.ctrlKey  && e.key !== 'Control') parts.push('CTRL');
    if (e.shiftKey && e.key !== 'Shift')   parts.push('SHIFT');
    if (e.altKey   && e.key !== 'Alt')     parts.push('ALT');
    const key = e.key;
    if (!['Control', 'Shift', 'Alt', 'Meta'].includes(key)) {
        parts.push(key === '`' ? 'grave' : key.toUpperCase());
    }
    if (parts.length > 1) hotkeyEl.value = parts.join('+');
});

// ─── Sauvegarde ───────────────────────────────────────────────────────────

saveBtn.addEventListener('click', async () => {
    const hotkey = hotkeyEl.value.trim() || 'SUPER+grave';

    saveBtn.disabled = true;
    statusEl.textContent = 'Enregistrement...';

    try {
        await window.__TAURI__.core.invoke('save_settings', {
            settings: {
                model:    modelEl.value,
                language: languageEl.value,
                hotkey,
            },
        });
        statusEl.textContent = 'Sauvegardé ✓';
    } catch (e) {
        statusEl.textContent = `Erreur : ${e}`;
        console.error('[settings] save_settings:', e);
    } finally {
        saveBtn.disabled = false;
        setTimeout(() => { statusEl.textContent = ''; }, 2500);
    }
});
