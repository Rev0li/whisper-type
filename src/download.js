// Download window — TICKET-09
// Écoute sidecar-msg pour afficher la progression du téléchargement du modèle.

const subtitle    = document.getElementById('subtitle');
const modelName   = document.getElementById('model-name');
const sizeHint    = document.getElementById('size-hint');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const fileCounter  = document.getElementById('file-counter');
const fileLabel    = document.getElementById('file-label');
const retryBtn     = document.getElementById('retry');

const MODEL_SIZES_MB = {
    tiny: 75, base: 141, small: 461, medium: 1530, large: 3100,
};

function setIndeterminate(on) {
    if (on) {
        progressFill.classList.add('indeterminate');
        progressFill.style.width = '';
    } else {
        progressFill.classList.remove('indeterminate');
    }
}

function setError(msg) {
    subtitle.textContent = 'Erreur de téléchargement';
    progressText.textContent = msg;
    fileLabel.textContent = '';
    fileCounter.textContent = '';
    setIndeterminate(false);
    progressFill.style.width = '0%';
    retryBtn.style.display = 'block';
}

window.__TAURI__.event.listen('sidecar-msg', (event) => {
    try {
        const msg = JSON.parse(event.payload);

        switch (msg.status) {
            case 'model_missing':
                modelName.textContent = msg.model || 'small';
                const mb = MODEL_SIZES_MB[msg.model] || msg.size_mb || '?';
                sizeHint.textContent = `~${mb} MB`;
                subtitle.textContent = 'Téléchargement du modèle...';
                retryBtn.style.display = 'none';
                setIndeterminate(true);
                break;

            case 'downloading':
                subtitle.textContent = 'Téléchargement en cours...';
                setIndeterminate(true);
                break;

            case 'download_progress': {
                const pct = msg.percent ?? 0;
                setIndeterminate(false);
                progressFill.style.width = pct + '%';
                progressText.textContent = pct + '%';
                if (msg.file)    fileLabel.textContent = msg.file;
                if (msg.total)   fileCounter.textContent = `${msg.current || 0}/${msg.total} fichiers`;
                break;
            }

            case 'model_ready':
                subtitle.textContent = 'Modèle prêt !';
                setIndeterminate(false);
                progressFill.style.width = '100%';
                progressText.textContent = '100%';
                fileLabel.textContent = '';
                // La fenêtre est fermée par Rust (handle_download_events)
                break;

            case 'download_error':
                setError(msg.error || 'Erreur inconnue');
                break;
        }
    } catch (_) { /* ignore */ }
});

retryBtn.addEventListener('click', async () => {
    retryBtn.style.display = 'none';
    subtitle.textContent = 'Nouvelle tentative...';
    progressText.textContent = 'Connexion...';
    fileLabel.textContent = '';
    setIndeterminate(true);
    try {
        await window.__TAURI__.core.invoke('retry_download');
    } catch (e) {
        setError('Impossible de relancer : ' + e);
    }
});
