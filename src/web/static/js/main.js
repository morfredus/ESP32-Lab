/* ==========================================================================
   ESP32-Lab — initialisation
   ========================================================================== */

async function initialize() {
    initTabs();

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
