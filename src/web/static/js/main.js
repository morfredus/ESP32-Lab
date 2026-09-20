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
    } catch (error) {
        /* La version est purement informative : on ignore l'échec. */
    }
}

async function initialize() {
    initTabs();
    loadVersion();

    setStatus("Initialisation...");

    await loadPorts();
    await loadInventory();
    // L'historique doit être chargé avant les cartes : le tableau des cartes
    // affiche le nombre de scans par MAC (issu de l'historique).
    await loadHistory();
    await loadDevices();

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
