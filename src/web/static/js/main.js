/* ==========================================================================
   ESP32-Lab — initialisation
   ========================================================================== */

async function loadVersion() {
    try {
        const health = await apiGet("/api/health");
        const label = document.getElementById("app-version");
        if (label && health.version) {
            label.textContent = "v" + health.version;
        }
        const portLabel = document.getElementById("app-port");
        // Port réellement utilisé par le serveur (peut différer de 8765 s'il
        // était occupé). Sinon, le port de la page.
        const port = health.port || window.location.port;
        if (portLabel && port) {
            portLabel.textContent = "port " + port;
        }
    } catch (error) {
        /* La version est purement informative : on ignore l'échec. */
    }
}

async function initialize() {
    initTabs();
    loadVersion();

    setStatus("Initialisation...");

    // Registre (noms) et historique d'abord : ils alimentent les noms de
    // cartes affichés partout.
    await loadDevices();
    await loadHistory();
    await loadDevices();   // ré-affiche avec le nombre de scans

    // Vide par défaut...
    await loadInventory(null);

    // ...puis détection des ports : si une carte est connectée ET déjà
    // scannée (n° de série USB = MAC connue en base), on affiche ses infos ;
    // sinon la vue reste vide.
    await loadPorts();

    if (statusElement.textContent === "Initialisation...") {
        setStatus("Prêt.");
    }
}

/* Ferme la modale historique en cliquant en dehors du contenu. */
window.addEventListener("click", event => {
    const modal = document.getElementById("history-modal");
    if (event.target === modal) {
        closeDeviceHistory();
    }
});

initialize();
